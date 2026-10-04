# Capability provenance — coordinated candidate

Scan names a power. Permit signs it into a grant and a proof. Kernel checks that proof at the execution edge. Airlock writes the receipt. Protocol supplies the shared exact-capability, authority-reference and refusal contract.

Package **1.5.0**, wire **1.2.0**. The implementation was merged in [Protocol #21](https://github.com/Actenon/actenon-protocol/pull/21) at `eba78d3dbd41a0b6c86166ece0f34cc8d7b7a002`. Version 1.5.0 is a source candidate, not a published package. Source-based CI is evidence of integration; it does not establish registry-consumer readiness.

## Contract

- `ExecutionProof.action.type` projects to PCCB `action.capability`. PCCB `action.name` is a signed operation label that may differ; it cannot substitute for the capability at a scope check.
- `SCOPE_CAPABILITY_MISMATCH` and `SCOPE_MODE_INVALID` are canonical refusal codes. Trusted disclosure preserves them; public disclosure is `PROOF_INVALID`.
- Minting an empty set or a capability containing `*`, `?`, `[` or `]` raises `CapabilityError`. No attempted-action or wildcard fallback is allowed.
- `scope_capabilities_for_verification(None, capability)` constructs an explicit single-capability declaration. A supplied empty tuple remains empty and authorises nothing.
- A signed `extensions.authority` reference identifies issuer, grant id and an explicit boolean `revocable`. A revocable proof requires an actual authoritative revocation check before execution; parsing the reference is insufficient.
- No trust root means `ISSUER_UNTRUSTED`; an invalid signature means `SIGNATURE_INVALID`. Public disclosure collapses both to `PROOF_INVALID`. Token length is never a verification input.

Wire 1.0.0 and 1.1.0 remain accepted. Optional `extensions` preserves existing proof compatibility. Missing mandatory fields within a supplied authority reference fail closed.

## One coordinated lineage

[Kernel #44](https://github.com/Actenon/actenon-kernel/pull/44) consolidates the production/release candidate #41 with provenance candidate #43. It retains signed minter extensions, durable replay, exact edge binding and real revocation enforcement. Dependents must use that unified line rather than choose a Kernel according to whether they need `extensions`.

Permit, Go and Rust are being consolidated from their production and provenance candidates. Their approved source revisions and fixture locks belong in the final release graph, after their full suites pass. Scan #101 is merged at `ee971b43c78ed8b58f5f7fb59382ab20ce9b8a5c`. Airlock #3 is preserved for its subsequent update against the coordinated candidates.

Before registry publication, freeze one source revision per component, run complete integration and clean-artifact checks, and regenerate the dependency graph in release order. Temporary source overrides must be removed before publishing dependent packages. No source pin or individually green historical PR constitutes a released ecosystem.
