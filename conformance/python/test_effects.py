"""Effect contract corpus, schema/model parity and safety counterexamples."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
from actenon_protocol import EffectError, effect_identity, validate_effect_outcome
from actenon_protocol.canonicalisation import CanonicalisationError
from actenon_protocol.types import EffectEvidence, EffectReference, ProofExtensions
from jsonschema import Draft202012Validator
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
VECTORS = sorted((ROOT / "conformance/vectors/effect").rglob("*.json"))


@pytest.mark.parametrize("path", VECTORS, ids=lambda p: p.stem)
def test_effect_corpus(path):
    vector = json.loads(path.read_text())
    valid = vector["expected_validation"] == "valid"
    operation = vector["operation"]
    if operation == "identity":
        if valid:
            assert effect_identity(vector["input"]) == vector["expected_effect_id"]
        else:
            with pytest.raises((EffectError, CanonicalisationError)):
                effect_identity(vector["input"])
        # JSON Schema is a coarse shape check; the canonicalizer rejects floats.
        schema = json.loads((ROOT / "schemas/effect_descriptor.v1.json").read_text())
        if path.stem != "fractional_parameter.v1":
            assert Draft202012Validator(schema).is_valid(vector["input"]) is valid
        return
    model, name = (
        (EffectReference, "effect_reference")
        if operation == "reference"
        else (EffectEvidence, "effect_evidence")
    )
    schema = json.loads((ROOT / ("schemas/" + name + ".v1.json")).read_text())
    assert Draft202012Validator(schema).is_valid(vector["artefact"]) is valid
    if valid:
        assert model.model_validate(vector["artefact"]).model_dump() == vector["artefact"]
    else:
        with pytest.raises(ValidationError):
            model.model_validate(vector["artefact"])


def _descriptor(name):
    return json.loads(
        (ROOT / ("conformance/vectors/effect/valid/" + name + ".v1.json")).read_text()
    )["input"]


def test_attempt_proof_grant_source_and_time_cannot_be_agent_nonce_fields():
    base = _descriptor("exact_refund")
    for name in ["attempt_id", "proof_id", "grant_id", "source_version", "timestamp"]:
        changed = {**base, name: "fresh-id"}
        with pytest.raises(EffectError):
            effect_identity(changed)


def test_exact_identity_binds_target_namespace_parameters_and_presence():
    base = effect_identity(_descriptor("exact_refund"))
    assert effect_identity(_descriptor("exact_reordered_parameters")) == base
    for name in [
        "exact_changed_amount",
        "exact_changed_target",
        "exact_changed_namespace",
        "exact_null_is_present",
    ]:
        assert effect_identity(_descriptor(name)) != base


def test_semantic_identity_never_silently_absorbs_parameters():
    descriptor = _descriptor("semantic_refund")
    with pytest.raises(EffectError):
        effect_identity({**descriptor, "parameters": {"amount_minor": 1}})
    assert effect_identity(descriptor) != effect_identity(_descriptor("semantic_distinct_refund"))


@pytest.mark.parametrize("occurred", [0, 1, "true", "false", [], {}])
def test_execution_occurred_never_coerces_untrusted_types(occurred):
    with pytest.raises(EffectError):
        validate_effect_outcome("COMMITTED", occurred, "a" * 64)


def test_known_effect_extension_validates_but_unknown_extensions_are_preserved():
    record = json.loads(
        (ROOT / "conformance/vectors/effect/valid/reference_valid.v1.json").read_text()
    )["artefact"]
    value = ProofExtensions.model_validate({"effect": record, "future_extension": {"data": 1}})
    assert value.effect.effect_id == record["effect_id"]
    assert value.model_dump()["future_extension"] == {"data": 1}
    with pytest.raises(ValidationError):
        ProofExtensions.model_validate({"effect": {**record, "profile": "UNKNOWN"}})
    with pytest.raises(ValidationError):
        ProofExtensions.model_validate({"effect": None})
    assert ProofExtensions.model_validate({"unrelated": 1}).effect is None


def test_standalone_runner_actually_calls_effect_implementation():
    spec = importlib.util.spec_from_file_location("effect_runner", ROOT / "conformance/runner.py")
    runner = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    assert len(runner.load_vectors("effect")) == len(VECTORS) == 30
    result = runner.ConformanceRunner(runner.ReferenceValidator()).run_all("effect")
    assert (result.total, result.passed, result.failed, result.skipped) == (30, 30, 0, 0)

    class MissingImplementation:
        pass

    refused = runner.ConformanceRunner(MissingImplementation()).run_all("effect")
    assert (refused.failed, refused.skipped) == (30, 0)


def test_identity_requires_canonical_json_and_explicit_nonempty_namespace():
    base = _descriptor("exact_refund")
    changed = copy.deepcopy(base)
    changed["parameters"]["amount_minor"] = float("nan")
    with pytest.raises(CanonicalisationError):
        effect_identity(changed)
    for value in ["", None, "  ", True]:
        with pytest.raises(EffectError):
            effect_identity({**base, "namespace": value})


def test_wire_effect_identity_retains_large_integers_and_refuses_lossy_spellings():
    from actenon_protocol import parse_strict

    first = _descriptor("integer_above_js_safe_range")
    second = _descriptor("adjacent_integer_above_js_safe_range")
    assert effect_identity(parse_strict(json.dumps(first))) != effect_identity(
        parse_strict(json.dumps(second))
    )
    wire = json.dumps(first)
    for number in ["0.9999999999999999999", "1.0", "1e0"]:
        with pytest.raises(CanonicalisationError):
            parse_strict(wire.replace("9007199254740992", number))
    with pytest.raises(CanonicalisationError):
        parse_strict(wire.replace('"amount_minor":', '"amount_minor": 1, "amount_minor":'))
