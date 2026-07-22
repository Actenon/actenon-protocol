# 11 — Disclosure Policy

## Purpose

The disclosure policy determines how much information a verifier reveals in an `ExecutionRefusal`. The protocol's two-layer model (`disclosed_code` + `internal_code`) exists to balance two competing concerns:

1. **Operability.** Trusted callers (internal services, audit logs) need detailed diagnostics to debug verification failures.
2. **Security.** Public callers must not receive cryptographic diagnostics that could help them forge proofs or probe the verifier's trust store.

## Policies

| Policy | Use case | `disclosed_code` | `internal_code` | `message` |
|---|---|---|---|---|
| `public` | Default. Safe for untrusted callers. | umbrella code (e.g. `PROOF_INVALID`) | `null` | generic, no cryptographic detail |
| `trusted` | Internal services, audit logs. | umbrella code | detailed code (e.g. `SIGNATURE_INVALID`) | may include diagnostic detail |
| `local_debug` | Local development only. MUST NOT be used in production. | umbrella code | detailed code | includes additional diagnostic context |

## Default policy

The default policy is `public`. A verifier that does not explicitly select a policy MUST use `public`.

A verifier selects a policy based on the caller's identity. The mechanism for caller identification is OUT OF SCOPE for the protocol (it is owned by the verifier's deployment). Examples:

* mTLS client certificate → `trusted` policy.
* Bearer token with `actenon-disclosure: trusted` claim → `trusted` policy.
* Local loopback (`127.0.0.1`) → `local_debug` policy (if explicitly enabled).
* Default → `public` policy.

## What `public` discloses

Under `public`, the `disclosed_code` is one of:

* `MALFORMED_REQUEST`
* `UNSUPPORTED_PROTOCOL_VERSION`
* `CANONICALISATION_FAILURE`
* `PROOF_MISSING`
* `PROOF_INVALID` (umbrella for all proof-validity failures except `PROOF_EXPIRED`, `PROOF_NOT_YET_VALID`, `REPLAY_DETECTED`)
* `PROOF_EXPIRED`
* `PROOF_NOT_YET_VALID`
* `REPLAY_DETECTED`
* `AUTHORITY_REVOKED`
* `POLICY_REFUSAL`
* `CREDENTIAL_UNAVAILABLE`
* `PROVIDER_REFUSAL`
* `PROVIDER_FAILURE`
* `OUTCOME_UNKNOWN`

Under `public`, the `internal_code` is `null`. The `message` is generic (e.g. `"proof verification failed"`).

## What `trusted` discloses

Under `trusted`, the `disclosed_code` is the same as under `public`. The `internal_code` is populated with the detailed code:

* `ISSUER_UNTRUSTED`
* `SIGNATURE_INVALID`
* `AUDIENCE_MISMATCH`
* `TARGET_MISMATCH`
* `ACTION_MISMATCH`
* `PARAMETER_MISMATCH`

Plus all the codes that are already detailed under `public` (they appear identically in `internal_code`).

The `message` MAY include diagnostic detail (e.g. `"signature verification failed: signature value does not match expected for key_id ed25519-9f3c1a175e9b"`).

## What `local_debug` discloses

Same as `trusted`, plus additional diagnostic context in `message` (e.g. the canonicalised proof payload, the recomputed hash, the expected vs actual signature). MUST NOT be used in production.

## Why `PROOF_EXPIRED`, `PROOF_NOT_YET_VALID`, and `REPLAY_DETECTED` are disclosed publicly

These three codes do NOT leak cryptographic information:

* `PROOF_EXPIRED` — the expiry is in the proof itself; the verifier is just confirming it.
* `PROOF_NOT_YET_VALID` — same, for `not_before`.
* `REPLAY_DETECTED` — the proof has been used; the caller knows this already.

By contrast, `SIGNATURE_INVALID` and `AUDIENCE_MISMATCH` DO leak cryptographic information (the caller can probe whether a signature is valid, or whether a specific audience is trusted). These are suppressed under `public`.

## Conformance

The conformance suite includes fixtures that prove:

* A `public`-policy refusal for `SIGNATURE_INVALID` carries `disclosed_code: "PROOF_INVALID"` and `internal_code: null`.
* A `trusted`-policy refusal for the same failure carries `disclosed_code: "PROOF_INVALID"` and `internal_code: "SIGNATURE_INVALID"`.
* A `public`-policy refusal for `PROOF_EXPIRED` carries `disclosed_code: "PROOF_EXPIRED"` and `internal_code: null`.
* A `trusted`-policy refusal for `PROOF_EXPIRED` carries `disclosed_code: "PROOF_EXPIRED"` and `internal_code: "PROOF_EXPIRED"`.

See [`conformance/vectors/refusal/`](../conformance/vectors/refusal/).
