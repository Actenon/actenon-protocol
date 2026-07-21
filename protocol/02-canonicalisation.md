# 02 — Canonicalisation

## Source of truth

The canonicalisation profile specification is at [`canonicalisation/ACTENON-JCS-STRICT-1.md`](../canonicalisation/ACTENON-JCS-STRICT-1.md). If this document and that specification disagree, the specification wins.

## Profile

The Actenon protocol uses ONE canonicalisation profile for all newly-minted artefacts: **`ACTENON-JCS-STRICT-1`**.

`ACTENON-JCS-STRICT-1` is a strict subset of [RFC 8785 (JCS)](https://www.rfc-editor.org/rfc/rfc8785.html) that rejects floating-point values entirely. The full specification is in [`canonicalisation/ACTENON-JCS-STRICT-1.md`](../canonicalisation/ACTENON-JCS-STRICT-1.md).

## Where the profile appears on the wire

The `canonicalisation` field on `ExecutionProof` and `ExecutionReceipt` carries the profile identifier. The field is a string matching one of:

* `ACTENON-JCS-STRICT-1` — canonical (newly minted proofs).
* `RFC8785-JCS` — deprecated alias (historical proofs); same logic, different label.

Any other value MUST be rejected with `CANONICALISATION_FAILURE`.

## What the profile is used for

The profile is used in three places:

1. **`action_hash` computation.** The verifier recomputes the hash of the canonicalised `(action, target, parameters)` tuple and compares to the `action_hash` in the proof. If the canonicalisation differs between issuer and verifier, the hashes will differ and the proof will be rejected.
2. **Signature payload.** The issuer signs the canonicalised proof payload. The verifier re-canonicalises and verifies the signature.
3. **Receipt digest.** The receipt's `resource_signature` (if present) is computed over the canonicalised receipt payload.

## Why a strict subset?

RFC 8785 permits floats but specifies that they be serialised using the shortest representation that round-trips. Different implementations disagree on edge cases (Python's `repr(0.1)` vs JavaScript's `(0.1).toString()`). These disagreements produce different bytes, which break cryptographic hashes and signatures.

`ACTENON-JCS-STRICT-1` rejects floats outright. Implementations that need to represent fractional values MUST use:

* Integer cents (e.g. `2500` for £25.00)
* String-encoded decimals (e.g. `"25.00"`)
* Integer-scaled fixed point (e.g. micro-units)

This is consistent with the existing actenon-kernel behaviour at `actenon/proof/canonical.py:53`.

## Conformance

An implementation claims conformance to `ACTENON-JCS-STRICT-1` by passing the conformance suite at [`conformance/vectors/canonicalisation/`](../conformance/vectors/canonicalisation/). The suite includes:

* **Valid vectors** — inputs and their expected canonical bytes. An implementation MUST produce the exact bytes.
* **Invalid vectors** — inputs that MUST be rejected (floats, oversized, too-deep, unsupported types). An implementation MUST raise an error, not produce output.

The Python reference implementation is at [`python/actenon_protocol/canonicalisation.py`](../python/actenon_protocol/canonicalisation.py). The TypeScript reference implementation is at [`typescript/src/canonicalisation.ts`](../typescript/src/canonicalisation.ts).
