"""Compile refusals/catalogue.v1.yaml -> python/actenon_protocol/data/catalogue.v1.json.

This script is run at build time and in CI to pre-compile the YAML catalogue
into JSON. The runtime package loads the JSON (zero-dep) and only falls back
to YAML when the `yaml` extra is installed.

Usage:
    python scripts/compile_yaml_to_json.py            # compile
    python scripts/compile_yaml_to_json.py --check    # fail if out of sync

Exit codes:
    0  success (or in --check mode: JSON is in sync)
    1  compilation error
    2  --check mode and JSON is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml is required to run this script. Install with "
        "`pip install pyyaml` or `pip install actenon-protocol[yaml]`.",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = REPO_ROOT / "refusals" / "catalogue.v1.yaml"
JSON_PATH = REPO_ROOT / "python" / "actenon_protocol" / "data" / "catalogue.v1.json"


def compile_yaml_to_json() -> dict:
    """Read the YAML catalogue and return the parsed dict."""
    if not YAML_PATH.exists():
        raise FileNotFoundError(f"YAML catalogue not found: {YAML_PATH}")
    with YAML_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Catalogue YAML did not parse to a dict")
    return data


def write_json(data: dict) -> None:
    """Write the JSON catalogue, sorted and deterministically formatted."""
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")


def check_in_sync() -> bool:
    """Return True if the JSON file is in sync with the YAML."""
    if not JSON_PATH.exists():
        return False
    expected = compile_yaml_to_json()
    with JSON_PATH.open("r", encoding="utf-8") as f:
        actual = json.load(f)
    return expected == actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail with exit code 2 if the JSON is stale.",
    )
    args = parser.parse_args()

    if args.check:
        if check_in_sync():
            print(f"OK: {JSON_PATH.name} is in sync with {YAML_PATH.name}")
            return 0
        print(
            f"STALE: {JSON_PATH.name} is out of sync with {YAML_PATH.name}. "
            f"Run `python scripts/compile_yaml_to_json.py` to regenerate.",
            file=sys.stderr,
        )
        return 2

    data = compile_yaml_to_json()
    write_json(data)
    print(f"Wrote {JSON_PATH.relative_to(REPO_ROOT)} ({len(json.dumps(data))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
