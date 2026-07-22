import { describe, test, expect } from "bun:test";
import {
  isValidIdentifier,
  generateIdentifier,
  normaliseIdentifier,
  PREFIXES,
} from "../src/identifiers.js";
import { canonicalizeJson, CanonicalisationError } from "../src/canonicalisation.js";
import { RefusalCode, DisclosurePolicy, refusalToDisclosedCode } from "../src/refusal-codes.js";
import { ExecutionMode } from "../src/execution-modes.js";

describe("identifiers", () => {
  test("accepts canonical prefixes", () => {
    for (const prefix of PREFIXES) {
      const id = generateIdentifier(prefix);
      expect(isValidIdentifier(id)).toBe(true);
    }
  });

  test("accepts 16-hex-char identifiers (backward compat)", () => {
    expect(isValidIdentifier("grant_9f3c1a175e9b4d80")).toBe(true);
  });

  test("accepts alias prefixes", () => {
    expect(isValidIdentifier("act_9f3c1a175e9b4d80")).toBe(true);
    expect(isValidIdentifier("pccb_9f3c1a175e9b4d80")).toBe(true);
  });

  test("normalises aliases to canonical", () => {
    expect(normaliseIdentifier("act_9f3c1a175e9b4d80")).toBe("intent_9f3c1a175e9b4d80");
    expect(normaliseIdentifier("pccb_9f3c1a175e9b4d80")).toBe("proof_9f3c1a175e9b4d80");
  });

  test("rejects forbidden prefixes", () => {
    expect(isValidIdentifier("tenant_abcdef0123456789")).toBe(false);
    expect(isValidIdentifier("user_abcdef0123456789")).toBe(false);
  });

  test("rejects short hex", () => {
    expect(isValidIdentifier("grant_short")).toBe(false);
    expect(isValidIdentifier("grant_9f3c1a175e9b4")).toBe(false);
  });

  test("rejects uppercase hex", () => {
    expect(isValidIdentifier("grant_9F3C1A175E9B4D80")).toBe(false);
  });

  test("rejects non-string", () => {
    expect(isValidIdentifier(42)).toBe(false);
    expect(isValidIdentifier(null)).toBe(false);
  });
});

describe("canonicalisation", () => {
  test("sorts object keys by UTF-8 byte order", () => {
    expect(canonicalizeJson({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
  });

  test("handles nested objects", () => {
    expect(canonicalizeJson({ outer: { z: 1, a: 2 } })).toBe('{"outer":{"a":2,"z":1}}');
  });

  test("handles arrays in order", () => {
    expect(canonicalizeJson([3, 1, 2])).toBe("[3,1,2]");
  });

  test("rejects floats", () => {
    expect(() => canonicalizeJson(3.14)).toThrow(CanonicalisationError);
    expect(() => canonicalizeJson({ amount: 19.99 })).toThrow(CanonicalisationError);
  });

  test("handles null, true, false", () => {
    expect(canonicalizeJson(null)).toBe("null");
    expect(canonicalizeJson(true)).toBe("true");
    expect(canonicalizeJson(false)).toBe("false");
  });

  test("does not \\u-escape non-ASCII", () => {
    expect(canonicalizeJson("café")).toBe('"café"');
    expect(canonicalizeJson("日本語")).toBe('"日本語"');
  });

  test("escapes control characters", () => {
    expect(canonicalizeJson("a\tb")).toBe('"a\\tb"');
    expect(canonicalizeJson("a\nb")).toBe('"a\\nb"');
  });

  test("handles integers of any size (BigInt for >2^53)", () => {
    expect(canonicalizeJson(0)).toBe("0");
    expect(canonicalizeJson(-1)).toBe("-1");
    // JS Number loses precision above 2^53 - 1; use BigInt for large integers.
    expect(canonicalizeJson(1234567890123456789n)).toBe("1234567890123456789");
  });

  test("produces identical bytes to Python reference (canonical vector)", () => {
    // This matches the Python conformance vector: canonicalisation/valid/simple_object.json
    const input = { z: 1, a: "hello", b: [true, null, 42] };
    const expected = '{"a":"hello","b":[true,null,42],"z":1}';
    expect(canonicalizeJson(input)).toBe(expected);
  });
});

describe("refusal codes", () => {
  test("disclosed_code for SIGNATURE_INVALID under PUBLIC is PROOF_INVALID", () => {
    expect(refusalToDisclosedCode(RefusalCode.SIGNATURE_INVALID, DisclosurePolicy.PUBLIC)).toBe("PROOF_INVALID");
  });

  test("disclosed_code for PROOF_EXPIRED is PROOF_EXPIRED (safe to disclose)", () => {
    expect(refusalToDisclosedCode(RefusalCode.PROOF_EXPIRED, DisclosurePolicy.PUBLIC)).toBe("PROOF_EXPIRED");
  });

  test("disclosed_code for REPLAY_DETECTED is REPLAY_DETECTED (safe to disclose)", () => {
    expect(refusalToDisclosedCode(RefusalCode.REPLAY_DETECTED, DisclosurePolicy.PUBLIC)).toBe("REPLAY_DETECTED");
  });
});

describe("execution modes", () => {
  test("both modes are defined", () => {
    expect(ExecutionMode.BROKERED as string).toBe("brokered");
    expect(ExecutionMode.RESOURCE_OWNED as string).toBe("resource_owned");
  });
});
