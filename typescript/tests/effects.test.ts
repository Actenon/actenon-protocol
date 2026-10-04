import { describe, test, expect } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { effectIdentity, validateEffectEvidence, validateEffectReference, validateEffectOutcome } from "../src/effects.js";
const root = join(import.meta.dir,"../../conformance/vectors/effect");
describe("ACTENON-EFFECT-1 shared corpus",() => {
  for (const sub of ["valid","invalid"]) {
    for (const name of readdirSync(join(root,sub)).filter(n=>n.endsWith(".json"))) {
      const v = JSON.parse(readFileSync(join(root,sub,name),"utf8"));
      test(name,()=> {
        const run = () => v.operation === "identity" ? effectIdentity(v.input) : v.operation === "reference" ? validateEffectReference(v.artefact) : validateEffectEvidence(v.artefact);
        if (v.expected_validation === "invalid") expect(run).toThrow();
        else if (v.operation === "identity") expect(run()).toBe(v.expected_effect_id);
        else expect(run()).toEqual(v.artefact);
      });
    }
  }
});
test("execution_occurred is never coerced",()=> {
  for (const v of [0,1,"true","false",[],{}]) expect(()=>validateEffectOutcome("COMMITTED",v,"a".repeat(64))).toThrow();
});
