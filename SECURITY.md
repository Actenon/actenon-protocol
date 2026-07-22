# Security Policy

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email security@actenon.dev with:

1. A description of the vulnerability.
2. The minimal reproduction steps.
3. The affected protocol version (see [VERSIONING.md](VERSIONING.md)).
4. The artefact type affected (`ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`, `issuer_metadata`, `evidence_link`, or the canonicalisation profile).

You will receive an acknowledgement within 72 hours. We will coordinate a fix and a disclosure timeline with you.

## Threat model

The protocol assumes the following threat model:

| Threat | Mitigation owned by |
|---|---|
| Forged `ExecutionProof` (signature invalid) | The verifier (Kernel or compatible) MUST reject with `SIGNATURE_INVALID` (under trusted disclosure) or `PROOF_INVALID` (under public disclosure). |
| Tampered action parameters (proof for action A used to authorise action B) | The `action_hash` field cryptographically binds the proof to one exact `(action, target, parameters)` tuple. The verifier MUST recompute the hash and compare. |
| Replay of a valid proof | The verifier MUST consult a replay store keyed by `proof_id` (or the issuer's nonce). Replay is refused with `REPLAY_DETECTED`. |
| Stale proof past expiry | The `expires_at` field is enforced by the verifier. Refusal: `PROOF_EXPIRED`. |
| Proof presented before `not_before` | Refusal: `PROOF_NOT_YET_VALID`. |
| Wrong audience (proof minted for service A presented to service B) | Refusal: `AUDIENCE_MISMATCH`. |
| Issuer key compromise | Revocation is via the issuer's `issuer_status` endpoint (out of scope for this repo — see `protocol/09-issuer-metadata.md`). |
| Canonicalisation divergence between implementations | The `ACTENON-JCS-STRICT-1` profile is fully specified in `canonicalisation/ACTENON-JCS-STRICT-1.md` and accompanied by a conformance suite that proves byte-identical output across implementations. |
| Float poisoning (a float in the action parameters producing different bytes in different canonicalisers) | `ACTENON-JCS-STRICT-1` REJECTS floats entirely. The conformance suite includes a fixture that proves a float input is rejected. |
| Disclosure of cryptographic diagnostics to untrusted callers | The refusal schema has a `disclosed_code` field (public-safe) and an optional `internal_code` field (only present when the disclosure policy permits). See `protocol/11-disclosure-policy.md`. |

## Out of scope

The protocol does NOT mitigate:

* Compromise of the issuer's signing key (mitigated by key custody at the issuer).
* Compromise of the verifier (mitigated by resource-owner key custody).
* Compromise of the broker (mitigated by the broker holding only scoped credentials, not signing keys).
* Network-level attacks (mitigated by TLS).
* Side-channel attacks against the verifier (mitigated by constant-time comparisons in the implementation).

## Supported versions

| Version | Supported | Security fixes until |
|---|---|---|
| 1.x | yes | indefinitely (LTS) |
| 0.x (pre-release) | no | n/a |

See [VERSIONING.md](VERSIONING.md) for the full versioning policy.
