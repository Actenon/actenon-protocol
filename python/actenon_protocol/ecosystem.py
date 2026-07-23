"""Ecosystem table renderer for Actenon README files.

Single source of truth: ``ecosystem.yaml`` at the protocol repo root,
shipped inside this package as ``actenon_protocol/data/ecosystem.yaml``.

CLI contract
------------
::

    python -m actenon_protocol.ecosystem --check README.md --repo <name>   # exit 1 on drift
    python -m actenon_protocol.ecosystem --write README.md --repo <name>

``--repo`` is REQUIRED. We never auto-detect the repo from ``git remote``:
detection works locally and fails silently under fork checkouts, detached
HEAD, and custom remotes — putting the "← you are here" marker on the
wrong row with nobody noticing. Explicit beats clever.

Output shape
------------
The renderer rewrites only the text between::

    <!-- ECOSYSTEM-TABLE:START -->
    <!-- ECOSYSTEM-TABLE:END -->

Inside that block it emits, in order:

  (a) the four repo rows as a markdown table, with the row matching
      ``--repo`` marked ``← you are here``
  (b) a blank line
  (c) the ``Optional`` line, rendered from the ``optional:`` section of
      ``ecosystem.yaml``::

          **Optional:** [`actenon-cloud`](https://github.com/Actenon/actenon-cloud)
          — a managed control plane (source-available; see its LICENSE). Not
          required by any component above; every capability in this ecosystem
          works without it.

The "Not required by any component above" clause is load-bearing: WO-9's
``test_cloud_optional.py`` makes it machine-checkable, which is precisely
why this is generated rather than hand-copied.

Build vs runtime
----------------
The renderer is shipped inside the package (``pip install actenon-protocol``).
``ecosystem.yaml`` is bundled as package data, so the installed wheel has
no network dependency at runtime. The renderer must never become a runtime
import of any other package — it is a build/CI/doc concern only.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "START_MARKER",
    "END_MARKER",
    "load_ecosystem",
    "render_table",
    "rewrite_readme",
    "main",
]

# --- Markers ---------------------------------------------------------------
START_MARKER = "<!-- ECOSYSTEM-TABLE:START -->"
END_MARKER = "<!-- ECOSYSTEM-TABLE:END -->"

# --- Ecosystem data access -------------------------------------------------
_DATA_FILE = Path(__file__).resolve().parent / "data" / "ecosystem.yaml"


def load_ecosystem() -> dict[str, Any]:
    """Load the bundled ``ecosystem.yaml``.

    The file is shipped as package data inside the wheel; no network access
    is needed at runtime. If the file is missing, the wheel build was
    broken — fail loudly.
    """
    if not _DATA_FILE.exists():
        raise FileNotFoundError(
            f"ecosystem.yaml not found at {_DATA_FILE}. The wheel build did "
            "not bundle it as package data; reinstall actenon-protocol."
        )
    with _DATA_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"ecosystem.yaml: expected a mapping at the top level, got {type(data).__name__}"
        )
    if "repos" not in data:
        raise ValueError("ecosystem.yaml: missing required 'repos' key")
    return data


# --- Rendering -------------------------------------------------------------
def _row_for_repo(repo: dict[str, Any], here: bool) -> str:
    """Render a single repo as a markdown table row."""
    name = repo["name"]
    role = repo.get("role", "")
    deps = repo.get("depends_on", []) or []
    deps_cell = ", ".join(f"`{d}`" for d in deps) if deps else "—"
    pkg_parts: list[str] = []
    if "pypi" in repo:
        pkg_parts.append(f"`{repo['pypi']}` (PyPI)")
    if "npm" in repo:
        pkg_parts.append(f"`{repo['npm']}` (npm)")
    pkg_cell = " · ".join(pkg_parts) if pkg_parts else "—"
    name_cell = f"**`{name}`**"
    if here:
        name_cell += " ← you are here"
    return f"| {name_cell} | {role} | {deps_cell} | {pkg_cell} |"


def _optional_line(opt: dict[str, Any]) -> str:
    """Render the Optional line for an `optional` entry.

    The trailing 'Not required by any component above; ...' clause is
    load-bearing: WO-9's test_cloud_optional.py greps for it verbatim.
    """
    name = opt["name"]
    url = opt["url"]
    summary = opt["summary"]
    licence = opt["licence"]
    note = opt["note"].replace("\n", " ").strip()
    return f"**Optional:** [`{name}`]({url}) — {summary} ({licence}). {note}"


def render_table(here_repo: str) -> str:
    """Render the full ecosystem-table block (markers excluded).

    Returns the text that should sit *between* START_MARKER and END_MARKER,
    including the leading and trailing newlines so the block reads cleanly
    when spliced into a README.
    """
    data = load_ecosystem()
    repos = data["repos"]
    optional = data.get("optional", [])

    if here_repo not in [r["name"] for r in repos]:
        raise ValueError(
            f"--repo {here_repo!r} is not one of the four ecosystem repos: "
            f"{[r['name'] for r in repos]!r}. The renderer does not "
            "auto-detect the current repo from git; pass --repo explicitly."
        )

    lines: list[str] = []
    lines.append("| Repository | Role | Depends on | Packages |")
    lines.append("|---|---|---|---|")
    for r in repos:
        lines.append(_row_for_repo(r, here=(r["name"] == here_repo)))
    lines.append("")  # blank line between rows and Optional
    for opt in optional:
        lines.append(_optional_line(opt))
    # Trailing newline so the END marker sits on its own line cleanly.
    return "\n".join(lines) + "\n"


# --- README rewriting ------------------------------------------------------
def _find_block(readme: str) -> tuple[int, int] | None:
    """Return (start_idx, end_idx) into readme covering the markers + body.

    The slice [start:end] includes both markers and the body between them,
    plus the trailing newline after END (so a re-write doesn't grow the
    file by one newline each run). Returns None if either marker is absent
    or out of order.
    """
    sm = readme.find(START_MARKER)
    em = readme.find(END_MARKER)
    if sm == -1 or em == -1 or em < sm:
        return None
    # Extend end past END_MARKER and its trailing newline (if any).
    end_idx = em + len(END_MARKER)
    if end_idx < len(readme) and readme[end_idx] == "\n":
        end_idx += 1
    return sm, end_idx


def rewrite_readme(readme: str, here_repo: str) -> str:
    """Return a copy of ``readme`` with the ecosystem-table block replaced."""
    span = _find_block(readme)
    if span is None:
        raise ValueError(
            f"README is missing the markers {START_MARKER!r} / "
            f"{END_MARKER!r}. Wrap the existing ecosystem table with them "
            "and re-run."
        )
    body = render_table(here_repo)
    block = f"{START_MARKER}\n{body}{END_MARKER}\n"
    s, e = span
    return readme[:s] + block + readme[e:]


# --- CLI -------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m actenon_protocol.ecosystem",
        description="Render the ecosystem table into a README from ecosystem.yaml.",
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the README block is out of sync with ecosystem.yaml",
    )
    grp.add_argument(
        "--write", action="store_true", help="rewrite the block between the markers in the README"
    )
    p.add_argument("readme", type=Path, help="path to the README.md to check or update")
    p.add_argument(
        "--repo",
        required=True,
        help="name of the repo whose README is being rendered "
        "(marks that row with '← you are here'). REQUIRED.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if not args.readme.exists():
        print(f"ecosystem: {args.readme} not found", file=sys.stderr)
        return 2

    current = args.readme.read_text(encoding="utf-8")
    try:
        expected = rewrite_readme(current, args.repo)
    except ValueError as e:
        print(f"ecosystem: {e}", file=sys.stderr)
        return 2

    if current == expected:
        print(f"ecosystem: in sync ({args.readme}, --repo {args.repo})")
        return 0

    if args.check:
        print(f"ecosystem: DRIFT detected ({args.readme}, --repo {args.repo})")
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=f"{args.readme} (current)",
            tofile=f"{args.readme} (expected)",
            n=2,
        )
        sys.stderr.writelines(diff)
        return 1

    # --write
    args.readme.write_text(expected, encoding="utf-8")
    print(f"ecosystem: wrote rendered table to {args.readme} (--repo {args.repo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
