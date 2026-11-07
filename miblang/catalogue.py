"""the ITU-T formal-description artifacts itulib mirrors: Recommendation, edition, language,
module, OID and digest.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    Artifact = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "modules_of",
]


def modules_of(rec: str, *, edition: str) -> list[Artifact]:
    """Pending behaviour defined by ITU-T.

    Not implemented yet. See the ``catalogue.modules_of()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("modules_of() is not implemented: ITU-T")
