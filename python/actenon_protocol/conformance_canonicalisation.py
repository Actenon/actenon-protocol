"""Reusable conformance command for ACTENON-JCS-STRICT-1 canonicalisation.

Run from any Actenon repository:
  python -m actenon_protocol.conformance_canonicalisation

Or as a script:
  python -m actenon_protocol.conformance_canonicalisation --verbose

The command loads all normative vectors from conformance/vectors/canonicalisation/
and verifies that the Python reference implementation produces the expected
canonical bytes for valid vectors and raises CanonicalisationError for invalid
vectors.

Exit code 0 = all vectors passed.
Exit code 1 = one or more vectors failed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from actenon_protocol.canonicalisation import (
    CanonicalisationError,
    canonicalize_json,
)


def _find_vectors_dir() -> Path:
    """Find the conformance vectors directory."""
    # Try relative to the package location
    pkg_dir = Path(__file__).resolve().parent
    # The data dir is at actenon_protocol/data/ (installed) or the repo root
    # is two levels up from the python package.
    candidates = [
        pkg_dir.parent.parent.parent / "conformance" / "vectors" / "canonicalisation",
        pkg_dir / "data" / "canonicalisation",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: search from cwd
    cwd_candidate = Path.cwd() / "conformance" / "vectors" / "canonicalisation"
    if cwd_candidate.exists():
        return cwd_candidate
    raise FileNotFoundError(
        f"Could not find conformance vectors directory. Searched: {[str(c) for c in candidates + [cwd_candidate]]}"
    )


def run_conformance(verbose: bool = False) -> int:
    """Run all canonicalisation conformance vectors. Returns 0 on success, 1 on failure."""
    vectors_dir = _find_vectors_dir()
    valid_dir = vectors_dir / "valid"
    invalid_dir = vectors_dir / "invalid"

    passed = 0
    failed = 0
    skipped = 0

    # ── Valid vectors ──────────────────────────────────────────────
    if valid_dir.exists():
        for path in sorted(valid_dir.glob("*.json")):
            with path.open() as f:
                vector = json.load(f)

            input_value = vector.get("input")
            expected = vector.get("expected_canonical")
            name = vector.get("name", path.stem)

            if input_value is None or expected is None:
                if verbose:
                    print(f"  SKIP  {name} (no input or expected)")
                skipped += 1
                continue

            try:
                actual = canonicalize_json(input_value)
            except Exception as e:
                print(f"  FAIL  {name}: canonicalize_json raised {type(e).__name__}: {e}")
                failed += 1
                continue

            if actual == expected:
                if verbose:
                    print(f"  PASS  {name} -> {actual}")
                passed += 1
            else:
                print(f"  FAIL  {name}: expected {expected!r}, got {actual!r}")
                failed += 1

    # ── Invalid vectors (JSON-representable) ──────────────────────
    if invalid_dir.exists():
        for path in sorted(invalid_dir.glob("*.json")):
            with path.open() as f:
                vector = json.load(f)

            name = vector.get("name", path.stem)
            input_json = vector.get("input_json")

            if input_json is not None:
                # Parse the JSON string, then try to canonicalise.
                # For floats, we need to parse with float support.
                try:
                    parsed = json.loads(input_json)
                except json.JSONDecodeError:
                    # NaN/Infinity are not valid JSON — skip if we can't parse
                    if verbose:
                        print(f"  SKIP  {name} (not parseable as JSON)")
                    skipped += 1
                    continue

                try:
                    canonicalize_json(parsed)
                    print(f"  FAIL  {name}: expected CanonicalisationError but got success")
                    failed += 1
                except (CanonicalisationError, TypeError):
                    if verbose:
                        print(f"  PASS  {name} (correctly rejected)")
                    passed += 1
                except Exception as e:
                    print(f"  FAIL  {name}: expected CanonicalisationError, got {type(e).__name__}: {e}")
                    failed += 1
            else:
                # Python-only vectors — skip in the CLI (tested in the pytest suite)
                if verbose:
                    print(f"  SKIP  {name} (Python-only)")
                skipped += 1

    # ── Python-only adversarial tests ─────────────────────────────
    # These can't be represented in JSON, so we test them directly.
    python_only_tests = [
        ("non_string_key", lambda: canonicalize_json({1: "a"})),
        ("unsupported_type_set", lambda: canonicalize_json({1, 2, 3})),
        ("unsupported_type_bytes", lambda: canonicalize_json(b"hello")),
        ("float_nan_direct", lambda: canonicalize_json(float("nan"))),
        ("float_inf_direct", lambda: canonicalize_json(float("inf"))),
        ("float_neg_inf_direct", lambda: canonicalize_json(float("-inf"))),
    ]

    for name, fn in python_only_tests:
        try:
            fn()
            print(f"  FAIL  {name}: expected error but got success")
            failed += 1
        except (CanonicalisationError, TypeError):
            if verbose:
                print(f"  PASS  {name} (correctly rejected)")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: expected CanonicalisationError, got {type(e).__name__}: {e}")
            failed += 1

    # ── Deeply nested test (33 levels, exceeds limit of 32) ───────
    deep_value = {"value": "bottom"}
    for _ in range(33):
        deep_value = {"n": deep_value}
    try:
        canonicalize_json(deep_value)
        print(f"  FAIL  deeply_nested_exceeds_limit: expected error but got success")
        failed += 1
    except (CanonicalisationError, ValueError, RecursionError):
        if verbose:
            print(f"  PASS  deeply_nested_exceeds_limit (correctly rejected)")
        passed += 1

    # ── Oversized structure (string > 1 MiB) ─────────────────────
    big_string = "x" * (1_048_577)
    try:
        from actenon_protocol.canonicalisation import canonicalize_bytes
        canonicalize_bytes(big_string)
        print(f"  FAIL  oversized_structure: expected error but got success")
        failed += 1
    except (CanonicalisationError, ValueError):
        if verbose:
            print(f"  PASS  oversized_structure (correctly rejected)")
        passed += 1

    print(f"\n{'='*60}")
    print(f"Canonicalisation conformance: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sys.exit(run_conformance(verbose=verbose))
