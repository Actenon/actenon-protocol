# 09 — Trusted Issuer Metadata

## Source of truth

The JSON Schema is at [`schemas/issuer_metadata.v1.json`](../schemas/issuer_metadata.v1.json). If this document and the schema disagree, the schema wins.

## Purpose

`IssuerMetadata` describes the issuer of an `ExecutionProof`. It allows a verifier to:

1. Discover the issuer's public keys (for signature verification).
2. Determine the issuer's current trust status (active, suspended, revoked).
3. Understand the issuer's key rotation policy.

The metadata is carried inline in the `issuer` field of an `ExecutionProof`. The verifier MAY also fetch fresh metadata from the issuer's well-known URL before honouring the proof (recommended for high-assurance deployments).

## Required fields

| Field | Type | Description |
|---|---|---|
| `issuer_id` | string | The unique identifier of the issuer. Stable across key rotations. |
| `issuer_type` | string | `authority_broker`, `resource_owner`, or `delegated_signer`. |
| `key_discovery` | object | How to discover the issuer's public keys. |

## Optional fields

| Field | Type | Description |
|---|---|---|
| `trust_status` | string | `active`, `suspended`, or `revoked`. The verifier MUST re-fetch the current status before honouring the proof. |
| `key_rotation_policy` | object | `{rotation_period_days, overlap_period_days}`. |

## Issuer types

| Type | Description | Example |
|---|---|---|
| `authority_broker` | The issuer is an authority broker such as actenon-permit. It issues proofs after running its policy engine. | actenon-permit with Ed25519 signing key. |
| `resource_owner` | The issuer is the resource owner self-issuing. This is the `resource_owned` execution mode. The resource mints proofs for actions it intends to execute itself. | A payment provider that issues proofs for its own refund API. |
| `delegated_signer` | The issuer is a delegated signing service. The authority broker has delegated proof-issuance to a separate signing service (e.g. an HSM-backed KMS). | actenon-cloud's managed signing service. |

## Key discovery methods

| Method | Description | Required fields |
|---|---|---|
| `well_known` | Fetch the issuer's key set and status from a well-known URL. | `well_known_url` |
| `embedded` | The public key is embedded in the proof itself. Suitable for `resource_owner` mode where the resource is its own issuer. | `embedded_key` |
| `external_registry` | Fetch from a configured external registry (e.g. a key transparency log). | `external_registry_url` |

## Well-known URL pattern

The recommended well-known URL pattern is:

```
https://<issuer-domain>/.well-known/actenon-issuer/<issuer_id>
```

The response is a JSON document containing:

```json
{
  "issuer_id": "...",
  "issuer_type": "authority_broker",
  "trust_status": "active",
  "keys": [
    {
      "key_id": "ed25519-9f3c1a175e9b",
      "algorithm": "EdDSA",
      "public_key": "base64url-encoded-key",
      "status": "active",
      "not_before": "2026-07-01T00:00:00Z",
      "expires_at": "2026-10-01T00:00:00Z"
    }
  ],
  "key_rotation_policy": {
    "rotation_period_days": 90,
    "overlap_period_days": 7
  }
}
```

The verifier SHOULD cache the well-known response for a short period (e.g. 5 minutes) to avoid excessive network requests. The cache MUST be invalidated if the issuer's `trust_status` is `suspended` or `revoked`.

The well-known URL pattern is proposed but NOT yet conformance-tested in v1.0. It is documented here to guide implementations; a future minor version will add conformance fixtures.

## Trust status

The `trust_status` field reflects the issuer's status AS KNOWN AT PROOF-ISSUANCE TIME. The verifier MUST re-fetch the current status before honouring the proof.

| Status | Description |
|---|---|
| `active` | The issuer is trusted and its keys are valid. |
| `suspended` | The issuer is temporarily untrusted (e.g. under investigation). The verifier MUST refuse with `ISSUER_UNTRUSTED` (trusted) / `PROOF_INVALID` (public). |
| `revoked` | The issuer is permanently untrusted (e.g. key compromise). The verifier MUST refuse with `AUTHORITY_REVOKED`. |

## Key rotation

When an issuer rotates its signing key:

1. The new key is added to the key set with `status: "active"`.
2. The old key remains in the key set with `status: "active"` for the `overlap_period_days` (so proofs signed with the old key continue to verify).
3. After the overlap period, the old key's status changes to `status: "retired"`.
4. The verifier refuses proofs signed with retired keys.

The protocol does not mandate a specific rotation period. The `key_rotation_policy` field is informative; the verifier MAY choose to ignore it.

## Conformance

The conformance suite includes fixtures that exercise:

* Embedded key discovery.
* Well-known URL discovery (mocked).
* Trust status transitions (active → suspended → revoked).

(Well-known URL fixtures are planned for v1.1; v1.0 only includes embedded-key fixtures.)
