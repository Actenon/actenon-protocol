# 10 — Evidence Linkage

## Source of truth

The JSON Schema is at [`schemas/evidence_link.v1.json`](../schemas/evidence_link.v1.json). If this document and the schema disagree, the schema wins.

## Purpose

`EvidenceLink` is a reference from a protocol artefact (proof, receipt, refusal) to an external evidence record. The evidence record provides tamper-evidence, audit trail, or third-party attestation.

Evidence links are OPTIONAL on every artefact. An artefact without evidence links is still valid; it just has no external tamper-evidence beyond its own signature.

## Evidence types

| Type | Description | Example issuer |
|---|---|---|
| `transparency_log` | An entry in a public append-only transparency log (e.g. a Certificate Transparency-style log for proofs). | Transparency log operator. |
| `receipt_chain` | An entry in a tamper-evident receipt chain (each entry counter-signs the previous). | Protected resource or receipt chain operator. |
| `audit_ledger` | An entry in a hash-chained audit ledger. | actenon-permit's `Ledger`. |
| `external_attestation` | A third-party attestation (e.g. a TLS notary attestation, a secure timestamp). | Third-party attestation service. |
| `counter_signature` | A counter-signature by a different key (e.g. the resource owner counter-signing a proof). | Resource owner or other signing party. |

## Link types

The `link_type` field determines how the evidence is referenced:

| Link type | Description | Required `target_ref` fields |
|---|---|---|
| `inline` | The evidence payload is embedded in the artefact. | `inline_payload` |
| `external_url` | The evidence is at the given URL. | `url` (and optionally `hash` for integrity) |
| `content_hash` | Only the hash of the evidence is recorded. | `hash` |

## Why content-hash-only?

Some deployments cannot expose the full evidence (e.g. because it contains PII, or because the evidence log is private). In those cases, the artefact records only the hash of the evidence. A third party can later verify that the evidence existed (by revealing the evidence and checking the hash) without the artefact itself revealing the evidence.

## Tamper-evidence chains

A receipt chain is built as follows:

1. The resource issues receipt R1 with `resource_signature = sign(canonical(R1 minus signature))`.
2. The transparency log operator includes R1 in its log, producing a transparency log entry T1.
3. R1 is updated with an `evidence_links` entry pointing to T1.
4. The next receipt R2 includes R1's hash in its `evidence_links` (as a `counter_signature` link).
5. And so on.

The chain is tamper-evident: any modification to a past receipt breaks the hash chain at the next receipt.

The protocol does NOT mandate a specific chain structure. It only defines the `EvidenceLink` shape so that implementations can interoperate.

## Conformance

The conformance suite includes fixtures that exercise:

* `inline` evidence links.
* `external_url` evidence links.
* `content_hash` evidence links.
* Receipt chains (multiple receipts linked by counter-signature).

See [`conformance/vectors/receipt/`](../conformance/vectors/receipt/) and [`conformance/vectors/proof/`](../conformance/vectors/proof/).
