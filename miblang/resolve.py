"""cross-module imports and the OID tree in both directions, with the module edition attached
to every answer.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    Imports = Any  # placeholder: give it a real type in the milestone that needs it
    Module = Any  # placeholder: give it a real type in the milestone that needs it
    Object = Any  # placeholder: give it a real type in the milestone that needs it
    Path = Any  # placeholder: give it a real type in the milestone that needs it
    Provenance = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "index",
    "load",
    "provenance",
    "resolve",
]


def load(path: Path, *, imports: Imports | None) -> Module:
    """Pending behaviour defined by RFC 2578.

    Not implemented yet. See the ``resolve.load()`` row in ROADMAP.md; this stub raises
    on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("load() is not implemented: RFC 2578")


def resolve(name: str) -> Object:
    """Pending behaviour defined by RFC 2578.

    Not implemented yet. See the ``resolve.resolve()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("resolve() is not implemented: RFC 2578")


def index(oid: str) -> Object | None:
    """Pending behaviour defined by RFC 2578.

    Not implemented yet. See the ``resolve.index()`` row in ROADMAP.md; this stub raises
    on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("index() is not implemented: RFC 2578")


def provenance(oid: str) -> Provenance:
    """Pending behaviour defined by design.

    Not implemented yet. See the ``resolve.provenance()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("provenance() is not implemented: design")
