/**
 * Actenon Protocol — TypeScript types.
 *
 * The neutral, open, implementation-independent boundary contract for the
 * Actenon ecosystem. This package provides type definitions and a
 * canonicalisation reference implementation.
 *
 * Wire format source of truth: schemas/*.v1.json
 * Canonicalisation source of truth: canonicalisation/ACTENON-JCS-STRICT-1.md
 */

export { PROTOCOL_VERSION, CANONICALISATION_PROFILE, LEGACY_CANONICALISATION_PROFILE, ACCEPTED_CANONICALISATION_PROFILES } from "./version.js";
export { isValidIdentifier, generateIdentifier, normaliseIdentifier, PREFIXES, ALIASES } from "./identifiers.js";
export { canonicalizeJson, canonicalizeBytes, CanonicalisationError } from "./canonicalisation.js";
export { RefusalCode, DisclosurePolicy, resolveAlias, refusalToDisclosedCode, refusalToInternalCode, refusalToRetryable, PUBLIC_SAFE_CODES, DETAILED_CODES } from "./refusal-codes.js";
export { ExecutionOutcome } from "./outcome-codes.js";
export { ExecutionMode } from "./execution-modes.js";

export type {
  ProtocolVersion,
  Identifier,
  Iso8601Timestamp,
  AudienceRef,
  TargetRef,
  ActionSpec,
  ActionHash,
  Signature,
  EvidenceLinkType,
  ExecutionProof,
  ExecutionReceipt,
  ExecutionRefusal,
  IssuerMetadata,
  EvidenceLink,
  AuthorisedExecutionIntent,
} from "./types.js";
