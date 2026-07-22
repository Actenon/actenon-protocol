# 04 — Proof Claim Names

This specification defines the canonical claim names that appear in an `ExecutionProof`. Claim names are stable for the life of protocol v1.x.

## Standard claims

| Claim | Type | Required | Description |
|---|---|---|---|
| `protocol_version` | string | yes | The protocol version (e.g. `"1.0.0"`). |
| `proof_id` | identifier | yes | The unique identifier of this proof. Prefix: `proof_`. |
| `issuer` | object | yes | The issuer metadata. See `protocol/09-issuer-metadata.md`. |
| `subject` | string | yes | The principal on whose behalf the proof was issued. |
| `audience` | object | yes | The intended audience (verifier service). |
| `action` | object | yes | The exact action spec (type + parameters). |
| `target` | object | yes | The target resource. |
| `issued_at` | timestamp | yes | When the proof was issued. |
| `not_before` | timestamp | no | If present, the proof is not valid before this timestamp. |
| `expires_at` | timestamp | yes | When the proof expires. |
| `canonicalisation` | string | yes | The canonicalisation profile. MUST be `ACTENON-JCS-STRICT-1` for new proofs. |
| `action_hash` | object | yes | The hash of the canonicalised `(action, target, parameters)` tuple. |
| `signature` | object | yes | The issuer's signature over the canonicalised proof payload. |
| `execution_mode` | string | yes | The execution mode (`brokered` or `resource_owned`). |
| `grant_id` | identifier \| null | no | The authority broker's grant identifier, if applicable. |
| `authority_decision_id` | identifier \| null | no | The authority broker's decision record identifier, if applicable. |
| `evidence_links` | array | no | Evidence links (transparency log entries, etc.). |
| `custom_claims` | object | no | Implementation-specific custom claims. Consumers MUST ignore unknown claims. Custom claims MUST NOT override protocol-defined fields. |

## Naming conventions

* All claim names are lowercase snake_case.
* Timestamps use `_at` suffix (`issued_at`, `expires_at`, `not_before`, `refused_at`, `executed_at`).
* Identifiers use `_id` suffix (`proof_id`, `grant_id`, `authority_decision_id`).
* Arrays use plural nouns (`evidence_links`, `parameters`).
* The `custom_claims` field is a deliberate escape hatch. Implementations that need to carry proprietary metadata (e.g. tenant identifiers, request correlation IDs) MUST put it in `custom_claims`, NOT in a new top-level field. Top-level fields are reserved for protocol-defined claims.

## Forbidden claim names

The following claim names MUST NOT appear as top-level fields (they are reserved for future protocol versions):

* `tenant_id` — tenant modelling is out of scope.
* `user_id` — user identity is out of scope.
* `policy_id` — policy evaluation is out of scope.
* `approval_id` — approvals are out of scope.
* `budget_id` — budgets are out of scope.

Implementations that need these concepts MUST put them in `custom_claims`.

## Compatibility with existing actenon-kernel PCCB claims

The actenon-kernel's `PCCB` model (in `actenon/models/contracts.py`) uses claim names that are close to but not identical with the protocol's. The mapping is:

| Kernel PCCB field | Protocol claim | Notes |
|---|---|---|
| `pccb_id` | `proof_id` | Different name; same concept. The Kernel's internal `pccb_id` field does NOT appear on the wire. |
| `issuer` | `issuer` | Same name; same concept. |
| `subject` | `subject` | Same. |
| `audience` | `audience` | Same. |
| `action` | `action` | Same. |
| `target` | `target` | Same. |
| `issued_at` | `issued_at` | Same. |
| `not_before` | `not_before` | Same. |
| `expires_at` | `expires_at` | Same. |
| `canonicalization` | `canonicalisation` | **Spelling change** (US → British). The protocol uses British spelling for consistency with the rest of the protocol's documentation. The Kernel MAY keep its US-spelling internal field; the wire format uses British spelling. |
| `action_hash` | `action_hash` | Same. |
| `signature` | `signature` | Same. |
| (none) | `execution_mode` | **New in v1.0.** The Kernel did not carry this on the PCCB; it was inferred from deployment. The protocol mandates it as an explicit field. |
| (none) | `grant_id` | **New in v1.0.** The Kernel did not reference the grant; the protocol adds it for revocation cascade. |
| (none) | `authority_decision_id` | **New in v1.0.** For audit. |
| (none) | `evidence_links` | **New in v1.0.** |
| (none) | `custom_claims` | **New in v1.0.** |

The Kernel's existing PCCB serialisation is NOT wire-compatible with the protocol's `ExecutionProof` — the protocol adds `execution_mode`, `grant_id`, `authority_decision_id`, `evidence_links`, `custom_claims`, and renames `canonicalization` → `canonicalisation`. The Kernel will be updated in a future minor version to emit protocol-compatible proofs. Until then, the protocol and the Kernel coexist via a translation layer (out of scope for this repo).
