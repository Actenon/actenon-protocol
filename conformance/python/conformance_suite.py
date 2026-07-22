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
        assert len(list(RefusalCode)) == 20

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
        assert resolve_alias("SCOPE_CAPABILITY_MISMATCH") == "PARAMETER_MISMATCH"
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

    def test_mode_distinction_vectors(self):
        """The execution-mode vectors prove that mode mismatch produces AUDIENCE_MISMATCH."""
        for vector_name, vector in _load_vectors("execution-mode"):
            proof_mode = vector["proof"]["execution_mode"]
            verifier_mode = vector["verifier_mode"]
            expected = vector["expected_outcome"]
            if proof_mode == verifier_mode:
                assert expected == "accepted", (
                    f"vector {vector_name!r}: same mode should be accepted"
                )
            else:
                assert expected == "refused", (
                    f"vector {vector_name!r}: mode mismatch should be refused"
                )
                assert vector["expected_disclosed_code"] == "PROOF_INVALID"
                assert vector["expected_internal_code"] == "AUDIENCE_MISMATCH"


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
        assert PROTOCOL_VERSION == "1.1.0"

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
