import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { parseStrict, canonicalizeJson, CanonicalisationError } from "../src/canonicalisation.js";
import * as runtime from "../../typescript-runtime/src/canonicalisation.js";
import { effectIdentity } from "../src/effects.js";

test("packaged parser copies are byte-identical to the source of truth", () => {
  expect(readFileSync(new URL("../src/strict-json.ts", import.meta.url), "utf8")).toBe(
    readFileSync(new URL("../../typescript-runtime/src/strict-json.ts", import.meta.url), "utf8"));
});
for (const [name, parser, canonical, ErrorType] of [
  ["protocol-types", parseStrict, canonicalizeJson, CanonicalisationError],
  ["protocol runtime", runtime.parseStrict, runtime.canonicalizeJson, runtime.CanonicalisationError],
] as const) describe(name, () => {
  for (const raw of ["9007199254740992", "9007199254740993", "-9007199254740993", "123456789012345678901234567890"]) {
    test(`retains every digit: ${raw}`, () => {
      expect(canonical(parser(`{"n":${raw}}`))).toBe(`{"n":${raw}}`);
      expect(typeof (parser(raw))).toBe("bigint");
    });
  }
  test("safe integer representation remains number", () => {
    expect(parser("9007199254740991")).toBe(9007199254740991);
    expect(parser("-9007199254740991")).toBe(-9007199254740991);
  });
  for (const raw of [
    '{"n":0.9999999999999999999}', '{"n":1.0}', '{"n":1e0}',
    '{"n":1,"\\u006e":2}', '{"a":[{"x":1,"x":2}]}',
    '{"n":01}', '{"n":-01}', '{"n":+1}', '{"n":1,}', '[1,]',
    'null false', 'NaN', 'Infinity', '{"n":}', '{"n" 1}',
    '"\\ud800"', '{"\\ud800":1}', '"unterminated', '"raw\ncontrol"',
    '['.repeat(34) + '0' + ']'.repeat(34),
  ]) test(`refuses malformed or lossy wire input: ${raw.slice(0, 55)}`, () => {
    expect(() => parser(raw)).toThrow(ErrorType);
  });
  test("nested objects, escaped keys and scalar strings survive", () => {
    const raw = ' {"__proto__":{"safe":1},"a":[{"x":1},{"x":2}],"s":"50.0 \\" café 😀"} ';
    const parsed = parser(raw) as Record<string, unknown>;
    expect(Object.getPrototypeOf(parsed)).toBe(Object.prototype);
    expect(Object.hasOwn(parsed,"__proto__")).toBe(true);
    expect(canonical(parsed)).toBe('{"__proto__":{"safe":1},"a":[{"x":1},{"x":2}],"s":"50.0 \\" café 😀"}');
  });
  test("canonical size limit applies", () => {
    expect(() => parser('"' + "a".repeat(1048575) + '"')).toThrow(ErrorType);
  });
});

test("effect identities retain adjacent large integer differences", () => {
  const descriptor = '{"profile":"ACTENON-EFFECT-1","namespace":"owner:payments","kind":"exact","action_type":"payment.refund","target":{"type":"payment","id":"one"},"parameters":{"n":NUMBER}}';
  expect(effectIdentity(parseStrict(descriptor.replace("NUMBER","9007199254740992")))).not.toBe(
    effectIdentity(parseStrict(descriptor.replace("NUMBER","9007199254740993"))));
  // Ordinary JSON.parse can also hide lexical floats that round to a safe
  // integer. The wire API must reject them before an in-memory object exists.
  expect(() => effectIdentity(parseStrict(descriptor.replace("NUMBER","0.9999999999999999999")))).toThrow();
});
