# 05 — ExecutionProof

## Source of truth

The JSON Schema is at [`schemas/execution_proof.v1.json`](../schemas/execution_proof.v1.json). If this document and the schema disagree, the schema wins.

## Purpose

`ExecutionProof` is the cryptographic boundary artefact verified by the protected resource. It authorises ONE exact `(action, target, parameters)` tuple under the resource owner's configured trust policy. It is the ONLY artefact that the protected resource trusts for execution decisions.

The proof is NOT the developer-facing `AuthorisedExecutionIntent`. The intent is the claim; the proof is what gets verified.

## Required fields

| Field | Type | Description |
|---|---|---|
| `protocol_version` | string | e.g. `"1.0.0"`. |
| `proof_id` | identifier | MUST use the `proof_` prefix. |
| `issuer` | object | See `protocol/09-issuer-metadata.md`. |
| `subject` | string | The principal on whose behalf the proof was issued. |
| `audience` | object | The intended verifier. See `protocol/04-claim-names.md`. |
| `action` | object | The exact action spec. |
| `target` | object | The exact target. |
| `issued_at` | timestamp | When the proof was issued. |
| `expires_at` | timestamp | When the proof expires. |
| `canonicalisation` | string | `ACTENON-JCS-STRICT-1` (canonical) or `RFC8785-JCS` (deprecated alias). |
| `action_hash` | object | `{algorithm, value}`. The hash of the canonicalised `(action, target, parameters)` tuple. |
| `signature` | object | `{algorithm, key_id, value}`. The issuer's signature over the canonicalised proof payload. |
| `execution_mode` | string | `brokered` or `resource_owned`. |

## Optional fields

| Field | Type | Description |
|---|---|---|
| `not_before` | timestamp | If present, the proof is not valid before this timestamp. |
| `grant_id` | identifier \| null | The authority broker's grant identifier. Used for revocation cascade. |
| `authority_decision_id` | identifier \| null | The authority broker's decision record identifier. For audit. |
| `evidence_links` | array | Evidence links. See `protocol/10-evidence-linkage.md`. |
| `custom_claims` | object | Implementation-specific custom claims. Consumers MUST ignore unknown claims. |

## Verification algorithm

A verifier receiving an `ExecutionProof` MUST perform the following steps in order. Each step's failure produces a specific refusal code.

1. **Parse.** If the artefact is not valid JSON or does not conform to the schema → `MALFORMED_REQUEST`.
2. **Check protocol version.** If the major version is not supported → `UNSUPPORTED_PROTOCOL_VERSION`.
3. **Check canonicalisation profile.** If `canonicalisation` is not `ACTENON-JCS-STRICT-1` or `RFC8785-JCS` → `CANONICALISATION_FAILURE`.
4. **Re-canonicalise the (action, target, parameters) tuple.** If canonicalisation fails (e.g. float detected) → `CANONICALISATION_FAILURE`.
5. **Recompute `action_hash`.** If it does not match the proof's `action_hash` → `PARAMETER_MISMATCH` (trusted) / `PROOF_INVALID` (public).
6. **Check `not_before` and `expires_at`.** If `now < not_before` → `PROOF_NOT_YET_VALID`. If `now > expires_at` → `PROOF_EXPIRED`.
7. **Check `audience`.** If it does not match the verifier's identity → `AUDIENCE_MISMATCH` (trusted) / `PROOF_INVALID` (public).
8. **Check `target`.** If it does not match the resource the verifier is protecting → `TARGET_MISMATCH` (trusted) / `PROOF_INVALID` (public).
9. **Check `action.type`.** If it does not match the action being attempted → `ACTION_MISMATCH` (trusted) / `PROOF_INVALID` (public).
10. **Check `execution_mode`.** If the verifier does not support the proof's mode → `AUDIENCE_MISMATCH` (trusted) / `PROOF_INVALID` (public).
11. **Check issuer trust.** Fetch the issuer's current key set and trust status. If the issuer is not trusted → `ISSUER_UNTRUSTED` (trusted) / `PROOF_INVALID` (public). If the issuer is suspended or revoked → `AUTHORITY_REVOKED`.
12. **Check `grant_id` revocation cascade.** If the grant referenced by `grant_id` has been revoked → `AUTHORITY_REVOKED`.
13. **Verify the signature.** If the signature does not verify under the issuer's public key → `SIGNATURE_INVALID` (trusted) / `PROOF_INVALID` (public).
14. **Check the replay store.** If the `proof_id` has already been used with a different `execution_attempt_id` → `REPLAY_DETECTED`.
15. **All checks pass.** The proof is valid. The verifier MAY proceed to execute the action.

Steps 1–14 MUST be performed in order. A failure at any step produces the corresponding refusal and skips the remaining steps.

## Issuance algorithm

An issuer (authority broker) minting an `ExecutionProof` MUST:

1. Receive an `AuthorisedExecutionIntent` from the developer (or construct one from the broker's own state).
2. Run the broker's policy engine to decide whether to issue. (Out of scope for the protocol — owned by the authority broker.)
3. Construct the proof payload: `protocol_version`, `proof_id` (freshly generated), `issuer`, `subject`, `audience`, `action`, `target`, `issued_at`, `expires_at`, `canonicalisation` (set to `ACTENON-JCS-STRICT-1`), `execution_mode`, optional `grant_id`, `authority_decision_id`, `evidence_links`, `custom_claims`.
4. Canonicalise the `(action, target, parameters)` tuple under `ACTENON-JCS-STRICT-1`.
5. Compute `action_hash = sha256(canonical_bytes)`.
6. Construct the signing payload (canonicalised proof payload minus the `signature` field).
7. Sign the signing payload with the issuer's private key.
8. Attach the signature.
9. Return the proof to the caller.

The proof is now ready to be presented to a verifier.

## Lifetime

A proof is single-use. Once consumed by a verifier (step 14 above), the `proof_id` is recorded in the verifier's replay store and cannot be reused. A new action requires a new proof.

The proof's `expires_at` is the maximum time the proof is valid for verification, regardless of whether it has been consumed. A proof that has not been consumed by `expires_at` is no longer verifiable.

## Conformance

The conformance suite includes:

* **Valid fixtures** — proofs that verify successfully under a test verifier.
* **Invalid fixtures** — proofs that fail verification at each of the 14 steps, with the expected refusal code.

See [`conformance/vectors/proof/`](../conformance/vectors/proof/).
