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

function canonicalizeString(value: string): string {
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
    const keys = Object.keys(obj).sort(utf8ByteCompare);
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
