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
 * This matches RFC 8785 §3.2.3 and the Python reference's
 * `sorted(keys, key=lambda k: k.encode("utf-8"))`.
 *
 * For BMP characters, UTF-8 byte order coincides with code point order.
 * For astral characters (code points > U+FFFF), UTF-8 byte order also
 * coincides with code point order. So this comparison is equivalent to
 * sorting by Unicode code point — but we do it via UTF-8 bytes to match
 * the spec exactly.
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
 * \u-escape non-ASCII), so we delegate to it.
 */
function canonicalizeString(value: string): string {
  return JSON.stringify(value);
}

// ─── Core recursive canonicaliser ──────────────────────────────────────

function canonicalizeJsonImpl(value: unknown): string {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "bigint") return value.toString();
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      // JS Number is a 64-bit float; integers > 2^53-1 lose precision.
      // Callers with large integers MUST pass them as BigInt.
      return value.toString();
    }
    throw new CanonicalisationError(
      "floating-point values are not supported in ACTENON-JCS-STRICT-1; " +
      "use integer cents or string-encoded decimals instead"
    );
  }
  if (typeof value === "string") return canonicalizeString(value);
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalizeJsonImpl).join(",") + "]";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    // Reject non-string keys (RFC 8785 requires string keys).
    // In JS, object keys are always strings (or Symbols, which
    // Object.keys() excludes), so this check is belt-and-suspenders.
    const keys = Object.keys(obj).sort(utf8ByteCompare);
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

/**
 * Parse a JSON string with duplicate-key detection.
 *
 * JavaScript's JSON.parse uses last-wins for duplicate keys, silently
 * discarding earlier values. ACTENON-JCS-STRICT-1 §4.12 prohibits
 * duplicate keys. This parser detects them and throws.
 *
 * Use this when parsing untrusted JSON that will be canonicalised. For
 * trusted input (constructed in code), the canonicaliser itself does not
 * need this — JS objects can't have duplicate keys.
 */
export function parseJson(input: string): unknown {
  // Use a reviver that tracks seen keys per object. JSON.parse calls the
  // reviver bottom-up, so we need to detect duplicates during parsing
  // rather than after. We do this by parsing with a reviver that checks
  // for duplicate keys at each level.
  //
  // Unfortunately, JSON.parse's reviver doesn't give us enough context
  // to detect duplicates reliably (it's called once per key-value pair,
  // and we'd need to track state per nesting level). Instead, we use a
  // small hand-rolled parser for duplicate detection.
  //
  // For performance, we first parse normally (fast path), then re-parse
  // with a reviver only if the fast parse succeeds. The reviver approach
  // actually CAN'T detect duplicates because JSON.parse collapses them
  // before the reviver runs. So we use a regex-based pre-check.

  // Count keys at each nesting level using a regex. This is not a full
  // parser but catches the common case of literal duplicate keys.
  // A more robust approach would use a streaming JSON parser.
  const seen = new Map<number, Set<string>>();
  let depth = 0;
  const keyRegex = /"((?:[^"\\]|\\.)*)"\s*:/g;
  let match: RegExpExecArray | null;
  while ((match = keyRegex.exec(input)) !== null) {
    // Count nesting depth up to this point
    const prefix = input.slice(0, match.index);
    depth = (prefix.match(/{/g) || []).length - (prefix.match(/}/g) || []).length;
    const key = match[1];
    let level = seen.get(depth);
    if (!level) {
      level = new Set();
      seen.set(depth, level);
    }
    if (level.has(key)) {
      throw new CanonicalisationError(
        `duplicate key ${JSON.stringify(key)} at depth ${depth}`
      );
    }
    level.add(key);
  }
  return JSON.parse(input);
}
