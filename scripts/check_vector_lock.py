#!/usr/bin/env python3
"""Verify (or rewrite) the hash lock over the conformance vectors.

The README describes the conformance vectors as "hash-locked": once
published, a vector's bytes never change, so an implementation that passes
them keeps passing them. This script is what makes that true.
``conformance/vectors.sha256`` records the SHA-256 of every
``conformance/vectors/**/*.json`` file in ``sha256sum`` format, so it can
also be checked without Python::

    cd conformance/vectors && sha256sum -c ../vectors.sha256

Usage:
    python scripts/check_vector_lock.py            # verify; exit 1 on drift
    python scripts/check_vector_lock.py --write    # re-lock after ADDING vectors

Only rewrite the lock when adding new vectors (a MINOR protocol change, see
conformance/vectors/README.md). Changing or deleting a locked vector breaks
the "frozen forever" guarantee and must not be papered over with --write.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VECTORS_DIR = REPO_ROOT / "conformance" / "vectors"
LOCK_PATH = REPO_ROOT / "conformance" / "vectors.sha256"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute(vectors_dir: Path) -> dict[str, str]:
    """Return {relative posix path: sha256 hex} for every vector file."""
    return {
        p.relative_to(vectors_dir).as_posix(): _digest(p)
        for p in sorted(vectors_dir.rglob("*.json"))
    }


def read_lock(lock_path: Path) -> dict[str, str]:
    """Parse a ``sha256sum``-format lock file."""
    entries: dict[str, str] = {}
    for lineno, line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64 or not name:
            raise ValueError(f"{lock_path}:{lineno}: malformed lock line {line!r}")
        if name in entries:
            raise ValueError(f"{lock_path}:{lineno}: duplicate entry {name!r}")
        entries[name] = digest
    return entries


def check_lock(vectors_dir: Path, lock_path: Path) -> list[str]:
    """Return a list of problems; empty means every vector matches the lock."""
    locked = read_lock(lock_path)
    actual = compute(vectors_dir)
    problems = []
    for name in sorted(locked.keys() - actual.keys()):
        problems.append(f"locked vector missing from disk: {name}")
    for name in sorted(actual.keys() - locked.keys()):
        problems.append(f"vector not in lock (add it with --write only if it is new): {name}")
    for name in sorted(locked.keys() & actual.keys()):
        if locked[name] != actual[name]:
            problems.append(
                f"vector changed after it was locked: {name} "
                f"(locked {locked[name][:12]}…, now {actual[name][:12]}…)"
            )
    return problems


def write_lock(vectors_dir: Path, lock_path: Path) -> int:
    entries = compute(vectors_dir)
    lock_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in entries.items()), encoding="utf-8"
    )
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the lock from disk")
    args = parser.parse_args()
    if args.write:
        n = write_lock(VECTORS_DIR, LOCK_PATH)
        print(f"wrote {LOCK_PATH.relative_to(REPO_ROOT)} ({n} vectors)")
        return 0
    problems = check_lock(VECTORS_DIR, LOCK_PATH)
    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print(f"OK: all {len(read_lock(LOCK_PATH))} conformance vectors match {LOCK_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
