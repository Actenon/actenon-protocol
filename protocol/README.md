# Protocol specifications

This directory contains the human-readable specifications for the Actenon protocol. The machine-readable sources of truth are in the sibling directories:

* [`schemas/`](../schemas/) — JSON Schemas (wire format)
* [`refusals/catalogue.v1.yaml`](../refusals/catalogue.v1.yaml) — refusal-code catalogue
* [`identifiers/prefixes.v1.yaml`](../identifiers/prefixes.v1.yaml) — identifier-prefix registry
* [`canonicalisation/ACTENON-JCS-STRICT-1.md`](../canonicalisation/ACTENON-JCS-STRICT-1.md) — canonicalisation profile spec

If the markdown and the machine-readable sources disagree, the machine-readable sources win.

## Specification index

| # | File | Topic |
|---|---|---|
| 00 | [00-versioning.md](00-versioning.md) | Protocol versioning (mirrors [VERSIONING.md](../VERSIONING.md)) |
| 01 | [01-identifiers.md](01-identifiers.md) | Identifier formats and prefixes |
| 02 | [02-canonicalisation.md](02-canonicalisation.md) | Canonicalisation profile overview |
| 03 | [03-execution-modes.md](03-execution-modes.md) | Execution modes (`brokered`, `resource_owned`) |
| 04 | [04-claim-names.md](04-claim-names.md) | Proof claim names |
| 05 | [05-proof.md](05-proof.md) | `ExecutionProof` |
| 06 | [06-receipt.md](06-receipt.md) | `ExecutionReceipt` |
| 07 | [07-refusal.md](07-refusal.md) | `ExecutionRefusal` and refusal-code catalogue |
| 08 | [08-outcome-codes.md](08-outcome-codes.md) | Verification and execution outcome codes |
| 09 | [09-issuer-metadata.md](09-issuer-metadata.md) | Trusted issuer metadata and discovery |
| 10 | [10-evidence-linkage.md](10-evidence-linkage.md) | Evidence-linkage fields |
| 11 | [11-disclosure-policy.md](11-disclosure-policy.md) | Secure disclosure policy |

## Normative references

* [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html) — JSON Canonicalization Scheme (the basis for `ACTENON-JCS-STRICT-1`)
* [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) — The JSON Data Interchange Syntax
* [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037.html) — CFRG ECDH and Signatures in JOSE (Ed25519)
* [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html)
* [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0)

## Conformance

An implementation claims conformance to the Actenon protocol by passing the conformance suite at [`../conformance/`](../conformance/). See [`../conformance/README.md`](../conformance/README.md) for details.
