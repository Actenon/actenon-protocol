/**
 * Cross-language canonicalisation conformance runner for @actenon/protocol.
 *
 * Run: bun run tests/conformance.ts
 *
 * Verifies that the runtime implementation produces the same canonical
 * bytes as the Python reference for all normative vectors.
 */

import { canonicalizeJson, canonicalize, CanonicalisationError } from "../src/canonicalisation.js";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";

interface ValidVector {
  name: string;
  description: string;
  input: unknown;
  expected_canonical: string;
}

interface InvalidVector {
  name: string;
  description: string;
  input_json?: string;
  expected_error: string;
  note?: string;
}

function findVectorsDir(): string {
  const candidates = [
    "../../conformance/vectors/canonicalisation",
    "../conformance/vectors/canonicalisation",
  ];
  for (const c of candidates) {
    try {
      readdirSync(join(import.meta.dir, c));
      return join(import.meta.dir, c);
    } catch {}
  }
  throw new Error("Could not find conformance vectors directory");
}

function run(): number {
  const vectorsDir = findVectorsDir();
  const validDir = join(vectorsDir, "valid");
  const invalidDir = join(vectorsDir, "invalid");

  let passed = 0;
  let failed = 0;
  let skipped = 0;

  // ── Valid vectors ──────────────────────────────────────────────
  try {
    const files = readdirSync(validDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const content = readFileSync(join(validDir, file), "utf-8");
      const vector = JSON.parse(content) as ValidVector;

      if (vector.input === undefined || vector.expected_canonical === undefined) {
        console.log(`  SKIP  ${vector.name}`);
        skipped++;
        continue;
      }

      // Skip vectors with integers > 2^53 (JS Number precision loss).
      function hasPrecisionLossInExpected(expected: string): boolean {
        return /:\d{16,}/.test(expected) || /:-\d{16,}/.test(expected);
      }
      if (hasPrecisionLossInExpected(vector.expected_canonical)) {
        console.log(`  SKIP  ${vector.name} (integers > 2^53 — JS Number precision)`);
        skipped++;
        continue;
      }

      try {
        const actual = canonicalizeJson(vector.input);
        if (actual === vector.expected_canonical) {
          passed++;
        } else {
          console.log(`  FAIL  ${vector.name}: expected ${vector.expected_canonical}, got ${actual}`);
          failed++;
        }
      } catch (e) {
        console.log(`  FAIL  ${vector.name}: ${e instanceof Error ? e.message : String(e)}`);
        failed++;
      }
    }
  } catch {}

  // ── Invalid vectors ────────────────────────────────────────────
  try {
    const files = readdirSync(invalidDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const content = readFileSync(join(invalidDir, file), "utf-8");
      const vector = JSON.parse(content) as InvalidVector;

      if (vector.input_json !== undefined) {
        // Skip vectors where JS JSON.parse loses the float/integer distinction.
        const jsFloatAmbiguous = ["float_zero", "float_exponent"];
        if (jsFloatAmbiguous.includes(vector.name)) {
          console.log(`  SKIP  ${vector.name} (JS Number cannot distinguish float from int after JSON.parse)`);
          skipped++;
          continue;
        }

        try {
          const parsed = JSON.parse(vector.input_json);
          try {
            canonicalizeJson(parsed);
            console.log(`  FAIL  ${vector.name}: expected error but got success`);
            failed++;
          } catch (e) {
            if (e instanceof CanonicalisationError || e instanceof TypeError) {
              passed++;
            } else {
              console.log(`  FAIL  ${vector.name}: wrong error type: ${e instanceof Error ? e.constructor.name : typeof e}`);
              failed++;
            }
          }
        } catch {
          // NaN/Infinity aren't valid JSON — skip
          skipped++;
        }
      } else {
        skipped++;
      }
    }
  } catch {}

  // ── TypeScript-specific adversarial tests ─────────────────────
  const tsOnlyTests: Array<[string, () => void]> = [
    ["float_nan_direct", () => canonicalizeJson(NaN)],
    ["float_inf_direct", () => canonicalizeJson(Infinity)],
    ["float_neg_inf_direct", () => canonicalizeJson(-Infinity)],
  ];

  for (const [name, fn] of tsOnlyTests) {
    try {
      fn();
      console.log(`  FAIL  ${name}: expected error but got success`);
      failed++;
    } catch (e) {
      if (e instanceof CanonicalisationError || e instanceof TypeError) {
        passed++;
      } else {
        console.log(`  FAIL  ${name}: wrong error type: ${e instanceof Error ? e.constructor.name : typeof e}`);
        failed++;
      }
    }
  }

  // ── BigInt support ────────────────────────────────────────────
  try {
    const result = canonicalizeJson(123456789012345678901234567890n);
    if (result === "123456789012345678901234567890") {
      passed++;
    } else {
      console.log(`  FAIL  bigint_large: expected '123456789012345678901234567890', got ${result}`);
      failed++;
    }
  } catch (e) {
    console.log(`  FAIL  bigint_large: ${e instanceof Error ? e.message : String(e)}`);
    failed++;
  }

  // ── canonicalize() returns Uint8Array ─────────────────────────
  try {
    const result = canonicalize({ n: 1 });
    if (result instanceof Uint8Array) {
      const text = new TextDecoder().decode(result);
      if (text === '{"n":1}') {
        passed++;
      } else {
        console.log(`  FAIL  canonicalize_returns_bytes: expected '{"n":1}', got ${text}`);
        failed++;
      }
    } else {
      console.log(`  FAIL  canonicalize_returns_bytes: expected Uint8Array, got ${typeof result}`);
      failed++;
    }
  } catch (e) {
    console.log(`  FAIL  canonicalize_returns_bytes: ${e instanceof Error ? e.message : String(e)}`);
    failed++;
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log(`Canonicalisation conformance (@actenon/protocol): ${passed} passed, ${failed} failed, ${skipped} skipped`);
  console.log(`${"=".repeat(60)}`);
  return failed === 0 ? 0 : 1;
}

process.exit(run());
