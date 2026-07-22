# Conformance vectors

This directory contains the test vectors that an implementation MUST pass to claim conformance to the Actenon protocol v1.x.

## Vector format

Each vector is a JSON file with the shape:

```json
{
  "name": "unique_vector_name",
  "description": "What this vector tests.",
  "input": { ... },          // for canonicalisation vectors
  "expected_canonical": "...", // for valid canonicalisation vectors
  "expected_error": "...",     // for invalid canonicalisation vectors
  "expected_refusal_code": "...", // for invalid canonicalisation vectors

  // OR for artefact vectors (proof, receipt, refusal, execution-mode):
  "artefact": { ... },         // the artefact to validate
  "expected_validation": "valid" | "invalid",
  "expected_error": "...",     // for invalid artefacts
  "expected_refusal_code": "..." // for invalid artefacts that produce a refusal
}
```

## Categories

| Directory | Contents |
|---|---|
| `canonicalisation/valid/` | Inputs and their expected canonical bytes (UTF-8). |
| `canonicalisation/invalid/` | Inputs that MUST be rejected with `CanonicalisationError` (and the protocol refusal code `CANONICALISATION_FAILURE`). |
| `proof/valid/` | `ExecutionProof` artefacts that MUST validate against the schema. |
| `proof/invalid/` | `ExecutionProof` artefacts that MUST fail validation, with the expected error. |
| `receipt/valid/` | `ExecutionReceipt` artefacts that MUST validate. |
| `receipt/invalid/` | `ExecutionReceipt` artefacts that MUST fail validation. |
| `refusal/valid/` | `ExecutionRefusal` artefacts that MUST validate (under their declared `disclosure_policy`). |
| `refusal/invalid/` | `ExecutionRefusal` artefacts that MUST fail validation. |
| `execution-mode/` | Mode-distinction vectors: a proof of mode X presented to a verifier of mode Y. |

## Cross-language consistency

The same vectors are consumed by:

* `conformance/python/` — Python conformance suite (pytest)
* `typescript/tests/conformance.test.ts` — TypeScript conformance (bun:test)

An implementation claims conformance by passing all vectors. The Python and TypeScript suites share the canonicalisation vectors; an implementation in a third language (Go, Rust) MUST also pass the same canonicalisation vectors byte-for-byte.

## Adding vectors

New vectors are added in MINOR protocol versions. Each new vector MUST:

1. Have a unique `name` (lowercase snake_case).
2. Have a `description` explaining what it tests.
3. Be added under the correct category (valid/invalid).
4. Be referenced in the CHANGELOG entry for the minor version.
