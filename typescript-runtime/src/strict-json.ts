/**
 * Lossless ACTENON-JCS-STRICT-1 parser source of truth.
 * The byte-identical copy in typescript-runtime/src is packaging only;
 * strict-json.test.ts fails if the two copies drift.
 */
export function parseStrictJson(
  text: string,
  ErrorType: new (message: string) => Error,
  maxDepth: number,
): unknown {
  let cursor = 0;
  const fail = (message: string): never => {
    throw new ErrorType(`${message} at offset ${cursor}`);
  };
  const whitespace = () => {
    while (cursor < text.length && /[\x20\t\r\n]/.test(text[cursor])) cursor++;
  };
  const string = (): string => {
    const start = cursor++;
    while (cursor < text.length) {
      const char = text[cursor++];
      if (char === "\\") cursor++;
      else if (char === '"') {
        try {
          return JSON.parse(text.slice(start, cursor)) as string;
        } catch {
          return fail("malformed JSON string");
        }
      }
    }
    return fail("unterminated JSON string");
  };
  const value = (depth: number): unknown => {
    if (depth > maxDepth) return fail(`JSON depth exceeds maximum ${maxDepth}`);
    whitespace();
    const char = text[cursor];
    if (char === '"') return string();
    if (char === "{") {
      cursor++;
      const result: Record<string, unknown> = {};
      const seen = new Set<string>();
      whitespace();
      if (text[cursor] === "}") { cursor++; return result; }
      while (true) {
        whitespace();
        if (text[cursor] !== '"') return fail("expected an object key");
        const key = string();
        if (seen.has(key)) return fail(`duplicate key ${JSON.stringify(key)}`);
        seen.add(key);
        whitespace();
        if (text[cursor++] !== ":") return fail("expected ':'");
        // __proto__ is an ordinary own JSON member, never a prototype setter.
        Object.defineProperty(result, key, {
          value: value(depth + 1), enumerable: true, writable: true, configurable: true,
        });
        whitespace();
        const delimiter = text[cursor++];
        if (delimiter === "}") return result;
        if (delimiter !== ",") return fail("expected ',' or '}'");
      }
    }
    if (char === "[") {
      cursor++;
      const result: unknown[] = [];
      whitespace();
      if (text[cursor] === "]") { cursor++; return result; }
      while (true) {
        result.push(value(depth + 1));
        whitespace();
        const delimiter = text[cursor++];
        if (delimiter === "]") return result;
        if (delimiter !== ",") return fail("expected ',' or ']'");
      }
    }
    for (const [literal, parsed] of [["true", true], ["false", false], ["null", null]] as const) {
      if (text.startsWith(literal, cursor)) { cursor += literal.length; return parsed; }
    }
    const match = /^-?(?:0|[1-9][0-9]*)/.exec(text.slice(cursor));
    if (!match) return fail("expected a JSON value");
    cursor += match[0].length;
    if (/[.eE]/.test(text[cursor] ?? "")) return fail("floating-point literals are prohibited");
    const integer = BigInt(match[0]);
    return integer >= -9007199254740991n && integer <= 9007199254740991n ? Number(integer) : integer;
  };
  if (typeof text !== "string") return fail("JSON input must be a string");
  const result = value(0);
  whitespace();
  if (cursor !== text.length) return fail("unexpected trailing JSON data");
  return result;
}
