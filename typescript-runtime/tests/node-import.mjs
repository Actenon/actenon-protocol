// Smoke test: the BUILT package must load under plain Node.js.
//
// Run after `bun run build`:  node tests/node-import.mjs
//
// Bun transpiles TypeScript inside node_modules, so the Bun-based
// conformance runner cannot catch a dist/ that pulls in a TS-source-only
// dependency at runtime. Node refuses such imports
// (ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING), which is what every
// Node.js consumer of @actenon/protocol would hit.
import assert from "node:assert/strict";

const mod = await import("../dist/index.js");

for (const name of [
  "canonicalize",
  "canonicalizeBytes",
  "canonicalizeJson",
  "parseStrict",
  "CanonicalisationError",
  "MAX_CANONICAL_OUTPUT_BYTES",
  "MAX_JSON_DEPTH",
  "PROTOCOL_VERSION",
  "CANONICALISATION_PROFILE",
  "LEGACY_CANONICALISATION_PROFILE",
  "ACCEPTED_CANONICALISATION_PROFILES",
]) {
  assert.ok(name in mod, `missing export: ${name}`);
}

assert.equal(
  new TextDecoder().decode(mod.canonicalize(mod.parseStrict('{"b":1,"a":[true,null,"é"]}'))),
  '{"a":[true,null,"é"],"b":1}'
);
assert.equal(mod.CANONICALISATION_PROFILE, "ACTENON-JCS-STRICT-1");
assert.deepEqual([...mod.ACCEPTED_CANONICALISATION_PROFILES], ["ACTENON-JCS-STRICT-1", "RFC8785-JCS"]);

console.log(`node import OK (${process.version}): @actenon/protocol dist/ loads without Bun`);
