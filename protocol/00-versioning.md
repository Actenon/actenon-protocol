# 00 — Protocol Versioning

This specification mirrors [VERSIONING.md](../VERSIONING.md). If the two disagree, [VERSIONING.md](../VERSIONING.md) is authoritative (it is the document referenced by the changelog and the governance process).

## Current version

* Protocol version: `1.0.0`
* Canonicalisation profile: `ACTENON-JCS-STRICT-1` (profile version `1`)
* Refusal taxonomy version: `1`
* Identifier registry version: `1`

## Version string format

`MAJOR.MINOR.PATCH` where:

* `MAJOR` — breaking changes (wire-incompatible).
* `MINOR` — compatible additions (new optional fields, new codes, new prefixes).
* `PATCH` — bug fixes that do not change wire semantics.

See [VERSIONING.md](../VERSIONING.md) § "What counts as a compatible addition" and § "What counts as a breaking change" for the full enumeration.

## Where the version appears on the wire

Every artefact (`ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`, `AuthorisedExecutionIntent`) carries a `protocol_version` field. The field is a string matching `^1\.[0-9]+\.[0-9]+$` for protocol v1.x.

The major version is also encoded in the JSON Schema `$id` URI: `urn:actenon:protocol:<artefact>:v<MAJOR>`. For example, `urn:actenon:protocol:execution-proof:v1` is the schema for `ExecutionProof` under protocol major version 1.

## Consumer pinning

Consumers MUST pin to a major version (`^1`) and tolerate any minor/patch within that major. Consumers MAY refuse unknown minor versions for stricter guarantees, but MUST NOT refuse known minor versions.

When a consumer receives an artefact from a higher minor version with unknown fields, it MUST ignore the unknown fields (forward compatibility). When it receives an artefact from an unsupported major, it MUST refuse with `UNSUPPORTED_PROTOCOL_VERSION`.

See [VERSIONING.md](../VERSIONING.md) § "Consumer pinning requirements" for the full rules.
