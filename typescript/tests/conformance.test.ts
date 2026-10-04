import { describe, test, expect } from "bun:test";
import {
  isValidIdentifier,
  generateIdentifier,
  normaliseIdentifier,
  PREFIXES,
} from "../src/identifiers.js";
import { canonicalizeJson, canonicalizeBytes, CanonicalisationError } from "../src/canonicalisation.js";
import {
  RefusalCode,
  DisclosurePolicy,
  refusalToDisclosedCode,
  refusalToRetryable,
  refusalToInternalCode,
  resolveAlias,
  COMPATIBILITY_ALIASES,
} from "../src/refusal-codes.js";
import { readFileSync } from "fs";
import { join } from "path";
import { ExecutionMode } from "../src/execution-modes.js";
import {
  CapabilityError,
  authorityExtension,
  capabilityInScope,
  scopeCapabilitiesForMint,
  scopeCapabilitiesForVerification,
  unauthenticatedRefusal,
} from "../src/capabilities.js";

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

  test("sorts keys by UTF-8 bytes, not UTF-16 code units", () => {
    // U+E000 (EE 80 80) < U+1F600 (F0 9F 98 80) in UTF-8; UTF-16 order is the reverse.
    expect(canonicalizeJson({ "\u{1F600}": 2, "\uE000": 1 })).toBe('{"\uE000":1,"\u{1F600}":2}');
  });

  test("rejects unpaired surrogates in values and keys", () => {
    for (const v of ["\uD800", "\uDC00", "x\uDBFFy", "\uDE00\uD83D", { k: "\uDFFF" }, { "\uD800": 1 }, [["\uD800"]]]) {
      expect(() => canonicalizeJson(v)).toThrow(CanonicalisationError);
      expect(() => canonicalizeBytes(v)).toThrow(CanonicalisationError);
    }
    // Two distinct lone-surrogate keys must not produce insertion-order-dependent output.
    expect(() => canonicalizeJson({ "\uD800": 1, "\uD801": 2 })).toThrow(CanonicalisationError);
    expect(() => canonicalizeJson(JSON.parse('{"s":"\\ud800"}'))).toThrow(CanonicalisationError);
  });

  test("accepts properly paired surrogates", () => {
    expect(canonicalizeJson(JSON.parse('"\\ud83d\\ude00"'))).toBe('"\u{1F600}"');
  });

  test("rejects Number integers outside the safe range (use BigInt)", () => {
    // 1e21.toString() is "1e+21" and 2**60 prints as 1152921504606847000:
    // neither is the integer the Python reference would emit.
    for (const n of [1e21, 2 ** 60, 9007199254740992, -9007199254740992, Number.MAX_VALUE]) {
      expect(() => canonicalizeJson(n)).toThrow(CanonicalisationError);
      expect(() => canonicalizeJson({ amount: n })).toThrow(CanonicalisationError);
    }
    expect(canonicalizeJson(9007199254740991)).toBe("9007199254740991");
    expect(canonicalizeJson(-9007199254740991)).toBe("-9007199254740991");
    expect(canonicalizeJson(2n ** 60n)).toBe("1152921504606846976");
  });

  test("rejects values that are not JSON types instead of serialising them as {}", () => {
    class Money {
      amount = 1;
    }
    const notJson: unknown[] = [
      new Date(0),
      new Map([["a", 1]]),
      new Set([1]),
      new Uint8Array([1, 2]),
      new ArrayBuffer(2),
      /x/,
      new Error("x"),
      new Money(),
      new String("x"),
      new Number(1),
      Promise.resolve(1),
    ];
    for (const v of notJson) {
      expect(() => canonicalizeJson(v)).toThrow(CanonicalisationError);
      expect(() => canonicalizeJson({ nested: [v] })).toThrow(CanonicalisationError);
    }
  });

  test("rejects sparse arrays instead of emitting invalid JSON", () => {
    expect(() => canonicalizeJson([1, , 3])).toThrow(CanonicalisationError);
    expect(() => canonicalizeJson(new Array(2))).toThrow(CanonicalisationError);
  });

  test("accepts plain and null-prototype objects", () => {
    expect(canonicalizeJson(Object.assign(Object.create(null), { b: 1, a: 2 }))).toBe('{"a":2,"b":1}');
    expect(canonicalizeJson(JSON.parse('{"__proto__":{"x":1}}'))).toBe('{"__proto__":{"x":1}}');
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

  test("mirrors the compiled catalogue (codes, disclosure, retryability, aliases)", () => {
    const catalogue = JSON.parse(
      readFileSync(join(import.meta.dir, "../../python/actenon_protocol/data/catalogue.v1.json"), "utf-8")
    );
    const codes = catalogue.codes as Array<{ code: string; disclosed_code: string; retryable: boolean }>;
    expect((Object.values(RefusalCode) as string[]).sort()).toEqual(codes.map((c) => c.code).sort());
    expect({ ...COMPATIBILITY_ALIASES }).toEqual(catalogue.compatibility_aliases);
    for (const c of codes) {
      expect(refusalToDisclosedCode(c.code, DisclosurePolicy.PUBLIC)).toBe(c.disclosed_code);
      expect(refusalToRetryable(c.code)).toBe(c.retryable);
    }
    // Aliases resolve BEFORE disclosure/retryability (DUPLICATE_REPLAY used to
    // disclose OUTCOME_UNKNOWN with retryable=true).
    for (const [alias, canonical] of Object.entries(catalogue.compatibility_aliases as Record<string, string>)) {
      const entry = codes.find((c) => c.code === canonical)!;
      expect(refusalToDisclosedCode(alias, DisclosurePolicy.PUBLIC)).toBe(entry.disclosed_code);
      expect(refusalToRetryable(alias)).toBe(entry.retryable);
      expect(refusalToInternalCode(alias, DisclosurePolicy.TRUSTED)).toBe(canonical);
      expect(refusalToInternalCode(alias, DisclosurePolicy.PUBLIC)).toBeNull();
    }
  });

  test("unknown codes named like Object.prototype members are unknown, not inherited", () => {
    for (const code of ["toString", "constructor", "__proto__", "hasOwnProperty"]) {
      expect(refusalToDisclosedCode(code, DisclosurePolicy.PUBLIC)).toBe("OUTCOME_UNKNOWN");
      expect(refusalToRetryable(code)).toBe(true);
      expect(() => resolveAlias(code)).toThrow();
    }
  });
});

describe("capability provenance", () => {
  test("does not widen an empty or wildcard scope", () => {
    expect(() => scopeCapabilitiesForMint([])).toThrow(CapabilityError);
    expect(() => scopeCapabilitiesForMint(["*"])).toThrow(/wildcard/);
    expect(scopeCapabilitiesForMint(["payment.refund"])).toEqual(["payment.refund"]);
    expect(scopeCapabilitiesForVerification(null, "payment.refund")).toEqual(["payment.refund"]);
    expect(scopeCapabilitiesForVerification([], "payment.refund")).toEqual([]);
    expect(capabilityInScope("payment.refund", [])).toBe(false);
    expect(capabilityInScope("*", ["*"])).toBe(false);
  });

  test("token length is not acceptance", () => {
    const token = "A".repeat(32);
    expect(token.length).toBeGreaterThanOrEqual(16);
    expect(unauthenticatedRefusal({ trustRootConfigured: false, signatureVerified: false })).toBe(
      "ISSUER_UNTRUSTED",
    );
    expect(unauthenticatedRefusal({ trustRootConfigured: true, signatureVerified: false })).toBe(
      "SIGNATURE_INVALID",
    );
  });

  test("authority extension names the grant", () => {
    expect(
      authorityExtension({
        issuer: "service:actenon-permit",
        grant_id: "grant_9f3c1a175e9b4d80a1b2c3d4e5f60718",
      }),
    ).toEqual({
      authority: {
        issuer: "service:actenon-permit",
        grant_id: "grant_9f3c1a175e9b4d80a1b2c3d4e5f60718",
        revocable: true,
      },
    });
  });

  test("capability mismatch resolves to itself", () => {
    expect(resolveAlias("SCOPE_CAPABILITY_MISMATCH")).toBe("SCOPE_CAPABILITY_MISMATCH");
    expect(refusalToInternalCode("SCOPE_CAPABILITY_MISMATCH", DisclosurePolicy.TRUSTED)).toBe(
      "SCOPE_CAPABILITY_MISMATCH",
    );
    expect(refusalToDisclosedCode("SCOPE_CAPABILITY_MISMATCH", DisclosurePolicy.PUBLIC)).toBe(
      "PROOF_INVALID",
    );
  });
});

describe("execution modes", () => {
  test("both modes are defined", () => {
    expect(ExecutionMode.BROKERED as string).toBe("brokered");
    expect(ExecutionMode.RESOURCE_OWNED as string).toBe("resource_owned");
  });
});
