/** Portable consequence identities; this module does not authorize execution. */
import { createHash } from "node:crypto";
import { canonicalizeBytes } from "./canonicalisation.js";

export const EFFECT_PROFILE = "ACTENON-EFFECT-1" as const;
export type EffectOutcome = "COMMITTED" | "NOT_EXECUTED" | "AMBIGUOUS";
export type EffectDescriptor = {
  profile: typeof EFFECT_PROFILE;
  namespace: string;
  action_type: string;
  target: { type: string; id: string };
} & ({ kind: "exact"; parameters: Record<string, unknown> } |
     { kind: "semantic"; semantic_key: Record<string, unknown> });
export interface EffectReference {
  profile: typeof EFFECT_PROFILE;
  effect_id: string;
  reservation_id: string;
  owner_attempt_id: string;
}
export interface EffectEvidence extends EffectReference {
  outcome: EffectOutcome;
  execution_occurred: boolean | null;
  evidence_hash: string;
}
export class EffectError extends Error {}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}
function text(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value === value.trim();
}
function keys(value: Record<string, unknown>, names: string[]): boolean {
  return Object.keys(value).sort().join("\u0000") === names.sort().join("\u0000");
}
export function effectIdentity(descriptor: unknown): string {
  if (!object(descriptor)) throw new EffectError("effect descriptor must be an object");
  const field = descriptor.kind === "exact" ? "parameters" : descriptor.kind === "semantic" ? "semantic_key" : null;
  if (!field || !keys(descriptor, ["profile","namespace","kind","action_type","target",field]))
    throw new EffectError("effect descriptor has missing or unsupported fields");
  if (descriptor.profile !== EFFECT_PROFILE) throw new EffectError("unsupported effect profile");
  if (!text(descriptor.namespace)) throw new EffectError("effect namespace must be an owner-configured identifier");
  if (!text(descriptor.action_type) || /[*?\[\]]/.test(descriptor.action_type))
    throw new EffectError("effect action must be a concrete capability");
  if (!object(descriptor.target) || !keys(descriptor.target, ["type","id"]) ||
      Object.values(descriptor.target).some(v => !text(v) || /[*?\[\]]/.test(v)))
    throw new EffectError("effect target must be a canonical exact TargetRef");
  if (!object(descriptor[field]) || (descriptor.kind === "semantic" && Object.keys(descriptor[field]).length === 0))
    throw new EffectError("effect parameters/key must be an object; semantic key must be nonempty");
  const hash = createHash("sha256").update("ACTENON-EFFECT-1\u0000").update(canonicalizeBytes(descriptor)).digest("hex");
  return "effect_" + hash;
}
export function validateEffectOutcome(outcome: unknown, executionOccurred: unknown, evidenceHash: unknown): EffectOutcome {
  if (!["COMMITTED","NOT_EXECUTED","AMBIGUOUS"].includes(outcome as string)) throw new EffectError("unknown effect outcome");
  if (executionOccurred !== null && typeof executionOccurred !== "boolean") throw new EffectError("execution_occurred must be boolean or null");
  if (typeof evidenceHash !== "string" || !/^[0-9a-f]{64}$/.test(evidenceHash)) throw new EffectError("evidence digest required");
  if (outcome === "COMMITTED" && executionOccurred !== true) throw new EffectError("COMMITTED requires observed execution");
  if (outcome === "NOT_EXECUTED" && executionOccurred !== false) throw new EffectError("NOT_EXECUTED requires established non-execution");
  if (outcome === "AMBIGUOUS" && executionOccurred === false) throw new EffectError("non-execution is NOT_EXECUTED");
  return outcome as EffectOutcome;
}
export function validateEffectReference(value: unknown): EffectReference {
  if (!object(value) || !keys(value,["profile","effect_id","reservation_id","owner_attempt_id"]) ||
      value.profile !== EFFECT_PROFILE || typeof value.effect_id !== "string" || !/^effect_[0-9a-f]{64}$/.test(value.effect_id) ||
      typeof value.reservation_id !== "string" || !/^reservation_[0-9a-f]{32}$/.test(value.reservation_id) ||
      typeof value.owner_attempt_id !== "string" || !/^exec_[0-9a-f]{16,}$/.test(value.owner_attempt_id))
    throw new EffectError("invalid effect reference");
  return value as unknown as EffectReference;
}
export function validateEffectEvidence(value: unknown): EffectEvidence {
  if (!object(value) || !keys(value,["profile","effect_id","reservation_id","owner_attempt_id","outcome","execution_occurred","evidence_hash"]))
    throw new EffectError("invalid effect evidence");
  validateEffectReference({profile:value.profile,effect_id:value.effect_id,reservation_id:value.reservation_id,owner_attempt_id:value.owner_attempt_id});
  validateEffectOutcome(value.outcome,value.execution_occurred,value.evidence_hash);
  return value as unknown as EffectEvidence;
}
