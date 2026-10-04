/**
 * Exact capabilities and the signed authority extension.
 *
 * Mirrors python/actenon_protocol/capabilities.py. A glob is not a
 * capability, an empty mint set is not widened, and token length is not
 * signature verification.
 */

export const GLOB_CHARS = new Set(["*", "?", "[", "]"]);

export class CapabilityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CapabilityError";
  }
}

export function isConcreteCapability(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    ![...value].some((ch) => GLOB_CHARS.has(ch))
  );
}

function requireConcrete(capabilities: readonly string[], emptyMessage: string): string[] {
  if (!Array.isArray(capabilities)) {
    throw new CapabilityError("capabilities must be a sequence of strings");
  }
  if (capabilities.length === 0) {
    throw new CapabilityError(emptyMessage);
  }
  for (const capability of capabilities) {
    if (!isConcreteCapability(capability)) {
      throw new CapabilityError(
        "proof capability must name one concrete action; a wildcard is not a capability",
      );
    }
  }
  return [...capabilities];
}

export function scopeCapabilitiesForMint(capabilities: readonly string[]): string[] {
  return requireConcrete(
    capabilities,
    "empty allow-list cannot mint a proof; refusing to widen to the attempted action",
  );
}

export function scopeCapabilitiesForVerification(
  declared: readonly string[] | null,
  intentCapability: string,
): string[] {
  if (!isConcreteCapability(intentCapability)) {
    throw new CapabilityError(
      "intent capability must name one concrete action; a wildcard is not a capability",
    );
  }
  if (declared === null) {
    return [intentCapability];
  }
  if (declared.length === 0) {
    return [];
  }
  return requireConcrete(declared, "empty edge allow-list authorises nothing");
}

export function capabilityInScope(capability: string, declared: readonly string[]): boolean {
  if (!isConcreteCapability(capability)) return false;
  return declared.includes(capability) && declared.every((item) => isConcreteCapability(item));
}

export interface AuthorityExtension {
  issuer: string;
  grant_id: string;
  revocable: boolean;
}

export function authorityExtension(args: {
  issuer: string;
  grant_id: string;
  revocable?: boolean;
}): { authority: AuthorityExtension } {
  const revocable = args.revocable ?? true;
  if (typeof args.issuer !== "string" || args.issuer.length === 0) {
    throw new CapabilityError("authority extension requires an issuer");
  }
  if (typeof args.grant_id !== "string" || args.grant_id.length === 0) {
    throw new CapabilityError("authority extension requires a grant_id");
  }
  if (typeof revocable !== "boolean") {
    throw new CapabilityError("authority extension revocable must be a boolean");
  }
  return { authority: { issuer: args.issuer, grant_id: args.grant_id, revocable } };
}

export function unauthenticatedRefusal(args: {
  trustRootConfigured: boolean;
  signatureVerified: boolean;
}): "ISSUER_UNTRUSTED" | "SIGNATURE_INVALID" | null {
  if (!args.trustRootConfigured) return "ISSUER_UNTRUSTED";
  if (!args.signatureVerified) return "SIGNATURE_INVALID";
  return null;
}
