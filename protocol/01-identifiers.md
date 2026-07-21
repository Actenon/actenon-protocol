# 01 — Identifiers

## Source of truth

The machine-readable identifier-prefix registry is at [`identifiers/prefixes.v1.yaml`](../identifiers/prefixes.v1.yaml). If this document and the registry disagree, the registry wins.

## Format

Every Actenon protocol identifier has the form:

```
<prefix><hex_chars>
```

Where:

* `prefix` is one of the registered prefixes (see below).
* `hex_chars` is a non-empty lowercase-hexadecimal string.
* The minimum length of `hex_chars` is 16 (preserves backward compatibility with existing actenon-permit identifiers).
* The recommended length of `hex_chars` is 32 (full UUID4 hex, 128 bits of entropy).
* The prefix is lowercase; the hex chars are lowercase.

The regex is:

```
^[a-z][a-z0-9_]*_[0-9a-f]{16,}$
```

## Registered prefixes

| Prefix | Artefact | New in v1.0? | Compatibility |
|---|---|---|---|
| `intent_` | `AuthorisedExecutionIntent` | canonical | Preserves the actenon-kernel `intent_id` convention. The actenon-permit `act_` prefix is accepted as a deprecated alias. |
| `authz_` | `AuthorityDecision` | new | No prior implementation. |
| `grant_` | `Grant` | canonical | Preserves the existing actenon-permit `grant_<16hex>` format. |
| `proof_` | `ExecutionProof` | new canonical | The actenon-kernel internally uses `pccb_id`; on the wire, the canonical prefix is `proof_`. The `pccb_` alias is registered defensively. |
| `exec_` | `ExecutionAttempt` | new | Separates replay (keyed by `proof_`) from idempotency (keyed by `exec_`), addressing audit finding K-04. |
| `rcpt_` | `ExecutionReceipt` | new canonical | No prior implementation; the kernel's `receipt_id` field had no canonical prefix. |
| `rful_` | `ExecutionRefusal` | new canonical | No prior implementation; the kernel's `refusal_id` field had no canonical prefix. |

## Aliases

The registry declares two aliases for backward compatibility:

| Canonical | Alias | Reason |
|---|---|---|
| `intent_` | `act_` | actenon-permit uses `act_<16hex>` for `Action.action_id`, which is passed as the kernel's `intent_id`. Existing permit deployments emit `act_`; consumers MUST accept it as equivalent to `intent_`. |
| `proof_` | `pccb_` | Defensive registration. No known implementation emits `pccb_` on the wire; the kernel's `pccb_id` is implementation-specific. |

Aliases are deprecated since v1.0.0 and will be removed in v2.0.0. Consumers SHOULD warn (not refuse) when they encounter an alias.

## Forbidden prefixes

The registry declares the following prefixes as forbidden — they MUST NOT be used because they belong to concerns outside the protocol's scope:

| Prefix | Reason |
|---|---|
| `tenant_` | Tenant modelling is owned by Cloud. |
| `user_` | User/subject identity is owned by the identity provider. |
| `policy_` | Policy evaluation is owned by the authority broker. |
| `approval_` | Approvals are owned by the authority broker. |

## Generation

Implementations SHOULD generate identifiers using a cryptographically secure random number generator (e.g. `os.urandom` in Python, `crypto.getRandomValues` in JavaScript). Implementations MUST NOT use sequential or time-based identifiers (predictable identifiers enable proof pre-emption attacks).

The recommended generation algorithm is:

```python
import os
def generate_identifier(prefix: str) -> str:
    return f"{prefix}{os.urandom(16).hex()}"  # 32 hex chars
```

```typescript
function generateIdentifier(prefix: string): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${prefix}${hex}`;
}
```

## Validation

The protocol's Python and TypeScript type packages include identifier validators. See:

* [`python/actenon_protocol/identifiers.py`](../python/actenon_protocol/identifiers.py)
* [`typescript/src/identifiers.ts`](../typescript/src/identifiers.ts)

Both validators implement the same regex and the same alias resolution. The conformance suite includes fixtures that prove identical acceptance and rejection behaviour across the two languages.
