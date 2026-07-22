/**
 * Identifier validation, generation, and alias resolution.
 *
 * Format: <prefix><hex_chars>
 *   - prefix is lowercase, matches ^[a-z][a-z0-9_]*_$
 *   - hex_chars is lowercase hexadecimal, minimum 16 chars, recommended 32
 *   - full regex: ^[a-z][a-z0-9_]*_[0-9a-f]{16,}$
 */

export const PREFIXES = [
  "intent_",
  "authz_",
  "grant_",
  "proof_",
  "exec_",
  "rcpt_",
  "rful_",
] as const;

export type Prefix = (typeof PREFIXES)[number];

export const ALIASES: Record<string, string> = {
  "act_": "intent_",
  "pccb_": "proof_",
};

export const FORBIDDEN_PREFIXES = ["tenant_", "user_", "policy_", "approval_"] as const;

const IDENTIFIER_RE = /^(?<prefix>[a-z][a-z0-9_]*_)(?<hex>[0-9a-f]{16,})$/;

export const RECOMMENDED_HEX_LENGTH = 32;
export const MINIMUM_HEX_LENGTH = 16;

export function isValidIdentifier(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = value.match(IDENTIFIER_RE);
  if (!match?.groups) return false;
  const prefix = match.groups.prefix;
  if (FORBIDDEN_PREFIXES.includes(prefix as never)) return false;
  return true;
}

export function normaliseIdentifier(value: string): string {
  if (!isValidIdentifier(value)) {
    throw new Error(`not a valid Actenon identifier: ${JSON.stringify(value)}`);
  }
  const match = value.match(IDENTIFIER_RE);
  if (!match?.groups) throw new Error("invalid identifier");
  const prefix = match.groups.prefix;
  const hex = match.groups.hex;
  const canonicalPrefix = ALIASES[prefix] ?? prefix;
  return `${canonicalPrefix}${hex}`;
}

export function generateIdentifier(prefix: string, hexLength: number = RECOMMENDED_HEX_LENGTH): string {
  if (!PREFIXES.includes(prefix as never)) {
    throw new Error(
      `prefix ${JSON.stringify(prefix)} is not a registered canonical prefix. Use one of: ${PREFIXES.join(", ")}`
    );
  }
  if (hexLength < MINIMUM_HEX_LENGTH) {
    throw new Error(`hexLength ${hexLength} is below minimum ${MINIMUM_HEX_LENGTH}`);
  }
  const numBytes = Math.ceil(hexLength / 2);
  const randomBytes = new Uint8Array(numBytes);
  crypto.getRandomValues(randomBytes);
  const hex = Array.from(randomBytes, (b) => b.toString(16).padStart(2, "0")).join("").slice(0, hexLength);
  return `${prefix}${hex}`;
}

export function getPrefix(value: string): string | null {
  if (!isValidIdentifier(value)) return null;
  const match = value.match(IDENTIFIER_RE);
  return match?.groups?.prefix ?? null;
}

export function getCanonicalPrefix(value: string): string | null {
  const prefix = getPrefix(value);
  if (prefix === null) return null;
  return ALIASES[prefix] ?? prefix;
}
