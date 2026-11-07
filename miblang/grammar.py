"""the RFC 2578 macro forms and the RFC 2579 TEXTUAL-CONVENTION form, kept as syntax rather
than as a tree of dicts.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    ModuleHeader = Any  # placeholder: give it a real type in the milestone that needs it
    Object = Any  # placeholder: give it a real type in the milestone that needs it
    Token = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "module_identity",
    "object_type",
]


def module_identity(tokens: Sequence[Token]) -> ModuleHeader:
    """Pending behaviour defined by RFC 2578.

    Not implemented yet. See the ``grammar.module_identity()`` row in ROADMAP.md; this
    stub raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("module_identity() is not implemented: RFC 2578")


def object_type(tokens: Sequence[Token]) -> Object:
    """Pending behaviour defined by RFC 2578.

    Not implemented yet. See the ``grammar.object_type()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("object_type() is not implemented: RFC 2578")
