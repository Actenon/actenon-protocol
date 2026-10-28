"""Regression tests for structured candidate-stage version waiver (R2 / F06)."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys

from packaging.version import Version
import pytest


def _load_coherence_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_version_coherence.py"
    spec = importlib.util.spec_from_file_location("check_version_coherence", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_structured_waiver_rejects_prose_and_substring_matches(tmp_path: Path) -> None:
    mod = _load_coherence_module()
    findings = tmp_path / "FINDINGS.md"

    # Negative prose ("Do not publish 1.6.0") must NOT pass:
    findings.write_text("# FINDINGS\nDo not publish 1.6.0 or 11.6.0.\n", encoding="utf-8")
    ok, reason = mod.validate_staged_candidate_waiver(
        "actenon-protocol",
        Version("1.6.0"),
        Version("1.4.0"),
        findings_path=findings,
        today=date(2026, 10, 28),
    )
    assert ok is False
    assert "no structured" in str(reason)

    # Substring version ("11.6.0") in structured block must NOT match "1.6.0":
    findings.write_text(
        """# FINDINGS
```version-waiver
{
  "package": "actenon-protocol",
  "staged_version": "11.6.0",
  "published_version": "1.4.0",
  "status": "RELEASE_BLOCKED",
  "owner": "rossbuckley1990-hash",
  "reason": "wrong version",
  "expires_at": "2026-11-05"
}
```
""",
        encoding="utf-8",
    )
    ok, reason = mod.validate_staged_candidate_waiver(
        "actenon-protocol",
        Version("1.6.0"),
        Version("1.4.0"),
        findings_path=findings,
        today=date(2026, 10, 28),
    )
    assert ok is False
    assert "does not exactly match" in str(reason)


def test_structured_waiver_enforces_expiry_and_status(tmp_path: Path) -> None:
    mod = _load_coherence_module()
    findings = tmp_path / "FINDINGS.md"

    # Expired waiver:
    findings.write_text(
        """# FINDINGS
```version-waiver
{
  "package": "actenon-protocol",
  "staged_version": "1.6.0",
  "published_version": "1.4.0",
  "status": "RELEASE_BLOCKED",
  "owner": "rossbuckley1990-hash",
  "reason": "expired",
  "expires_at": "2026-10-20"
}
```
""",
        encoding="utf-8",
    )
    ok, reason = mod.validate_staged_candidate_waiver(
        "actenon-protocol",
        Version("1.6.0"),
        Version("1.4.0"),
        findings_path=findings,
        today=date(2026, 10, 28),
    )
    assert ok is False
    assert "expired" in str(reason)

    # Unbounded expiry (>14 days):
    findings.write_text(
        """# FINDINGS
```version-waiver
{
  "package": "actenon-protocol",
  "staged_version": "1.6.0",
  "published_version": "1.4.0",
  "status": "RELEASE_BLOCKED",
  "owner": "rossbuckley1990-hash",
  "reason": "too far in future",
  "expires_at": "2027-01-01"
}
```
""",
        encoding="utf-8",
    )
    ok, reason = mod.validate_staged_candidate_waiver(
        "actenon-protocol",
        Version("1.6.0"),
        Version("1.4.0"),
        findings_path=findings,
        today=date(2026, 10, 28),
    )
    assert ok is False
    assert "exceeds 14-day bound" in str(reason)


def test_repo_findings_waiver_is_valid_for_candidate_and_blocked_for_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_coherence_module()
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(mod, "pypi_latest", lambda _pkg: Version("1.4.0"))
    monkeypatch.setattr(mod, "newest_release_tag", lambda: Version("1.4.0"))
    monkeypatch.setattr(mod, "version_bump_age_seconds", lambda _v: 20 * 86400)

    # Candidate mode (`--mode main`) passes with explicit RELEASE_BLOCKED warning:
    assert mod.main(["--mode", "main"]) == 0
    # Release mode (`--mode release`) fails because 1.6.0 is not yet tagged/published:
    assert mod.main(["--mode", "release"]) == 1
