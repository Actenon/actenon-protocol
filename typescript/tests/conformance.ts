/**
 * Cross-language canonicalisation conformance runner for TypeScript.
 *
 * Run: bun run conformance.ts
 *
 * Verifies that the TypeScript implementation produces the same canonical
 * bytes as the Python reference for all normative vectors.
 */

import { canonicalizeJson, canonicalizeBytes, parseStrict, CanonicalisationError } from "../src/canonicalisation.js";
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
      const vector = parseStrict(content) as ValidVector;

      if (vector.input === undefined || vector.expected_canonical === undefined) {
        console.log(`  SKIP  ${vector.name}`);
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
  } catch (e) {
    // Never swallow: a vector that cannot be read or parsed is a failure.
    console.log(`  FAIL  valid vectors: ${e instanceof Error ? e.message : String(e)}`);
    failed++;
  }

  // ── Invalid vectors (JSON-representable) ──────────────────────
  try {
    const files = readdirSync(invalidDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const content = readFileSync(join(invalidDir, file), "utf-8");
      const vector = JSON.parse(content) as InvalidVector;

      if (vector.input_json !== undefined) {
        try {
          const parsed = parseStrict(vector.input_json);
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
        } catch (e) {
          if (e instanceof CanonicalisationError) passed++;
          else { console.log(`  FAIL  ${vector.name}: ${e}`); failed++; }
        }
      } else if (vector.name === "duplicate_keys" || vector.name === "oversized_structure") {
        try {
          if (vector.name === "duplicate_keys") parseStrict('{"a":1,"a":2}');
          else canonicalizeBytes("a".repeat(1048575));
          console.log(`  FAIL  ${vector.name}: expected refusal`);
          failed++;
        } catch (e) {
          if (e instanceof CanonicalisationError) passed++;
          else { console.log(`  FAIL  ${vector.name}: ${e}`); failed++; }
        }
      } else {
        console.log(`  SKIP  ${vector.name} (no JavaScript representation for native type)`);
        skipped++;
      }
    }
  } catch (e) {
    // Never swallow: a vector that cannot be read or parsed is a failure.
    console.log(`  FAIL  invalid vectors: ${e instanceof Error ? e.message : String(e)}`);
    failed++;
  }

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

  console.log(`\n${"=".repeat(60)}`);
  console.log(`Canonicalisation conformance (TypeScript): ${passed} passed, ${failed} failed, ${skipped} skipped`);
  console.log(`${"=".repeat(60)}`);
  return failed === 0 ? 0 : 1;
}

process.exit(run());
