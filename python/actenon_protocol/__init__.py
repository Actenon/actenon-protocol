"""Actenon Protocol — neutral, open, implementation-independent boundary contract.

This package provides:
  - Protocol version constants
  - Identifier validation and generation
  - The ACTENON-JCS-STRICT-1 canonicalisation reference implementation
  - The refusal-code catalogue (loaded from refusals/catalogue.v1.yaml)
  - Outcome code enums
  - Execution mode enum
  - Pydantic types mirroring the JSON Schemas

The package is the Python reference for the protocol. Other implementations
(TypeScript, Go, Rust) MUST produce byte-identical output for the same input.
"""

from __future__ import annotations

from actenon_protocol.canonicalisation import (
    MAX_CANONICAL_OUTPUT_BYTES,
    MAX_JSON_DEPTH,
    CanonicalisationError,
    canonicalize_bytes,
    canonicalize_json,
)
from actenon_protocol.execution_modes import ExecutionMode
from actenon_protocol.identifiers import (
    ALIASES,
    FORBIDDEN_PREFIXES,
    PREFIXES,
    generate_identifier,
    is_valid_identifier,
    normalise_identifier,
)
from actenon_protocol.outcome_codes import ExecutionOutcome
from actenon_protocol.refusal_codes import (
    COMPATIBILITY_ALIASES,
    DETAILED_CODES,
    PUBLIC_SAFE_CODES,
    DisclosurePolicy,
    RefusalCode,
    refusal_to_disclosed_code,
    refusal_to_internal_code,
    refusal_to_retryable,
    resolve_alias,
)
from actenon_protocol.version import (
    ACCEPTED_CANONICALISATION_PROFILES,
    CANONICALISATION_PROFILE,
    CANONICALISATION_PROFILE_VERSION,
    IDENTIFIER_REGISTRY_VERSION,
    LEGACY_CANONICALISATION_PROFILE,
    PROTOCOL_VERSION,
    TAXONOMY_VERSION,
)

__all__ = [
    # Version
    "PROTOCOL_VERSION",
    "CANONICALISATION_PROFILE",
    "CANONICALISATION_PROFILE_VERSION",
    "TAXONOMY_VERSION",
    "IDENTIFIER_REGISTRY_VERSION",
    "LEGACY_CANONICALISATION_PROFILE",
    "ACCEPTED_CANONICALISATION_PROFILES",
    # Identifiers
    "is_valid_identifier",
    "generate_identifier",
    "normalise_identifier",
    "PREFIXES",
    "ALIASES",
    "FORBIDDEN_PREFIXES",
    # Canonicalisation
    "canonicalize_json",
    "canonicalize_bytes",
    "CanonicalisationError",
    "MAX_CANONICAL_OUTPUT_BYTES",
    "MAX_JSON_DEPTH",
    # Refusal codes
    "RefusalCode",
    "DisclosurePolicy",
    "resolve_alias",
    "refusal_to_disclosed_code",
    "refusal_to_internal_code",
    "refusal_to_retryable",
    "PUBLIC_SAFE_CODES",
    "DETAILED_CODES",
    "COMPATIBILITY_ALIASES",
    # Outcomes
    "ExecutionOutcome",
    # Execution modes
    "ExecutionMode",
]

__version__ = PROTOCOL_VERSION
