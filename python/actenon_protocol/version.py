"""Protocol version constants.

These are the canonical version identifiers for the Actenon protocol.
See VERSIONING.md and CHANGELOG.md for the versioning policy.
"""

from __future__ import annotations

# The protocol version. MAJOR.MINOR.PATCH.
# See VERSIONING.md for what each bump means.
#
# 1.1.0 (Prompt 9): added the ExecutionResult discriminated union
# (BrokeredExecutionResult | ResourceOwnedExecutionResult) and the
# per-mode state machines. Purely additive: no existing v1.0.0
# artefact's wire format changed. See protocol/12-execution-results.md.
PROTOCOL_VERSION = "1.1.0"

# The canonical canonicalisation profile label.
# This is the label that newly-minted proofs and receipts MUST use.
CANONICALISATION_PROFILE = "ACTENON-JCS-STRICT-1"
CANONICALISATION_PROFILE_VERSION = "1"

# A legacy alias for the canonical profile.
# Historical proofs may carry this label. The canonicalisation logic is
# identical; only the label differs. New proofs MUST NOT use this label.
LEGACY_CANONICALISATION_PROFILE = "RFC8785-JCS"

# All canonicalisation labels accepted by the protocol.
ACCEPTED_CANONICALISATION_PROFILES = frozenset(
    {
        CANONICALISATION_PROFILE,
        LEGACY_CANONICALISATION_PROFILE,
    }
)

# A doc-only label that NO implementation accepts. Explicitly rejected.
REJECTED_CANONICALISATION_PROFILE = "actenon-jcs-sha256-v1"

# The refusal taxonomy version.
# See refusals/catalogue.v1.yaml.
TAXONOMY_VERSION = "1"

# The identifier registry version.
# See identifiers/prefixes.v1.yaml.
IDENTIFIER_REGISTRY_VERSION = "1"
