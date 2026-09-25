/**
 * Protocol version constants for the runtime package.
 *
 * These MUST equal the constants in typescript/src/version.ts
 * (@actenon/protocol-types). They are defined here rather than
 * re-exported because @actenon/protocol-types ships TypeScript source
 * only: a runtime `export { X } from "@actenon/protocol-types"` makes
 * dist/index.js unloadable under Node.js
 * (ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING). tests/conformance.ts
 * asserts the two copies agree.
 */

// Wire-protocol version; MUST equal python/actenon_protocol/version.py (tested).
export const PROTOCOL_VERSION = "1.1.0" as const;

export const CANONICALISATION_PROFILE = "ACTENON-JCS-STRICT-1" as const;

export const LEGACY_CANONICALISATION_PROFILE = "RFC8785-JCS" as const;

export const ACCEPTED_CANONICALISATION_PROFILES = [
  "ACTENON-JCS-STRICT-1",
  "RFC8785-JCS",
] as const;
