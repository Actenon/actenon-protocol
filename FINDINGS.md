# FINDINGS

Discoveries recorded during review runs. Entries are append-only: when a
finding is superseded, a resolution block is added; the original is never
edited or deleted.

## FINDING: package version rolled back on `main` (2026-07-24 run)

**Severity:** defect — shipped to `main`, corrected same day.

**What happened.** Commit `9e637e4` (PR #7, "Close doc-to-code drift: make
'zero dependencies' claim true") lowered `pyproject.toml` from `1.2.0` to
`1.1.0`. At that point tag `v1.2.0` existed and PyPI served `1.2.0`, so `main`
was labelled *behind* the published package: a source build from `main`
produced an artifact stamped `1.1.0` that actually contained post-`1.2.0`
code.

**Why it happened.** The PR's stated rationale was version coherence:
`pyproject.toml` (`1.2.0`) disagreed with `version.py` and the README version
badge (both `1.1.0`), and "the previous 1.2.0 was unreachable from the package
code". The rationale conflated two different versions:

* `PROTOCOL_VERSION` in `version.py` is the **wire protocol** version. It was
  legitimately `1.1.0` — no wire semantics changed after protocol `1.1.0`.
* `pyproject.toml` carries the **package** version. It was legitimately
  `1.2.0` — the `v1.2.0` package release added the ecosystem-table tooling
  without touching the wire format.

Faced with the apparent mismatch, the PR resolved it by lowering the
authoritative, published version instead of recognising the two versions as
distinct (or bumping forward). This is exactly the failure mode the operating
rule now names: **never lower a version to make a check pass — bump forward
instead.**

**Contributing factor.** The version-drift CI gate in place at the time
(`version-drift.yml`, WO-19 4.5) only checked "does a tag exist for the
pyproject version?" — a one-directional check that a rollback trivially
satisfies, because the *old* tag exists. The gate could not catch
"repo behind published".

**Resolution (same run).**

* Package version set **forward** to `1.3.0` (not back to `1.2.0`: `main`
  carries additive changes since `v1.2.0` — the pre-compiled JSON catalogue,
  the extras restructure, and CI gates — see CHANGELOG). Tagged and published.
* `VERSIONING.md` now defines the protocol-version / package-version
  distinction explicitly.
* The one-directional drift gate is replaced by a three-way coherence gate
  (`scripts/check_version_coherence.py`): `pyproject >= PyPI` (hard, both
  directions of drift), `newest tag == PyPI` (hard, on main), `pyproject ==
  newest tag` (warn, escalating after 7 days).

**Related discovery.** `VERSIONING.md` declared "Protocol version: 1.0.0"
while `version.py` declared `1.1.0` — the stale doc line predated this run and
likely fed the confusion. Corrected to `1.1.0`.

## FINDING: publishing 1.3.0 exposed downstream reliance on removed transitive deps (2026-07-24 run)

**Severity:** NOTE — downstream CI breakage, fixed same day; no runtime impact.

**What happened.** PR #7's zero-dependency restructure merged to `main` on
2026-07-23 but was first *published* with 1.3.0. The moment 1.3.0 hit PyPI,
consumer CI that relied on the old transitive closure broke:

* `actenon-scan`: every `test` and `drift-gate` job (`ModuleNotFoundError:
  pydantic` in `tests/test_protocol_drift.py`) and the README-claims job
  (`ModuleNotFoundError: yaml` in the ecosystem-table check). Fixed in
  actenon-scan#9 by declaring `actenon-protocol[types]` / `[yaml]`.
* `actenon-permit`: the same ecosystem-check pattern survived only because a
  stale package index still served 1.2.0. Fixed preemptively in
  actenon-permit#16.
* `actenon-kernel`: unaffected — every job that runs the ecosystem check also
  installs the kernel, which depends on pyyaml directly.

**Lesson.** Removing transitive dependencies is a compatible change for the
package itself but a breaking change for consumers who never declared what
they actually import. The fix direction is consumers declaring their real
dependencies (extras), not the protocol restoring fat defaults.
