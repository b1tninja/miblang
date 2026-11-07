"""MODULE-COMPLIANCE and AGENT-CAPABILITY reduced to an obligation set a test can check.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    ComplianceSet = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "compliance",
]


def compliance(module: str) -> ComplianceSet:
    """Pending behaviour defined by RFC 2580.

    Not implemented yet. See the ``conformance.compliance()`` row in ROADMAP.md; this
    stub raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("compliance() is not implemented: RFC 2580")
