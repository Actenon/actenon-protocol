"""Refusal-code catalogue and disclosure-policy implementation.

Loads the canonical catalogue from refusals/catalogue.v1.yaml and provides:
  - RefusalCode enum (the 20 canonical codes)
  - DisclosurePolicy enum (public, trusted, local_debug)
  - alias resolution (compatibility with actenon-kernel FailureCode)
  - disclosed/internal code selection per policy
  - retryability lookup
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Final

import yaml

from actenon_protocol._compat import StrEnum


def _load_catalogue() -> dict:
    """Load the catalogue YAML.

    Uses importlib.resources so the file is found both in the source tree
    (dev installs) and in installed wheels (where the YAML is vendored
    under actenon_protocol/data/).
    """
    # Try the packaged data directory first (works for installed wheels and
    # editable installs where the data dir is present).
    try:
        with (
            resources.files("actenon_protocol.data")
            .joinpath("catalogue.v1.yaml")
            .open("r", encoding="utf-8") as f
        ):
            return yaml.safe_load(f)
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass
    # Fallback: resolve relative to the source repo (dev checkout without
    # the data dir copied in).
    repo_root = Path(__file__).resolve().parent.parent.parent
    catalogue_path = repo_root / "refusals" / "catalogue.v1.yaml"
    with catalogue_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_CATALOGUE: Final[dict] = _load_catalogue()


class RefusalCode(StrEnum):
    """The 20 canonical refusal codes defined in the protocol."""

    # request_shape
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    UNSUPPORTED_PROTOCOL_VERSION = "UNSUPPORTED_PROTOCOL_VERSION"
    CANONICALISATION_FAILURE = "CANONICALISATION_FAILURE"

    # proof_presence
    PROOF_MISSING = "PROOF_MISSING"

    # proof_validity (umbrella + detailed)
    PROOF_INVALID = "PROOF_INVALID"  # umbrella
    ISSUER_UNTRUSTED = "ISSUER_UNTRUSTED"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    PROOF_EXPIRED = "PROOF_EXPIRED"
    PROOF_NOT_YET_VALID = "PROOF_NOT_YET_VALID"
    AUDIENCE_MISMATCH = "AUDIENCE_MISMATCH"
    TARGET_MISMATCH = "TARGET_MISMATCH"
    ACTION_MISMATCH = "ACTION_MISMATCH"
    PARAMETER_MISMATCH = "PARAMETER_MISMATCH"
    REPLAY_DETECTED = "REPLAY_DETECTED"

    # authority_state
    AUTHORITY_REVOKED = "AUTHORITY_REVOKED"
    POLICY_REFUSAL = "POLICY_REFUSAL"

    # provider
    CREDENTIAL_UNAVAILABLE = "CREDENTIAL_UNAVAILABLE"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"

    # outcome
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class DisclosurePolicy(StrEnum):
    """The three disclosure policies."""

    PUBLIC = "public"
    TRUSTED = "trusted"
    LOCAL_DEBUG = "local_debug"


# Codes that are safe to disclose under the `public` policy.
# These appear in the `disclosed_code` field of ExecutionRefusal.
PUBLIC_SAFE_CODES: Final[frozenset[str]] = frozenset(
    code["disclosed_code"] for code in _CATALOGUE["codes"]
)

# Codes that are only emitted under `trusted` or `local_debug` policy.
# These appear in the `internal_code` field when the disclosure policy permits.
DETAILED_CODES: Final[frozenset[str]] = frozenset(
    code["internal_code"] for code in _CATALOGUE["codes"] if code["internal_code"] is not None
)

# Map: alias (from existing actenon-kernel FailureCode enum) → canonical code.
COMPATIBILITY_ALIASES: Final[dict[str, str]] = dict(_CATALOGUE["compatibility_aliases"])

# Map: canonical internal_code → disclosed_code (public-safe umbrella).
_INTERNAL_TO_DISCLOSED: Final[dict[str | None, str]] = {
    code["internal_code"]: code["disclosed_code"] for code in _CATALOGUE["codes"]
}

# Map: canonical code → retryable boolean.
_RETRYABLE: Final[dict[str, bool]] = {
    code["code"]: code["retryable"] for code in _CATALOGUE["codes"]
}


def resolve_alias(alias: str) -> str:
    """Resolve a compatibility alias to its canonical code.

    If `alias` is already a canonical code, return it unchanged.
    If `alias` is a registered alias (e.g. "PCCB_REQUIRED"), return the
    canonical code (e.g. "PROOF_MISSING").

    Raises KeyError if `alias` is neither a canonical code nor a registered alias.
    """
    # Try canonical first
    try:
        RefusalCode(alias)
        return alias
    except ValueError:
        pass
    # Try alias map
    if alias in COMPATIBILITY_ALIASES:
        return COMPATIBILITY_ALIASES[alias]
    raise KeyError(
        f"refusal code {alias!r} is neither canonical nor a registered alias. "
        f"If this is a new code, add it to refusals/catalogue.v1.yaml."
    )


def refusal_to_disclosed_code(internal_code: str | None, policy: DisclosurePolicy) -> str:
    """Map an internal refusal code to the disclosed code under the given policy.

    Under `public` policy, detailed codes collapse to their umbrella
    (e.g. SIGNATURE_INVALID → PROOF_INVALID).

    Under `trusted` or `local_debug`, the disclosed_code is still the
    umbrella (the disclosed_code field is always public-safe); the
    internal_code field carries the detail.
    """
    if internal_code is None:
        # Caller used None to mean PROOF_MISSING (the only code with no
        # internal specialisation — it is its own disclosed_code).
        return RefusalCode.PROOF_MISSING.value
    if internal_code not in _INTERNAL_TO_DISCLOSED:
        # Unknown code — forward-compat escape hatch
        return RefusalCode.OUTCOME_UNKNOWN.value
    return _INTERNAL_TO_DISCLOSED[internal_code]


def refusal_to_internal_code(internal_code: str | None, policy: DisclosurePolicy) -> str | None:
    """Return the internal_code to emit under the given policy.

    Under `public` policy, returns None (suppress detail).
    Under `trusted` or `local_debug`, returns the internal_code.
    """
    if policy == DisclosurePolicy.PUBLIC:
        return None
    return internal_code


def refusal_to_retryable(internal_code: str | None) -> bool:
    """Return the retryable flag for the given internal code."""
    if internal_code is None:
        return _RETRYABLE[RefusalCode.PROOF_MISSING.value]
    if internal_code not in _RETRYABLE:
        # Unknown code — forward-compat: treat as retryable (safer default
        # for OUTCOME_UNKNOWN-like cases).
        return True
    return _RETRYABLE[internal_code]


def is_disclosed_code_safe(code: str) -> bool:
    """Return True if `code` is safe to appear in the disclosed_code field
    (i.e. it is in PUBLIC_SAFE_CODES)."""
    return code in PUBLIC_SAFE_CODES


def is_detailed_code(code: str) -> bool:
    """Return True if `code` is a detailed code that may appear in
    internal_code under trusted disclosure."""
    return code in DETAILED_CODES


def all_codes() -> list[dict]:
    """Return the full catalogue as a list of code entries."""
    return list(_CATALOGUE["codes"])
