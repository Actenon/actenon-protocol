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
 * Parse a JSON string with ACTENON-JCS-STRICT-1 lexical rules.
 *
 * JavaScript's JSON.parse has two problems for strict canonicalisation:
 *
 *  1. It loses the float/integer distinction. JSON.parse("0.0") produces
 *     the number 0, and Number.isInteger(0) is true — so the canonicaliser
 *     can't reject 0.0 as a float. But the raw JSON text "0.0" clearly
 *     contains a float literal (it has a decimal point).
 *
 *  2. It truncates integers > 2^53-1. JSON.parse("9007199254740993")
 *     produces 9007199254740992 (the nearest representable double). The
 *     canonicaliser sees the wrong value and produces wrong bytes.
 *
 * parseStrict solves both by scanning the RAW TEXT before JSON.parse:
 *   - Any number literal containing '.', 'e', or 'E' → float → reject
 *   - Any integer literal outside ±(2^53 − 1) → unsafe integer → reject
 *
 * The scan uses a proper JSON tokenizer that understands string
 * boundaries — a naive regex would match digits inside string values
 * like {"note":"costs 50.0 dollars"}, which must be ACCEPTED.
 *
 * After the scan, JSON.parse is called on the (validated) text. The
 * parsed value is returned as-is — it's now guaranteed to contain only
 * safe integers, strings, booleans, null, arrays, and objects.
 *
 * Throws CanonicalisationError on float literals or unsafe integers.
 * Throws SyntaxError (from JSON.parse) on malformed JSON.
 */
export function parseStrict(text: string): unknown {
  scanNumberLiterals(text);
  return JSON.parse(text);
}

/**
 * Scan raw JSON text for number literals that violate ACTENON-JCS-STRICT-1.
 *
 * This is a lexical pre-check that runs BEFORE JSON.parse. It walks the
 * text character by character, tracking whether we're inside a string
 * (so digits inside strings are not mistaken for number literals).
 *
 * For each number literal found:
 *   - If it contains '.', 'e', or 'E' → float → reject
 *   - If it's an integer outside ±(2^53 − 1) → unsafe → reject
 *
 * The tokenizer handles: strings (with escape sequences), objects,
 * arrays, booleans, null, and numbers. It does NOT need to fully parse
 * the JSON — just track string boundaries and find number tokens.
 */
function scanNumberLiterals(text: string): void {
  const len = text.length;
  let i = 0;
  let inString = false;

  while (i < len) {
    const ch = text[i];

    if (inString) {
      if (ch === "\\") {
        // Escape sequence — skip the next character
        i += 2;
        continue;
      }
      if (ch === '"') {
        inString = false;
      }
      i++;
      continue;
    }

    // Not in a string
    if (ch === '"') {
      inString = true;
      i++;
      continue;
    }

    // Skip whitespace and structural characters
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r" ||
        ch === "{" || ch === "}" || ch === "[" || ch === "]" ||
        ch === ":" || ch === ",") {
      i++;
      continue;
    }

    // Skip literals: true, false, null
    if (ch === "t" && text.slice(i, i + 4) === "true") {
      i += 4;
      continue;
    }
    if (ch === "f" && text.slice(i, i + 5) === "false") {
      i += 5;
      continue;
    }
    if (ch === "n" && text.slice(i, i + 4) === "null") {
      i += 4;
      continue;
    }

    // Number literal: starts with digit or minus
    if (ch === "-" || (ch >= "0" && ch <= "9")) {
      const start = i;
      // Scan the full number literal
      if (ch === "-") i++;
      while (i < len && text[i] >= "0" && text[i] <= "9") i++;

      // Check for fractional or exponent part
      let isFloat = false;
      if (i < len && text[i] === ".") {
        isFloat = true;
        i++;
        while (i < len && text[i] >= "0" && text[i] <= "9") i++;
      }
      if (i < len && (text[i] === "e" || text[i] === "E")) {
        isFloat = true;
        i++;
        if (i < len && (text[i] === "+" || text[i] === "-")) i++;
        while (i < len && text[i] >= "0" && text[i] <= "9") i++;
      }

      const literal = text.slice(start, i);

      if (isFloat) {
        throw new CanonicalisationError(
          "floating-point values are not supported in ACTENON-JCS-STRICT-1; " +
          "use integer cents or string-encoded decimals instead"
        );
      }

      // Check integer range: must be within ±(2^53 − 1) = ±9007199254740991.
      // Parse as BigInt to avoid precision loss in the check itself.
      const bigVal = BigInt(literal);
      const MAX_SAFE = BigInt(9007199254740991); // 2^53 - 1
      if (bigVal > MAX_SAFE || bigVal < -MAX_SAFE) {
        throw new CanonicalisationError(
          `integer ${literal} exceeds the safe integer range ±(2^53 − 1) ` +
          `for ACTENON-JCS-STRICT-1; pass as BigInt or encode as a string`
        );
      }
      continue;
    }

    // Unexpected character — let JSON.parse produce the error
    i++;
  }
}
