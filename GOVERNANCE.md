# Governance

## Purpose

`actenon-protocol` is the neutral, open, implementation-independent boundary contract for the Actenon ecosystem. It is governed as a **protocol**, not as a product. No implementation (including the official Actenon implementations) has special standing to change the protocol unilaterally.

## Maintainers

The protocol is maintained by a **protocol maintainer team**. Initial maintainers (at v1.0.0):

* Actenon Ltd (protocol steward)

Maintainership is expected to expand over time to include representatives from major implementation teams and third-party adopters. The mechanism for adding maintainers is documented in `MAINTAINERS.md` (to be created upon first external adoption).

## Decision-making

| Change type | Process | Notice period |
|---|---|---|
| Compatible minor addition (new optional field, new refusal code, new canonicalisation alias) | Maintainer review + 14-day comment period | 14 days |
| Breaking major change | Maintainer review + 90-day deprecation period + major version bump | 90 days |
| Security fix | Maintainer review + coordinated disclosure (see [SECURITY.md](SECURITY.md)) + backport to previous major version for 60 days | immediate |
| Documentation clarification | Maintainer review | none |

## Compatibility commitments

The protocol guarantees:

1. **Wire compatibility.** A proof minted under protocol version `1.0` will verify under any `1.x` implementation. Breaking changes require a major version bump to `2.0`.
2. **Identifier compatibility.** Prefixes (`grant_`, `proof_`, `rcpt_`, `rful_`, `exec_`, `authz_`, `intent_`) are stable for the life of the major version. A prefix cannot be reused for a different concept within the same major version.
3. **Canonicalisation compatibility.** The `ACTENON-JCS-STRICT-1` profile is immutable for the life of the major version. A new profile (e.g. `ACTENON-JCS-STRICT-2`) would be a major version bump.
4. **Refusal-code compatibility.** A refusal code, once added, cannot be removed within the major version. It can be deprecated (with a `deprecated_since` field in the catalogue) but not removed.

## Relationship to the Actenon implementation repos

The four implementation repos (`actenon-kernel`, `actenon-permit`, `actenon-cloud`, `actenon-scan`) are **consumers** of this protocol, not owners of it. They may add implementation-specific extensions (e.g. Cloud's `IssuedProof` ORM row) but those extensions are not part of the protocol.

If an implementation needs a protocol change, the change is proposed here first, reviewed under the governance process above, and only then adopted by the implementation.

## Licensing of contributions

All contributions to this repository are licensed under Apache-2.0 (see [LICENSE](LICENSE)). Contributors retain their copyright but grant a perpetual, worldwide, non-exclusive, royalty-free licence under the Apache-2.0 terms.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
