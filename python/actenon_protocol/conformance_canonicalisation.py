"""Reusable conformance command for ACTENON-JCS-STRICT-1 canonicalisation.

From a checkout of actenon-protocol:
  python -m actenon_protocol.conformance_canonicalisation [--verbose]

From anywhere else (the vectors are not shipped in the wheel), point it at a
copy of conformance/vectors/canonicalisation/:
  python -m actenon_protocol.conformance_canonicalisation --vectors PATH

The command loads the normative canonicalisation vectors and verifies that
the INSTALLED actenon_protocol reference implementation produces the
expected canonical bytes for valid vectors and raises CanonicalisationError
for invalid vectors. It does not test another package's canonicaliser.

Exit code 0 = all vectors passed.
Exit code 1 = one or more vectors failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from actenon_protocol.canonicalisation import (
    CanonicalisationError,
    canonicalize_json,
    parse_strict,
)


def _default_candidates() -> list[Path]:
    pkg_dir = Path(__file__).resolve().parent
    return [
        # Editable install / source checkout: <repo>/python/actenon_protocol
        pkg_dir.parent.parent / "conformance" / "vectors" / "canonicalisation",
        # Current working directory is a checkout of actenon-protocol
        Path.cwd() / "conformance" / "vectors" / "canonicalisation",
    ]


def _find_vectors_dir() -> Path:
    """Find the conformance vectors directory."""
    candidates = _default_candidates()
    for c in candidates:
        if (c / "valid").is_dir():
            return c
    raise FileNotFoundError(
        "could not find the canonicalisation vectors (they are not shipped in the "
        "wheel). Pass --vectors PATH/TO/conformance/vectors/canonicalisation. "
        f"Searched: {[str(c) for c in candidates]}"
    )


def run_conformance(verbose: bool = False, vectors_dir: Path | None = None) -> int:
    """Run all canonicalisation conformance vectors. Returns 0 on success, 1 on failure."""
    vectors_dir = vectors_dir if vectors_dir is not None else _find_vectors_dir()
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
                try:
                    canonicalize_json(parse_strict(input_json))
                    print(f"  FAIL  {name}: expected CanonicalisationError but got success")
                    failed += 1
                except (CanonicalisationError, TypeError):
                    if verbose:
                        print(f"  PASS  {name} (correctly rejected)")
                    passed += 1
                except Exception as e:
                    print(
                        f"  FAIL  {name}: expected CanonicalisationError, got {type(e).__name__}: {e}"
                    )
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
        print("  FAIL  deeply_nested_exceeds_limit: expected error but got success")
        failed += 1
    except (CanonicalisationError, ValueError, RecursionError):
        if verbose:
            print("  PASS  deeply_nested_exceeds_limit (correctly rejected)")
        passed += 1

    # ── Oversized structure (string > 1 MiB) ─────────────────────
    big_string = "x" * (1_048_577)
    try:
        from actenon_protocol.canonicalisation import canonicalize_bytes

        canonicalize_bytes(big_string)
        print("  FAIL  oversized_structure: expected error but got success")
        failed += 1
    except (CanonicalisationError, ValueError):
        if verbose:
            print("  PASS  oversized_structure (correctly rejected)")
        passed += 1

    print(f"\n{'=' * 60}")
    print(f"Canonicalisation conformance: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'=' * 60}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m actenon_protocol.conformance_canonicalisation",
        description="Run the ACTENON-JCS-STRICT-1 vectors against the installed reference.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="print every vector")
    parser.add_argument(
        "--vectors",
        type=Path,
        help="path to conformance/vectors/canonicalisation (required outside a checkout)",
    )
    args = parser.parse_args(argv)
    try:
        vectors_dir = args.vectors if args.vectors is not None else _find_vectors_dir()
    except FileNotFoundError as e:
        print(f"conformance_canonicalisation: {e}", file=sys.stderr)
        return 2
    if not (vectors_dir / "valid").is_dir() or not (vectors_dir / "invalid").is_dir():
        print(
            f"conformance_canonicalisation: {vectors_dir} has no valid/ and invalid/ vectors",
            file=sys.stderr,
        )
        return 2
    return run_conformance(verbose=args.verbose, vectors_dir=vectors_dir)


if __name__ == "__main__":
    sys.exit(main())
