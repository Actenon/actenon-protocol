/**
 * @actenon/protocol — runtime package.
 *
 * Provides the ACTENON-JCS-STRICT-1 canonicaliser and related utilities
 * for TypeScript/JavaScript consumers. This package ships compiled JS;
 * for type-only imports, use @actenon/protocol-types.
 */

export {
  canonicalize,
  canonicalizeBytes,
  canonicalizeJson,
  parseStrict,
  CanonicalisationError,
  MAX_CANONICAL_OUTPUT_BYTES,
  MAX_JSON_DEPTH,
} from "./canonicalisation.js";

// Version constants are defined locally: @actenon/protocol-types ships
// TypeScript source only, so re-exporting its VALUES would make this
// package unloadable under Node.js. Types are erased at build time and
// are safe to re-export.
export {
  PROTOCOL_VERSION,
  CANONICALISATION_PROFILE,
  LEGACY_CANONICALISATION_PROFILE,
  ACCEPTED_CANONICALISATION_PROFILES,
} from "./version.js";

export type {
  ProtocolVersion,
  Identifier,
  Iso8601Timestamp,
  ExecutionProof,
  ExecutionReceipt,
  ExecutionRefusal,
} from "@actenon/protocol-types";
