# 08 — Outcome Codes

This specification defines two kinds of outcome codes:

1. **Verification outcome codes** — emitted by the verifier when examining an `ExecutionProof`. These are the refusal codes defined in `protocol/07-refusal.md` plus the implicit `VERIFIED` outcome.
2. **Execution outcome codes** — emitted by the protected resource or broker when an action is executed (or refused, or partially executed). These appear in `ExecutionReceipt.outcome`.

## Verification outcome codes

When a verifier examines an `ExecutionProof`, the outcome is one of:

| Outcome | Meaning | Refusal code (if any) |
|---|---|---|
| `VERIFIED` | The proof is valid and the action may proceed. | (none) |
| `REFUSED` | The proof was rejected. | One of the 20 codes from `protocol/07-refusal.md`. |

There is no third outcome. The verifier either accepts the proof or refuses it with a specific code.

The verifier MUST produce an `ExecutionRefusal` artefact for every `REFUSED` outcome, carrying the `disclosed_code` and (under trusted disclosure) the `internal_code`.

## Execution outcome codes

When a protected resource or broker executes an action, the outcome is one of:

| Code | Meaning | Receipt `refusal_id` |
|---|---|---|
| `EXECUTED` | The action completed successfully. The provider returned a success response. | (none) |
| `REFUSED` | The action was refused. The proof was valid, but the resource or broker chose not to execute (e.g. the resource's own policy engine denied the request, or the broker could not resolve a credential). | present (points to the `ExecutionRefusal`) |
| `PARTIAL` | The action partially completed. The provider returned a partial success (e.g. a batch operation where some items succeeded and some failed). | (none; the receipt's `provider_response_summary` SHOULD explain) |
| `UNKNOWN` | The outcome could not be determined. The provider timed out, returned a 5xx, or the network failed. | (none; the receipt's `provider_response_summary` SHOULD explain) |

The `outcome` field is REQUIRED on every `ExecutionReceipt`. A receipt without an outcome is malformed.

## Relationship between verification and execution outcomes

The two outcome code spaces are distinct:

* A proof can be `VERIFIED` (verification outcome) but the action can still be `REFUSED` (execution outcome) — e.g. the proof is valid but the resource's own policy engine denies the request.
* A proof can be `REFUSED` (verification outcome) — in which case there is no execution, and the receipt's `outcome` is `REFUSED` with `refusal_id` pointing to the verification refusal.

The receipt's `outcome` reflects the END STATE of the execution attempt, not the verification state. If verification failed, the receipt's `outcome` is `REFUSED` and the `refusal_id` points to the verification refusal. If verification succeeded but execution failed, the receipt's `outcome` is `REFUSED` and the `refusal_id` points to a new execution refusal (with code `PROVIDER_REFUSAL` or `PROVIDER_FAILURE`).

## Forward compatibility

Unknown execution outcome codes (from a newer minor version) MUST be treated as `UNKNOWN`. Unknown verification outcome codes do not exist — verification is binary (`VERIFIED` or `REFUSED` with a code).

## Conformance

The conformance suite includes fixtures that exercise each execution outcome code in `conformance/vectors/receipt/`.
