#!/usr/bin/env bash
# Both candidates must be built first. No repository-local imports or publish.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT
(cd "$repo/typescript" && npm pack --silent --pack-destination "$workspace" >/dev/null)
(cd "$repo/typescript-runtime" && npm pack --silent --pack-destination "$workspace" >/dev/null)
cd "$workspace"
npm init -y >/dev/null
npm install --ignore-scripts --no-audit --no-fund ./*.tgz >/dev/null
node --input-type=module - "$repo/conformance/vectors/effect/valid" <<'JS'
import assert from "node:assert/strict";
import {readFileSync, readdirSync} from "node:fs";
import {join} from "node:path";
import * as types from "@actenon/protocol-types";
import * as runtime from "@actenon/protocol";
let effects = 0;
for (const name of readdirSync(process.argv[2])) {
  const raw = readFileSync(join(process.argv[2],name),"utf8");
  const vector = types.parseStrict(raw);
  if (vector.operation !== "identity") continue;
  assert.equal(types.effectIdentity(vector.input), vector.expected_effect_id);
  assert.equal(types.canonicalizeJson(vector.input), runtime.canonicalizeJson(runtime.parseStrict(raw).input));
  effects++;
}
for (const pkg of [types, runtime]) {
  assert.equal(pkg.canonicalizeJson(pkg.parseStrict("9007199254740993")), "9007199254740993");
  assert.throws(() => pkg.parseStrict('{"n":1,"\\u006e":2}'));
  assert.throws(() => pkg.parseStrict('{"n":0.9999999999999999999}'));
}
console.log(JSON.stringify({node:process.version,source:"two installed npm candidate tarballs",effect_identity_vectors:effects,integer_duplicate_float_checks:"PASS"}));
JS
