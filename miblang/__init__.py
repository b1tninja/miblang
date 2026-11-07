"""miblang -- SMIv2 module parsing that says which edition an answer came from.

snmpy carries about 150 KB of hand-maintained management-information code and not one line of
grammar: mib_view.py is 40,505 bytes of hand-written per-MIB views, mib.py is 25,969 bytes of
hand-copied OID constants whose own header cites RFC 1156, a HISTORIC document obsoleted by
the MIB-II of RFC 1213, and across all 70 of its python files there is exactly one stray
NOTIFICATION-TYPE token and no MODULE-IDENTITY or OBJECT-TYPE anywhere.
"""

from __future__ import annotations

from . import apps, catalogue, cli, conformance, conventions, grammar, lexer, resolve
from .catalogue import modules_of
from .conformance import compliance
from .conventions import textual_convention
from .grammar import module_identity, object_type
from .lexer import lex
from .resolve import index, load, provenance

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "apps",
    "catalogue",
    "cli",
    "compliance",
    "conformance",
    "conventions",
    "grammar",
    "index",
    "lex",
    "lexer",
    "load",
    "module_identity",
    "modules_of",
    "object_type",
    "provenance",
    "resolve",
    "textual_convention",
]
