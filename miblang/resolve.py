"""cross-module imports and the OID tree in both directions, with the module edition attached
to every answer.

A ``Mib`` holds parsed modules (``grammar.Module``), resolves every OID-valued definition across
``IMPORTS`` into numbers (RFC 2578 3.2, 3.5), and answers

* ``resolve(name)``: a symbol, ``MODULE::symbol`` or dotted OID to an ``Object``, with the metadata a
  consumer otherwise copies by hand (the syntax chain down to its base type, access, status and whether
  the object is a scalar, table, row or column);
* ``index(oid)``: an instance OID to the object it belongs to by longest-prefix match, with the row index
  split off according to the INDEX clause (RFC 2578 7.7; RFC 1212 4.1.6);
* ``provenance(oid)``: which published document the answer came from and what has happened to it since.

Nothing here guesses. A name that cannot be resolved is recorded in ``Mib.problems`` and left out of the
tree; a symbol defined in more than one loaded module needs a ``MODULE::`` prefix, and ``resolve`` says
so rather than choosing one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from . import bundled
from .grammar import (
    AgentCapabilities,
    Definition,
    IndexItem,
    Module,
    ModuleCompliance,
    ModuleIdentity,
    NotificationGroup,
    NotificationType,
    ObjectGroup,
    ObjectIdentifierAssignment,
    ObjectIdentity,
    ObjectType,
    Oid,
    Syntax,
    TextualConvention,
    TypeAssignment,
    parse,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "IndexValue",
    "Instance",
    "Mib",
    "Object",
    "Provenance",
    "ResolveError",
    "TypeInfo",
    "default",
    "index",
    "load",
    "parse_oid",
    "provenance",
    "resolve",
]

# ASN.1 root arcs, which an OBJECT IDENTIFIER value may name without defining them (RFC 2578 3.5 builds
# every value from "iso" or from a symbol that does).
_ROOTS = {"ccitt": 0, "iso": 1, "joint-iso-ccitt": 2}
_SMI_MODULES = frozenset({"SNMPv2-SMI", "RFC1155-SMI"})
_PRIMITIVES = frozenset(
    {
        "INTEGER",
        "OCTET STRING",
        "OBJECT IDENTIFIER",
        "BITS",
        "NULL",
        "BOOLEAN",
        "SEQUENCE",
        "SEQUENCE OF",
        "CHOICE",
    }
)
# What a base-type name means when no loaded module defines it (RFC 2578 2, RFC 1155 6).
_BUILTIN_PRIMITIVE = {
    "Integer32": "INTEGER",
    "Unsigned32": "INTEGER",
    "Counter32": "INTEGER",
    "Counter64": "INTEGER",
    "Gauge32": "INTEGER",
    "TimeTicks": "INTEGER",
    "Counter": "INTEGER",
    "Gauge": "INTEGER",
    "IpAddress": "OCTET STRING",
    "Opaque": "OCTET STRING",
}
_MAX_SUBID = 2**32 - 1  # RFC 2578 3.5
_MAX_OID_LENGTH = 4096  # a local bound against hostile input, not a protocol limit

# SMIv1 access words in the SMIv2 vocabulary (RFC 3584 2.1.1 item 5: write-only becomes read-write).
_ACCESS_V1_TO_V2 = {
    "read-only": "read-only",
    "read-write": "read-write",
    "write-only": "read-write",
    "not-accessible": "not-accessible",
}
# RFC 1213 groups that were later re-specified: (OID prefix, updating RFC, its current replacement).
# rfclib (2026-11-13): RFC 1213 is updated by RFC 2011, 2012 and 2013; each of those is OBSOLETE, obsoleted
# by RFC 4293, 4022 and 4113 respectively. RFC 2011 covers IP and ICMP.
_UPDATED_GROUPS: tuple[tuple[tuple[int, ...], str, str], ...] = (
    ((1, 3, 6, 1, 2, 1, 4), "RFC 2011", "RFC 4293"),
    ((1, 3, 6, 1, 2, 1, 5), "RFC 2011", "RFC 4293"),
    ((1, 3, 6, 1, 2, 1, 6), "RFC 2012", "RFC 4022"),
    ((1, 3, 6, 1, 2, 1, 7), "RFC 2013", "RFC 4113"),
)

Value = int | bytes | tuple[int, ...] | str


class ResolveError(LookupError):
    """A name or OID cannot be resolved, or an answer would need a guess."""


def parse_oid(text: str) -> tuple[int, ...]:
    """A dotted OID (``1.3.6.1`` or ``.1.3.6.1``) as sub-identifiers, each 0..2^32-1 (RFC 2578 3.5)."""
    body = text[1:] if text.startswith(".") else text
    parts = body.split(".")
    if not body or len(parts) > _MAX_OID_LENGTH:
        raise ResolveError(f"not a dotted OID: {text[:60]!r}")
    out: list[int] = []
    for part in parts:
        if not (part.isascii() and part.isdigit()) or int(part) > _MAX_SUBID:
            raise ResolveError(f"not a dotted OID: {text[:60]!r}")
        out.append(int(part))
    return tuple(out)


def _dotted(oid: tuple[int, ...]) -> str:
    return ".".join(str(n) for n in oid)


@dataclass(frozen=True)
class TypeInfo:
    """A SYNTAX followed down to its base type.

    ``name`` is the type as written (``DisplayString``, ``INTEGER``), ``chain`` the type names walked on the
    way to ``base`` (RFC 2579 3.5 says a textual convention's SYNTAX cannot name another one, so a chain of
    more than one name is an object refining a convention (RFC 2579 4) or a module that breaks that rule,
    which is noted). ``base`` is the primitive (INTEGER, OCTET STRING, OBJECT IDENTIFIER, BITS, ...) and
    ``smi_type`` the last SMI base type met (``Counter32``, ``Gauge32``, ``IpAddress``, or the primitive
    itself). ``ranges``, ``sizes`` and ``named_numbers`` are the outermost refinement that writes one, as
    each refinement narrows the one inside it (RFC 2578 9).
    """

    name: str
    base: str
    smi_type: str
    chain: tuple[str, ...] = ()
    named_numbers: tuple[tuple[str, int], ...] = ()
    ranges: tuple[tuple[int | str, int | str], ...] = ()
    sizes: tuple[tuple[int | str, int | str], ...] = ()
    textual_convention: str | None = None
    display_hint: str | None = None
    resolved: bool = True
    notes: tuple[str, ...] = ()

    @property
    def smiv2_only(self) -> bool:
        """True when the type is Counter64, which an SNMPv1 agent cannot carry (RFC 3584 4.2.2.1)."""
        return self.smi_type == "Counter64" or "Counter64" in self.chain


@dataclass(frozen=True)
class Object:
    """A named node with a number path, plus what its definition says about it.

    ``role`` is ``scalar``, ``table``, ``row`` or ``column`` for an OBJECT-TYPE (RFC 2578 7.10: a table
    holds exactly one row, a row holds columns) and None for any other kind.
    """

    name: str
    module: str
    oid: tuple[int, ...]
    kind: str
    definition: Definition
    role: str | None = None
    type: TypeInfo | None = None
    smi: int | None = None

    @property
    def dotted(self) -> str:
        return _dotted(self.oid)

    @property
    def status(self) -> str | None:
        status = getattr(self.definition, "status", None)
        return status if isinstance(status, str) else None

    @property
    def access(self) -> str | None:
        """The ACCESS or MAX-ACCESS word as written."""
        return self.definition.access if isinstance(self.definition, ObjectType) else None

    @property
    def max_access(self) -> str | None:
        """The access in the SMIv2 vocabulary: SMIv1 ``write-only`` is ``read-write`` (RFC 3584 2.1.1)."""
        if not isinstance(self.definition, ObjectType):
            return None
        if self.definition.smi == 2:
            return self.definition.access
        return _ACCESS_V1_TO_V2.get(self.definition.access, self.definition.access)

    @property
    def is_notification(self) -> bool:
        return self.kind in {"notification-type", "notification-group"}

    @property
    def smiv2_only(self) -> bool:
        return self.type is not None and self.type.smiv2_only


@dataclass(frozen=True)
class IndexValue:
    """One INDEX component decoded from an instance suffix."""

    name: str | None
    value: Value
    subids: tuple[int, ...]


@dataclass(frozen=True)
class Instance:
    """The result of ``index``: the object an instance OID belongs to and what follows it.

    ``others`` are further objects at the same OID in other loaded modules. ``problem`` is set when the
    suffix is not a valid instance of ``object`` (a scalar wants ``.0``; a column wants an index that the
    INDEX clause can decode, with nothing left over).
    """

    object: Object
    suffix: tuple[int, ...]
    index: tuple[IndexValue, ...] = ()
    others: tuple[Object, ...] = ()
    problem: str | None = None


@dataclass(frozen=True)
class Provenance:
    """Which document an object came from, and what has happened to it.

    ``revision`` is the module's own LAST-UPDATED (RFC 2578 5.1) when it has a MODULE-IDENTITY. ``source`` is
    ``"bundled"`` for a module cut from an RFC (``rfc`` and ``status`` are then set), ``"file"`` for a module
    read from a file (``path`` and the ``sha256`` of the bytes read are set) and ``"text"`` for one added as
    text with no recorded origin (only a ``sha256`` of the text as UTF-8, when it was given).
    """

    module: str
    rfc: int | None
    status: str | None
    updated_by: tuple[str, ...] = ()
    current_replacement: tuple[str, ...] = ()
    flagged: bool = False
    note: str = ""
    revision: str | None = None
    path: str | None = None
    sha256: str | None = None
    source: str = "bundled"


class Mib:
    """A set of modules and the OID tree they define. Build one, add modules, then query."""

    def __init__(self) -> None:
        self.problems: list[str] = []
        self._modules: dict[str, Module] = {}
        self._built = False
        self._defs: dict[str, dict[str, Definition]] = {}
        self._objects: dict[tuple[str, str], Object] = {}
        self._by_oid: dict[tuple[int, ...], list[Object]] = {}
        self._by_name: dict[str, list[Object]] = {}
        self._oid_memo: dict[tuple[str, str], tuple[int, ...] | None] = {}
        self._origin: dict[str, tuple[str | None, str | None]] = {}

    @classmethod
    def with_bundled(cls, *optional: str) -> Mib:
        """A Mib holding the bundled SMI base modules and MIB-II (``miblang.bundled``).

        ``optional`` names bundled modules to add as well, those the manifest marks optional (SNMPv2-MIB,
        IF-MIB): ``Mib.with_bundled("SNMPv2-MIB", "IF-MIB")``. IF-MIB also imports IANAifType-MIB, which is
        not bundled and has to be added by the caller. A name that is not bundled raises ``BundleError``.
        """
        mib = cls()
        for name in (*bundled.default_names(), *optional):
            mib.add(bundled.load_module(name))
        return mib

    def add(self, module: Module, *, path: str | None = None, sha256: str | None = None) -> None:
        """Add a parsed module, replacing a loaded one of the same name.

        ``path`` and ``sha256`` record where the module was read from and the hash of the bytes read; they
        come back in ``provenance`` (design). A module added without them has none to report.
        """
        self._modules[module.name] = module
        self._origin.pop(module.name, None)
        if path is not None or sha256 is not None:
            self._origin[module.name] = (path, sha256)
        self._built = False

    def add_text(self, text: str, *, path: str | None = None, sha256: str | None = None) -> Module:
        module = parse(text)
        self.add(module, path=path, sha256=sha256)
        return module

    @property
    def modules(self) -> tuple[str, ...]:
        return tuple(self._modules)

    # ---- building -------------------------------------------------------------------------

    def _build(self) -> None:
        if self._built:
            return
        self.problems = []
        self._defs, self._objects, self._by_oid, self._by_name = {}, {}, {}, {}
        self._oid_memo = {}
        for module in self._modules.values():
            table: dict[str, Definition] = {}
            for definition in module.definitions:
                name = getattr(definition, "name", None)
                if not isinstance(name, str):
                    continue
                if name in table:
                    self.problems.append(
                        f"{module.name}: {name} is defined twice; the first is kept"
                    )
                    continue
                table[name] = definition
            self._defs[module.name] = table
        self._check_imports()
        for module in self._modules.values():
            for name, definition in self._defs[module.name].items():
                kind = _kind_of(definition)
                oid = self._definition_oid(module.name, name, ()) if kind is not None else None
                if kind is None or oid is None:
                    continue
                obj = Object(name, module.name, oid, kind, definition, smi=module.smi)
                self._objects[module.name, name] = obj
                self._by_oid.setdefault(oid, []).append(obj)
                self._by_name.setdefault(name, []).append(obj)
        self._classify()
        self._order_overlaps()
        self._built = True

    def _order_overlaps(self) -> None:
        """Put the SMIv2 module first where two modules define the same OID, and report each overlap.

        An answer by OID goes to the first object at it, so the order is the answer. A module written in
        SMIv2 (RFC 2578) supersedes one written in SMIv1 (RFC 1155, RFC 1212) for the same OID, as IF-MIB
        (RFC 2863) does RFC 1213-MIB's interfaces group, so it is moved ahead; among modules of the same
        dialect the order they were added in stands. Nothing is resolved silently: one entry in
        ``problems`` per pair of modules names the winner, the loser and some of the OIDs
        (PORTFOLIO section 9 item 15). The SMI base modules, which restate each other's roots on purpose
        (``internet``, ``mib-2``), are ordered but not reported. ``MODULE::name`` lookups are not affected.
        """
        overlaps: dict[tuple[str, str], list[tuple[int, ...]]] = {}
        for oid, objects in self._by_oid.items():
            if len({o.module for o in objects}) < 2:
                continue
            ordered = sorted(objects, key=lambda o: 0 if o.smi == 2 else 1)  # stable
            self._by_oid[oid] = ordered
            winner = ordered[0].module
            for other in ordered[1:]:
                if other.module != winner and not {winner, other.module} & _SMI_MODULES:
                    overlaps.setdefault((winner, other.module), []).append(oid)
        for (winner, loser), oids in overlaps.items():
            shown = ", ".join(_dotted(o) for o in sorted(oids)[:3])
            more = f" and {len(oids) - 3} more" if len(oids) > 3 else ""
            self.problems.append(
                f"OID overlap: {winner} and {loser} both define {len(oids)} OID(s) ({shown}{more}); "
                f"{winner} answers a lookup by OID"
            )

    def _check_imports(self) -> None:
        """Report an IMPORTS entry the loaded source module does not define, and a descriptor imported twice.

        RFC 2578 3.2: an import names both the descriptor and the module that defines it, and where the same
        descriptor is imported from different modules the ambiguity is resolved with a ``module.descriptor``
        prefix. A source module that is not loaded is not checked: nothing here knows what it defines.
        """
        for module in self._modules.values():
            sources: dict[str, list[str]] = {}
            for source, symbols in module.imports:
                table = self._defs.get(source)
                for symbol in symbols:
                    seen = sources.setdefault(symbol, [])
                    if source not in seen:
                        seen.append(source)
                    if table is not None and symbol not in table:
                        self.problems.append(
                            f"{module.name}: imports {symbol} from {source}, which is loaded and does not define it"
                            " (RFC 2578 3.2)"
                        )
            for symbol, found in sources.items():
                if len(found) > 1:
                    self.problems.append(
                        f"{module.name}: {symbol} is imported from {' and '.join(found)}; RFC 2578 3.2 resolves"
                        " that with a module.descriptor prefix"
                    )

    def _lookup(
        self,
        module: str,
        name: str,
        qualifier: str | None = None,
        seen: frozenset[tuple[str, str]] = frozenset(),
    ) -> tuple[str, Definition] | None:
        """Find ``name`` as ``module`` sees it: qualified, then its own definitions, then its IMPORTS."""
        if qualifier is not None:
            found = self._defs.get(qualifier, {}).get(name)
            return (qualifier, found) if found is not None else None
        own = self._defs.get(module, {}).get(name)
        if own is not None:
            return module, own
        loaded = self._modules.get(module)
        if loaded is None or (module, name) in seen:
            return None
        for source, symbols in loaded.imports:
            if name in symbols:
                return self._lookup(source, name, None, seen | {(module, name)})
        return None

    def _definition_oid(
        self, module: str, name: str, stack: tuple[tuple[str, str], ...]
    ) -> tuple[int, ...] | None:
        key = (module, name)
        if key in self._oid_memo:
            return self._oid_memo[key]
        if key in stack:
            self.problems.append(f"{module}: {name} is defined in terms of itself")
            return None
        oid = getattr(self._defs.get(module, {}).get(name), "oid", None)
        if not isinstance(oid, Oid):
            return None
        value = self._oid_value(module, name, oid, (*stack, key))
        self._oid_memo[key] = value
        return value

    def _oid_value(
        self, module: str, owner: str, oid: Oid, stack: tuple[tuple[str, str], ...]
    ) -> tuple[int, ...] | None:
        out: list[int] = []
        for position, part in enumerate(oid.components):
            if part.number is not None:
                out.append(part.number)
                continue
            if position != 0 or part.name is None:
                self.problems.append(
                    f"{module}: {owner}: the name {part.name!r} stands alone after the first arc (RFC 2578 3.5)"
                )
                return None
            if (
                part.module is None
                and part.name in _ROOTS
                and part.name not in self._defs.get(module, {})
            ):
                out.append(_ROOTS[part.name])
                continue
            found = self._lookup(module, part.name, part.module)
            parent = None if found is None else self._definition_oid(found[0], part.name, stack)
            if parent is None:
                where = f"{part.module}." if part.module else ""
                self.problems.append(f"{module}: {owner}: cannot resolve {where}{part.name}")
                return None
            out.extend(parent)
        return tuple(out)

    # ---- types ----------------------------------------------------------------------------

    def type_info(
        self, syntax: Syntax, module: str, _seen: frozenset[tuple[str, str]] = frozenset()
    ) -> TypeInfo:
        """Follow ``syntax`` as written in ``module`` down to its base type (RFC 2579 3.5, 4; RFC 2578 9)."""
        base = syntax.base
        if base in _PRIMITIVES:
            return TypeInfo(
                base,
                base,
                base,
                named_numbers=syntax.named_numbers,
                ranges=syntax.ranges,
                sizes=syntax.sizes,
            )
        found = self._lookup(module, base)
        if found is None or (found[0], base) in _seen:
            if base in _BUILTIN_PRIMITIVE:
                return TypeInfo(
                    base,
                    _BUILTIN_PRIMITIVE[base],
                    base,
                    named_numbers=syntax.named_numbers,
                    ranges=syntax.ranges,
                    sizes=syntax.sizes,
                    notes=(f"{base} assumed from RFC 2578 2: no loaded module defines it",),
                )
            note = f"type {base} cannot be resolved from {module}"
            self.problems.append(note)
            return TypeInfo(base, base, base, resolved=False, notes=(note,))
        home, definition = found
        if not isinstance(definition, TextualConvention | TypeAssignment):
            return TypeInfo(base, base, base, resolved=False, notes=(f"{base} is not a type",))
        inner = self.type_info(definition.syntax, home, _seen | {(home, base)})
        notes = inner.notes
        is_tc = isinstance(definition, TextualConvention)
        if is_tc and inner.textual_convention is not None:
            notes = (
                *notes,
                f"{base} is defined over {inner.textual_convention}, which RFC 2579 3.5 does not allow",
            )
        hint = definition.display_hint if isinstance(definition, TextualConvention) else None
        return TypeInfo(
            base,
            inner.base,
            base if home in _SMI_MODULES else inner.smi_type,
            chain=(base, *inner.chain),
            named_numbers=syntax.named_numbers or inner.named_numbers,
            ranges=syntax.ranges or inner.ranges,
            sizes=syntax.sizes or inner.sizes,
            textual_convention=base if is_tc else inner.textual_convention,
            display_hint=hint or inner.display_hint,
            resolved=inner.resolved,
            notes=notes,
        )

    # ---- classification --------------------------------------------------------------------

    def _set(self, obj: Object, **changes: object) -> None:
        new = replace(obj, **changes)  # type: ignore[arg-type]
        self._objects[obj.module, obj.name] = new
        self._by_oid[obj.oid] = [new if o is obj else o for o in self._by_oid[obj.oid]]
        self._by_name[obj.name] = [new if o is obj else o for o in self._by_name[obj.name]]

    def _classify(self) -> None:
        """Type every object, then mark tables, rows and columns (RFC 2578 7.10, 7.7, 7.8)."""
        for obj in list(self._objects.values()):
            if isinstance(obj.definition, ObjectType):
                self._set(obj, type=self.type_info(obj.definition.syntax, obj.module))
        for obj in list(self._objects.values()):
            definition = obj.definition
            if not isinstance(definition, ObjectType) or obj.type is None:
                continue
            if obj.type.base == "SEQUENCE OF":
                self._set(obj, role="table")
            elif definition.index or definition.augments:
                self._set(obj, role="row")
        for obj in list(self._objects.values()):
            if isinstance(obj.definition, ObjectType) and obj.role is None:
                parents = self._by_oid.get(obj.oid[:-1], [])
                self._set(obj, role="column" if any(p.role == "row" for p in parents) else "scalar")

    # ---- queries --------------------------------------------------------------------------

    def resolve(self, name: str) -> Object:
        """A name, ``MODULE::name`` or dotted OID to its ``Object`` (RFC 2578 3.5, 4)."""
        self._build()
        if name[:1].isdigit() or name.startswith("."):
            at = self._by_oid.get(parse_oid(name))
            if not at:
                raise ResolveError(f"no object at {name}")
            return at[0]
        if "::" in name:
            module, _, symbol = name.partition("::")
            found = self._objects.get((module, symbol))
            if found is None:
                raise ResolveError(f"{symbol} is not an OID-valued definition of {module}")
            return found
        candidates = self._by_name.get(name, [])
        if not candidates:
            raise ResolveError(f"no object named {name}")
        if len({o.oid for o in candidates}) > 1:
            modules = ", ".join(sorted(o.module for o in candidates))
            raise ResolveError(
                f"{name} is defined in several modules with different OIDs ({modules}); use MODULE::{name}"
            )
        return candidates[0]

    def objects_at(self, oid: tuple[int, ...]) -> tuple[Object, ...]:
        """Every loaded object with exactly this OID."""
        self._build()
        return tuple(self._by_oid.get(oid, ()))

    @property
    def problem_list(self) -> tuple[str, ...]:
        """Everything the build could not resolve, in the order met."""
        self._build()
        return tuple(self.problems)

    def index(self, oid: str | tuple[int, ...]) -> Instance | None:
        """Longest-prefix match of an instance OID, with the row index split off (RFC 2578 7.7)."""
        self._build()
        full = parse_oid(oid) if isinstance(oid, str) else oid
        for cut in range(len(full), 0, -1):
            found = self._by_oid.get(full[:cut])
            if found:
                obj = next((o for o in found if o.kind == "object-type"), found[0])
                others = tuple(o for o in found if o is not obj)
                return self._instance(obj, full[cut:], others)
        return None

    def _instance(
        self, obj: Object, suffix: tuple[int, ...], others: tuple[Object, ...]
    ) -> Instance:
        if obj.role == "scalar":
            problem = (
                None if suffix == (0,) else "a scalar object is instanced as .0 (RFC 1212 4.1.6)"
            )
            return Instance(obj, suffix, (), others, problem)
        if obj.role == "column":
            row = next(p for p in self._by_oid[obj.oid[:-1]] if p.role == "row")
            return self._decode_index(obj, row, suffix, others)
        problem = None if not suffix else f"{obj.name} is not a scalar or columnar object"
        return Instance(obj, suffix, (), others, problem)

    def _row_index(self, row: Object) -> tuple[str, tuple[IndexItem, ...]] | None:
        definition = row.definition
        if not isinstance(definition, ObjectType):
            return None
        if definition.augments:
            found = self._lookup(row.module, definition.augments)
            base = None if found is None else self._objects.get((found[0], definition.augments))
            if (
                base is None
                or not isinstance(base.definition, ObjectType)
                or base.definition.augments
            ):
                return None
            return base.module, base.definition.index
        return row.module, definition.index

    def _decode_index(
        self, column: Object, row: Object, suffix: tuple[int, ...], others: tuple[Object, ...]
    ) -> Instance:
        located = self._row_index(row)
        if located is None:
            return Instance(column, suffix, (), others, f"the INDEX of {row.name} cannot be found")
        module, items = located
        values: list[IndexValue] = []
        position = 0
        for item in items:
            info = self._index_type(module, item)
            label = item.name or "index"
            if info is None:
                return Instance(column, suffix, tuple(values), others, f"{label} cannot be typed")
            taken = _take(info, item.implied, suffix[position:])
            if isinstance(taken, str):
                return Instance(column, suffix, tuple(values), others, f"{label}: {taken}")
            value, used = taken
            values.append(IndexValue(item.name, value, suffix[position : position + used]))
            position += used
        left = len(suffix) - position
        problem = None if left == 0 else f"{left} sub-identifiers remain after the INDEX"
        return Instance(column, suffix, tuple(values), others, problem)

    def _index_type(self, module: str, item: IndexItem) -> TypeInfo | None:
        if item.syntax is not None:
            return self.type_info(item.syntax, module)
        found = None if item.name is None else self._lookup(module, item.name)
        if found is None or not isinstance(found[1], ObjectType):
            return None
        return self.type_info(found[1].syntax, found[0])

    def provenance(self, oid: str | tuple[int, ...]) -> Provenance:
        """The document an OID's answer came from, flagging superseded sources such as RFC 1213's groups."""
        full = parse_oid(oid) if isinstance(oid, str) else oid
        hit = self.index(full)
        if hit is None:
            raise ResolveError(f"no object covers {_dotted(full)}")
        obj = hit.object
        entry = bundled.manifest().get(obj.module)
        revision = self._revision(obj.module)
        origin = self._origin.get(obj.module)
        if origin is not None:
            path, digest = origin
            return Provenance(
                obj.module,
                None,
                None,
                note=f"{obj.module} was read from {path}"
                if path
                else f"{obj.module} was added as text",
                revision=revision,
                path=path,
                sha256=digest,
                source="file" if path else "text",
            )
        if entry is None:
            return Provenance(
                obj.module,
                None,
                None,
                note=f"{obj.module} is not bundled: no provenance recorded",
                revision=revision,
                source="text",
            )
        rfc = int(str(entry["rfc"]))
        status = str(entry["status"])
        if obj.module == "RFC1213-MIB":
            for prefix, updater, replacement in _UPDATED_GROUPS:
                if obj.oid[: len(prefix)] == prefix:
                    return Provenance(
                        obj.module,
                        rfc,
                        status,
                        updated_by=(updater,),
                        current_replacement=(replacement,),
                        flagged=True,
                        note=f"{updater} updated this group of RFC 1213 and is obsolete; {replacement} replaces it",
                        revision=revision,
                        sha256=str(entry["sha256"]),
                    )
        return Provenance(obj.module, rfc, status, revision=revision, sha256=str(entry["sha256"]))

    def _revision(self, module: str) -> str | None:
        """The LAST-UPDATED of a loaded module's MODULE-IDENTITY, or None for a module that has none."""
        loaded = self._modules.get(module)
        if loaded is None:
            return None
        for definition in loaded.definitions:
            if isinstance(definition, ModuleIdentity):
                return definition.last_updated
        return None


def _kind_of(definition: Definition) -> str | None:
    if isinstance(definition, ObjectType):
        return "object-type"
    if isinstance(definition, ObjectIdentity):
        return "object-identity"
    if isinstance(definition, ModuleIdentity):
        return "module-identity"
    if isinstance(definition, NotificationType):
        return "notification-type"
    if isinstance(definition, ObjectIdentifierAssignment):
        return "object-identifier"
    if isinstance(definition, ObjectGroup):
        return "object-group"
    if isinstance(definition, NotificationGroup):
        return "notification-group"
    if isinstance(definition, ModuleCompliance):
        return "module-compliance"
    if isinstance(definition, AgentCapabilities):
        return "agent-capabilities"
    return None


def _take(info: TypeInfo, implied: bool, rest: tuple[int, ...]) -> tuple[Value, int] | str:
    """Decode one INDEX component from the front of ``rest`` (RFC 2578 7.7; RFC 1212 4.1.6)."""
    if info.smi_type == "IpAddress":
        if len(rest) < 4 or any(n > 255 for n in rest[:4]):
            return "an IpAddress needs four sub-identifiers, each 0..255"
        return ".".join(str(n) for n in rest[:4]), 4
    if info.smi_type == "NetworkAddress":
        if not rest or rest[0] != 1:
            return "only the IpAddress kind (1) of NetworkAddress is decoded (RFC 1212 4.1.6)"
        if len(rest) < 5 or any(n > 255 for n in rest[1:5]):
            return "a NetworkAddress of kind 1 needs four more sub-identifiers, each 0..255"
        return ".".join(str(n) for n in rest[1:5]), 5
    if info.base == "INTEGER":
        return (rest[0], 1) if rest else "an integer index needs one sub-identifier"
    if info.base in {"OCTET STRING", "BITS"}:
        size = (
            info.sizes[0] if len(info.sizes) == 1 and info.sizes[0][0] == info.sizes[0][1] else None
        )
        fixed = size[0] if size is not None else None
        if isinstance(fixed, int):
            skip, count = 0, fixed
        elif implied:
            skip, count = 0, len(rest)
        elif rest:
            skip, count = 1, rest[0]
        else:
            return "a variable-length string needs a length sub-identifier"
        chunk = rest[skip : skip + count]
        if len(chunk) != count or any(n > 255 for n in chunk):
            return "string octets are missing or above 255"
        return bytes(chunk), skip + count
    if info.base == "OBJECT IDENTIFIER":
        if implied:
            skip, count = 0, len(rest)
        elif rest:
            skip, count = 1, rest[0]
        else:
            return "an object identifier index needs a length sub-identifier"
        chunk = rest[skip : skip + count]
        if len(chunk) != count:
            return "object identifier sub-identifiers are missing"
        return tuple(chunk), skip + count
    return f"a {info.base} value cannot be an index"


_default: list[Mib] = []


def default() -> Mib:
    """The shared ``Mib`` of the bundled modules, built on first use."""
    if not _default:
        _default.append(Mib.with_bundled())
    return _default[0]


def load(path: Path | str, *, imports: Iterable[Module | Path | str] | None = None) -> Mib:
    """Read one module file into a new ``Mib`` that already holds the bundled modules (RFC 2578).

    ``imports`` are further modules the file needs, as parsed ``Module`` objects or paths to read. A file is
    read as UTF-8 and, failing that, as Latin-1, because published modules contain both.
    """
    mib = Mib.with_bundled()
    for extra in imports or ():
        if isinstance(extra, Module):
            mib.add(extra)
        else:
            _add_file(mib, Path(extra))
    _add_file(mib, Path(path))
    return mib


def _add_file(mib: Mib, path: Path) -> None:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    mib.add_text(text, path=str(path), sha256=hashlib.sha256(data).hexdigest())


def resolve(name: str, *, mib: Mib | None = None) -> Object:
    """A name, ``MODULE::name`` or dotted OID to an ``Object`` in the bundled or given ``Mib`` (RFC 2578)."""
    return (mib or default()).resolve(name)


def index(oid: str, *, mib: Mib | None = None) -> Instance | None:
    """Longest-prefix match of an instance OID, with the row index split off (RFC 2578 7.7)."""
    return (mib or default()).index(oid)


def provenance(oid: str, *, mib: Mib | None = None) -> Provenance:
    """Which document an OID came from and whether it has been superseded (design; RFC 1213 and its updates)."""
    return (mib or default()).provenance(oid)
