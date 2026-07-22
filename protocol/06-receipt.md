# 06 — ExecutionReceipt

## Source of truth

The JSON Schema is at [`schemas/execution_receipt.v1.json`](../schemas/execution_receipt.v1.json). If this document and the schema disagree, the schema wins.

## Purpose

`ExecutionReceipt` is the durable record that an `ExecutionProof` was verified and an action was executed (or refused) at a protected resource. It is the audit artefact that survives long after the proof has expired and the action has completed.

Receipts may be counter-signed by a transparency log or receipt chain for tamper-evidence. They may be used as evidence in incident response, compliance audits, or insurance claims.

## Required fields

| Field | Type | Description |
|---|---|---|
| `protocol_version` | string | e.g. `"1.0.0"`. |
| `receipt_id` | identifier | MUST use the `rcpt_` prefix. |
| `proof_id` | identifier | The proof that authorised this execution. |
| `execution_attempt_id` | identifier | The execution attempt. MUST use the `exec_` prefix. Distinct from `proof_id`. |
| `execution_mode` | string | `brokered` or `resource_owned`. MUST match the proof's mode. |
| `executed_at` | timestamp | When the action was executed. |
| `outcome` | string | `EXECUTED`, `REFUSED`, `PARTIAL`, or `UNKNOWN`. See `protocol/08-outcome-codes.md`. |
| `target` | object | The target resource. MUST match the proof's target. |
| `action` | object | The action. MUST match the proof's action. |

## Optional fields

| Field | Type | Description |
|---|---|---|
| `provider_response_summary` | object | A summary of the provider's response. MUST NOT contain sensitive data. |
| `refusal_id` | identifier \| null | Present if `outcome` is `REFUSED`. The identifier of the `ExecutionRefusal`. |
| `evidence_links` | array | Evidence links (transparency log entries, counter-signatures). |
| `resource_signature` | object \| null | The protected resource's signature over the canonicalised receipt payload. Required for tamper-evident receipt chains. |

## Lifecycle

A receipt is issued by the protected resource (in `resource_owned` mode) or by the broker (in `brokered` mode) after the action has been executed (or refused).

```
[Proof verified] → [Action executed] → [Receipt issued] → [Receipt counter-signed (optional)] → [Receipt persisted]
```

The receipt's `executed_at` is the time the action completed (or was refused), not the time the receipt was issued. The receipt may be issued slightly after the action completes (e.g. after the provider's response is processed).

## Outcome codes

See `protocol/08-outcome-codes.md` for the full definition of `EXECUTED`, `REFUSED`, `PARTIAL`, and `UNKNOWN`.

If `outcome` is `REFUSED`, the receipt MUST include `refusal_id` pointing to the corresponding `ExecutionRefusal`.

If `outcome` is `EXECUTED`, the receipt MAY include `provider_response_summary` (a non-sensitive summary of the provider's response).

If `outcome` is `PARTIAL` or `UNKNOWN`, the receipt SHOULD include `provider_response_summary` explaining the partial/unknown state.

## Tamper-evidence

A receipt is tamper-evident if it carries a `resource_signature`. The signature is computed over the canonicalised receipt payload (under `ACTENON-JCS-STRICT-1`) minus the `resource_signature` field itself.

A receipt chain is a sequence of receipts where each receipt's `resource_signature` is counter-signed by the next receipt's issuer (e.g. a transparency log). This creates a tamper-evident append-only log of executions.

The protocol does NOT mandate tamper-evidence — that is a deployment decision. The protocol only defines the shape of the signature field so that implementations can interoperate.

## Idempotency

If the same `execution_attempt_id` is retried with the same `proof_id`, the resource SHOULD return the prior receipt (if it supports idempotent retry). This is the SEPARATION between replay (keyed by `proof_id`) and idempotency (keyed by `execution_attempt_id`) — addressing audit finding K-04.

A retry with a different `execution_attempt_id` but the same `proof_id` is a replay and is refused with `REPLAY_DETECTED` (see `protocol/05-proof.md` step 14).

## Conformance

The conformance suite includes:

* **Valid fixtures** — receipts that validate against the schema and verify under the resource's signature (if present).
* **Invalid fixtures** — receipts that fail validation (missing required fields, mismatched `execution_mode`, invalid signature).

See [`conformance/vectors/receipt/`](../conformance/vectors/receipt/).
