# Changelog

All notable changes to `actenon-protocol` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the protocol-specific extensions described in [VERSIONING.md](VERSIONING.md).

## [1.0.0] — 2026-07-21

### Context

This is the initial release of `actenon-protocol`. It is the formal extraction of the boundary contract that was previously implicit in the four Actenon implementation repositories (`actenon-kernel`, `actenon-permit`, `actenon-cloud`, `actenon-scan`). The audit baseline for this release is the state of those repos at the following commits:

| Repo | Commit SHA | Audit date |
|---|---|---|
| `actenon-kernel` | `2b080d3574312abbca01f426a96f91c8990e344c` | 2026-07-21 |
| `actenon-permit` | `8d66fdac92888d397d01150899846be2090246b3` | 2026-07-21 |
| `actenon-cloud` | `8af48161eeac5a435f8eacbbbd96f40b9565936e` | 2026-07-20 |
| `actenon-scan` | `10c40df621d0ab9720baf25f4cdf644fc2a7fac2` | 2026-07-21 |

### Added

* **Protocol versioning** — `1.0.0`. See [VERSIONING.md](VERSIONING.md).
* **Canonicalisation profile** — `ACTENON-JCS-STRICT-1` is the canonical label. Strict subset of RFC 8785. Rejects floats. 1 MiB max output. 32-level depth limit. See [canonicalisation/ACTENON-JCS-STRICT-1.md](canonicalisation/ACTENON-JCS-STRICT-1.md).
* **Identifier prefixes** — `intent_`, `authz_`, `grant_`, `proof_`, `exec_`, `rcpt_`, `rful_`. See [identifiers/prefixes.v1.yaml](identifiers/prefixes.v1.yaml).
* **Execution modes** — `brokered` and `resource_owned`. Explicit field on every receipt, refusal, and SDK result. See [protocol/03-execution-modes.md](protocol/03-execution-modes.md).
* **Refusal taxonomy** — 20 canonical refusal codes organised in a two-layer disclosure model (`disclosed_code` for public callers, `internal_code` for trusted callers). See [refusals/catalogue.v1.yaml](refusals/catalogue.v1.yaml).
* **Outcome codes** — `EXECUTED`, `REFUSED`, `PARTIAL`, `UNKNOWN`. See [protocol/08-outcome-codes.md](protocol/08-outcome-codes.md).
* **Schemas** — `ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`, `issuer_metadata`, `evidence_link`, `AuthorisedExecutionIntent` (referenced only — the lifecycle is owned by Permit/Cloud), `_common`. See [schemas/](schemas/).
* **Conformance vectors** — valid and invalid fixtures for canonicalisation, proof, receipt, refusal, and execution-mode distinction. See [conformance/vectors/](conformance/vectors/).
* **Conformance suite** — Python implementation of `ACTENON-JCS-STRICT-1` plus pytest tests for canonicalisation, schema validation, identifiers, refusal catalogue, and execution modes. See [conformance/python/](conformance/python/).
* **Python types** — `actenon_protocol` package with pydantic models mirroring the JSON Schemas. See [python/](python/).
* **TypeScript types** — `@actenon/protocol-types` package with hand-written types matching the JSON Schemas. See [typescript/](typescript/).
* **OpenAPI components** — OpenAPI 3.1 components referencing the JSON Schemas. See [openapi/components.yaml](openapi/components.yaml).

### Compatibility decisions

The following decisions preserve compatibility with the audited implementation repos. They are listed here so that future maintainers can understand what was preserved and what was changed.

| Decision | Rationale |
|---|---|
| Adopt `ACTENON-JCS-STRICT-1` as the canonical canonicalisation label | This is the label the Python Kernel uses at HEAD (`actenon/proof/canonical.py:20`). The audit (finding K-01) found that TypeScript/Go/Rust SDKs only accept `RFC8785-JCS`, and docs reference a third label `actenon-jcs-sha256-v1` that no implementation accepts. Picking `ACTENON-JCS-STRICT-1` matches the most-recently-updated implementation; the SDKs will be updated to accept it. |
| Accept `RFC8785-JCS` as a deprecated alias | Historical proofs in the wild carry this label. The canonicalisation logic is identical; only the label differs. Rejecting historical proofs would break existing deployments. |
| Reject `actenon-jcs-sha256-v1` | This label appears only in documentation and conformance suite metadata — never in any implementation's accepted set. Removing it eliminates a drift vector without breaking any real proof. |
| Preserve the 16 existing `FailureCode` enum members as aliases | The Kernel's `outcomes.py` defines `ALLOWED`, `APPROVAL_REQUIRED`, `NOT_ACTIVE`, `REVOKED`, `EXPIRED`, `SCOPE_DENIED`, `OUT_OF_SCOPE`, `BUDGET_EXCEEDED`, `RATE_LIMITED`, `ENGINE_ERROR`, `PCCB_REQUIRED`, `SIGNATURE_INVALID`, `ACTION_MISMATCH`, `PCCB_EXPIRED`, `DUPLICATE_REPLAY`, `AUDIENCE_MISMATCH`. The protocol's 20-code catalogue covers all of these (with new canonical names) and adds 4 new codes for provider-side outcomes. Existing implementations that emit Kernel-style codes will continue to work; consumers resolve aliases via the catalogue. |
| Preserve the `grant_` and `act_` prefixes from Permit | These are in active use by Permit's `Grant.id` and `Action.action_id`. Changing them would break existing grant tokens. |
| Add `proof_` as the canonical prefix for `ExecutionProof.id` | The Kernel uses `pccb_id` internally. For the neutral protocol, `proof_` is more universal (the brief mandates the artefact name `ExecutionProof`). The Kernel's internal `pccb_id` is implementation-specific. |
| Add `rcpt_`, `rful_`, `exec_`, `authz_` as new prefixes | These artefacts (receipt, refusal, execution attempt, authority decision) did not previously have canonical prefixes. The protocol establishes them. |
| Reject floats in canonicalisation | This matches the Kernel's existing strict profile. Floats produce non-deterministic bytes across implementations (Python's `repr(0.1)` differs from JS's `(0.1).toString()`). The protocol's conformance suite includes a fixture that proves a float input is rejected. Implementations that need to represent fractional values MUST use integer cents or string-encoded decimals. |
| Make `execution_mode` an explicit field on every receipt, refusal, and SDK result | The brief mandates this. The audit (findings P-01, C-04) found that the absence of an explicit mode allowed the trust boundary to collapse (Permit's bearer token was treated as a boundary control in some paths). Making the mode explicit prevents this collapse. |
| Two-layer disclosure model (`disclosed_code` + `internal_code`) | The audit (findings K-04, C-01) found that the Kernel's `public_generic` vs `trusted_detailed` modes were a source of cross-repo drift (Cloud tests asserted on `SIGNATURE_INVALID` but Kernel emits `PROOF_INVALID` in public mode). The two-layer model makes the disclosure explicit on the wire, so consumers always know which layer they are seeing. |

### NOT changed (intentionally)

The following items were considered and explicitly NOT changed in this release:

* **The Kernel's `FailureCode` enum members.** They remain valid aliases. The protocol does NOT require implementations to rename their internal enums.
* **The Kernel's `PCCBMinter` / `PCCBVerifier` API.** The protocol is wire-level; it does not constrain the implementation's class names.
* **Permit's `Grant` schema.** The Grant is an authority-broker artefact, not a boundary artefact. It is owned by Permit, not by the protocol.
* **Cloud's `IssuedProof` ORM row.** Same reason — Cloud-internal persistence, not a boundary artefact.
* **Scan's guard vocabulary.** Scan is an independent scanner; its guard vocabulary is its own concern.

### Known unresolved questions

These are documented in the completion-gate report and tracked for future minor versions:

1. **Replay-store contract.** The protocol defines `REPLAY_DETECTED` but does not specify the replay-store API. Should the protocol own a `ReplayStore` interface, or is that an implementation concern? (Current position: implementation concern. The protocol only specifies that the verifier MUST consult a replay store.)
2. **Idempotency key.** The audit (finding K-04) found that the Kernel conflates replay with idempotency. The protocol introduces `execution_attempt_id` as the idempotency key (separate from `proof_id` which is the replay key). This separation is documented but not yet tested across implementations.
3. **Issuer-status discovery.** The protocol defines `issuer_metadata` but does not specify how a verifier discovers the issuer's current status (revoked keys, rotated keys). The well-known URL pattern (`.well-known/actenon-issuer/<issuer_id>`) is proposed in `protocol/09-issuer-metadata.md` but not yet conformance-tested.
4. **Multi-issuer proofs.** The current schema assumes a single issuer per proof. UCAN-style delegation chains may require multi-issuer support. Deferred to v1.1.
5. **Cross-language conformance runner.** The current conformance suite is Python-only. A TypeScript port is planned for v1.1 to prove byte-identical canonicalisation across languages.
