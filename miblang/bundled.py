"""The SMI base modules, bundled as data with the sha256 of each one.

``miblang/data/`` holds RFC1155-SMI, RFC1213-MIB, SNMPv2-SMI, SNMPv2-TC and SNMPv2-CONF as published in
RFC 1155, 1213, 2578, 2579 and 2580, and, marked optional in the manifest, SNMPv2-MIB (RFC 3418) and IF-MIB
(RFC 2863), cut out of the RFC Editor text by ``tools/extract_bundle.py`` with
the page furniture removed and nothing else changed. ``MANIFEST.json`` records the RFC, its status, the
line range, the sha256 of the RFC text that was read, the sha256 of each module and the verified errata
that touch the module text and were deliberately not applied.

RFC 1212 (``OBJECT-TYPE`` for SMIv1) and RFC 1215 (``TRAP-TYPE``) are not here: each defines its macro
inside running text with no ``DEFINITIONS`` wrapper, so there is no published module to bundle verbatim.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from importlib import resources

from .grammar import Module, parse

__all__ = ["BundleError", "default_names", "load_module", "manifest", "names", "text"]


class BundleError(RuntimeError):
    """A bundled module is missing, or its bytes do not match the manifest."""


@cache
def manifest() -> dict[str, dict[str, object]]:
    """The manifest entry of each bundled module, by module name."""
    raw = (resources.files("miblang") / "data" / "MANIFEST.json").read_bytes()
    return {entry["module"]: entry for entry in json.loads(raw)}


def names() -> tuple[str, ...]:
    """Every bundled module, sorted."""
    return tuple(sorted(manifest()))


def default_names() -> tuple[str, ...]:
    """The bundled modules a ``Mib`` holds without being asked: all but those the manifest marks optional.

    IF-MIB and SNMPv2-MIB are optional. Each redefines, as the SMIv2 successor, OIDs that RFC1213-MIB defines,
    and IF-MIB imports IANAifType-MIB, which is not bundled (the IANA registry is fetched, see
    ``tools/fetch_iana_mibs.py``), so a Mib that held them by default would report problems of its own.
    """
    return tuple(n for n in names() if not manifest()[n].get("optional"))


def text(name: str) -> str:
    """The text of a bundled module, verified against its sha256 before it is returned."""
    entry = manifest().get(name)
    if entry is None:
        raise BundleError(f"no bundled module named {name!r}")
    data = (resources.files("miblang") / "data" / f"{name}.mib").read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise BundleError(f"bundled module {name} does not match its manifest sha256")
    return data.decode("ascii")


@cache
def load_module(name: str) -> Module:
    """Parse a bundled module."""
    return parse(text(name))
