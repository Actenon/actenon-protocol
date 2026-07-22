# Protocol Versioning

## Current version

**Protocol version:** `1.0.0`
**Canonicalisation profile:** `ACTENON-JCS-STRICT-1` (profile version `1`)
**Refusal taxonomy version:** `1`
**Identifier registry version:** `1`

## Versioning scheme

The protocol uses **semantic versioning** (`MAJOR.MINOR.PATCH`) with the following protocol-specific rules:

| Component | Bumped when | Example |
|---|---|---|
| `PATCH` | A bug fix in the conformance suite, schemas, or types that does NOT change wire semantics. | `1.0.0` → `1.0.1` (fix a typo in a fixture) |
| `MINOR` | A compatible addition: new optional field, new refusal code, new identifier prefix, new canonicalisation alias. | `1.0.0` → `1.1.0` (add `POLICY_REFUSAL` code) |
| `MAJOR` | A breaking change: removed field, changed field semantics, removed refusal code, new canonicalisation profile. | `1.0.0` → `2.0.0` (replace `ACTENON-JCS-STRICT-1` with `ACTENON-JCS-STRICT-2`) |

## What counts as a compatible addition (MINOR)

The following changes are **compatible** and require only a MINOR bump:

* Adding a new optional field to any schema. Existing consumers MUST ignore unknown fields.
* Adding a new refusal code to the catalogue. Existing consumers MUST treat unknown codes as `OUTCOME_UNKNOWN` (see "Unknown-version behaviour" below).
* Adding a new identifier prefix to the registry. Existing consumers MUST accept identifiers with unknown prefixes (they cannot assume a specific prefix set).
* Adding a new canonicalisation alias that maps to an existing profile's logic.
* Adding a new optional claim name to `ExecutionProof`.
* Adding a new evidence-link type.
* Adding a new execution-mode value (this is rare and SHOULD be avoided — execution modes are a closed set in practice).

## What counts as a breaking change (MAJOR)

The following changes are **breaking** and require a MAJOR bump:

* Removing a field from any schema.
* Changing the semantics of an existing field (e.g. redefining `action_hash` to use a different algorithm by default).
* Removing a refusal code from the catalogue (codes can be DEPRECATED but not removed within a major version).
* Removing an identifier prefix.
* Replacing the canonicalisation profile (e.g. `ACTENON-JCS-STRICT-1` → `ACTENON-JCS-STRICT-2`).
* Changing the disclosure policy defaults (e.g. making `SIGNATURE_INVALID` the default disclosed code instead of `PROOF_INVALID`).
* Changing the required field set of any schema.

## Deprecation periods

| Change type | Deprecation period | Removal |
|---|---|---|
| Compatible minor addition | n/a (additions are immediately available) | n/a |
| Breaking major change | 90 days from deprecation announcement | requires MAJOR bump; old behaviour preserved in previous major for 60 days after the new major ships |
| Security fix | immediate disclosure | backported to previous major for 60 days |

A deprecated field/code/prefix gets a `deprecated_since` field in its catalogue entry. Consumers SHOULD warn when they encounter a deprecated artefact. The deprecation period gives consumers time to migrate before the next major version removes it.

## Alias handling

The protocol supports two kinds of alias:

1. **Canonicalisation aliases.** `RFC8785-JCS` is an alias for `ACTENON-JCS-STRICT-1` (same logic, different label). Historical proofs with the legacy label continue to verify. New proofs MUST use the canonical label.

2. **Refusal-code aliases.** The existing `actenon-kernel` `FailureCode` enum members (`PCCB_REQUIRED`, `PCCB_EXPIRED`, `DUPLICATE_REPLAY`, etc.) are preserved as aliases for the new canonical codes (`PROOF_MISSING`, `PROOF_EXPIRED`, `REPLAY_DETECTED`). See `refusals/catalogue.v1.yaml`.

Aliases are resolved by the consumer before processing. An alias does NOT trigger an "unknown-version" refusal.

## Unknown-version behaviour

When a consumer receives an artefact whose `protocol_version` major matches the consumer's supported major but whose minor is higher:

* The consumer MUST process the artefact.
* The consumer MUST ignore unknown fields.
* The consumer MUST treat unknown refusal codes as `OUTCOME_UNKNOWN` (see `protocol/07-refusal.md`).
* The consumer MUST treat unknown identifier prefixes as valid (the prefix is informative, not authoritative).
* The consumer MUST treat unknown canonicalisation profiles as a `CANONICALISATION_FAILURE` refusal (the canonicalisation profile is authoritative — see below).

## Unsupported-major refusal

When a consumer receives an artefact whose `protocol_version` major does NOT match the consumer's supported major:

* The consumer MUST refuse with `UNSUPPORTED_PROTOCOL_VERSION`.
* The consumer SHOULD include the supported major(s) in the refusal message.
* The consumer MUST NOT attempt to process the artefact.

This is the ONLY refusal that can be issued before the artefact is parsed. All other refusals require successful parsing.

## Security-patch handling

A security patch is a fix that addresses a vulnerability in the protocol itself (e.g. a canonicalisation edge case, a disclosure leak). It is treated as:

* A PATCH bump if the fix is transparent to consumers (e.g. tightened conformance vectors).
* A MINOR bump if the fix adds a new optional field (e.g. a `disclosure_policy` override).
* A MAJOR bump (with 90-day deprecation) if the fix changes wire semantics.

Security patches are backported to the previous major version for 60 days. After 60 days, the previous major is end-of-life.

## Consumer pinning requirements

Consumers (verifiers, brokers, SDKs) MUST:

1. Pin to a specific protocol MAJOR version (e.g. `^1`).
2. Tolerate any MINOR version within the pinned MAJOR.
3. Refuse to process artefacts from a different MAJOR.
4. Log a warning (not a refusal) when they encounter an artefact from a higher MINOR with unknown fields.
5. Update their pin within 90 days of a MAJOR release.

Consumers MAY:

* Pin to a specific MINOR version for stricter guarantees (e.g. refuse unknown refusal codes rather than mapping to `OUTCOME_UNKNOWN`).
* Pin to a specific PATCH version for reproducibility (e.g. in CI).

## Version discovery

The protocol version is carried in:

1. The `protocol_version` field on every artefact (`ExecutionProof`, `ExecutionReceipt`, `ExecutionRefusal`, `issuer_metadata`).
2. The `$id` URI of every JSON Schema (e.g. `urn:actenon:protocol:execution-proof:v1`).
3. The `protocol_version` field in the conformance suite metadata (`conformance/suite.json`).

The canonicalisation profile is carried in:

1. The `canonicalisation` field on `ExecutionProof` and `ExecutionReceipt`.
2. The `profile` field in the canonicalisation profile specification (`canonicalisation/ACTENON-JCS-STRICT-1.md`).

The refusal taxonomy version is carried in:

1. The `taxonomy_version` field in `refusals/catalogue.v1.yaml`.
2. (Future) a `taxonomy_version` field on `ExecutionRefusal` if a v2 taxonomy is ever introduced.
