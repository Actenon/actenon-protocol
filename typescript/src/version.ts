/** Protocol version constants. */

export const PROTOCOL_VERSION = "1.0.0" as const;

export const CANONICALISATION_PROFILE = "ACTENON-JCS-STRICT-1" as const;
export const CANONICALISATION_PROFILE_VERSION = "1" as const;

export const LEGACY_CANONICALISATION_PROFILE = "RFC8785-JCS" as const;

export const ACCEPTED_CANONICALISATION_PROFILES = [
  "ACTENON-JCS-STRICT-1",
  "RFC8785-JCS",
] as const;

export const REJECTED_CANONICALISATION_PROFILE = "actenon-jcs-sha256-v1" as const;

export const TAXONOMY_VERSION = "1" as const;
export const IDENTIFIER_REGISTRY_VERSION = "1" as const;
