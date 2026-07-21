# Integration Guide — `actenon-protocol` v1.0.0

> How the four Actenon implementation repos adopt the neutral protocol.

This document is for maintainers of `actenon-kernel`, `actenon-permit`, `actenon-cloud`, and `actenon-scan`. It is NOT itself part of the protocol — it lives in the protocol repo as guidance for downstream consumers.

## Audit baseline

The protocol was extracted from the four implementation repos at these commits:

| Repo | Commit SHA | Audit date |
|---|---|---|
| `actenon-kernel` | `2b080d3574312abbca01f426a96f91c8990e344c` | 2026-07-21 |
| `actenon-permit` | `8d66fdac92888d397d01150899846be2090246b3` | 2026-07-21 |
| `actenon-cloud` | `8af48161eeac5a435f8eacbbbd96f40b9565936e` | 2026-07-20 |
| `actenon-scan` | `10c40df621d0ab9720baf25f4cdf644fc2a7fac2` | 2026-07-21 |

The full audit report lives in the programme-level working docs (`ACTENON_AUDIT_REPORT.md`).

## What the protocol gives you

A single source of truth for:

- `ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal` wire shapes (`schemas/*.v1.json`)
- The `ACTENON-JCS-STRICT-1` canonicalisation profile (`canonicalisation/ACTENON-JCS-STRICT-1.md`)
- The 20-code refusal taxonomy with two-layer disclosure (`refusals/catalogue.v1.yaml`)
- Identifier prefixes (`identifiers/prefixes.v1.yaml`)
- Conformance vectors (`conformance/vectors/`)
- Python and TypeScript reference types (`python/`, `typescript/`)

## What the protocol does NOT give you

- Policy evaluation, approvals, budgets, tenant models, credential storage, provider adapters, Cloud persistence, billing, the complete `AuthorisedExecutionIntent` lifecycle, action execution. Those remain owned by the implementation repos.

## Recommended adoption order

The phases below are gated: each phase unblocks the next. Do not skip ahead. Every phase is independently reviewable and mergeable.

### Phase A — Kernel (highest leverage, lowest risk)

The Kernel is already the closest to the protocol. The main deltas are:

1. **Rename `canonicalization` → `canonicalisation`** on the wire (British spelling, per `protocol/04-claim-names.md`). Internal Python field names can stay US-spelling; only the JSON serialisation needs to change. Backward-compat: accept the US spelling on input for v1.x.
2. **Emit `execution_mode`** on every `PCCB`. The Kernel already knows the mode (it's inferred from the verifier's deployment); make it explicit on the artefact.
3. **Add `proof_` prefix** to `pccb_id` on the wire. Internal `pccb_id` can stay; only the wire serialisation changes.
4. **Accept `RFC8785-JCS`** as a deprecated alias for `ACTENON-JCS-STRICT-1` (Kernel already does this at HEAD — confirmed in audit).
5. **Import `FailureCode` from `actenon_protocol`** instead of defining it locally. The protocol's `refusal_codes.py` exports the same 16 codes the Kernel already has, plus 4 new ones, all as a StrEnum. The Kernel's `outcomes.py` becomes a thin re-export.

Files likely to change:
- `actenon/proof/canonical.py` — no change (already conforms)
- `actenon/models/contracts.py` — add `execution_mode`, `grant_id`, `authority_decision_id`, `evidence_links`, `custom_claims` to `PCCB`; rename `canonicalization` → `canonicalisation` on JSON serialisation only
- `actenon/outcomes.py` — replace with `from actenon_protocol.refusal_codes import RefusalCode as FailureCode, ...`
- `actenon/verifier/*` — accept the renamed `canonicalisation` field; emit `execution_mode` on receipts/refusals

### Phase B — Permit

Permit has the largest gap to close (audit finding P-01: bearer token is HMAC, not PCCB). The protocol defines the target shape; Permit implements toward it.

1. **Replace `grant_to_token()` output** with `v1.<b64url(PCCB)>` using the protocol's `ExecutionProof` schema. The (currently dead) `pccb_to_token_payload` becomes live.
2. **Surface structured `disclosed_code` + `internal_code`** in the gateway HTTP DENY response, instead of free-text.
3. **Adopt `execution_attempt_id`** as the idempotency key (separate from `proof_id`).
4. **Add `parent_grant_id`** to attenuated children for revocation cascade.
5. **Drop the `skills/`, `upload/`, `tool-results/` contamination** and the three broken gitlinks (audit findings P-02, P-03).

Files likely to change:
- `src/actenon_permit/token.py` — produce protocol-shaped `ExecutionProof`
- `src/actenon_permit/kernel_bridge.py` — un-dead `pccb_to_token_payload` / `token_payload_to_pccb`
- `src/actenon_permit/gateway.py:284-297` — surface `disclosed_code` + `internal_code`
- `src/actenon_permit/model.py` — add `parent_grant_id` to `Grant.attenuate()`
- `src/actenon_permit/control.py:226-236` — cascade revocation
- Repo root — remove contamination

### Phase C — Cloud

Cloud has the deepest internal coupling (audit finding C-02). Adoption is the most work but also the highest payoff — once Cloud calls only the published Kernel API, Kernel can refactor freely.

1. **Replace `json.dumps(sort_keys=True)` canonicalisation** with `actenon_protocol.canonicalize_bytes()` in `app/services/issuance.py`, `signing.py`, `receipts.py`, `escrow.py`.
2. **Wire `kernel_bridge.export_kernel_pccb`** into `IssuanceService.issue_proof` runtime path (currently dead, tests-only — audit C-03).
3. **Replace Kernel-internal imports** with `actenon_protocol` public API imports. Touch every file listed in audit C-02.
4. **Stop redefining Kernel schemas locally** in `schemas/kernel/*.json` (audit C-10).
5. **Call Permit's broker** for credential release instead of minting Cloud's own JWT (audit C-04).
6. **Update Cloud tests** to assert on `disclosed_code` (public-safe) instead of raw `refusal_code` strings (audit C-01).
7. **Reconcile `SHIP_STATUS.md`** with `CONTROL_PLANE_RELEASE_READINESS.md` (audit DC-08).

### Phase D — Scan

Scan has two critical drift items to fix (audit S-01, S-02). Both are local to Scan and do not depend on Kernel/Permit/Cloud adoption.

1. **Remove `permit_check`, `permit_authorize`, `permit_validate`** from `default_rules.json` guards (audit S-01).
2. **Add non-Actenon guard recognition** (OAuth, RBAC, JWT, OPA, Casbin, IAM, CF Access, mTLS, Zanzibar) — audit S-02.
3. **Recognise the protocol's class-level API** (`ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`) in addition to the existing `verify_proof` function-call pattern.
4. **Recognise `execution_mode`** as an explicit field on scanned artefacts (so Scan can flag a `brokered` proof presented to a `resource_owned` verifier).
5. **Fix `action.yml` command injection** (audit S-03) and **inline suppression key mismatch** (audit S-04).
6. **Reconcile versions** (`pyproject.toml` 0.1.3, SARIF `0.1.0`, tags `v0.1.1`/`v1`/`v.0.1.1`) — audit S-14.

## Cross-repo conformance

After all four repos adopt the protocol, the cross-repo conformance test (currently in `actenon-permit/tests/test_cross_repo_conformance.py` with a hardcoded cloud path — audit X-02) should be moved into this repo as `conformance/python/test_cross_repo.py` and run against all four implementations in CI.

## Versioning contract

Once a repo adopts the protocol, it MUST:

1. Pin to a protocol MAJOR version (`actenon-protocol@^1` in `pyproject.toml` / `package.json`).
2. Tolerate any MINOR version within that MAJOR.
3. Refuse to process artefacts from a different MAJOR (with `UNSUPPORTED_PROTOCOL_VERSION`).
4. Update the pin within 90 days of a MAJOR release.

See [VERSIONING.md](VERSIONING.md) § "Consumer pinning requirements".

## Getting help

- File issues at https://github.com/Actenon/actenon-protocol/issues
- Email security@actenon.dev for vulnerability reports (see [SECURITY.md](SECURITY.md))
- Protocol governance: see [GOVERNANCE.md](GOVERNANCE.md)
