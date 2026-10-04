# Consequential effect identity and certainty

Status: normative additive profile `ACTENON-EFFECT-1`, introduced in package 1.6.0 / wire 1.3.0. Existing proofs, receipts and execution results remain valid. This profile defines portable contracts; it does not claim that existing executors already implement an effect ledger.

## Identity

An action ID identifies an attempt. An effect ID identifies a logical consequence within a resource-owner-configured namespace. Neither is authorization. A fresh action ID, proof ID, grant ID, process, source revision or approval MUST NOT make an unresolved retry a new effect.

The trusted adapter produces an `EffectDescriptor`. It MUST use Scan's concrete action vocabulary and the same canonical target actually supplied to the execution boundary. Protocol does not classify tools or infer resource identities. Resource adapters perform canonicalization before hashing; this helper does not rewrite case, URL encoding, filesystem aliases or database identities.

For exact descriptors, `parameters` includes every consequential parameter. Credentials, proof/action IDs, timestamps, tracing and transport retry metadata are excluded by the reviewed adapter's projection, never by the agent. For semantic descriptors, `semantic_key` is a nonempty reviewed projection identifying the business consequence, for example a payment ID and logical refund ID. The policy must validate every parameter independently: a semantic key does not authorize a changed amount. The agent cannot select a different namespace, descriptor kind or key projection to evade a reservation.

The hash is:

```text
effect_ + lower_hex(SHA256(UTF8("ACTENON-EFFECT-1") || 0x00 ||
                          ACTENON-JCS-STRICT-1(descriptor)))
```

The profile, namespace, kind, action type, target and parameters/key are all included. Unknown descriptor fields, empty semantic keys, unresolved/wildcard targets and noncanonical JSON are refused. Integer/scaled monetary representations follow the existing strict canonicalization profile; floating-point money is not introduced.

Exact equality of a payload does not prove two intentionally repeated operations are the same business effect. When an operation legitimately repeats, the reviewed adapter MUST include a stable business operation identity in consequential parameters or use an explicit semantic key. Where that identity cannot be safely determined, the boundary refuses or requires configuration; it must not silently merge different consequences or mint random identities for retries.

## Reservation and proof

`extensions.effect` is a signed `EffectReference`: profile, effect ID, reservation ID and owner attempt ID. It binds the existing exact action/target/parameters proof to the ledger reservation. The existing signed authority extension binds the grant. The reservation must store and check the action hash, canonical target, principal and grant alongside ownership.

An effect-protected edge MUST be explicitly configured to require this profile. Before any credential release or side effect it MUST:

1. Verify the cryptographic proof and existing E1–E5 requirements, including exact parameters, target, single-use and revocation.
2. Recompute the effect identity using its trusted adapter projection and compare it to the signed effect reference.
3. Atomically check/claim the reservation owner against the authoritative store, including the exact action hash, target, principal, grant and attempt.
4. Refuse a missing reference, unknown profile, missing/unreachable ledger, non-owner, revoked authority, committed effect or unresolved prior attempt.

A signed string is not an atomic reservation. A separate read followed by execution is insufficient. Reservation and cumulative budget debit MUST share one transaction; the only owner may cross the edge. An existing verifier that ignores unknown extensions does not become effect-protected. Capability discovery and explicit deployment configuration must prevent silently routing an effect-protected action to that legacy edge.

Local coordination uses SQLite with durable acknowledged writes. Multi-host coordination requires a shared transactional store such as PostgreSQL. No process-local map qualifies. A lease expiry, process death or clock advance MUST NOT automatically release a potentially dispatched effect. A crash while reserved/dispatching remains blocking until trusted reconciliation.

## Consequence certainty

`EffectEvidence` records `COMMITTED`, `NOT_EXECUTED` or `AMBIGUOUS`, separately from HTTP status, provider failure and existing receipt outcome names.

| Effect outcome | execution_occurred | Required evidence | Retry |
|---|---|---|---|
| COMMITTED | true | Trusted boundary confirms the intended consequence | Refused for the same logical effect |
| NOT_EXECUTED | false | Trusted boundary establishes no consequence occurred | A new attempt may reserve after settlement |
| AMBIGUOUS | null or true | Dispatch may have crossed the edge, or a partial consequence is observed without final certainty | Refused until reconciliation |

`evidence_hash` commits to the redacted observation. This digest authenticates nothing by itself; include the complete EffectEvidence as an inline `audit_ledger` evidence link in a signed receipt, or authenticate it with equivalent resource evidence. Keep credentials and sensitive payloads out of public evidence. The reference validator checks shape and consistency; it does not verify signatures or inspect a real provider.

Existing `ExecutionReceipt.outcome` and execution-mode result enums are unchanged. `EXECUTED` alone does not establish COMMITTED. REFUSED before dispatch maps to NOT_EXECUTED. UNKNOWN and uncertain PARTIAL map to AMBIGUOUS. A provider's FAILED result or HTTP 500 does not prove non-execution. An HTTP 200, submitted request, released local operation or broker credential resolution does not prove COMMITTED.

A reservation owner records dispatch intent durably before crossing the consequence boundary. After dispatch, timeout, connection loss, malformed response and a crash are AMBIGUOUS unless a trusted boundary can establish the actual outcome. Reservation and budget remain held. Blind retries, even with another action ID or grant, are refused within that owner-configured effect namespace.

## Reconciliation

Only a trusted operator or configured provider reconciliation hook may resolve ambiguity. An agent's assertion is not provider evidence. The decision binds the effect, original reservation/attempt, observation digest, reconciler identity and timestamp, and leaves authenticated evidence. Resolution to COMMITTED keeps duplicate execution blocked and settles cost once. Resolution to NOT_EXECUTED releases the exact held reservation/budget once and permits a fresh authorized attempt. Conflicting or replayed reconciliation cannot refund again or replace a committed outcome.

This profile guarantees neither exactly-once remote execution nor correctness of a provider's internals. A conforming protected boundary guarantees it does not knowingly dispatch the same reserved logical effect twice and does not blindly retry an unresolved effect.

## Conformance and deployment status

JSON Schemas, Python models/helpers, TypeScript helpers and locked vectors define descriptor hashing and evidence consistency. The standalone runner executes the new vectors; a missing implementation is a failure, never a pass/skip. Full effect protection also requires executor/store attack tests for threads, processes, shared hosts, crashes, proof/approval replay, mutated action/target/parameters and lost responses. Schema conformance alone is insufficient. Kernel, Permit, SDKs and Airlock must explicitly integrate and test the profile before claiming protected effect execution.
