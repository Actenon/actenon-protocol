# 07 — ExecutionRefusal

## Source of truth

The JSON Schema is at [`schemas/execution_refusal.v1.json`](../schemas/execution_refusal.v1.json). The refusal-code catalogue is at [`refusals/catalogue.v1.yaml`](../refusals/catalogue.v1.yaml). If this document and those sources disagree, the machine-readable sources win.

## Purpose

`ExecutionRefusal` is the durable record that an `ExecutionProof` was rejected or an action was refused. It carries a two-layer disclosure model so that public callers receive only safe information while trusted callers receive detailed diagnostics.

## Required fields

| Field | Type | Description |
|---|---|---|
| `protocol_version` | string | e.g. `"1.0.0"`. |
| `refusal_id` | identifier | MUST use the `rful_` prefix. |
| `execution_mode` | string | `brokered` or `resource_owned`. MUST be explicit. |
| `refused_at` | timestamp | When the refusal occurred. |
| `disclosed_code` | string | The public-safe refusal code. Always present. |
| `retryable` | boolean | Whether the caller may retry. |

## Optional fields

| Field | Type | Description |
|---|---|---|
| `proof_id` | identifier \| null | The proof that was refused, if a proof was supplied. `null` if `PROOF_MISSING`. |
| `execution_attempt_id` | identifier \| null | The execution attempt that was refused, if applicable. |
| `internal_code` | string \| null | The detailed refusal code. Present only under trusted disclosure. `null` under public disclosure. |
| `message` | string | A human-readable refusal message. MUST NOT leak cryptographic diagnostics under public disclosure. |
| `evidence_links` | array | Evidence links. |

## Two-layer disclosure model

The protocol's disclosure model has three policies:

* **`public`** (default) — Safe for untrusted callers. The `disclosed_code` is the umbrella code (e.g. `PROOF_INVALID` for all proof-validity failures). The `internal_code` is `null`. The `message` does not leak cryptographic details.
* **`trusted`** — For trusted callers (internal services, audit logs). The `disclosed_code` is the same as under `public`. The `internal_code` is populated with the detailed code (e.g. `SIGNATURE_INVALID`, `AUDIENCE_MISMATCH`). The `message` may include diagnostic detail.
* **`local_debug`** — For local development only. Same as `trusted` but with additional diagnostic context in `message`. MUST NOT be used in production.

See `protocol/11-disclosure-policy.md` for the full policy specification.

## Refusal-code catalogue

The 20 canonical refusal codes are organised into 6 categories:

| Category | Codes |
|---|---|
| `request_shape` | `MALFORMED_REQUEST`, `UNSUPPORTED_PROTOCOL_VERSION`, `CANONICALISATION_FAILURE` |
| `proof_presence` | `PROOF_MISSING` |
| `proof_validity` | `PROOF_INVALID` (umbrella), `ISSUER_UNTRUSTED`, `SIGNATURE_INVALID`, `PROOF_EXPIRED`, `PROOF_NOT_YET_VALID`, `AUDIENCE_MISMATCH`, `TARGET_MISMATCH`, `ACTION_MISMATCH`, `PARAMETER_MISMATCH`, `REPLAY_DETECTED` |
| `authority_state` | `AUTHORITY_REVOKED`, `POLICY_REFUSAL` |
| `provider` | `CREDENTIAL_UNAVAILABLE`, `PROVIDER_REFUSAL`, `PROVIDER_FAILURE` |
| `outcome` | `OUTCOME_UNKNOWN` |

The full catalogue (with disclosure rules, retryability, and compatibility aliases) is at [`refusals/catalogue.v1.yaml`](../refusals/catalogue.v1.yaml).

## Compatibility aliases

The existing `actenon-kernel` `FailureCode` enum members are preserved as aliases. Consumers receiving an older Kernel-style code resolve it via the catalogue's `compatibility_aliases` map:

| Kernel/Permit code | Canonical code |
|---|---|
| `PCCB_REQUIRED` | `PROOF_MISSING` |
| `PCCB_EXPIRED` | `PROOF_EXPIRED` |
| `DUPLICATE_REPLAY` | `REPLAY_DETECTED` |
| `SIGNATURE_INVALID` | `SIGNATURE_INVALID` (same) |
| `ACTION_MISMATCH` | `ACTION_MISMATCH` (same) |
| `AUDIENCE_MISMATCH` | `AUDIENCE_MISMATCH` (same) |
| `INTENT_MISMATCH` | `PARAMETER_MISMATCH` |
| `TARGET_MISMATCH` | `TARGET_MISMATCH` (same) |
| `ACTION_HASH_MISMATCH` | `PARAMETER_MISMATCH` |
| `SCOPE_CAPABILITY_MISMATCH` | `PARAMETER_MISMATCH` |
| `TENANT_MISMATCH` | `TARGET_MISMATCH` |
| `SUBJECT_MISMATCH` | `TARGET_MISMATCH` |
| `PROOF_PAYLOAD_INVALID` | `MALFORMED_REQUEST` |
| `NOT_ACTIVE` | `POLICY_REFUSAL` |
| `REVOKED` | `AUTHORITY_REVOKED` |
| `EXPIRED` | `PROOF_EXPIRED` |
| `SCOPE_DENIED` | `POLICY_REFUSAL` |
| `OUT_OF_SCOPE` | `POLICY_REFUSAL` |
| `BUDGET_EXCEEDED` | `POLICY_REFUSAL` |
| `RATE_LIMITED` | `POLICY_REFUSAL` |
| `ENGINE_ERROR` | `OUTCOME_UNKNOWN` |

## Retryability

The `retryable` field is derived from the `internal_code` (or `disclosed_code` if `internal_code` is null):

| Code | Retryable |
|---|---|
| `MALFORMED_REQUEST` | false |
| `UNSUPPORTED_PROTOCOL_VERSION` | false |
| `CANONICALISATION_FAILURE` | false |
| `PROOF_MISSING` | false |
| `PROOF_INVALID` | false |
| `ISSUER_UNTRUSTED` | false |
| `SIGNATURE_INVALID` | false |
| `PROOF_EXPIRED` | false |
| `PROOF_NOT_YET_VALID` | true |
| `AUDIENCE_MISMATCH` | false |
| `TARGET_MISMATCH` | false |
| `ACTION_MISMATCH` | false |
| `PARAMETER_MISMATCH` | false |
| `REPLAY_DETECTED` | false |
| `AUTHORITY_REVOKED` | false |
| `POLICY_REFUSAL` | false |
| `CREDENTIAL_UNAVAILABLE` | true |
| `PROVIDER_REFUSAL` | false |
| `PROVIDER_FAILURE` | true |
| `OUTCOME_UNKNOWN` | true |

## Forward compatibility

When a consumer receives a refusal with an unknown `disclosed_code` (e.g. from a newer minor version of the protocol), it MUST treat it as `OUTCOME_UNKNOWN` and consult the `retryable` field. This is the protocol's forward-compatibility escape hatch.

## Conformance

The conformance suite includes:

* **Valid fixtures** — refusals that validate against the schema and exercise each `disclosed_code`.
* **Invalid fixtures** — refusals that fail validation (missing required fields, mismatched `disclosed_code` and `internal_code` pairing, invalid disclosure policy).
* **Disclosure fixtures** — refusals under `public` vs `trusted` policy, proving that the `internal_code` is correctly suppressed under `public`.

See [`conformance/vectors/refusal/`](../conformance/vectors/refusal/).
