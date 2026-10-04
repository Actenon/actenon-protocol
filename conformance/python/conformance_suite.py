"""Actenon Protocol — Conformance Suite (Python).

This suite proves that the Python reference implementation conforms to the
Actenon protocol v1.x. It runs:

1. Canonicalisation vectors (valid + invalid).
2. Schema validation against all artefact vectors (proof, receipt, refusal).
3. Identifier validation (canonical prefixes, aliases, forbidden prefixes).
4. Refusal catalogue (alias resolution, disclosure policy, retryability).
5. Execution-mode distinction (brokered vs resource_owned).

Run with: `python -m pytest conformance/python/ -v`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from actenon_protocol import (
    CANONICALISATION_PROFILE,
    DETAILED_CODES,
    FORBIDDEN_PREFIXES,
    PREFIXES,
    PROTOCOL_VERSION,
    PUBLIC_SAFE_CODES,
    CanonicalisationError,
    DisclosurePolicy,
    ExecutionMode,
    ExecutionOutcome,
    RefusalCode,
    canonicalize_bytes,
    canonicalize_json,
    generate_identifier,
    is_valid_identifier,
    normalise_identifier,
    refusal_to_disclosed_code,
    refusal_to_internal_code,
    refusal_to_retryable,
    resolve_alias,
)
from actenon_protocol.types import (
    AuthorisedExecutionIntent,
    ExecutionProof,
    ExecutionReceipt,
    ExecutionRefusal,
)

# Resolve paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VECTORS_DIR = REPO_ROOT / "conformance" / "vectors"
SCHEMAS_DIR = REPO_ROOT / "schemas"


# ---------- helpers ----------


def _load_vector(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_vectors(category: str, sub: str | None = None) -> list[tuple[str, dict]]:
    """Load all vectors in a category, optionally filtered by subdirectory."""
    base = VECTORS_DIR / category
    if sub:
        base = base / sub
    out = []
    for path in sorted(base.glob("*.json")):
        out.append((path.name, _load_vector(path)))
    return out


# ---------- 1. Canonicalisation ----------


class TestCanonicalisationValid:
    """Valid canonicalisation vectors — must produce the exact expected bytes."""

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("canonicalisation", "valid"),
        ids=[v[0] for v in _load_vectors("canonicalisation", "valid")],
    )
    def test_valid_canonicalisation(self, vector_name: str, vector: dict):
        input_value = vector["input"]
        expected = vector["expected_canonical"]
        actual = canonicalize_json(input_value)
        assert actual == expected, f"vector {vector_name!r}: expected {expected!r}, got {actual!r}"

    def test_returns_str_and_bytes_match(self):
        """canonicalize_json returns str; canonicalize_bytes returns UTF-8 of same."""
        for vector_name, vector in _load_vectors("canonicalisation", "valid"):
            input_value = vector["input"]
            expected = vector["expected_canonical"]
            bytes_form = canonicalize_bytes(input_value)
            assert bytes_form == expected.encode("utf-8"), (
                f"vector {vector_name!r}: bytes form does not match expected UTF-8"
            )


class TestCanonicalisationInvalid:
    """Invalid canonicalisation vectors — must raise CanonicalisationError."""

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("canonicalisation", "invalid"),
        ids=[v[0] for v in _load_vectors("canonicalisation", "invalid")],
    )
    def test_invalid_canonicalisation(self, vector_name: str, vector: dict):
        # Some vectors use input_python_only (the JSON form is illustrative
        # because the input is a Python-specific type that has no JSON form).
        # Those are tested separately in test_invalid_canonicalisation_python_only.
        if "input_python_only" in vector:
            pytest.skip(f"vector {vector_name!r} uses input_python_only; tested separately")
        # Vectors that only have input_json (not "input") are tested via
        # the conformance CLI and the test_float_* tests below.
        if "input" not in vector:
            pytest.skip(
                f"vector {vector_name!r} has no 'input' field (uses input_json or is Python-only)"
            )
        input_value = vector["input"]
        with pytest.raises(CanonicalisationError):
            canonicalize_json(input_value)

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("canonicalisation", "invalid"),
        ids=[v[0] for v in _load_vectors("canonicalisation", "invalid")],
    )
    def test_invalid_canonicalisation_json_vectors(self, vector_name: str, vector: dict):
        """Test invalid vectors that use input_json (floats, NaN, Infinity, etc.).

        These vectors provide a raw JSON string that, when parsed, produces
        a value containing floats or other rejected types.
        """
        input_json = vector.get("input_json")
        if input_json is None:
            pytest.skip(f"vector {vector_name!r} has no input_json field")
        # Parse the JSON string. For NaN/Infinity, json.loads may fail
        # (they're not valid JSON). In that case, we test the Python
        # float directly.
        try:
            parsed = json.loads(input_json)
        except json.JSONDecodeError:
            # NaN, Infinity, -Infinity are not valid JSON. Test the
            # Python float directly.
            if input_json == "NaN":
                parsed = float("nan")
            elif input_json == "Infinity":
                parsed = float("inf")
            elif input_json == "-Infinity":
                parsed = float("-inf")
            else:
                pytest.skip(f"vector {vector_name!r}: cannot parse {input_json!r}")
        with pytest.raises((CanonicalisationError, TypeError)):
            canonicalize_json(parsed)

    def test_invalid_canonicalisation_python_only(self):
        """Python-specific invalid inputs that have no JSON form.

        Note: tuples ARE accepted (serialised as arrays, matching the
        actenon-kernel reference). Sets, non-string dict keys, and bytes
        are rejected.
        """
        # Set (not a JSON type)
        with pytest.raises(CanonicalisationError):
            canonicalize_json({1, 2, 3})
        # Non-string dict key (int)
        with pytest.raises(CanonicalisationError):
            canonicalize_json({1: "a", 2: "b"})
        # Non-string dict key (tuple)
        with pytest.raises(CanonicalisationError):
            canonicalize_json({(1, 2): "a"})
        # bytes (not a JSON type)
        with pytest.raises(CanonicalisationError):
            canonicalize_json(b"hello")

        # Custom object (not a JSON type)
        class Custom:
            pass

        with pytest.raises(CanonicalisationError):
            canonicalize_json(Custom())

    def test_floats_rejected_at_all_levels(self):
        """Floats must be rejected at top level, in objects, in arrays, and nested."""
        with pytest.raises(CanonicalisationError):
            canonicalize_json(3.14)
        with pytest.raises(CanonicalisationError):
            canonicalize_json({"amount": 19.99})
        with pytest.raises(CanonicalisationError):
            canonicalize_json([1, 2, 3.14, 4])
        with pytest.raises(CanonicalisationError):
            canonicalize_json({"outer": {"inner": {"value": 0.1}}})

    def test_non_string_keys_rejected(self):
        with pytest.raises(CanonicalisationError):
            canonicalize_json({1: "a", 2: "b"})

    def test_unsupported_types_rejected(self):
        class Custom:
            pass

        with pytest.raises(CanonicalisationError):
            canonicalize_json(Custom())

    def test_int_subclasses_serialise_as_plain_integers(self):
        """int subclasses must emit their integer value, never their __str__.

        On Python 3.10, str(HTTPStatus.OK) is "HTTPStatus.OK", so the
        canonical form was not even JSON and differed from 3.11+ ("200").
        A subclass overriding __str__ could inject arbitrary members.
        """
        import enum
        from http import HTTPStatus

        class Code(enum.IntEnum):
            REFUND = 7

        class Sneaky(int):
            def __str__(self):
                return '1,"injected":true'

            __repr__ = __str__

        assert canonicalize_json({"status": HTTPStatus.OK}) == '{"status":200}'
        assert canonicalize_json([Code.REFUND]) == "[7]"
        assert canonicalize_json({"a": Sneaky(1)}) == '{"a":1}'

    def test_str_subclass_cannot_change_key_order(self):
        """Key order comes from the UTF-8 bytes of the string data itself."""

        class Liar(str):
            def encode(self, *args, **kwargs):
                return b"\x00" + str.encode(self, *args, **kwargs)

        assert canonicalize_json({"a": 1, Liar("b"): 2}) == canonicalize_json({"a": 1, "b": 2})
        assert canonicalize_json({Liar("b"): 2, "a": 1}) == '{"a":1,"b":2}'


class TestCanonicalisationUnicodeAndOrdering:
    """Specific Unicode and key-ordering guarantees."""

    def test_non_ascii_not_u_escaped(self):
        """RFC 8785 §3.2.2 — non-ASCII characters are NOT \\u-escaped."""
        assert canonicalize_json("café") == '"café"'
        assert canonicalize_json("東京") == '"東京"'

    def test_key_order_utf8_byte(self):
        """Keys must be sorted by UTF-8 byte order, not codepoint order."""
        # 'Z' (U+005A = byte 0x5A) sorts before 'é' (U+00E9 = bytes 0xC3 0xA9)
        result = canonicalize_json({"é": 1, "Z": 2, "a": 3})
        assert result == '{"Z":2,"a":3,"é":1}'

    def test_control_chars_escaped(self):
        """Control characters must be escaped."""
        assert canonicalize_json("a\tb") == '"a\\tb"'
        assert canonicalize_json("a\nb") == '"a\\nb"'
        assert canonicalize_json("a\rb") == '"a\\rb"'
        assert canonicalize_json("a\u0000b") == '"a\\u0000b"'

    def test_empty_collections(self):
        assert canonicalize_json({}) == "{}"
        assert canonicalize_json([]) == "[]"

    def test_key_order_utf8_not_utf16(self):
        """U+E000..U+FFFF sort BEFORE astral keys (UTF-8 byte order).

        This is where the profile deviates from RFC 8785, which sorts by
        UTF-16 code units and would put the astral key first.
        """
        assert canonicalize_json({"\U0001f600": 2, "\ue000": 1}) == '{"\ue000":1,"\U0001f600":2}'
        assert canonicalize_json({"\U00010000": 2, "\uffff": 1}) == '{"\uffff":1,"\U00010000":2}'

    @pytest.mark.parametrize(
        "value",
        [
            "\ud800",
            "\udc00",
            "x\udbffy",
            "\ude00\ud83d",  # reversed pair: two unpaired surrogates
            {"k": "\udfff"},
            {"\ud800": 1},
            {chr(0xD800): 1, chr(0xD801): 2},
            [["\ud800"]],
        ],
    )
    def test_lone_surrogates_rejected(self, value):
        """Unpaired surrogates are not Unicode scalar values and have no
        UTF-8 encoding (§4.2): both entry points must raise
        CanonicalisationError, not UnicodeEncodeError, and must never
        return a string that cannot be encoded.
        """
        with pytest.raises(CanonicalisationError):
            canonicalize_json(value)
        with pytest.raises(CanonicalisationError):
            canonicalize_bytes(value)

    def test_lone_surrogates_from_json_escapes_rejected(self):
        """json.loads decodes "\\ud800" to a lone surrogate; it must not canonicalise."""
        with pytest.raises(CanonicalisationError):
            canonicalize_bytes(json.loads('{"s":"\\ud800"}'))

    def test_surrogate_pair_accepted(self):
        """A properly paired escape decodes to one astral scalar value."""
        assert canonicalize_bytes(json.loads('"\\ud83d\\ude00"')) == '"\U0001f600"'.encode()


# ---------- 2. Schema validation ----------


class TestSchemaValidation:
    """Validate all artefact vectors against the JSON Schemas."""

    @pytest.fixture(scope="class")
    @classmethod
    def schema_registry(cls):
        """Load all schemas into a jsonschema registry."""
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        schemas: dict[str, dict] = {}
        for path in SCHEMAS_DIR.glob("*.v1.json"):
            with path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            schemas[schema["$id"]] = schema

        def retrieve(uri: str):
            return Resource.from_contents(schemas[uri])

        registry = Registry(retrieve=retrieve)
        return {"schemas": schemas, "registry": registry, "Validator": Draft202012Validator}

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("proof", "valid"),
        ids=[v[0] for v in _load_vectors("proof", "valid")],
    )
    def test_valid_proof(self, schema_registry, vector_name: str, vector: dict):
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-proof:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        artefact = vector["artefact"]
        errors = list(validator.iter_errors(artefact))
        assert not errors, (
            f"vector {vector_name!r}: expected valid, got errors: {[e.message for e in errors]}"
        )

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("proof", "invalid"),
        ids=[v[0] for v in _load_vectors("proof", "invalid")],
    )
    def test_invalid_proof(self, schema_registry, vector_name: str, vector: dict):
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-proof:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        artefact = vector["artefact"]
        # JSON Schema enforces pattern + structure. The Identifier pattern
        # (^[a-z][a-z0-9_]*_[0-9a-f]{16,}$) does NOT enforce prefix-vs-alias
        # rules; that is enforced by the Python is_valid_identifier() helper.
        # So a vector like invalid_proof_id_prefix.v1.json (which uses a
        # forbidden prefix that DOES match the regex) passes JSON Schema
        # but fails is_valid_identifier(). We accept EITHER failure.
        schema_errors = list(validator.iter_errors(artefact))
        pydantic_error = False
        try:
            ExecutionProof(**artefact)
        except Exception:
            pydantic_error = True
        identifier_error = False
        proof_id = artefact.get("proof_id", "")
        if proof_id and not is_valid_identifier(proof_id):
            identifier_error = True
        assert schema_errors or pydantic_error or identifier_error, (
            f"vector {vector_name!r}: expected invalid (schema, pydantic, or identifier), "
            f"but all passed"
        )

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("receipt", "valid"),
        ids=[v[0] for v in _load_vectors("receipt", "valid")],
    )
    def test_valid_receipt(self, schema_registry, vector_name: str, vector: dict):
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-receipt:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        errors = list(validator.iter_errors(vector["artefact"]))
        assert not errors, f"vector {vector_name!r}: {[(e.message, e.json_path) for e in errors]}"

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("receipt", "invalid"),
        ids=[v[0] for v in _load_vectors("receipt", "invalid")],
    )
    def test_invalid_receipt(self, schema_registry, vector_name: str, vector: dict):
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-receipt:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        errors = list(validator.iter_errors(vector["artefact"]))
        assert errors, f"vector {vector_name!r}: expected invalid"

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("refusal", "valid"),
        ids=[v[0] for v in _load_vectors("refusal", "valid")],
    )
    def test_valid_refusal(self, schema_registry, vector_name: str, vector: dict):
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-refusal:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        errors = list(validator.iter_errors(vector["artefact"]))
        assert not errors, f"vector {vector_name!r}: {[(e.message, e.json_path) for e in errors]}"

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("refusal", "invalid"),
        ids=[v[0] for v in _load_vectors("refusal", "invalid")],
    )
    def test_invalid_refusal_schema(self, schema_registry, vector_name: str, vector: dict):
        """Note: some invalid refusal vectors are invalid due to disclosure-policy
        consistency, not pure schema violations. The schema check is a coarse
        filter; the disclosure-policy check is the fine filter (see TestRefusalDisclosure)."""
        from jsonschema import Draft202012Validator

        schema = schema_registry["schemas"]["urn:actenon:protocol:execution-refusal:v1"]
        validator = Draft202012Validator(schema, registry=schema_registry["registry"])
        artefact = vector["artefact"]
        # We accept either schema-invalid OR pydantic-invalid (disclosure-policy)
        schema_errors = list(validator.iter_errors(artefact))
        pydantic_error = False
        try:
            ExecutionRefusal(**artefact)
        except Exception:
            pydantic_error = True
        assert schema_errors or pydantic_error, (
            f"vector {vector_name!r}: expected invalid (schema or pydantic), but both passed"
        )


# ---------- 3. Identifier validation ----------


class TestIdentifiers:
    def test_all_canonical_prefixes_accepted(self):
        for prefix in PREFIXES:
            ident = generate_identifier(prefix)
            assert is_valid_identifier(ident), f"generated {ident!r} should be valid"

    def test_canonical_prefixes_complete(self):
        assert (
            frozenset(
                {
                    "intent_",
                    "authz_",
                    "grant_",
                    "proof_",
                    "exec_",
                    "rcpt_",
                    "rful_",
                }
            )
            == PREFIXES
        )

    def test_aliases_accepted(self):
        # act_ → intent_
        assert is_valid_identifier("act_9f3c1a175e9b4d80")
        # pccb_ → proof_
        assert is_valid_identifier("pccb_9f3c1a175e9b4d80")

    def test_alias_normalisation(self):
        assert normalise_identifier("act_9f3c1a175e9b4d80") == "intent_9f3c1a175e9b4d80"
        assert normalise_identifier("pccb_9f3c1a175e9b4d80") == "proof_9f3c1a175e9b4d80"
        # Canonical identifiers normalise to themselves
        assert normalise_identifier("proof_9f3c1a175e9b4d80") == "proof_9f3c1a175e9b4d80"

    def test_forbidden_prefixes_rejected(self):
        for prefix in FORBIDDEN_PREFIXES:
            assert not is_valid_identifier(f"{prefix}abcdef0123456789"), (
                f"forbidden prefix {prefix!r} should be rejected"
            )

    def test_short_hex_rejected(self):
        assert not is_valid_identifier("grant_short")
        assert not is_valid_identifier("grant_9f3c1a175e9b4")

    def test_uppercase_hex_rejected(self):
        assert not is_valid_identifier("grant_9F3C1A175E9B4D80")

    def test_non_string_rejected(self):
        assert not is_valid_identifier(42)
        assert not is_valid_identifier(None)
        assert not is_valid_identifier(b"grant_abcdef0123456789")

    def test_generate_identifier_rejects_alias_prefix(self):
        with pytest.raises(ValueError):
            generate_identifier("act_")  # alias, not canonical

    def test_generate_identifier_rejects_forbidden_prefix(self):
        with pytest.raises(ValueError):
            generate_identifier("tenant_")

    def test_generate_identifier_rejects_short_hex(self):
        with pytest.raises(ValueError):
            generate_identifier("proof_", hex_length=8)

    def test_generated_identifier_is_unique(self):
        ids = {generate_identifier("proof_") for _ in range(100)}
        assert len(ids) == 100, "100 generations should produce 100 unique identifiers"


# ---------- 4. Refusal catalogue ----------


class TestRefusalCatalogue:
    def test_twenty_canonical_codes(self):
        assert len(list(RefusalCode)) == 22

    def test_all_codes_have_catalogue_entry(self):
        """Every canonical code has an entry in the catalogue YAML."""
        # The catalogue is the source of truth; the enum must match it.
        catalogue_codes = {
            entry["code"]
            for entry in __import__(
                "actenon_protocol.refusal_codes", fromlist=["_CATALOGUE"]
            )._CATALOGUE["codes"]
        }
        enum_codes = {code.value for code in RefusalCode}
        assert catalogue_codes == enum_codes, (
            f"catalogue and enum disagree. catalogue-only: {catalogue_codes - enum_codes}, "
            f"enum-only: {enum_codes - catalogue_codes}"
        )

    @pytest.mark.parametrize("policy", list(DisclosurePolicy))
    def test_disclosed_code_matches_catalogue_for_every_code(self, policy):
        """refusal_to_disclosed_code(code) is the catalogue's disclosed_code.

        Includes the PROOF_INVALID umbrella, whose internal_code is null in
        the catalogue: it used to fall through to OUTCOME_UNKNOWN, telling a
        public caller "execution may have happened" for an invalid proof.
        """
        from actenon_protocol.refusal_codes import all_codes

        for entry in all_codes():
            assert refusal_to_disclosed_code(entry["code"], policy) == entry["disclosed_code"], (
                entry["code"]
            )
            assert refusal_to_retryable(entry["code"]) is entry["retryable"], entry["code"]

    @pytest.mark.parametrize(
        "kernel_code,canonical",
        [
            # Emitted by actenon-kernel but absent from the catalogue, so they
            # disclosed as OUTCOME_UNKNOWN / retryable (E2E finding F12).
            ("SCHEMA_INVALID", "MALFORMED_REQUEST"),  # actenon/core/errors.py
            ("ESCROW_REFERENCE_MISSING", "MALFORMED_REQUEST"),  # protected_executor.py
            ("EXECUTION_FAILED", "OUTCOME_UNKNOWN"),  # executor raised; effect unknown
            ("POLICY_REFUSED", "POLICY_REFUSAL"),  # protected_executor.py default
        ],
    )
    def test_emitted_kernel_codes_are_catalogued(self, kernel_code, canonical):
        assert resolve_alias(kernel_code) == canonical

    @pytest.mark.parametrize("alias", sorted(__import__("actenon_protocol").COMPATIBILITY_ALIASES))
    def test_compatibility_aliases_disclose_like_their_canonical_code(self, alias):
        """Legacy kernel/permit codes must resolve BEFORE disclosure mapping.

        They used to miss the map and come out as OUTCOME_UNKNOWN with
        retryable=True: DUPLICATE_REPLAY, REVOKED and EXPIRED were told to
        retry although REPLAY_DETECTED / AUTHORITY_REVOKED / PROOF_EXPIRED
        are final. The trusted internal_code must be the canonical code,
        because the refusal schema's internal_code enum has no aliases.
        """
        from actenon_protocol.refusal_codes import all_codes

        canonical = resolve_alias(alias)
        entry = next(e for e in all_codes() if e["code"] == canonical)
        for policy in DisclosurePolicy:
            assert refusal_to_disclosed_code(alias, policy) == entry["disclosed_code"]
        assert refusal_to_retryable(alias) is entry["retryable"]
        assert refusal_to_internal_code(alias, DisclosurePolicy.PUBLIC) is None
        assert refusal_to_internal_code(alias, DisclosurePolicy.TRUSTED) == canonical

    def test_public_safe_codes_subset_of_detailed_or_umbrella(self):
        # PUBLIC_SAFE_CODES includes umbrella codes (like PROOF_INVALID) that
        # have internal_code=null in the catalogue. DETAILED_CODES only
        # includes codes with internal_code != null. So PUBLIC_SAFE_CODES
        # is NOT a subset of DETAILED_CODES — it includes the umbrellas.
        # Instead, every public-safe code is EITHER a detailed code OR
        # an umbrella code (internal_code=null in catalogue).
        catalogue = __import__("actenon_protocol.refusal_codes", fromlist=["_CATALOGUE"])._CATALOGUE
        umbrella_codes = {
            entry["code"] for entry in catalogue["codes"] if entry["internal_code"] is None
        }
        for code in PUBLIC_SAFE_CODES:
            assert code in DETAILED_CODES or code in umbrella_codes, (
                f"public-safe code {code!r} is neither detailed nor umbrella"
            )

    def test_alias_resolution_preserves_canonical(self):
        # Canonical codes resolve to themselves
        for code in RefusalCode:
            assert resolve_alias(code.value) == code.value

    def test_alias_resolution_for_kernel_codes(self):
        assert resolve_alias("PCCB_REQUIRED") == "PROOF_MISSING"
        assert resolve_alias("PCCB_EXPIRED") == "PROOF_EXPIRED"
        assert resolve_alias("DUPLICATE_REPLAY") == "REPLAY_DETECTED"
        assert resolve_alias("SIGNATURE_INVALID") == "SIGNATURE_INVALID"
        assert resolve_alias("ACTION_MISMATCH") == "ACTION_MISMATCH"
        assert resolve_alias("AUDIENCE_MISMATCH") == "AUDIENCE_MISMATCH"
        assert resolve_alias("INTENT_MISMATCH") == "PARAMETER_MISMATCH"
        assert resolve_alias("ACTION_HASH_MISMATCH") == "PARAMETER_MISMATCH"
        assert resolve_alias("SCOPE_CAPABILITY_MISMATCH") == "SCOPE_CAPABILITY_MISMATCH"
        assert resolve_alias("SCOPE_MODE_INVALID") == "SCOPE_MODE_INVALID"
        assert resolve_alias("TENANT_MISMATCH") == "TARGET_MISMATCH"
        assert resolve_alias("SUBJECT_MISMATCH") == "TARGET_MISMATCH"
        assert resolve_alias("PROOF_PAYLOAD_INVALID") == "MALFORMED_REQUEST"
        assert resolve_alias("NOT_ACTIVE") == "POLICY_REFUSAL"
        assert resolve_alias("REVOKED") == "AUTHORITY_REVOKED"
        assert resolve_alias("EXPIRED") == "PROOF_EXPIRED"
        assert resolve_alias("SCOPE_DENIED") == "POLICY_REFUSAL"
        assert resolve_alias("OUT_OF_SCOPE") == "POLICY_REFUSAL"
        assert resolve_alias("BUDGET_EXCEEDED") == "POLICY_REFUSAL"
        assert resolve_alias("RATE_LIMITED") == "POLICY_REFUSAL"
        assert resolve_alias("ENGINE_ERROR") == "OUTCOME_UNKNOWN"

    def test_alias_resolution_rejects_unknown(self):
        with pytest.raises(KeyError):
            resolve_alias("NOT_A_REAL_CODE")


class TestRefusalDisclosure:
    def test_signature_invalid_under_public_is_proof_invalid(self):
        # SIGNATURE_INVALID under PUBLIC policy → disclosed PROOF_INVALID, internal null
        disclosed = refusal_to_disclosed_code(
            RefusalCode.SIGNATURE_INVALID.value, DisclosurePolicy.PUBLIC
        )
        internal = refusal_to_internal_code(
            RefusalCode.SIGNATURE_INVALID.value, DisclosurePolicy.PUBLIC
        )
        assert disclosed == "PROOF_INVALID"
        assert internal is None

    def test_signature_invalid_under_trusted_keeps_detail(self):
        disclosed = refusal_to_disclosed_code(
            RefusalCode.SIGNATURE_INVALID.value, DisclosurePolicy.TRUSTED
        )
        internal = refusal_to_internal_code(
            RefusalCode.SIGNATURE_INVALID.value, DisclosurePolicy.TRUSTED
        )
        assert disclosed == "PROOF_INVALID"  # umbrella still in disclosed_code
        assert internal == "SIGNATURE_INVALID"  # detail in internal_code

    def test_proof_expired_is_safe_to_disclose(self):
        # PROOF_EXPIRED is safe to disclose publicly (the expiry is in the proof itself)
        disclosed = refusal_to_disclosed_code(
            RefusalCode.PROOF_EXPIRED.value, DisclosurePolicy.PUBLIC
        )
        assert disclosed == "PROOF_EXPIRED"

    def test_replay_detected_is_safe_to_disclose(self):
        disclosed = refusal_to_disclosed_code(
            RefusalCode.REPLAY_DETECTED.value, DisclosurePolicy.PUBLIC
        )
        assert disclosed == "REPLAY_DETECTED"

    def test_proof_not_yet_valid_is_safe_to_disclose(self):
        disclosed = refusal_to_disclosed_code(
            RefusalCode.PROOF_NOT_YET_VALID.value, DisclosurePolicy.PUBLIC
        )
        assert disclosed == "PROOF_NOT_YET_VALID"

    def test_audience_mismatch_under_public_is_proof_invalid(self):
        # AUDIENCE_MISMATCH leaks the verifier's identity — must collapse to PROOF_INVALID
        disclosed = refusal_to_disclosed_code(
            RefusalCode.AUDIENCE_MISMATCH.value, DisclosurePolicy.PUBLIC
        )
        assert disclosed == "PROOF_INVALID"

    def test_retryable_values(self):
        # Non-retryable
        for code in [
            RefusalCode.MALFORMED_REQUEST,
            RefusalCode.UNSUPPORTED_PROTOCOL_VERSION,
            RefusalCode.CANONICALISATION_FAILURE,
            RefusalCode.PROOF_MISSING,
            RefusalCode.PROOF_INVALID,
            RefusalCode.ISSUER_UNTRUSTED,
            RefusalCode.SIGNATURE_INVALID,
            RefusalCode.PROOF_EXPIRED,
            RefusalCode.AUDIENCE_MISMATCH,
            RefusalCode.TARGET_MISMATCH,
            RefusalCode.ACTION_MISMATCH,
            RefusalCode.PARAMETER_MISMATCH,
            RefusalCode.REPLAY_DETECTED,
            RefusalCode.AUTHORITY_REVOKED,
            RefusalCode.POLICY_REFUSAL,
            RefusalCode.PROVIDER_REFUSAL,
        ]:
            assert refusal_to_retryable(code.value) is False, f"{code} should not be retryable"
        # Retryable
        for code in [
            RefusalCode.PROOF_NOT_YET_VALID,
            RefusalCode.CREDENTIAL_UNAVAILABLE,
            RefusalCode.PROVIDER_FAILURE,
            RefusalCode.OUTCOME_UNKNOWN,
        ]:
            assert refusal_to_retryable(code.value) is True, f"{code} should be retryable"


class TestRefusalFactory:
    def test_from_internal_code_public(self):
        refusal = ExecutionRefusal.from_internal_code(
            refusal_id="rful_abcdef0123456789abcdef0123456789",
            internal_code="SIGNATURE_INVALID",
            execution_mode=ExecutionMode.BROKERED,
            refused_at="2026-07-21T12:00:00Z",
            policy=DisclosurePolicy.PUBLIC,
            proof_id="proof_abcdef0123456789abcdef0123456789",
            message="proof verification failed",
        )
        assert refusal.disclosed_code == "PROOF_INVALID"
        assert refusal.internal_code is None
        assert refusal.retryable is False

    def test_from_internal_code_trusted(self):
        refusal = ExecutionRefusal.from_internal_code(
            refusal_id="rful_abcdef0123456789abcdef0123456789",
            internal_code="SIGNATURE_INVALID",
            execution_mode=ExecutionMode.BROKERED,
            refused_at="2026-07-21T12:00:00Z",
            policy=DisclosurePolicy.TRUSTED,
            proof_id="proof_abcdef0123456789abcdef0123456789",
            message="signature verification failed",
        )
        assert refusal.disclosed_code == "PROOF_INVALID"
        assert refusal.internal_code == "SIGNATURE_INVALID"
        assert refusal.retryable is False

    def test_from_internal_code_proof_missing(self):
        refusal = ExecutionRefusal.from_internal_code(
            refusal_id="rful_abcdef0123456789abcdef0123456789",
            internal_code=None,  # PROOF_MISSING has no detail
            execution_mode=ExecutionMode.BROKERED,
            refused_at="2026-07-21T12:00:00Z",
            policy=DisclosurePolicy.PUBLIC,
        )
        assert refusal.disclosed_code == "PROOF_MISSING"
        assert refusal.internal_code is None
        assert refusal.retryable is False


class TestRefusalConformanceVectors:
    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("refusal", "valid"),
        ids=[v[0] for v in _load_vectors("refusal", "valid")],
    )
    def test_valid_refusal_pydantic(self, vector_name: str, vector: dict):
        """Valid refusal vectors must construct successfully via pydantic."""
        refusal = ExecutionRefusal(**vector["artefact"])
        assert refusal.protocol_version == vector["artefact"]["protocol_version"]

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("refusal", "invalid"),
        ids=[v[0] for v in _load_vectors("refusal", "invalid")],
    )
    def test_invalid_refusal_pydantic(self, vector_name: str, vector: dict):
        """Invalid refusal vectors must fail pydantic construction."""
        with pytest.raises((ValueError, TypeError)):
            ExecutionRefusal(**vector["artefact"])


# ---------- 5. Execution modes ----------


class TestExecutionModes:
    def test_both_modes_defined(self):
        assert ExecutionMode.BROKERED == "brokered"
        assert ExecutionMode.RESOURCE_OWNED == "resource_owned"

    def test_mode_is_explicit_on_every_artefact(self):
        """Every proof, receipt, refusal MUST carry execution_mode."""
        # This is enforced by the schemas (execution_mode is required).
        # This test verifies the conformance vectors all carry it.
        for cat in ["proof", "receipt", "refusal"]:
            for sub in ["valid"]:
                for vector_name, vector in _load_vectors(cat, sub):
                    if "artefact" in vector:
                        assert "execution_mode" in vector["artefact"], (
                            f"vector {vector_name!r} in {cat}/{sub} missing execution_mode"
                        )

    def test_execution_mode_vectors_are_all_exercised(self):
        """All 10 execution-mode vectors exist and are run below.

        The previous test globbed ``execution-mode/*.json`` while the vectors
        live in ``execution-mode/valid/``, so it iterated zero times and
        passed vacuously (it also expected keys no vector has).
        """
        vectors = _load_vectors("execution-mode", "valid")
        assert len(vectors) == 10
        assert not _load_vectors("execution-mode", "invalid")

    @pytest.mark.parametrize(
        "vector_name,vector",
        _load_vectors("execution-mode", "valid"),
        ids=[v[0] for v in _load_vectors("execution-mode", "valid")],
    )
    def test_execution_mode_vector(self, vector_name: str, vector: dict):
        """Check each execution-mode vector against the reference implementation.

        The vectors carry exactly one expectation:

        * ``expected_mode`` — ``input.execution_mode`` parses to that mode.
        * ``expected_validation`` on an ``{"execution_mode": ...}`` input —
          the value must be present and satisfy the schema's execution_mode
          definition (explicit, never inferred; a string enum).
        * ``expected_validation`` / ``expected_finality`` on a
          ``{"mode", "result"}`` input — the result is built with the
          reference ``ExecutionResult`` models. These vectors use receipt
          vocabulary: brokered success (``outcome: EXECUTED`` or a succeeded
          ``provider_response_summary``) is observed only when a
          ``provider_response_summary`` is present; resource-owned
          ``outcome`` names the state (default ``SUCCEEDED``), and a
          ``resource_signature`` is the verified resource receipt.
        """
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ExecutionResultValidationError,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )
        from jsonschema import Draft202012Validator

        expectations = {"expected_mode", "expected_validation", "expected_finality"} & set(vector)
        assert len(expectations) == 1, f"{vector_name}: expected exactly one expectation key"
        assert vector["name"] + ".v1.json" == vector_name
        inp = vector["input"]

        if "expected_mode" in vector:
            assert ExecutionMode(inp["execution_mode"]) == vector["expected_mode"]
            return

        if "result" not in inp:
            common = json.loads((SCHEMAS_DIR / "_common.v1.json").read_text())
            mode_schema = common["$defs"]["execution_mode"]
            valid = "execution_mode" in inp and Draft202012Validator(mode_schema).is_valid(
                inp["execution_mode"]
            )
            assert valid == (vector["expected_validation"] == "valid"), vector_name
            return

        result = inp["result"]
        common_fields = {
            "verified_by": "verifier",
            "executed_by": "executor",
            "attempt_id": "exec_abcdef0123456789",
            "occurred_at": "2026-07-21T12:00:00Z",
        }
        try:
            if inp["mode"] == "brokered":
                summary = result.get("provider_response_summary", {})
                assert result.get("outcome") == "EXECUTED" or summary.get("status") == "succeeded"
                built = BrokeredExecutionResult(
                    state=BrokeredExecutionState.SUCCEEDED,
                    provider_execution_observed="provider_response_summary" in result,
                    **common_fields,
                )
            else:
                assert inp["mode"] == "resource_owned"
                signed = "resource_signature" in result
                built = ResourceOwnedExecutionResult(
                    state=ResourceOwnedExecutionState(result.get("outcome", "SUCCEEDED").lower()),
                    provider_execution_observed=signed,
                    resource_receipt_received=signed,
                    resource_receipt_verified=signed,
                    **common_fields,
                )
        except ExecutionResultValidationError:
            built = None

        if "expected_finality" in vector:
            assert built is not None, vector_name
            assert built.finality == vector["expected_finality"], vector_name
        else:
            assert (built is not None) == (vector["expected_validation"] == "valid"), vector_name


# ---------- 5b. Execution results (Prompt 9) ----------


class TestExecutionResults:
    """Conformance for the discriminated ExecutionResult model.

    The two result shapes (brokered vs resource_owned) are NOT
    interchangeable. The mode field is the discriminator. Hard rules
    enforced at construction:

      * brokered succeeded requires provider_execution_observed=True
      * resource_owned succeeded requires resource_receipt_verified=True
      * resource_owned submitted requires finality=non_final
      * mode-specific fields must not mix
    """

    def test_both_state_families_defined(self):
        from actenon_protocol import (
            BrokeredExecutionState,
            ResourceOwnedExecutionState,
        )

        assert set(s.value for s in BrokeredExecutionState) == {
            "succeeded",
            "failed",
            "refused",
            "outcome_unknown",
        }
        assert set(s.value for s in ResourceOwnedExecutionState) == {
            "submitted",
            "accepted",
            "refused",
            "succeeded",
            "failed",
            "outcome_unknown",
        }

    def test_brokered_succeeded_requires_observation(self):
        """A brokered result with state=succeeded and provider_execution_observed=False
        must be rejected at construction. This is what prevents a
        credential-resolution success from being reported as execution success."""
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ExecutionResultValidationError,
        )

        with pytest.raises(ExecutionResultValidationError):
            BrokeredExecutionResult(
                state=BrokeredExecutionState.SUCCEEDED,
                verified_by="x",
                executed_by="x",
                provider_execution_observed=False,
                attempt_id="exec_x",
                occurred_at="2026-07-22T10:00:00Z",
            )

    def test_resource_owned_succeeded_requires_verified_receipt(self):
        """A resource_owned result with state=succeeded and
        resource_receipt_verified=False must be rejected. This is what
        prevents a forged receipt from being reported as execution success."""
        from actenon_protocol import (
            ExecutionResultValidationError,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )

        with pytest.raises(ExecutionResultValidationError):
            ResourceOwnedExecutionResult(
                state=ResourceOwnedExecutionState.SUCCEEDED,
                verified_by="r",
                executed_by="r",
                attempt_id="exec_y",
                occurred_at="2026-07-22T10:00:00Z",
                provider_execution_observed=True,
                resource_receipt_received=True,
                resource_receipt_verified=False,
            )

    def test_resource_owned_submitted_requires_non_final(self):
        """submitted is non_final. Submission is NOT execution."""
        from actenon_protocol import (
            RESOURCE_OWNED_FINALITY,
            FinalityStatus,
            ResourceOwnedExecutionState,
        )

        assert (
            RESOURCE_OWNED_FINALITY[ResourceOwnedExecutionState.SUBMITTED]
            == FinalityStatus.NON_FINAL
        )

    def test_resource_owned_submitted_requires_no_observation(self):
        """submitted requires provider_execution_observed=False and
        resource_receipt_received=False."""
        from actenon_protocol import (
            ExecutionResultValidationError,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )

        with pytest.raises(ExecutionResultValidationError):
            ResourceOwnedExecutionResult(
                state=ResourceOwnedExecutionState.SUBMITTED,
                verified_by="r",
                executed_by="r",
                attempt_id="exec_z",
                occurred_at="2026-07-22T10:00:00Z",
                provider_execution_observed=True,
            )

    def test_serialisation_preserves_mode_distinction(self):
        """serialise_result() must produce a dict whose 'mode' field
        matches the result type, and the dicts of the two modes must
        not share mode-specific keys."""
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
            serialise_result,
        )

        b = BrokeredExecutionResult(
            state=BrokeredExecutionState.SUCCEEDED,
            verified_by="b",
            executed_by="b",
            provider_execution_observed=True,
            attempt_id="exec_b",
            occurred_at="2026-07-22T10:00:00Z",
            receipt_received=True,
            receipt_verified=True,
        )
        r = ResourceOwnedExecutionResult(
            state=ResourceOwnedExecutionState.SUBMITTED,
            verified_by="r",
            executed_by="r",
            attempt_id="exec_r",
            occurred_at="2026-07-22T10:00:00Z",
            submission_reference="sub_1",
        )

        b_dict = serialise_result(b)
        r_dict = serialise_result(r)

        assert b_dict["mode"] == "brokered"
        assert r_dict["mode"] == "resource_owned"

        # brokered-only keys must not appear in resource_owned
        brokered_only = {
            "receipt_received",
            "receipt_verified",
            "provider_evidence",
            "reconciliation_status",
        }
        resource_only = {
            "resource_receipt_received",
            "resource_receipt_verified",
            "resource_receipt",
            "submission_reference",
        }
        assert brokered_only.isdisjoint(r_dict.keys()), (
            f"resource_owned result carries brokered-only keys: {brokered_only & set(r_dict.keys())}"
        )
        assert resource_only.isdisjoint(b_dict.keys()), (
            f"brokered result carries resource_owned-only keys: {resource_only & set(b_dict.keys())}"
        )

    def test_valid_vectors_construct(self):
        """Every valid execution-result vector must construct without raising."""
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )

        for _vector_name, vector in _load_vectors("execution-result", "valid"):
            artefact = vector["artefact"]
            assert artefact["mode"] in ("brokered", "resource_owned")
            if artefact["mode"] == "brokered":
                BrokeredExecutionResult(
                    state=BrokeredExecutionState(artefact["state"]),
                    verified_by=artefact["verified_by"],
                    executed_by=artefact["executed_by"],
                    provider_execution_observed=artefact["provider_execution_observed"],
                    attempt_id=artefact["attempt_id"],
                    occurred_at=artefact["occurred_at"],
                    receipt_received=artefact.get("receipt_received", False),
                    receipt_verified=artefact.get("receipt_verified", False),
                    provider_evidence=artefact.get("provider_evidence", {}),
                    reconciliation_status=artefact.get("reconciliation_status"),
                )
            else:
                ResourceOwnedExecutionResult(
                    state=ResourceOwnedExecutionState(artefact["state"]),
                    verified_by=artefact["verified_by"],
                    executed_by=artefact["executed_by"],
                    attempt_id=artefact["attempt_id"],
                    occurred_at=artefact["occurred_at"],
                    provider_execution_observed=artefact.get("provider_execution_observed", False),
                    resource_receipt_received=artefact.get("resource_receipt_received", False),
                    resource_receipt_verified=artefact.get("resource_receipt_verified", False),
                    resource_receipt=artefact.get("resource_receipt"),
                    submission_reference=artefact.get("submission_reference"),
                )

    def test_invalid_vectors_rejected(self):
        """Every invalid execution-result vector must raise at construction."""
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ExecutionResultValidationError,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )

        for _vector_name, vector in _load_vectors("execution-result", "invalid"):
            artefact = vector["artefact"]
            violation = vector.get("expected_violation", "")
            # Mixed-mode-field vectors are caught by the schema layer, not
            # the dataclass layer (the dataclass silently drops unknown
            # fields). Skip them here; they are covered by the schema test.
            if violation == "mode_field_mixing":
                continue
            # Finality-vs-state mismatches are also schema-only: the dataclass
            # derives finality from state, so it cannot represent the
            # contradiction. The schema's if/then rules catch it.
            if violation == "submitted_must_be_non_final":
                continue
            with pytest.raises(ExecutionResultValidationError):
                if artefact["mode"] == "brokered":
                    BrokeredExecutionResult(
                        state=BrokeredExecutionState(artefact["state"]),
                        verified_by=artefact["verified_by"],
                        executed_by=artefact["executed_by"],
                        provider_execution_observed=artefact["provider_execution_observed"],
                        attempt_id=artefact["attempt_id"],
                        occurred_at=artefact["occurred_at"],
                        receipt_received=artefact.get("receipt_received", False),
                        receipt_verified=artefact.get("receipt_verified", False),
                        provider_evidence=artefact.get("provider_evidence", {}),
                        reconciliation_status=artefact.get("reconciliation_status"),
                    )
                else:
                    ResourceOwnedExecutionResult(
                        state=ResourceOwnedExecutionState(artefact["state"]),
                        verified_by=artefact["verified_by"],
                        executed_by=artefact["executed_by"],
                        attempt_id=artefact["attempt_id"],
                        occurred_at=artefact["occurred_at"],
                        provider_execution_observed=artefact.get(
                            "provider_execution_observed", False
                        ),
                        resource_receipt_received=artefact.get("resource_receipt_received", False),
                        resource_receipt_verified=artefact.get("resource_receipt_verified", False),
                        resource_receipt=artefact.get("resource_receipt"),
                        submission_reference=artefact.get("submission_reference"),
                    )

    def test_json_schema_rejects_invalid_vectors(self):
        """The JSON Schema in schemas/execution_result.v1.json must reject
        every invalid vector and accept every valid vector. Loads the
        schema registry inline so this test class is self-contained."""
        import json as _json

        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        # Load all schemas and build a registry so $ref to _common.v1.json resolves.
        schemas: dict[str, dict] = {}
        for path in SCHEMAS_DIR.glob("*.v1.json"):
            with path.open("r", encoding="utf-8") as f:
                schema = _json.load(f)
            schemas[schema["$id"]] = schema

        def retrieve(uri: str):
            return Resource.from_contents(schemas[uri])

        registry = Registry(retrieve=retrieve)
        schema = schemas["urn:actenon:protocol:execution-result:v1"]
        validator = Draft202012Validator(schema, registry=registry)

        for vector_name, vector in _load_vectors("execution-result", "valid"):
            errors = list(validator.iter_errors(vector["artefact"]))
            assert not errors, (
                f"valid vector {vector_name!r} rejected by schema: {[e.message for e in errors]}"
            )

        for vector_name, vector in _load_vectors("execution-result", "invalid"):
            errors = list(validator.iter_errors(vector["artefact"]))
            assert errors, f"invalid vector {vector_name!r} accepted by schema (should be rejected)"


# ---------- 6. Version constants ----------


class TestVersionConstants:
    def test_protocol_version(self):
        assert PROTOCOL_VERSION == "1.3.0"

    def test_dunder_version_is_the_package_version(self):
        """__version__ is the distribution version (what pip reports); the wire
        version is PROTOCOL_VERSION. It used to be PROTOCOL_VERSION ("1.1.0")
        while the installed package was 1.3.0."""
        import importlib.metadata
        import re

        import actenon_protocol

        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        declared = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
        assert actenon_protocol.__version__ == importlib.metadata.version("actenon-protocol")
        assert actenon_protocol.__version__ == declared

    def test_protocol_version_single_sourced(self):
        """VERSIONING.md and both TypeScript packages state the same wire
        version as version.py (TS said 1.0.0, so TS and Python producers
        stamped different protocol_version values)."""
        import re

        versioning = (REPO_ROOT / "VERSIONING.md").read_text(encoding="utf-8")
        assert (
            re.search(r"\*\*Protocol version:\*\* `([^`]+)`", versioning).group(1)
            == PROTOCOL_VERSION
        )
        for ts in ("typescript/src/version.ts", "typescript-runtime/src/version.ts"):
            text = (REPO_ROOT / ts).read_text(encoding="utf-8")
            m = re.search(r'PROTOCOL_VERSION = "([^"]+)"', text)
            assert m and m.group(1) == PROTOCOL_VERSION, ts

    def test_canonicalisation_profile(self):
        assert CANONICALISATION_PROFILE == "ACTENON-JCS-STRICT-1"

    def test_legacy_alias(self):
        from actenon_protocol import LEGACY_CANONICALISATION_PROFILE

        assert LEGACY_CANONICALISATION_PROFILE == "RFC8785-JCS"

    def test_rejected_label_is_not_accepted(self):
        from actenon_protocol.canonicalisation import is_accepted_profile

        assert not is_accepted_profile("actenon-jcs-sha256-v1")
        assert is_accepted_profile("ACTENON-JCS-STRICT-1")
        assert is_accepted_profile("RFC8785-JCS")


# ---------- 7. Pydantic types ----------


class TestPydanticTypes:
    def test_execution_proof_round_trip(self):
        """A proof constructed from a valid vector should round-trip through JSON."""
        for _vector_name, vector in _load_vectors("proof", "valid"):
            proof = ExecutionProof(**vector["artefact"])
            # Round-trip
            dumped = proof.model_dump(mode="json", exclude_none=True)
            reconstructed = ExecutionProof(**dumped)
            assert reconstructed.proof_id == proof.proof_id

    def test_execution_receipt_round_trip(self):
        for _vector_name, vector in _load_vectors("receipt", "valid"):
            receipt = ExecutionReceipt(**vector["artefact"])
            dumped = receipt.model_dump(mode="json", exclude_none=True)
            reconstructed = ExecutionReceipt(**dumped)
            assert reconstructed.receipt_id == receipt.receipt_id

    def test_authorised_execution_intent_constructs(self):
        intent = AuthorisedExecutionIntent(
            protocol_version="1.0.0",
            intent_id="intent_abcdef0123456789abcdef0123456789",
            subject="agent:refund-bot-001",
            action={"type": "payment.refund", "parameters": {"amount_cents": 2500}},
            target={"type": "payment-provider", "id": "stripe"},
            requested_at="2026-07-21T12:00:00Z",
        )
        assert intent.intent_id == "intent_abcdef0123456789abcdef0123456789"


# ---------- 8. ExecutionOutcome ----------


class TestExecutionOutcome:
    def test_four_outcomes(self):
        assert len(list(ExecutionOutcome)) == 4
        assert ExecutionOutcome.EXECUTED == "EXECUTED"
        assert ExecutionOutcome.REFUSED == "REFUSED"
        assert ExecutionOutcome.PARTIAL == "PARTIAL"
        assert ExecutionOutcome.UNKNOWN == "UNKNOWN"


# ---------- 9. Vector hash lock ----------


def _vector_lock_module():
    """Import scripts/check_vector_lock.py (scripts/ is not a package)."""
    import importlib.util

    path = REPO_ROOT / "scripts" / "check_vector_lock.py"
    spec = importlib.util.spec_from_file_location("check_vector_lock", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestVectorHashLock:
    """The README calls the vectors "hash-locked": prove the lock bites."""

    LOCK = REPO_ROOT / "conformance" / "vectors.sha256"

    def _copy(self, tmp_path):
        import shutil

        vectors = tmp_path / "vectors"
        shutil.copytree(VECTORS_DIR, vectors)
        lock = tmp_path / "vectors.sha256"
        shutil.copy(self.LOCK, lock)
        return vectors, lock

    def test_committed_vectors_match_lock(self):
        problems = _vector_lock_module().check_lock(VECTORS_DIR, self.LOCK)
        assert problems == []

    def test_lock_covers_every_vector(self):
        entries = _vector_lock_module().read_lock(self.LOCK)
        on_disk = {p.relative_to(VECTORS_DIR).as_posix() for p in VECTORS_DIR.rglob("*.json")}
        assert set(entries) == on_disk
        assert len(entries) == 156

    def test_tampered_vector_detected(self, tmp_path):
        vectors, lock = self._copy(tmp_path)
        target = vectors / "canonicalisation" / "valid" / "simple_object.json"
        target.write_bytes(target.read_bytes().replace(b'"z": 1', b'"z": 2'))
        problems = _vector_lock_module().check_lock(vectors, lock)
        assert any("canonicalisation/valid/simple_object.json" in p for p in problems), problems

    def test_whitespace_only_change_detected(self, tmp_path):
        vectors, lock = self._copy(tmp_path)
        target = vectors / "refusal" / "valid" / "replay_detected.v1.json"
        target.write_bytes(target.read_bytes() + b" ")
        assert _vector_lock_module().check_lock(vectors, lock)

    def test_added_and_removed_vectors_detected(self, tmp_path):
        vectors, lock = self._copy(tmp_path)
        (vectors / "proof" / "valid" / "extra.v1.json").write_text("{}\n")
        (vectors / "receipt" / "invalid" / "missing_target.v1.json").unlink()
        problems = "\n".join(_vector_lock_module().check_lock(vectors, lock))
        assert "proof/valid/extra.v1.json" in problems
        assert "receipt/invalid/missing_target.v1.json" in problems


# ---------- 10. Standalone runner (conformance/runner.py) ----------


def _runner_module():
    import importlib.util

    path = REPO_ROOT / "conformance" / "runner.py"
    spec = importlib.util.spec_from_file_location("actenon_conformance_runner", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


class TestStandaloneRunner:
    """The runner external implementers use to claim compatibility must not
    certify a non-conformant implementation."""

    def test_reference_passes_every_vector_exactly_once(self):
        runner = _runner_module()
        results = runner.ConformanceRunner(runner.ReferenceValidator()).run_all()
        assert results.failures == []
        assert results.total == 156  # was double-counted as 258
        assert results.passed == 156
        assert results.skipped == 0

    def test_float_accepting_canonicaliser_is_not_compatible(self):
        runner = _runner_module()

        class AcceptsEverything(runner.ReferenceValidator):
            def canonicalize(self, input_value):
                try:
                    return super().canonicalize(input_value)
                except Exception:
                    return json.dumps(input_value)

            def parse_json(self, text):
                return json.loads(text)

        results = runner.ConformanceRunner(AcceptsEverything()).run_all("canonicalisation")
        failed = {vr.vector.name for vr in results.failures}
        assert {
            "float_top_level",
            "float_in_object",
            "float_nan",
            "deeply_nested_exceeds_limit",
            "oversized_structure",
            "duplicate_keys",
        } <= failed

    def test_execution_result_vectors_are_executed(self):
        runner = _runner_module()

        class AcceptsAnyResult(runner.ReferenceValidator):
            def validate_execution_result(self, artefact):
                return True, None

        results = runner.ConformanceRunner(AcceptsAnyResult()).run_all("execution-result")
        assert len(results.failures) == 4
        assert all(vr.vector.sub == "invalid" for vr in results.failures)

    def test_language_specific_vectors_are_skipped_not_passed(self):
        runner = _runner_module()

        class NoNativeInputs(runner.ReferenceValidator):
            def language_specific_input(self, vector_name):
                return runner.NOT_APPLICABLE

        results = runner.ConformanceRunner(NoNativeInputs()).run_all("canonicalisation")
        assert results.failed == 0
        assert results.skipped == 3
        assert results.passed == 34


# ---------- 11. README claims about the Python package ----------


class TestReadmeClaims:
    """Executable checks for README statements CI did not previously verify."""

    README = REPO_ROOT / "README.md"

    def _section(self, heading: str) -> str:
        text = self.README.read_text(encoding="utf-8")
        start = text.index(heading)
        end = text.find("\n## ", start + len(heading))
        return text[start : end if end != -1 else None]

    def test_refusal_codes_named_in_readme_exist(self):
        """Every code the README's refusal section names is a catalogue code
        or a registered compatibility alias; disclosed-code examples are
        public-safe codes."""
        import re

        from actenon_protocol import COMPATIBILITY_ALIASES

        section = self._section("## Refusal taxonomy")
        named = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", section))
        assert named, "no codes found in the refusal section"
        known = {c.value for c in RefusalCode} | set(COMPATIBILITY_ALIASES)
        assert named <= known, f"README names unknown refusal codes: {sorted(named - known)}"
        disclosed_line = next(
            line for line in section.splitlines() if line.startswith("- **`disclosed_code`**")
        )
        disclosed = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", disclosed_line))
        assert disclosed <= PUBLIC_SAFE_CODES, sorted(disclosed - PUBLIC_SAFE_CODES)

    def test_python_usage_snippet_runs(self):
        """The ```python block under "## Use" executes as written."""
        section = self._section("## Use")
        code = section.split("```python\n", 1)[1].split("```", 1)[0]
        exec(compile(code, "README.md#use", "exec"), {})

    def test_repo_layout_paths_exist(self):
        """Every file or directory listed under "What's in this repo" exists."""
        import re

        block = self._section("## What's in this repo").split("```", 2)[1]
        parent = None
        for line in block.splitlines():
            m = re.match(r"^(\s*)([\w.-]+/?)(\s|$)", line)
            if not m or set(m.group(2)) == {"."}:  # skip "..." elisions
                continue
            indent, name = m.group(1), m.group(2)
            if not indent:
                parent = name if name.endswith("/") else None
                path = REPO_ROOT / name
            else:
                assert parent, line
                path = REPO_ROOT / parent / name
            assert path.exists(), (
                f"README lists {path.relative_to(REPO_ROOT)}, which does not exist"
            )


# ---------- 12. Packaged data copies ----------


@pytest.mark.parametrize(
    "source,packaged",
    [
        ("ecosystem.yaml", "ecosystem.yaml"),
        ("refusals/catalogue.v1.yaml", "catalogue.v1.yaml"),
        ("identifiers/prefixes.v1.yaml", "prefixes.v1.yaml"),
    ]
    + [
        (f"schemas/{p.name}", p.name)
        for p in sorted((REPO_ROOT / "python" / "actenon_protocol" / "data").glob("*.v1.json"))
        if p.name != "catalogue.v1.json"  # compiled from YAML; checked by compile_yaml_to_json.py
    ],
)
def test_packaged_data_matches_source(source: str, packaged: str):
    """The wheel ships copies of the repo's source-of-truth files. A stale
    copy means the installed package (and the ecosystem-table gate sibling
    repos run from PyPI) disagrees with this repository."""
    src = (REPO_ROOT / source).read_bytes()
    dst = (REPO_ROOT / "python" / "actenon_protocol" / "data" / packaged).read_bytes()
    assert src == dst, f"python/actenon_protocol/data/{packaged} is out of sync with {source}"


# ---------- 13. python -m actenon_protocol.conformance_canonicalisation ----------


class TestCanonicalisationConformanceCommand:
    def _run(self, *args, cwd):
        import subprocess

        return subprocess.run(
            [sys.executable, "-m", "actenon_protocol.conformance_canonicalisation", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_runs_against_explicit_vectors_dir_from_anywhere(self, tmp_path):
        vectors = VECTORS_DIR / "canonicalisation"
        proc = self._run("--vectors", str(vectors), cwd=tmp_path)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "0 failed" in proc.stdout

    def test_missing_vectors_is_a_clear_error_not_a_traceback(self, tmp_path, monkeypatch):
        import actenon_protocol.conformance_canonicalisation as cli

        monkeypatch.setattr(cli, "_default_candidates", lambda: [tmp_path / "nope"])
        monkeypatch.chdir(tmp_path)
        assert cli.main([]) == 2


def test_compatibility_mark_is_consistent_everywhere(monkeypatch):
    """README (enforced by verify-claims), CONFORMANCE.md, RUNNER_SPEC.md,
    the generator and the runner's own verdict name the same mark. The
    runner printed "Actenon-compatible v1.1.0" while the docs promise v1.3.0."""
    import contextlib
    import io
    import re

    import actenon_protocol

    mark = f"Actenon-compatible v{actenon_protocol.__version__}"
    for rel in (
        "README.md",
        "CONFORMANCE.md",
        "conformance/RUNNER_SPEC.md",
        "conformance/generate_vectors.py",
        "conformance/runner.py",
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for found in re.findall(r"Actenon-compatible v\d+\.\d+\.\d+", text):
            assert found == mark, f"{rel}: {found!r} != {mark!r}"
    runner = _runner_module()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        monkeypatch.setattr(sys, "argv", ["runner.py"])
        runner.main()
    assert f"✅ {mark}" in out.getvalue()


# ---------- 14. Ecosystem table: never link a repository the public cannot open ----------


class TestEcosystemOptionalLine:
    """The Optional line is rendered into every sibling repo's README.

    actenon-cloud is a private repository: linking it put a 404 into the
    README of every public repo and turned their link checks red (or made
    them add exclusions). An optional component without a public URL is
    rendered as a plain name.
    """

    def test_optional_entry_without_url_renders_as_plain_name(self):
        from actenon_protocol.ecosystem import _optional_line

        line = _optional_line(
            {"name": "x-private", "summary": "a thing", "licence": "private", "note": "Optional."}
        )
        assert line == "**Optional:** `x-private` — a thing (private). Optional."

    def test_optional_entry_with_url_still_links(self):
        from actenon_protocol.ecosystem import _optional_line

        line = _optional_line(
            {
                "name": "x",
                "url": "https://example.org/x",
                "summary": "s",
                "licence": "l",
                "note": "n",
            }
        )
        assert line == "**Optional:** [`x`](https://example.org/x) — s (l). n"

    def test_rendered_table_does_not_link_the_private_cloud_repo(self):
        pytest.importorskip("yaml")
        from actenon_protocol.ecosystem import render_table

        assert "github.com/Actenon/actenon-cloud" not in render_table("actenon-protocol")
