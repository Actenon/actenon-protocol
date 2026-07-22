"""Compatibility shim for StrEnum across Python versions.

`enum.StrEnum` was added in Python 3.11. This module provides a
backport for Python 3.10 that uses `str, Enum` mixin (which has the
same behaviour: members are strings, and `str(member)` returns the
value, not `ClassName.MEMBER`).

On Python 3.11+, this module re-exports the stdlib `StrEnum`.
On Python 3.10, it defines a compatible base class.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of enum.StrEnum for Python 3.10.

        On Python 3.11+, use the stdlib enum.StrEnum instead.
        """

        def __str__(self) -> str:
            return self.value

        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name

__all__ = ["StrEnum"]
