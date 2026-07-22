/**
 * TypeScript types for the Actenon protocol artefacts.
 *
 * Hand-written from schemas/*.v1.json. If a schema changes, regenerate
 * the corresponding type. The schemas are the source of truth.
 */

export type ProtocolVersion = string; // pattern: ^1\.[0-9]+\.[0-9]+$
export type Identifier = string; // pattern: ^[a-z][a-z0-9_]*_[0-9a-f]{16,}$
export type Iso8601Timestamp = string;

export type EvidenceLinkType =
  | "transparency_log"
  | "receipt_chain"
  | "audit_ledger"
  | "external_attestation"
  | "counter_signature";

export type ExecutionMode = "brokered" | "resource_owned";
export type ExecutionOutcome = "EXECUTED" | "REFUSED" | "PARTIAL" | "UNKNOWN";

export interface AudienceRef {
  type: string;
  id: string;
}

export interface TargetRef {
  type: string;
  id: string;
}

export interface ActionSpec {
  type: string;
  parameters: Record<string, unknown>;
}

export interface ActionHash {
  algorithm: string; // default "sha256"
  value: string; // 64-char lowercase hex
}

export interface Signature {
  algorithm: string; // e.g. "EdDSA", "ES256", "HS256"
  key_id: string;
  value: string; // base64url, no padding
}

export interface EmbeddedKey {
  algorithm: string;
  public_key: string; // base64url
  key_id: string;
}

export interface KeyDiscovery {
  method: "well_known" | "embedded" | "external_registry";
  well_known_url?: string;
  embedded_key?: EmbeddedKey;
  external_registry_url?: string;
}

export interface KeyRotationPolicy {
  rotation_period_days: number;
  overlap_period_days: number;
}

export interface IssuerMetadata {
  issuer_id: string;
  issuer_type: "authority_broker" | "resource_owner" | "delegated_signer";
  key_discovery: KeyDiscovery;
  trust_status?: "active" | "suspended" | "revoked";
  key_rotation_policy?: KeyRotationPolicy;
}

export interface EvidenceTargetRef {
  url?: string;
  hash?: ActionHash;
  inline_payload?: Record<string, unknown>;
}

export interface EvidenceLink {
  type: EvidenceLinkType;
  link_type: "inline" | "external_url" | "content_hash";
  target_ref: EvidenceTargetRef;
  issued_at?: Iso8601Timestamp;
  issuer_id?: string;
}

export interface ExecutionProof {
  protocol_version: ProtocolVersion;
  proof_id: Identifier;
  issuer: IssuerMetadata;
  subject: string;
  audience: AudienceRef;
  action: ActionSpec;
  target: TargetRef;
  issued_at: Iso8601Timestamp;
  not_before?: Iso8601Timestamp;
  expires_at: Iso8601Timestamp;
  canonicalisation: "ACTENON-JCS-STRICT-1" | "RFC8785-JCS";
  action_hash: ActionHash;
  signature: Signature;
  execution_mode: ExecutionMode;
  grant_id?: Identifier | null;
  authority_decision_id?: Identifier | null;
  evidence_links?: EvidenceLink[];
  custom_claims?: Record<string, unknown>;
}

export interface ExecutionReceipt {
  protocol_version: ProtocolVersion;
  receipt_id: Identifier;
  proof_id: Identifier;
  execution_attempt_id: Identifier;
  execution_mode: ExecutionMode;
  executed_at: Iso8601Timestamp;
  outcome: ExecutionOutcome;
  target: TargetRef;
  action: ActionSpec;
  provider_response_summary?: Record<string, unknown>;
  refusal_id?: Identifier | null;
  evidence_links?: EvidenceLink[];
  resource_signature?: Signature | null;
}

export interface ExecutionRefusal {
  protocol_version: ProtocolVersion;
  refusal_id: Identifier;
  proof_id?: Identifier | null;
  execution_attempt_id?: Identifier | null;
  execution_mode: ExecutionMode;
  refused_at: Iso8601Timestamp;
  disclosed_code: string;
  internal_code?: string | null;
  message?: string;
  retryable: boolean;
  evidence_links?: EvidenceLink[];
}

export interface AuthorisedExecutionIntent {
  protocol_version: ProtocolVersion;
  intent_id: Identifier;
  subject: string;
  action: ActionSpec;
  target: TargetRef;
  requested_at: Iso8601Timestamp;
  requested_expiry?: Iso8601Timestamp;
  requested_execution_mode?: ExecutionMode;
  metadata?: Record<string, unknown>;
}
