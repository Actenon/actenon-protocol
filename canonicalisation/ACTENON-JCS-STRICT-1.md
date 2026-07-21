# ACTENON-JCS-STRICT-1 — Canonicalisation Profile

**Profile name:** `ACTENON-JCS-STRICT-1`
**Profile version:** `1`
**Status:** Canonical (the only label accepted for newly-minted proofs and receipts under protocol v1.x)
**Supersedes:** `RFC8785-JCS` (accepted as a deprecated alias for historical proofs; same logic, different label)
**Rejected label:** `actenon-jcs-sha256-v1` (never accepted by any implementation; removed from the protocol)

## 1. Purpose

`ACTENON-JCS-STRICT-1` is the canonicalisation profile used by every `ExecutionProof` and `ExecutionReceipt` in the Actenon protocol. It is a **strict subset** of [RFC 8785 (JSON Canonicalization Scheme)](https://www.rfc-editor.org/rfc/rfc8785.html) that rejects floating-point values entirely.

The profile exists to guarantee **byte-identical output across implementations** for the same input, regardless of language (Python, TypeScript, Go, Rust), runtime, or platform. This is a hard requirement for cryptographic hashing and signature verification.

## 2. Why a strict subset?

RFC 8785 permits floats but specifies that they be serialised using the shortest representation that round-trips. Different implementations disagree on edge cases (e.g. `0.1 + 0.2` in Python vs JavaScript, `repr(1e20)` vs `(1e20).toString()`). These disagreements produce different bytes, which break cryptographic hashes and signatures.

`ACTENON-JCS-STRICT-1` rejects floats outright. Implementations that need to represent fractional values MUST use:

* Integer cents (e.g. `2500` for £25.00)
* String-encoded decimals (e.g. `"25.00"`)
* Integer-scaled fixed point (e.g. micro-units)

This is consistent with the audit finding K-04 and the existing Kernel behaviour at `actenon/proof/canonical.py:53` (`raise TypeError("floating-point values are not supported in canonical action hashing")`).

## 3. Algorithm

### 3.1 Input validation

Before canonicalisation, the input MUST be validated:

1. **Depth limit.** The maximum nesting depth is 32. Inputs deeper than 32 levels MUST be rejected with `CANONICALISATION_FAILURE`.
2. **Output size limit.** The maximum canonicalised output size is 1,048,576 bytes (1 MiB). Inputs whose canonical form exceeds this MUST be rejected with `CANONICALISATION_FAILURE`.
3. **Type check.** The input MUST be a JSON value: `null`, `bool`, `int`, `str`, `list`, or `dict`. `float` MUST be rejected. Any other type (e.g. `tuple`, `set`, `bytes`, custom objects) MUST be rejected.

### 3.2 Serialisation rules

| JSON type | Canonical form |
|---|---|
| `null` | `null` |
| `true` | `true` |
| `false` | `false` |
| `int` (any size) | The integer's decimal string representation. No leading zeros (except for `0` itself). No `+` sign. Negative numbers use `-`. |
| `float` | **REJECTED.** Implementations MUST raise `TypeError` (or language equivalent). |
| `str` | The string encoded per RFC 8785 §3.2.2: UTF-8 bytes, escaped per JSON string rules, no ASCII shortcuts (i.e. non-ASCII characters are NOT `\u`-escaped). `ensure_ascii=False`. |
| `list` (array) | `[` + comma-separated canonicalised elements (in original order) + `]`. No whitespace. |
| `dict` (object) | `{` + comma-separated `"key":value` pairs (keys sorted by UTF-8 byte order, ascending) + `}`. No whitespace. |

### 3.3 Key sorting

Object keys MUST be sorted by their UTF-8 byte representation, ascending. This matches RFC 8785 §3.2.3.

Implementation note: in Python, `sorted(value.keys())` produces the correct order because Python strings compare by Unicode code point, which matches UTF-8 byte order for the BMP. For astral characters (code points > U+FFFF), UTF-8 byte order and code point order agree, so this remains correct.

In JavaScript, `Object.keys(value).sort()` produces the correct order for ASCII keys but may differ for non-ASCII keys (the default sort is by UTF-16 code unit, not UTF-8 byte). Implementations MUST sort by UTF-8 byte. A correct implementation is:

```javascript
function utf8ByteCompare(a, b) {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  for (let i = 0; i < Math.min(aBytes.length, bBytes.length); i++) {
    if (aBytes[i] !== bBytes[i]) return aBytes[i] - bBytes[i];
  }
  return aBytes.length - bBytes.length;
}
Object.keys(value).sort(utf8ByteCompare);
```

### 3.4 String escaping

Strings are escaped per RFC 8259 §7 with the following specifics:

* `"` → `\"`
* `\` → `\\`
* Control characters (U+0000 through U+001F) → `\uXXXX` (lowercase hex)
* U+0008 (BS) → `\b`
* U+0009 (TAB) → `\t`
* U+000A (LF) → `\n`
* U+000C (FF) → `\f`
* U+000D (CR) → `\r`
* All other characters (including non-ASCII) → literal UTF-8 bytes

The output is UTF-8 encoded. `ensure_ascii=False` (Python) or equivalent — non-ASCII characters are NOT `\u`-escaped.

### 3.5 Separators

* Object key-value separator: `:`
* Array/object element separator: `,`
* No whitespace anywhere outside string contents.

In Python: `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` — BUT this Python snippet will NOT reject floats. The protocol's reference implementation wraps it with an explicit float check. See `python/actenon_protocol/canonicalisation.py`.

## 4. Reference implementation

A Python reference implementation is provided at `python/actenon_protocol/canonicalisation.py`. It produces byte-identical output to the existing `actenon-kernel/actenon/proof/canonical.py` for all valid inputs.

A TypeScript reference implementation is provided at `typescript/src/canonicalisation.ts`. It is verified against the same conformance vectors as the Python implementation.

## 5. Conformance

An implementation claims conformance to `ACTENON-JCS-STRICT-1` by passing the conformance suite at `conformance/vectors/canonicalisation/`. The suite includes:

* **Valid vectors** — inputs and their expected canonical bytes. An implementation MUST produce the exact bytes.
* **Invalid vectors** — inputs that MUST be rejected (floats, oversized, too-deep, unsupported types). An implementation MUST raise an error, not produce output.

See `conformance/vectors/canonicalisation/README.md` for the vector format.

## 6. Versioning

The profile is versioned. The current version is `1`. A future `ACTENON-JCS-STRICT-2` would be a breaking change requiring a protocol MAJOR version bump. The protocol guarantees that `ACTENON-JCS-STRICT-1` will not change for the life of protocol v1.x.

## 7. Aliases

| Alias | Status | Logic | Use case |
|---|---|---|---|
| `ACTENON-JCS-STRICT-1` | **Canonical** | (this spec) | New proofs and receipts. |
| `RFC8785-JCS` | **Deprecated** (accepted, not emitted) | Identical to `ACTENON-JCS-STRICT-1` | Historical proofs minted by older Kernel versions. Will be removed in protocol v2.0. |
| `actenon-jcs-sha256-v1` | **Rejected** | n/a | Never accepted. Appeared only in docs. Removed. |

Consumers MUST accept both `ACTENON-JCS-STRICT-1` and `RFC8785-JCS` for verification. Consumers MUST emit `ACTENON-JCS-STRICT-1` for new artefacts. Consumers MUST reject `actenon-jcs-sha256-v1` and any other label with `CANONICALISATION_FAILURE`.
