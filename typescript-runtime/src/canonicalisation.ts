import { parseStrictJson } from "./strict-json.js";

/**
 * ACTENON-JCS-STRICT-1 canonicalisation — runtime implementation.
 *
 * This is the runtime counterpart to @actenon/protocol-types. It provides
 * compiled JavaScript functions that can be imported by any TypeScript or
 * JavaScript consumer without needing to compile TypeScript source.
 *
 * The implementation produces byte-identical output to:
 *   - python/actenon_protocol/canonicalisation.py (Python reference)
 *   - typescript/src/canonicalisation.ts (types-only package)
 *
 * See canonicalisation/ACTENON-JCS-STRICT-1.md for the full specification.
 */

export const MAX_CANONICAL_OUTPUT_BYTES = 1_048_576; // 1 MiB
export const MAX_JSON_DEPTH = 32;

export class CanonicalisationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CanonicalisationError";
  }
}

// ─── Depth validation ──────────────────────────────────────────────────

function validateDepth(value: unknown, maxDepth: number, currentDepth: number = 0): void {
  if (currentDepth > maxDepth) {
    throw new CanonicalisationError(`JSON depth exceeds maximum ${maxDepth}`);
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      validateDepth(item, maxDepth, currentDepth + 1);
    }
  } else if (value !== null && typeof value === "object") {
    for (const v of Object.values(value as Record<string, unknown>)) {
      validateDepth(v, maxDepth, currentDepth + 1);
    }
  }
}

// ─── Key sorting ───────────────────────────────────────────────────────
/**
 * Compare two strings by their UTF-8 byte representation, ascending.
 * This matches the Python reference's
 * `sorted(keys, key=lambda k: k.encode("utf-8"))`.
 *
 * UTF-8 byte order coincides with Unicode code point order. It does NOT
 * match RFC 8785 §3.2.3, which sorts by UTF-16 code units: the two differ
 * when U+E000..U+FFFF is compared with an astral character (profile §4.1).
 *
 * Note: JavaScript's default Array.prototype.sort() on strings sorts by
 * UTF-16 code unit, which diverges from code point order for astral
 * characters. We must NOT use the default string sort.
 */
function utf8ByteCompare(a: string, b: string): number {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  for (let i = 0; i < Math.min(aBytes.length, bBytes.length); i++) {
    if (aBytes[i] !== bBytes[i]) return aBytes[i] - bBytes[i];
  }
  return aBytes.length - bBytes.length;
}

// ─── String serialisation ──────────────────────────────────────────────
/**
 * Serialise a string per RFC 8259 §7 with ACTENON-JCS-STRICT-1 rules:
 * - " and \ are escaped
 * - Control characters (U+0000–U+001F) use \b \t \n \f \r or \uXXXX
 * - Non-ASCII characters appear as literal UTF-8 bytes (no \u escaping)
 *
 * JSON.stringify produces exactly this output by default (it does not
 * \u-escape non-ASCII), so we delegate to it — after rejecting unpaired
 * surrogates, which JSON.stringify would emit as "\udXXX" escapes.
 */
function canonicalizeString(value: string): string {
  assertWellFormed(value);
  return JSON.stringify(value);
}

/**
 * Throw if `value` contains an unpaired UTF-16 surrogate. Such a string is
 * not a sequence of Unicode scalar values and has no UTF-8 encoding
 * (profile §4.2). JSON.stringify would escape it and TextEncoder would
 * silently substitute U+FFFD, so neither may see it.
 */
function assertWellFormed(value: string): void {
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i);
    if (c < 0xd800 || c > 0xdfff) continue;
    const next = value.charCodeAt(i + 1);
    if (c <= 0xdbff && next >= 0xdc00 && next <= 0xdfff) {
      i++;
      continue;
    }
    throw new CanonicalisationError(
      `strings must not contain unpaired UTF-16 surrogates (found U+${c.toString(16).toUpperCase()}); ` +
      "they cannot be encoded as UTF-8"
    );
  }
}

// ─── Type checks ───────────────────────────────────────────────────────
/**
 * Only plain objects are JSON objects. Date, Map, Set, typed arrays, boxed
 * primitives and class instances have no own enumerable data (or the wrong
 * data) and used to canonicalise as "{}" or {"0":..}: two different Dates
 * hashed identically. Reject them (profile §3.3, §6).
 */
function assertPlainObject(value: object): void {
  const proto = Object.getPrototypeOf(value);
  if (proto === null || proto === Object.prototype) return;
  // A plain object from another realm (vm context, iframe).
  if (
    Object.getPrototypeOf(proto) === null &&
    Object.prototype.toString.call(value) === "[object Object]"
  ) {
    return;
  }
  const name =
    (proto && typeof proto.constructor === "function" && proto.constructor.name) || "unknown";
  throw new CanonicalisationError(
    `unsupported value type for canonicalization: ${name} (not a plain JSON object)`
  );
}

// ─── Core recursive canonicaliser ──────────────────────────────────────

function canonicalizeJsonImpl(value: unknown): string {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "bigint") return value.toString();
  if (typeof value === "number") {
    if (!Number.isInteger(value)) {
      throw new CanonicalisationError(
        "floating-point values are not supported in ACTENON-JCS-STRICT-1; " +
        "use integer cents or string-encoded decimals instead"
      );
    }
    // JS Number is a 64-bit float and represents integers exactly only up
    // to 2^53 - 1. Beyond that toString() prints a rounded value
    // (2**60 -> "1152921504606847000") or exponent form (1e21 -> "1e+21"),
    // neither of which is the integer's canonical decimal. Callers with
    // large integers MUST pass them as BigInt (parseStrict preserves
    // integer values losslessly from JSON text).
    if (!Number.isSafeInteger(value)) {
      throw new CanonicalisationError(
        `integer ${value} is outside the safe integer range ±(2^53 − 1); pass it as a BigInt`
      );
    }
    return value.toString();
  }
  if (typeof value === "string") return canonicalizeString(value);
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      if (!(i in value)) {
        throw new CanonicalisationError(`sparse arrays are not supported (hole at index ${i})`);
      }
    }
    return "[" + value.map(canonicalizeJsonImpl).join(",") + "]";
  }
  if (typeof value === "object") {
    assertPlainObject(value);
    const obj = value as Record<string, unknown>;
    // Reject non-string keys (RFC 8785 requires string keys).
    // In JS, object keys are always strings (or Symbols, which
    // Object.keys() excludes), so this check is belt-and-suspenders.
    const keys = Object.keys(obj);
    // Validate before sorting: TextEncoder maps every lone surrogate to
    // U+FFFD, so two distinct malformed keys would compare equal and the
    // output would depend on insertion order.
    keys.forEach(assertWellFormed);
    keys.sort(utf8ByteCompare);
    const pieces = keys.map(
      (k) => `${canonicalizeString(k)}:${canonicalizeJsonImpl(obj[k])}`
    );
    return "{" + pieces.join(",") + "}";
  }
  throw new CanonicalisationError(
    `unsupported value type for canonicalization: ${typeof value}`
  );
}

// ─── Public API ────────────────────────────────────────────────────────

/**
 * Canonicalise `value` under ACTENON-JCS-STRICT-1. Returns the canonical
 * string.
 *
 * Throws CanonicalisationError if:
 *   - the input contains a float (or NaN / Infinity)
 *   - the input is too deep (depth > 32)
 *   - the input contains an unsupported type (undefined, function, symbol, etc.)
 */
export function canonicalizeJson(value: unknown, maxDepth: number = MAX_JSON_DEPTH): string {
  validateDepth(value, maxDepth);
  return canonicalizeJsonImpl(value);
}

/**
 * Canonicalise `value` and return the UTF-8 encoded bytes.
 *
 * This is the primary function for cryptographic use — HMAC signatures
 * and SHA-256 digests should be computed over the bytes returned here.
 *
 * Throws CanonicalisationError if:
 *   - any of the canonicalizeJson error conditions are met
 *   - the canonical output exceeds 1 MiB (1,048,576 bytes)
 */
export function canonicalizeBytes(
  value: unknown,
  maxDepth: number = MAX_JSON_DEPTH,
  maxOutputBytes: number = MAX_CANONICAL_OUTPUT_BYTES
): Uint8Array {
  if (maxOutputBytes <= 0) throw new Error("maxOutputBytes must be positive");
  const str = canonicalizeJson(value, maxDepth);
  const bytes = new TextEncoder().encode(str);
  if (bytes.length > maxOutputBytes) {
    throw new CanonicalisationError(
      `canonical output exceeds maximum ${maxOutputBytes} bytes (got ${bytes.length} bytes)`
    );
  }
  return bytes;
}

/**
 * Canonicalise `value` under ACTENON-JCS-STRICT-1 and return the UTF-8 bytes.
 *
 * Alias for `canonicalizeBytes`. This is the function name specified in
 * WO-5 and the one cross-language consumers (e.g. @actenon/sdk) import.
 */
export function canonicalize(value: unknown): Uint8Array {
  return canonicalizeBytes(value);
}


/** Parse raw JSON without rounding integers or discarding duplicate members.
 * Integers outside Number's exact range are returned as BigInt. The canonical
 * profile's depth, Unicode and output limits also apply to the parsed value.
 */
export function parseStrict(text: string): unknown {
  const parsed = parseStrictJson(text, CanonicalisationError, MAX_JSON_DEPTH);
  canonicalizeBytes(parsed);
  return parsed;
}
