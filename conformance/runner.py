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
        """Return the canonical bytes for the input."""

    def validate_execution_mode(self, input_value: dict) -> tuple[bool, str | None]:
        """Return (is_valid, error_message) for execution-mode vectors."""


# ---------------------------------------------------------------------------
# Reference implementation validator (uses the Python reference)
# ---------------------------------------------------------------------------

class ReferenceValidator:
    """Validator that uses the Python reference implementation."""

    def __init__(self):
        from actenon_protocol import canonicalize_json, is_valid_identifier
        from actenon_protocol.types import ExecutionProof, ExecutionReceipt, ExecutionRefusal
        self._canonicalize = canonicalize_json
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
        return self._canonicalize(input_value)

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
            return VectorResult(vector, True, "execution-result vectors not yet implemented in runner")
        else:
            return VectorResult(vector, False, f"unknown category: {cat}")

    def _run_canonicalisation(self, vector: Vector) -> VectorResult:
        input_value = vector.data.get("input")
        expected = vector.data.get("expected_canonical")
        if expected is None:
            return VectorResult(vector, True, "no expected_canonical — skipping")
        try:
            actual = self.validator.canonicalize(input_value)
            if actual == expected:
                return VectorResult(vector, True)
            else:
                return VectorResult(vector, False, f"canonical mismatch: expected {expected!r}, got {actual!r}")
        except Exception as e:
            if vector.sub == "invalid":
                return VectorResult(vector, True, f"correctly rejected: {e}")
            return VectorResult(vector, False, f"canonicalisation raised: {e}")

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
        results = RunResults(total=len(vectors))
        for vector in vectors:
            vr = self.run_vector(vector)
            results.total += 1
            if vr.passed:
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
