/**
 * ACTENON-JCS-STRICT-1 canonicalisation reference implementation.
 *
 * Strict subset of RFC 8785 (JCS) that rejects floating-point values.
 * Produces byte-identical output to the Python reference implementation
 * in python/actenon_protocol/canonicalisation.py.
 */

export const MAX_CANONICAL_OUTPUT_BYTES = 1_048_576;
export const MAX_JSON_DEPTH = 32;

export class CanonicalisationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CanonicalisationError";
  }
}

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

// Throw if `value` contains an unpaired UTF-16 surrogate. Such a string is
// not a sequence of Unicode scalar values and has no UTF-8 encoding
// (profile §4.2). JSON.stringify would emit it as a "\udXXX" escape and
// TextEncoder would silently substitute U+FFFD, so neither may see it.
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

function canonicalizeString(value: string): string {
  assertWellFormed(value);
  // JSON.stringify with no whitespace, no ASCII escaping
  // Note: JSON.stringify produces the correct RFC 8259 escapes for
  // control characters and double-quotes. It does NOT \u-escape non-ASCII
  // (which is what we want — matches RFC 8785 §3.2.2).
  return JSON.stringify(value);
}

function utf8ByteCompare(a: string, b: string): number {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  for (let i = 0; i < Math.min(aBytes.length, bBytes.length); i++) {
    if (aBytes[i] !== bBytes[i]) return aBytes[i] - bBytes[i];
  }
  return aBytes.length - bBytes.length;
}

function canonicalizeJsonImpl(value: unknown): string {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "bigint") return value.toString();
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      // Note: JS Number is a 64-bit float and can only represent integers
      // up to 2^53 - 1 exactly. Larger integers must be passed as BigInt.
      return value.toString();
    }
    throw new CanonicalisationError(
      "floating-point values are not supported in ACTENON-JCS-STRICT-1; use integer cents or string-encoded decimals instead"
    );
  }
  if (typeof value === "string") return canonicalizeString(value);
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalizeJsonImpl).join(",") + "]";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj);
    // Validate before sorting: TextEncoder maps every lone surrogate to
    // U+FFFD, so two distinct malformed keys would compare equal.
    keys.forEach(assertWellFormed);
    keys.sort(utf8ByteCompare);
    const pieces = keys.map((k) => `${canonicalizeString(k)}:${canonicalizeJsonImpl(obj[k])}`);
    return "{" + pieces.join(",") + "}";
  }
  throw new CanonicalisationError(`unsupported value type for canonicalization: ${typeof value}`);
}

export function canonicalizeJson(value: unknown, maxDepth: number = MAX_JSON_DEPTH): string {
  validateDepth(value, maxDepth);
  return canonicalizeJsonImpl(value);
}

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
