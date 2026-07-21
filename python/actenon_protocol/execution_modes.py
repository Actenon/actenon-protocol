"""Execution mode enum."""

from __future__ import annotations

from enum import StrEnum


class ExecutionMode(StrEnum):
    """The execution mode. Explicit on every proof, receipt, refusal, and SDK result.

    BROKERED: the deployment obtains or resolves a scoped provider credential,
        verifies the exact-action proof, and invokes the protected provider
        or action adapter.

    RESOURCE_OWNED: the protected resource independently receives a request
        and proof, verifies it using its own Kernel deployment or compatible
        verifier, and decides whether to execute.
    """

    BROKERED = "brokered"
    RESOURCE_OWNED = "resource_owned"
