# 14 — Capability provenance

Status: **Normative** from actenon-protocol 1.5.0 (package) / wire `1.2.0`. Decision record: 2026-10-04.

The path is Scan vocabulary, then a signed grant, then Kernel `protect()`, then a receipt. This document is the protocol piece of that path. It does not name Scan's extractor, Permit's HMAC, or the Kernel's process model. It fixes the wire and the refusal codes those components share.

## What a capability is

A capability is one exact string.

- Scan-named powers are capabilities: an action kind such as `http.get`, `filesystem.write`, `process.exec`, or `email.send`, or a compiled id (`airlock.` plus a digest of action, resource, and transport).
- On `ExecutionProof`, the capability is `action.type`.
- On the Kernel PCCB, the same string is `action.capability`. When both `action.name` and `action.capability` are present they MUST be equal to that string for the action the proof authorises.
- Grant allow-lists may contain patterns (`payment.*`). A proof MUST NOT. The characters `*`, `?`, `[`, and `]` are grant-scope syntax. They are not capabilities, and a verifier MUST NOT expand them.
- An unresolved call (`airlock.unresolved.<digest>`) is a concrete capability. It is denied because it is outside the grant, not because the string is malformed.

## Issuance

An issuer minting a proof MUST:

1. Choose the capabilities the proof authorises. The set MUST be non-empty, and every member MUST be a concrete capability.
2. Refuse to mint when the set is empty. The attempted action MUST NOT be substituted, and `*` MUST NOT be substituted. That substitution widens an unnamed action into a proof.
3. Put exactly those strings in the signed scope. A grant of `payment.*` plus `email.send` that authorises `payment.refund` yields a proof whose capability is `payment.refund`, not the allow-list and not `payment.*`.
4. When the proof is revocable, include a signed authority reference:

```json
{"authority": {"issuer": "service:actenon-permit", "grant_id": "<grant id>", "revocable": true}}
```

On `ExecutionProof` this object is `extensions.authority`. On the Kernel PCCB it is the same object at `extensions.authority`, inside the signed payload. `custom_claims` MUST NOT be used instead: verifiers that implement [13-edge-binding.md](13-edge-binding.md) E5 read `extensions.authority`.

`scope_capabilities or (attempted_action,)` is non-conformant. An empty declaration stays empty.

## Verification

Parsing is not acceptance.

- A verifier MUST NOT report a token valid because it is long, because it starts with `v1.`, or because it is well-formed JSON. A string of 16 or more characters is not a proof.
- With no configured trust root the refusal is `ISSUER_UNTRUSTED` (trusted disclosure) / `PROOF_INVALID` (public).
- A forged or unverifiable signature is `SIGNATURE_INVALID` / `PROOF_INVALID`. The side effect MUST NOT run.
- After the signature verifies, the intent's capability MUST be an element of the edge's declared `scope_capabilities` ([13-edge-binding.md](13-edge-binding.md) E1). The refusal is `SCOPE_CAPABILITY_MISMATCH`. An empty declaration refuses with the same code. It is not rewritten to `PARAMETER_MISMATCH`: the action hash may still match.
- A proof whose signed single-use flag is not `true` is `SCOPE_MODE_INVALID`, not `PARAMETER_MISMATCH`.
- When `extensions.authority.revocable` is true, the edge consults that issuer's revocation source before any side effect (E5). Unknown grant, missing authority reference, or a source that cannot be read refuses closed. The code is `AUTHORITY_REVOKED`.

`SCOPE_CAPABILITY_MISMATCH` and `SCOPE_MODE_INVALID` are canonical catalogue codes. Public disclosure still collapses them to `PROOF_INVALID`. Trusted disclosure keeps the specific code.

## What this does not claim

The protocol does not confine a process, intercept a syscall, or sandbox native code. A program that never presents a proof is outside this check. That isolation is a separate control.
