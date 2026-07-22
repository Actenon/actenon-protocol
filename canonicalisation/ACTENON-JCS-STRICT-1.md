# ACTENON-JCS-STRICT-1 — Canonicalisation Profile

**Profile name:** `ACTENON-JCS-STRICT-1`
**Profile version:** `1`
**Status:** Canonical (the only label accepted for newly-minted proofs and receipts under protocol v1.x)
**Supersedes:** `RFC8785-JCS` (accepted as a deprecated alias for historical proofs; same logic, different label)
**Rejected label:** `actenon-jcs-sha256-v1` (never accepted by any implementation; removed from the protocol)

---

## 1. Purpose

`ACTENON-JCS-STRICT-1` is the canonicalisation profile used by every `ExecutionProof` and `ExecutionReceipt` in the Actenon protocol. It is a **strict subset** of [RFC 8785 (JSON Canonicalization Scheme)](https://www.rfc-editor.org/rfc/rfc8785.html) that rejects floating-point values entirely.

The profile exists to guarantee **byte-identical output across implementations** for the same input, regardless of language (Python, TypeScript, Go, Rust), runtime, or platform. This is a hard requirement for cryptographic hashing and signature verification.

## 2. Why a strict subset?

RFC 8785 permits floats but specifies that they be serialised using the shortest representation that round-trips. Different implementations disagree on edge cases (e.g. `0.1 + 0.2` in Python vs JavaScript, `repr(1e20)` vs `(1e20).toString()`). These disagreements produce different bytes, which break cryptographic hashes and signatures.

`ACTENON-JCS-STRICT-1` rejects floats outright. Implementations that need to represent fractional values MUST use:

* Integer cents (e.g. `2500` for £25.00)
* String-encoded decimals (e.g. `"25.00"`)
* Integer-scaled fixed point (e.g. micro-units)

## 3. Input validation

Before canonicalisation, the input MUST be validated:

1. **Depth limit.** The maximum nesting depth is 32. Inputs deeper than 32 levels MUST be rejected with `CANONICALISATION_FAILURE`.
2. **Output size limit.** The maximum canonicalised output size is 1,048,576 bytes (1 MiB). Inputs whose canonical form exceeds this MUST be rejected with `CANONICALISATION_FAILURE`.
3. **Type check.** The input MUST be a JSON value: `null`, `bool`, `int`, `str`, `list`, or `dict` (object). `float` MUST be rejected. Any other type (e.g. `tuple` in Python, `undefined` in JavaScript, `set`, `bytes`, custom objects) MUST be rejected.

## 4. Normative serialisation rules (all 18 behaviours)

### 4.1 Object key ordering

Object keys MUST be sorted by their UTF-8 byte representation, ascending. This matches RFC 8785 §3.2.3. The sort is by **bytes**, not by Unicode code point or by locale. For the BMP this coincides with code point order; for astral characters (code points > U+FFFF), UTF-8 byte order also coincides with code point order, so the two agree.

**Python:** `sorted(value.keys(), key=lambda k: k.encode("utf-8"))`
**TypeScript:** `Object.keys(obj).sort((a, b) => { const ab = new TextEncoder().encode(a); const bb = new TextEncoder().encode(b); for (let i = 0; i < Math.min(ab.length, bb.length); i++) { if (ab[i] !== bb[i]) return ab[i] - bb[i]; } return ab.length - bb.length; })`

### 4.2 UTF-8

All output MUST be UTF-8 encoded. String values are NOT `\u`-escaped — non-ASCII characters appear as their literal UTF-8 bytes. This matches RFC 8785 §3.2.2 ("no ASCII shortcuts").

**Python:** `json.dumps(value, ensure_ascii=False)`
**TypeScript:** `JSON.stringify(value)` (JavaScript's `JSON.stringify` does not `\u`-escape non-ASCII by default).

### 4.3 Unicode normalisation

**No Unicode normalisation is performed.** The input is canonicalised as-is. If the caller needs a specific normalisation form (NFC, NFD, etc.), they MUST apply it before passing the value to the canonicaliser. Two strings that are visually identical but have different Unicode representations will produce different canonical bytes. This is a deliberate choice — normalisation can change semantics and the canonicaliser must not silently alter input.

### 4.4 Strings

Strings are escaped per RFC 8259 §7 with the following specifics:

| Character | Escape |
|---|---|
| `"` (U+0022) | `\"` |
| `\` (U+005C) | `\\` |
| U+0008 (BS) | `\b` |
| U+0009 (TAB) | `\t` |
| U+000A (LF) | `\n` |
| U+000C (FF) | `\f` |
| U+000D (CR) | `\r` |
| Other control characters (U+0000–U+001F, excluding the above) | `\uXXXX` (lowercase hex) |
| All other characters (including non-ASCII) | Literal UTF-8 bytes |

The output is UTF-8 encoded. `ensure_ascii=False` (Python) or equivalent.

### 4.5 Integers

Integers are serialised as their decimal string representation:

* No leading zeros (except for `0` itself).
* No `+` sign.
* Negative numbers use `-`.
* Arbitrary precision is supported (Python: native `int`; TypeScript: `BigInt`).

**Examples:** `0` → `"0"`, `42` → `"42"`, `-1` → `"-1"`, `123456789012345678901234567890` → `"123456789012345678901234567890"`.

### 4.6 Negative integers

Negative integers use a leading `-` followed by the absolute value's decimal representation, with no leading zeros.

**Examples:** `-1` → `"-1"`, `-0` is NOT a valid integer (zero is `0`, not `-0`).

### 4.7 Zero

Zero is serialised as `"0"` (no leading zeros, no sign).

### 4.8 Booleans

* `true` → `"true"`
* `false` → `"false"`

### 4.9 Null

`null` → `"null"`

### 4.10 Arrays

Arrays are serialised as `[` + comma-separated canonicalised elements (in original order) + `]`. No whitespace between elements or around delimiters.

**Example:** `[1, "hello", true, null]` → `"[1,\"hello\",true,null]"`

### 4.11 Nested objects

Nested objects are canonicalised recursively. Each level's keys are sorted independently. The nesting structure is preserved.

**Example:** `{"outer": {"z": 1, "a": 2}}` → `"{"outer":{"a":2,"z":1}}"`

### 4.12 Duplicate keys

**Duplicate keys in a single object are PROHIBITED.** If the input contains duplicate keys (e.g. `{"a": 1, "a": 2}`), the behaviour is implementation-defined and MUST be treated as a malformed input. Implementations SHOULD raise `CanonicalisationError`.

**Python:** Python's `dict` silently overwrites duplicate keys (last-wins). Callers MUST NOT pass dicts with duplicate keys. The `json.loads` function also uses last-wins by default. To detect duplicates, parsers should use `object_pairs_hook` to check for duplicates before constructing the dict.

**TypeScript:** JavaScript's `JSON.parse` also uses last-wins. Callers MUST NOT pass objects with duplicate keys.

The canonicaliser itself does not detect duplicate keys (the dict/object has already been constructed by the time the canonicaliser sees it). Duplicate-key detection is the responsibility of the JSON parser, not the canonicaliser.

### 4.13 Unsupported numbers

The only supported numeric types are integers (Python `int`, TypeScript `BigInt`). Any other numeric type is unsupported:

* `float` (Python) / non-integer `number` (TypeScript) → **REJECTED**
* `complex` (Python) → **REJECTED**
* `Decimal` (Python) → **REJECTED** (use string encoding instead)

### 4.14 Floating-point values

**All floating-point values are REJECTED.** This is the defining characteristic of the "STRICT" profile. Implementations MUST raise `CanonicalisationError` (or language equivalent) when encountering a float.

**Python:** `isinstance(value, float)` → raise.
**TypeScript:** `typeof value === "number" && !Number.isInteger(value)` → raise.

### 4.15 NaN and Infinity

**NaN, Infinity, and -Infinity are REJECTED.** They are not valid JSON values (RFC 8259 §6 explicitly excludes them). Even if a language's JSON parser accepts them (Python's `json.loads` does by default), the canonicaliser MUST reject them.

**Python:** `float("nan")`, `float("inf")`, `float("-inf")` are all `float` instances and are caught by the float check (§4.14). Additionally, `json.dumps(..., allow_nan=False)` rejects them at the string-serialisation level.

**TypeScript:** `NaN` is a `number` but `Number.isInteger(NaN)` returns `false`, so it is caught by the float check. `Infinity` is also a non-integer `number`, caught by the same check.

### 4.16 Dates and timestamps

Dates and timestamps are NOT a JSON type. They MUST be represented as:

* ISO 8601 strings (e.g. `"2026-07-21T12:00:00Z"`)
* Unix timestamps as integers (e.g. `1721563200`)

The canonicaliser treats them as strings or integers respectively. No date-specific normalisation is performed.

### 4.17 Binary values

Binary values (Python `bytes`, `bytearray`; TypeScript `Uint8Array`, `ArrayBuffer`) are NOT a JSON type. They MUST be represented as:

* Base64url-encoded strings (e.g. `"YWJjZA"`)

The canonicaliser treats them as strings. No binary-specific handling is performed. Passing a raw `bytes` value to the canonicaliser is an error (unsupported type).

### 4.18 Absent versus null fields

**Absent fields and null fields are semantically different.**

* An **absent** field (a key that does not exist in the object) is not canonicalised — it does not appear in the output.
* A **null** field (a key that exists with value `null`) IS canonicalised — it appears as `"key":null` in the output.

**Example:** `{"a": 1}` (absent `b`) → `"{"a":1}"`; `{"a": 1, "b": null}` (null `b`) → `"{"a":1,"b":null}"`.

Implementations MUST NOT treat absent fields as null or vice versa. The caller is responsible for ensuring that optional fields are either present with a value (including `null`) or absent from the dict/object.

## 5. Digest algorithm

The canonicalisation profile is paired with a digest algorithm for computing action hashes and proof signatures:

* **Algorithm:** SHA-256
* **Input:** The UTF-8 bytes of the canonicalised JSON.
* **Output:** The 64-character lowercase hexadecimal string of the SHA-256 digest.

**Python:** `hashlib.sha256(canonical_bytes).hexdigest()`
**TypeScript:** `crypto.subtle.digest("SHA-256", canonicalBytes)` → hex-encode the result.

## 6. Prohibited inputs

The following inputs MUST be rejected with `CanonicalisationError`:

| Input | Reason |
|---|---|
| `float` (any value, including NaN, Infinity, -Infinity) | §4.14 |
| `NaN` | §4.15 |
| `Infinity`, `-Infinity` | §4.15 |
| Non-string dict keys (int, float, tuple, None) | §4.12 / RFC 8785 requires string keys |
| `bytes`, `bytearray`, `set`, `frozenset` | Not a JSON type |
| `tuple` in Python | Accepted as an array (for backward compat with the kernel); rejected in strict mode |
| Custom objects (not a JSON type) | Not a JSON type |
| `undefined` in JavaScript | Not a JSON type |
| Input deeper than 32 levels | §3.1 |
| Canonical output exceeding 1 MiB | §3.1 |

## 7. Compatibility handling

* **`RFC8785-JCS` (deprecated alias):** Historical proofs may carry this label. The canonicalisation logic is identical to `ACTENON-JCS-STRICT-1`. Consumers MUST accept this label for verification; producers MUST NOT emit it for new artefacts.
* **`actenon-jcs-sha256-v1` (rejected):** Never accepted by any implementation. Removed from the protocol.
* **Backward verification:** Existing proofs canonicalised under `ACTENON-JCS-STRICT-1` or `RFC8785-JCS` continue to verify. The profile's serialisation rules are immutable for the life of protocol v1.x. A future `ACTENON-JCS-STRICT-2` would be a breaking change requiring a protocol MAJOR version bump.

## 8. Reference implementations

* **Python:** `python/actenon_protocol/canonicalisation.py`
* **TypeScript:** `typescript/src/canonicalisation.ts`

Both implementations MUST produce byte-identical output for all valid inputs. The conformance suite at `conformance/vectors/canonicalisation/` is the normative test.

## 9. Conformance command

A reusable conformance command is available:

```bash
# Python
python -m actenon_protocol.conformance_canonicalisation

# TypeScript (from the typescript/ directory)
bun run conformance.ts
```

The command runs all normative vectors and reports pass/fail. Each repository in the Actenon ecosystem can invoke this command in CI to verify that its canonicalisation implementation produces the expected bytes.
