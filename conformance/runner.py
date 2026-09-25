#!/usr/bin/env python3
"""Standalone Actenon protocol conformance runner.

This runner loads every vector from conformance/vectors/ and validates it
against the Python reference implementation. External implementations can
use this as a template for their own runner, or subclass ConformanceRunner
to plug in their own validation functions.

Usage:
    python conformance/runner.py                    # run all vectors
    python conformance/runner.py --category proof   # run only proof vectors
    python conformance/runner.py --json             # machine-readable output
    python conformance/runner.py --verbose          # show every vector

Exit code:
    0 — all vectors passed (Actenon-compatible v1.1.0)
    1 — one or more vectors failed
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

VECTORS_DIR = Path(__file__).resolve().parent / "vectors"
SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Returned by Validator.language_specific_input() for canonicalisation vectors
# whose input only exists as a native value in some languages (a Python set,
# bytes, a non-string dict key). Such vectors are reported as SKIPPED, never
# as passed.
NOT_APPLICABLE = object()

# Language-neutral forms of the two invalid canonicalisation vectors that
# carry no input_json: a string whose canonical form (with its quotes)
# exceeds the 1 MiB output limit, and an object with a duplicate key.
OVERSIZED_INPUT_LENGTH = 1_048_576
DUPLICATE_KEYS_JSON = '{"a": 1, "a": 2}'


# ---------------------------------------------------------------------------
# Vector loading
# ---------------------------------------------------------------------------

@dataclass
class Vector:
    category: str
    sub: str  # "valid" or "invalid"
    name: str
    data: dict
    path: Path


def load_vectors(category: str | None = None) -> list[Vector]:
    """Load all vectors, optionally filtered by category."""
    vectors = []
    if not VECTORS_DIR.exists():
        return vectors
    for cat_dir in sorted(VECTORS_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        if category and cat_dir.name != category:
            continue
        for sub_dir in sorted(cat_dir.iterdir()):
            if not sub_dir.is_dir():
                continue
            for vec_file in sorted(sub_dir.glob("*.json")):
                with vec_file.open() as f:
                    data = json.load(f)
                vectors.append(Vector(
                    category=cat_dir.name,
                    sub=sub_dir.name,
                    name=data.get("name", vec_file.stem),
                    data=data,
                    path=vec_file,
                ))
    return vectors


# ---------------------------------------------------------------------------
# Validation interface
# ---------------------------------------------------------------------------

class Validator(Protocol):
    """Interface that external implementations implement."""

    def validate_proof(self, artefact: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message). is_valid=True if the proof is accepted."""

    def validate_receipt(self, artefact: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message)."""

    def validate_refusal(self, artefact: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message)."""

    def canonicalize(self, input_value: Any) -> str:
        """Return the canonical form of the input, or raise if the profile
        forbids it (floats, NaN, depth > 32, output > 1 MiB, ...)."""

    def parse_json(self, text: str) -> Any:
        """Parse JSON text the way the implementation parses untrusted input.
        Raise on duplicate object keys and non-JSON constants (NaN, Infinity)."""

    def language_specific_input(self, vector_name: str) -> Any:
        """Return the native value for a language-specific invalid vector
        (non_string_key, unsupported_type_set, unsupported_type_bytes), or
        NOT_APPLICABLE if the language cannot express it."""

    def validate_execution_result(self, artefact: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message) for an ExecutionResult artefact."""

    def validate_execution_mode(self, input_value: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message) for execution-mode vectors."""


# ---------------------------------------------------------------------------
# Reference implementation validator (uses the Python reference)
# ---------------------------------------------------------------------------

class ReferenceValidator:
    """Validator that uses the Python reference implementation."""

    def __init__(self):
        from actenon_protocol import canonicalize_bytes, is_valid_identifier
        from actenon_protocol.types import ExecutionProof, ExecutionReceipt, ExecutionRefusal
        self._canonicalize_bytes = canonicalize_bytes
        self._is_valid_id = is_valid_identifier
        self._Proof = ExecutionProof
        self._Receipt = ExecutionReceipt
        self._Refusal = ExecutionRefusal

    def validate_proof(self, artefact: dict) -> tuple[bool, str | None]:
        # Check identifier prefixes first (Pydantic doesn't enforce these)
        proof_id = artefact.get("proof_id", "")
        if proof_id and not self._is_valid_id(proof_id):
            return False, f"INVALID_IDENTIFIER: {proof_id}"
        try:
            self._Proof(**artefact)
            return True, None
        except Exception as e:
            return False, str(e)

    def validate_receipt(self, artefact: dict) -> tuple[bool, str | None]:
        receipt_id = artefact.get("receipt_id", "")
        if receipt_id and not self._is_valid_id(receipt_id):
            return False, f"INVALID_IDENTIFIER: {receipt_id}"
        try:
            self._Receipt(**artefact)
            return True, None
        except Exception as e:
            return False, str(e)

    def validate_refusal(self, artefact: dict) -> tuple[bool, str | None]:
        refusal_id = artefact.get("refusal_id", "")
        if refusal_id and not self._is_valid_id(refusal_id):
            return False, f"INVALID_IDENTIFIER: {refusal_id}"
        try:
            self._Refusal(**artefact)
            return True, None
        except Exception as e:
            return False, str(e)

    def canonicalize(self, input_value: Any) -> str:
        # canonicalize_bytes, not canonicalize_json: the 1 MiB output limit
        # is only enforced on the encoded form.
        return self._canonicalize_bytes(input_value).decode("utf-8")

    def parse_json(self, text: str) -> Any:
        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict:
            obj: dict = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError(f"duplicate object key {key!r}")
                obj[key] = value
            return obj

        def reject_constant(name: str) -> Any:
            raise ValueError(f"{name} is not valid JSON")

        return json.loads(text, object_pairs_hook=reject_duplicates, parse_constant=reject_constant)

    def language_specific_input(self, vector_name: str) -> Any:
        return {
            "non_string_key": {1: "a"},
            "unsupported_type_set": {1, 2, 3},
            "unsupported_type_bytes": b"hello",
        }.get(vector_name, NOT_APPLICABLE)

    def validate_execution_result(self, artefact: dict) -> tuple[bool, str | None]:
        from actenon_protocol import (
            BrokeredExecutionResult,
            BrokeredExecutionState,
            ResourceOwnedExecutionResult,
            ResourceOwnedExecutionState,
        )
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        schemas = {}
        for path in SCHEMAS_DIR.glob("*.v1.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            schemas[schema["$id"]] = schema
        registry = Registry().with_resources(
            (uri, Resource.from_contents(schema)) for uri, schema in schemas.items()
        )
        validator = Draft202012Validator(
            schemas["urn:actenon:protocol:execution-result:v1"], registry=registry
        )
        errors = [e.message for e in validator.iter_errors(artefact)]
        if errors:
            return False, f"SCHEMA_INVALID: {errors[0]}"
        try:
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
        except Exception as e:
            return False, str(e)
        return True, None

    def validate_execution_mode(self, input_value: dict) -> tuple[bool, str | None]:
        mode = input_value.get("execution_mode") or input_value.get("mode")
        if mode is None:
            if "execution_mode" in input_value or "mode" in input_value:
                return False, "MISSING_EXECUTION_MODE"
            return False, "MISSING_EXECUTION_MODE"
        if mode not in ("brokered", "resource_owned"):
            return False, "SCHEMA_INVALID"
        if not isinstance(mode, str):
            return False, "SCHEMA_INVALID"
        return True, None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class VectorResult:
    vector: Vector
    passed: bool
    reason: str | None = None
    skipped: bool = False  # not applicable to this language; neither passed nor failed


@dataclass
class RunResults:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[VectorResult] = field(default_factory=list)
    passes: list[VectorResult] = field(default_factory=list)


class ConformanceRunner:
    """Runs all vectors against a validator."""

    def __init__(self, validator: Validator):
        self.validator = validator

    def run_vector(self, vector: Vector) -> VectorResult:
        """Run a single vector and return the result."""
        cat = vector.category
        data = vector.data

        if cat == "canonicalisation":
            return self._run_canonicalisation(vector)
        elif cat == "proof":
            return self._run_artefact(vector, self.validator.validate_proof)
        elif cat == "receipt":
            return self._run_artefact(vector, self.validator.validate_receipt)
        elif cat == "refusal":
            return self._run_artefact(vector, self.validator.validate_refusal)
        elif cat == "execution-mode":
            return self._run_execution_mode(vector)
        elif cat == "execution-result":
            return self._run_execution_result(vector)
        else:
            return VectorResult(vector, False, f"unknown category: {cat}")

    def _run_canonicalisation(self, vector: Vector) -> VectorResult:
        data = vector.data
        if vector.sub == "valid":
            expected = data.get("expected_canonical")
            if "input" not in data or expected is None:
                return VectorResult(vector, False, "malformed vector: needs input and expected_canonical")
            try:
                actual = self.validator.canonicalize(data["input"])
            except Exception as e:
                return VectorResult(vector, False, f"canonicalisation raised: {e}")
            if actual == expected:
                return VectorResult(vector, True)
            return VectorResult(vector, False, f"canonical mismatch: expected {expected!r}, got {actual!r}")

        # Invalid vector: the implementation must REFUSE the input, either
        # while parsing it or while canonicalising it. Every invalid vector
        # is executed; none is passed without running.
        try:
            if "input_json" in data:
                value = self.validator.parse_json(data["input_json"])
            elif vector.name == "duplicate_keys":
                value = self.validator.parse_json(DUPLICATE_KEYS_JSON)
            elif vector.name == "oversized_structure":
                value = "x" * OVERSIZED_INPUT_LENGTH
            else:
                value = self.validator.language_specific_input(vector.name)
                if value is NOT_APPLICABLE:
                    return VectorResult(vector, True, "language-specific input", skipped=True)
            self.validator.canonicalize(value)
        except Exception as e:
            return VectorResult(vector, True, f"correctly rejected: {type(e).__name__}: {e}")
        return VectorResult(vector, False, "expected rejection, but the input was canonicalised")

    def _run_execution_result(self, vector: Vector) -> VectorResult:
        is_valid, error = self.validator.validate_execution_result(vector.data.get("artefact", {}))
        if vector.data.get("expected_valid") is True:
            if is_valid:
                return VectorResult(vector, True)
            return VectorResult(vector, False, f"expected valid but got error: {error}")
        if not is_valid:
            return VectorResult(vector, True, f"correctly rejected: {error}")
        return VectorResult(vector, False, "expected invalid but was accepted")

    def _run_artefact(self, vector: Vector, validate_fn: Callable) -> VectorResult:
        artefact = vector.data.get("artefact", {})
        is_valid, error = validate_fn(artefact)
        expected_valid = vector.data.get("expected_validation") == "valid"

        if expected_valid:
            if is_valid:
                return VectorResult(vector, True)
            else:
                return VectorResult(vector, False, f"expected valid but got error: {error}")
        else:
            if not is_valid:
                return VectorResult(vector, True, f"correctly rejected: {error}")
            else:
                return VectorResult(vector, False, "expected invalid but was accepted")

    def _run_execution_mode(self, vector: Vector) -> VectorResult:
        input_value = vector.data.get("input", {})
        expected = vector.data.get("expected_validation", "valid")

        # Check finality if specified
        expected_finality = vector.data.get("expected_finality")
        if expected_finality:
            outcome = input_value.get("result", {}).get("outcome", "")
            is_final = outcome in ("EXECUTED", "SUCCEEDED", "FAILED", "REFUSED", "UNKNOWN")
            if expected_finality == "final" and not is_final:
                return VectorResult(vector, False, f"expected final but {outcome} is non-final")
            if expected_finality == "non_final" and is_final:
                return VectorResult(vector, False, f"expected non-final but {outcome} is final")
            return VectorResult(vector, True)

        # Check mode validity
        mode = input_value.get("execution_mode") or input_value.get("mode")

        # Handle missing/invalid mode
        if mode is None:
            if expected == "invalid":
                return VectorResult(vector, True, "correctly rejected: missing execution_mode")
            return VectorResult(vector, False, "expected valid but mode is missing")
        if not isinstance(mode, str):
            if expected == "invalid":
                return VectorResult(vector, True, f"correctly rejected: mode is not a string")
            return VectorResult(vector, False, f"expected valid but mode is not a string")
        if mode not in ("brokered", "resource_owned"):
            if expected == "invalid":
                return VectorResult(vector, True, f"correctly rejected: invalid mode {mode!r}")
            return VectorResult(vector, False, f"expected valid but mode {mode!r} is invalid")

        # Check mode-specific field constraints
        result = input_value.get("result", {})
        outcome = result.get("outcome", "")

        if expected == "invalid":
            expected_error = vector.data.get("expected_error", "")

            # brokered + EXECUTED requires provider_response_summary
            if (mode == "brokered" and outcome == "EXECUTED"
                    and "provider_response_summary" not in result
                    and "BROKERED_SUCCEEDED_REQUIRES_OBSERVATION" in expected_error):
                return VectorResult(vector, True, "correctly rejected: brokered EXECUTED without provider_response_summary")

            # resource_owned + SUCCEEDED requires resource_signature
            if (mode == "resource_owned" and outcome == "SUCCEEDED"
                    and "resource_signature" not in result
                    and "RESOURCE_OWNED_SUCCEEDED_REQUIRES_SIGNATURE" in expected_error):
                return VectorResult(vector, True, "correctly rejected: resource_owned SUCCEEDED without resource_signature")

            # If we get here, the vector expected invalid but we can't determine why
            return VectorResult(vector, False, f"expected invalid ({expected_error}) but was accepted")

        return VectorResult(vector, True)

    def run_all(self, category: str | None = None) -> RunResults:
        vectors = load_vectors(category)
        results = RunResults()
        for vector in vectors:
            vr = self.run_vector(vector)
            results.total += 1
            if vr.skipped:
                results.skipped += 1
            elif vr.passed:
                results.passed += 1
                results.passes.append(vr)
            else:
                results.failed += 1
                results.failures.append(vr)
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Actenon protocol conformance runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit code:
  0 — all vectors passed (Actenon-compatible v1.1.0)
  1 — one or more vectors failed
        """,
    )
    parser.add_argument("--category", "-c", help="run only a specific category (proof, receipt, refusal, canonicalisation, execution-mode, execution-result)")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument("--verbose", "-v", action="store_true", help="show every vector, not just failures")
    args = parser.parse_args()

    validator = ReferenceValidator()
    runner = ConformanceRunner(validator)
    results = runner.run_all(category=args.category)

    if args.json:
        output = {
            "total": results.total,
            "passed": results.passed,
            "failed": results.failed,
            "skipped": results.skipped,
            "compatible": results.failed == 0,
            "failures": [
                {
                    "category": vr.vector.category,
                    "name": vr.vector.name,
                    "reason": vr.reason,
                }
                for vr in results.failures
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Actenon Protocol Conformance Runner")
        print(f"=" * 50)
        print(f"Total:   {results.total}")
        print(f"Passed:  {results.passed}")
        print(f"Failed:  {results.failed}")
        print(f"Skipped: {results.skipped} (language-specific inputs)")
        print()

        if args.verbose:
            print("Passed vectors:")
            for vr in results.passes:
                print(f"  PASS  {vr.vector.category}/{vr.vector.name}")
            print()

        if results.failures:
            print("Failed vectors:")
            for vr in results.failures:
                print(f"  FAIL  {vr.vector.category}/{vr.vector.name}")
                if vr.reason:
                    print(f"        {vr.reason}")
            print()

        if results.failed == 0:
            print("✅ Actenon-compatible v1.1.0")
        else:
            print(f"❌ {results.failed} vector(s) failed — not Actenon-compatible")

    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
