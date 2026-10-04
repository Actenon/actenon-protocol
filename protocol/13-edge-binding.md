# 13 — Edge binding: what the protected edge itself declares

Status: **Normative** from actenon-protocol 1.4.0 (package version). Decision record: 2026-10-02.

Versioning: these rules change what a verifier accepts. `scope_capabilities`, `parameter_constraints`
and `resource_selectors` already existed as verifier context. The Kernel PCCB already had an open
`extensions` object; `ExecutionProof` gained optional `extensions` in wire `1.2.0` (package 1.5.0)
so `extensions.authority` has a protocol field. Under VERSIONING.md § Security-patch handling the
1.4.0 rules were a MINOR package bump. The 1.5.0 catalogue fix (the two edge codes are canonical,
not aliases of `PARAMETER_MISMATCH`) is a wire MINOR because `internal_code` may now carry them.

## Why this exists

A proof binds an exact action to an issuer, an audience and a time window. The protected edge also knows things about
itself the proof cannot know: which capabilities this endpoint actually performs, which parameter constraints it relies on,
and which resources it is about to touch. Implementations already accepted these as verifier context
(`scope_capabilities`, `parameter_constraints`, `resource_selectors`) — and the reference verifier then ignored them.

A differential run (kernel_diff_v1, 179 cases) showed the consequence. An edge declaring
`scope_capabilities = ["payments.read"]` **accepted** a valid `payments.refund` proof presented with a `payments.refund`
intent. Edge parameter constraints and resource selectors that contradicted the proof were also accepted. An edge that passes
context believes it is enforced; this document makes that belief true.

## The rules

Context fields are the edge's own declaration. They are never taken from the request. The checks run after the
signature verifies (post-authentication), so their refusal codes may be disclosed under the trusted profile
(`11-disclosure-policy.md`).

### E1 — `scope_capabilities` (required, exact)
- The edge MUST declare a non-empty set of capability strings it performs.
- The verifier MUST refuse with `SCOPE_CAPABILITY_MISMATCH` unless the intent's `action.capability` is an element of the
  declared set. This is in addition to the existing rule that it must be an element of the proof's signed
  `scope.capabilities`.
- An empty declaration is refused, also with `SCOPE_CAPABILITY_MISMATCH`.
- Comparison is exact string equality. Patterns (`payments.*`) are **not** expanded: a broker may authorise with patterns,
  but the proof and the edge speak in exact capabilities. See [14-capability-provenance.md](14-capability-provenance.md).
- `SCOPE_CAPABILITY_MISMATCH` is a canonical refusal code. It MUST NOT be rewritten to `PARAMETER_MISMATCH`.
  Package 1.4.0 named the code and the catalogue still aliased it; package 1.5.0 (wire 1.2.0) stops that alias.

### E2 — `parameter_constraints` (optional, subset of what was signed)
- An empty object imposes nothing.
- Otherwise, for every member `(k, v)` the edge declares, the proof's signed `scope.parameter_constraints` MUST contain
  `k` with a value whose canonical form (`02-canonicalisation.md`) is byte-identical to that of `v`.
- Otherwise the verifier MUST refuse with `PARAMETER_MISMATCH`.
- The edge thereby requires the authority to have issued the proof under at least the constraints the edge relies on.
- The exact parameters themselves remain bound by the action hash.

### E3 — `resource_selectors` (optional, any-of against the bound target)
- An empty list imposes nothing.
- Otherwise the proof's signed `target` MUST satisfy **at least one** declared selector. A selector is satisfied when every
  member `(k, v)` holds, where:
  - `resource_id` and `resource_type` compare with `target.resource_id` / `target.resource_type`;
  - any other key compares with `target.selectors[k]`;
  - comparison is canonical equality; a key the target does not carry is not satisfied.
- Otherwise the verifier MUST refuse with `TARGET_MISMATCH`.

### E4 — `single_use` (required true)
- Protocol v1 proofs are single-use only. A proof whose signed `scope.single_use` is not the JSON value `true` MUST be refused
  with `SCOPE_MODE_INVALID`.
- Verifiers MUST NOT treat a non-single-use proof as reusable.
- The executor's replay claim is still mandatory for every proof.

### E5 — revocation of the underlying authority
- When a proof carries a signed authority reference (`extensions.authority`), an edge configured with that issuer's
  revocation source MUST consult it after all other checks pass and before any replay claim or side effect.
- A revoked authority MUST be refused with `AUTHORITY_REVOKED`.
- If the revocation source cannot be consulted, the edge MUST refuse (fail closed); it MUST NOT execute.
- A proof whose issuer declares revocable authority, presented to an edge with no revocation source, is a deployment
  error. Implementations SHOULD refuse to start in that configuration outside development intent.

## Order

E4 runs with the scope-mode check, and E1 with the scope-capability check. E2 and E3 run after the action-hash check and
before revocation (E5). An implementation MAY order the four checks differently. The refusal code for a single violated rule
is the one given above.

## Compatibility

- This narrows acceptance; it does not widen it.
- An edge whose declarations agree with its proofs sees no change.
- An edge whose declarations contradicted its proofs was previously executing actions outside what it declared. That was the
  defect.
- Released verifiers that ignore these fields are non-conformant from 1.4.0. Their operators SHOULD treat the gap as a
  security fix (see the issuing component's advisory).

## Conformance

Executable vectors: `actenon-kernel/actenon/conformance/vectors/verifier_sdk_v1/edge_binding_cases.json`. These are shared,
hash-locked and vendored by the Go and Rust SDKs. Every listed SDK MUST produce the expected outcome, `reason_code` and
public message for each case.
