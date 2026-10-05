# Lossless wire JSON and effect identities

Baseline: `3442bf3cffe0b55ac7d531e66ca0355d2c0784e5` (Protocol main,
package 1.6.0 / wire 1.3.0, unreleased). This repair does not publish either
package or change the ACTENON-JCS-STRICT-1 numeric domain.

## Counterexamples preserved

`before-effect-corpus.log` records 28 passes and three failures after adding
three valid vectors, before changing the implementation: adjacent amounts
9007199254740992 and 9007199254740993, and a negative 30-digit amount. The old
TypeScript corpus loader used JSON.parse, then rejected the rounded unsafe
Number; its canonicalisation runners skipped large integers altogether.
The runtime parser also rejected valid integer literals outside the safe
Number range despite the profile's existing BigInt support.

`python-before-strict-parser-and-lock.xml` records the first full run after
adding the raw escaped-duplicate vector. The Python standalone canonical CLI
and one direct test silently overwrote its duplicate member with json.loads.
The other failures were intentionally not-yet-updated corpus counts/hash locks.
`python-before-count-update.*` preserves the remaining old-count assertion.
These are intermediate failures, not the final result.

## Repair and verified scope

Both TypeScript packages use the same byte-locked parser source
(`typescript/src/strict-json.ts`; runtime copy is solely for packaging).
`parseStrict` returns exact safe numbers and BigInt for larger integer literals.
Python exposes `parse_strict`, shared by the standalone runner and canonical
CLI. Duplicate decoded members, lexical float/exponent spellings, malformed
JSON, Unicode, nesting and canonical size violations are rejected.

The five new hash-locked vectors are additive. All 156 prior vector files and
hashes are unchanged. The corpus now contains 161 vectors.

- `python-after.*`: 346 passed, 22 parametrized placeholders skipped; those
  placeholders cover nonapplicable input encodings and are tested through the
  appropriate raw/native path. This is not 22 untested normative cases.
- `standalone-after.log`: all 161 normative vectors passed, zero skipped.
- `typescript-after.log`: 121 tests passed, zero failures, including both parser
  copies and raw adversarial input. `targeted-after.log` preserves the earlier
  87-test focused run.
- `typescript-corpus-after.log`: 40 passes, three non-JavaScript native types
  skipped (bytes, set, non-string dictionary keys). No numeric/float skip.
- `typescript-runtime-corpus-after.log`: 76 passes, the same three native-type
  skips. Its count includes runtime adversarial and API tests.
- `npm-*-pack-after.log`: both built tarballs import under plain Node.
- `npm-installed-behavior.log`: both tarballs installed together into an empty
  temporary project; all 11 valid effect identity vectors match their exact
  hashes, and large-integer/duplicate/float checks pass through public exports.
  Reproduce with `bash scripts/smoke-strict-json-pack.sh` after building both
  packages. CI runs this check.

An ordinary JSON.parse call upstream can still destroy lexical evidence before
an in-memory helper receives it. Consumers must use the strict wire API and
execute the same parsed value they verify; this candidate does not claim to
repair arbitrary third-party parsers or prove every dependent verifier.
Go/Rust/Kernel differential and protected-edge integration remain separately
owned G2 work. This evidence is internally verified, not independent reproduction.
