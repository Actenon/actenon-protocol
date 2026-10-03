#!/usr/bin/env python3
"""Resolve a manual npm retry to existing, unchanged and CI-approved tagged source.

The running workflow is repaired on main; the release tag is never moved. The
normal shared release gate still verifies the actual tag's source commit. The
package tree, gate implementation and required-check list must be identical in
the running workflow's commit and the tagged source. Consequently npm provenance
names a workflow commit with exactly the same package inputs as the release tag.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import release_gate

ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(r"ts-types-v[0-9]+\.[0-9]+\.[0-9]+")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def prepare() -> int:
    if (
        os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
    ):
        raise ValueError("A manual retry must run the repaired workflow from main")
    tag = os.environ.get("RELEASE_TAG", "")
    if not TAG.fullmatch(tag):
        raise ValueError("release_tag must be an existing ts-types-v<major>.<minor>.<patch> tag")
    ref = f"refs/tags/{tag}"
    if git("cat-file", "-t", ref) != "tag":
        raise ValueError("The release must use an existing annotated tag")
    source = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if git("rev-parse", f"{source}:typescript") != git("rev-parse", "HEAD:typescript"):
        raise ValueError("Tagged package inputs differ from the running workflow's package inputs")
    for path in ("scripts/release_gate.py", ".github/required-checks.json"):
        if git("rev-parse", f"{source}:{path}") != git("rev-parse", f"HEAD:{path}"):
            raise ValueError(f"The original release gate must remain unchanged: {path}")

    # These context values come from a validated, annotated Git ref, not caller
    # supplied SHAs. The gate still requires that exact commit on origin/main
    # and all original required release checks successful on that commit.
    original_ref, original_sha = os.environ.get("GITHUB_REF"), os.environ.get("GITHUB_SHA")
    try:
        os.environ["GITHUB_REF"], os.environ["GITHUB_SHA"] = ref, source
        result = release_gate.gate(
            release_gate.version_from("typescript/package.json"), "ts-types-v"
        )
    finally:
        for key, old in (("GITHUB_REF", original_ref), ("GITHUB_SHA", original_sha)):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    if result:
        return result
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise ValueError(
            "GITHUB_OUTPUT is required to bind downstream jobs to the verified release ref"
        )
    with Path(output).open("a", encoding="utf-8") as stream:
        stream.write(f"release_ref={ref}\n")
    print(
        f"Manual retry preserves {ref} at {source}; package inputs and release gate are unchanged"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(prepare())
    except (ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"::error::{exc}")
