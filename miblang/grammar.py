"""the RFC 2578 macro forms and the RFC 2579 TEXTUAL-CONVENTION form, kept as syntax rather
than as a tree of dicts.

The parser reads one information module from the tokens ``lexer.lex`` produces. It covers

* the module header, ``IMPORTS`` and (SMIv1 only) ``EXPORTS`` (RFC 2578 3, 3.2, 3.3);
* OBJECT IDENTIFIER assignments (RFC 2578 3.5, 3.6);
* the SMIv2 macros MODULE-IDENTITY, OBJECT-IDENTITY, OBJECT-TYPE, NOTIFICATION-TYPE (RFC 2578
  5 to 8), TEXTUAL-CONVENTION (RFC 2579 2, 3), OBJECT-GROUP, NOTIFICATION-GROUP, MODULE-COMPLIANCE
  and AGENT-CAPABILITIES (RFC 2580 2 to 6);
* the SMIv1 forms: OBJECT-TYPE with ACCESS and the mandatory/optional status values (RFC 1155 6,
  RFC 1212 4) and TRAP-TYPE (RFC 1215 2);
* type assignments, including SEQUENCE and CHOICE, and ``MACRO`` definitions, which are recorded by
  name and skipped (the macros that matter are built in).

Every clause is kept as syntax. Nothing here resolves a name, checks that a DEFVAL fits its SYNTAX,
or decides what an object identifier means: that is the resolver's job (ROADMAP.md, M2).

Strictness: a clause that RFC 2578 or its companions mark as required is required, a clause given
twice is refused, and a STATUS or ACCESS word outside the set the macro defines is refused. Anything
the parser does not understand raises ``ParseError`` with the line and column; it never skips.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .lexer import Token, TokenKind, lex

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = [
    "AgentCapabilities",
    "ComplianceModule",
    "ComplianceObject",
    "DefVal",
    "Definition",
    "IndexItem",
    "MacroDefinition",
    "Module",
    "ModuleCompliance",
    "ModuleIdentity",
    "NotificationGroup",
    "NotificationType",
    "ObjectGroup",
    "ObjectIdentifierAssignment",
    "ObjectIdentity",
    "ObjectType",
    "Oid",
    "OidComponent",
    "ParseError",
    "Revision",
    "SupportsModule",
    "Syntax",
    "TextualConvention",
    "TrapType",
    "TypeAssignment",
    "Variation",
    "module_identity",
    "object_type",
    "parse",
    "parse_module",
]

# Value sets, each from the TYPE NOTATION of the macro that owns it (read through rfclib 2026-11-13).
_STATUS_V2 = frozenset({"current", "deprecated", "obsolete"})  # RFC 2578 2, 2580 2, 2579 2
_STATUS_V1 = frozenset({"mandatory", "optional", "obsolete", "deprecated"})  # RFC 1155 6, 1212 4
_STATUS_CAPABILITIES = frozenset({"current", "obsolete"})  # RFC 2580 2, AGENT-CAPABILITIES
_ACCESS_V2 = frozenset(
    {"not-accessible", "accessible-for-notify", "read-only", "read-write", "read-create"}
)
_ACCESS_V1 = frozenset({"read-only", "read-write", "write-only", "not-accessible"})
_ACCESS_VARIATION = frozenset(
    {
        "not-implemented",
        "accessible-for-notify",
        "read-only",
        "read-write",
        "read-create",
        "write-only",
    }
)
_MAX_SUBID = 2**32 - 1  # RFC 2578 3.5
_MAX_DEPTH = 32
_TEXTUAL = (
    TokenKind.KEYWORD,
    TokenKind.PUNCT,
    TokenKind.IDENT,
    TokenKind.UPPER_IDENT,
    TokenKind.ASSIGN,
    TokenKind.RANGE,
)
_BASE_KEYWORDS = frozenset(
    {
        "NULL",
        "Integer32",
        "Counter32",
        "Counter64",
        "Gauge32",
        "Unsigned32",
        "IpAddress",
        "TimeTicks",
        "Opaque",
        "BOOLEAN",
    }
)


class ParseError(ValueError):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


@dataclass(frozen=True)
class OidComponent:
    """One element of ``{ parent 1 name(2) Module.sym }``."""

    name: str | None
    number: int | None
    module: str | None = None


@dataclass(frozen=True)
class Oid:
    components: tuple[OidComponent, ...]


Bound = int | str  # an integer, or the words MIN and MAX (RFC 2578 11.2 forbids them in SMIv2)


@dataclass(frozen=True)
class Syntax:
    """A type as written. ``base`` is the type name or one of INTEGER, OCTET STRING, OBJECT
    IDENTIFIER, BITS, SEQUENCE OF, SEQUENCE, CHOICE, NULL.

    ``ranges`` hold a value constraint, ``sizes`` a SIZE constraint, each as (low, high) pairs where
    a single value is (n, n). ``named_numbers`` hold INTEGER enumerations and BITS names.
    """

    base: str
    named_numbers: tuple[tuple[str, int], ...] = ()
    ranges: tuple[tuple[Bound, Bound], ...] = ()
    sizes: tuple[tuple[Bound, Bound], ...] = ()
    item_type: str | None = None
    fields: tuple[tuple[str, Syntax], ...] = ()
    tag: str | None = None
    tag_mode: str | None = None


@dataclass(frozen=True)
class DefVal:
    """A DEFVAL value as written; resolving it against the SYNTAX is not this module's job.

    ``kind`` is integer, cstring, hstring, bstring, identifier, keyword (NULL, TRUE, FALSE), bits (a braced, comma separated name
    set, possibly empty) or composite (several tokens, such as ``system 2`` or ``internet 'c0210415'h``,
    held as their texts).
    """

    kind: str
    value: object


@dataclass(frozen=True)
class IndexItem:
    """An INDEX entry: an object name, or (SMIv1, RFC 1212 4) a type."""

    name: str | None
    syntax: Syntax | None = None
    implied: bool = False


@dataclass(frozen=True)
class Revision:
    date: str
    description: str


@dataclass(frozen=True)
class ModuleIdentity:
    name: str
    last_updated: str
    organization: str
    contact_info: str
    description: str
    revisions: tuple[Revision, ...]
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class ObjectIdentity:
    name: str
    status: str
    description: str
    reference: str | None
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class ObjectType:
    """OBJECT-TYPE in either dialect: ``smi`` is 2 when written with MAX-ACCESS (RFC 2578 7) and 1
    when written with ACCESS (RFC 1155 6, RFC 1212 4); ``access`` holds whichever word was written.
    """

    name: str
    smi: int
    syntax: Syntax
    units: str | None
    access: str
    status: str
    description: str | None
    reference: str | None
    index: tuple[IndexItem, ...]
    augments: str | None
    defval: DefVal | None
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class NotificationType:
    name: str
    objects: tuple[str, ...]
    status: str
    description: str
    reference: str | None
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class TrapType:
    """SMIv1 TRAP-TYPE (RFC 1215 2): ``number`` is the specific-trap value."""

    name: str
    enterprise: Oid
    variables: tuple[str, ...]
    description: str | None
    reference: str | None
    number: int
    line: int = 0


@dataclass(frozen=True)
class ObjectIdentifierAssignment:
    name: str
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class TextualConvention:
    name: str
    display_hint: str | None
    status: str
    description: str
    reference: str | None
    syntax: Syntax
    line: int = 0


@dataclass(frozen=True)
class TypeAssignment:
    name: str
    syntax: Syntax
    line: int = 0


@dataclass(frozen=True)
class MacroDefinition:
    """``NAME MACRO ::= BEGIN ... END``: recorded and skipped."""

    name: str
    line: int = 0


@dataclass(frozen=True)
class ObjectGroup:
    name: str
    objects: tuple[str, ...]
    status: str
    description: str
    reference: str | None
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class NotificationGroup:
    name: str
    notifications: tuple[str, ...]
    status: str
    description: str
    reference: str | None
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class ComplianceObject:
    """An ``OBJECT`` refinement inside a MODULE clause."""

    name: str
    syntax: Syntax | None
    write_syntax: Syntax | None
    min_access: str | None
    description: str


@dataclass(frozen=True)
class ComplianceModule:
    """A ``MODULE`` clause. ``name`` is None for the containing module (RFC 2580 2)."""

    name: str | None
    oid: Oid | None
    mandatory_groups: tuple[str, ...]
    groups: tuple[tuple[str, str], ...]  # (group, description)
    objects: tuple[ComplianceObject, ...]


@dataclass(frozen=True)
class ModuleCompliance:
    name: str
    status: str
    description: str
    reference: str | None
    modules: tuple[ComplianceModule, ...]
    oid: Oid
    line: int = 0


@dataclass(frozen=True)
class Variation:
    name: str
    syntax: Syntax | None
    write_syntax: Syntax | None
    access: str | None
    creation_requires: tuple[str, ...]
    defval: DefVal | None
    description: str


@dataclass(frozen=True)
class SupportsModule:
    name: str
    oid: Oid | None
    includes: tuple[str, ...]
    variations: tuple[Variation, ...]


@dataclass(frozen=True)
class AgentCapabilities:
    name: str
    product_release: str
    status: str
    description: str
    reference: str | None
    supports: tuple[SupportsModule, ...]
    oid: Oid
    line: int = 0


Definition = (
    ModuleIdentity
    | ObjectIdentity
    | ObjectType
    | NotificationType
    | TrapType
    | ObjectIdentifierAssignment
    | TextualConvention
    | TypeAssignment
    | MacroDefinition
    | ObjectGroup
    | NotificationGroup
    | ModuleCompliance
    | AgentCapabilities
)


@dataclass(frozen=True)
class Module:
    """One information module. ``smi`` is 1 or 2 when the module's own content settles it, else None
    (a module of only OBJECT IDENTIFIER assignments is neither)."""

    name: str
    smi: int | None
    imports: tuple[tuple[str, tuple[str, ...]], ...]  # (module, symbols), in source order
    exports: tuple[str, ...] | None  # SMIv1 only (RFC 2578 3.3 forbids EXPORTS in SMIv2)
    definitions: tuple[Definition, ...]
    module_oid: Oid | None = None

    def find(self, name: str) -> Definition | None:
        for item in self.definitions:
            if getattr(item, "name", None) == name:
                return item
        return None


class _Parser:
    def __init__(self, tokens: Sequence[Token]) -> None:
        if not tokens:
            raise ParseError("no tokens", 1, 1)
        self.tokens = list(tokens)
        if self.tokens[-1].kind is not TokenKind.EOF:
            last = self.tokens[-1]
            self.tokens.append(Token(TokenKind.EOF, "", last.line, last.column, last.offset))
        self.index = 0

    # -- token plumbing ------------------------------------------------------------------------
    def peek(self, ahead: int = 0) -> Token:
        return self.tokens[min(self.index + ahead, len(self.tokens) - 1)]

    def next(self) -> Token:
        token = self.peek()
        if token.kind is not TokenKind.EOF:
            self.index += 1
        return token

    def error(self, message: str, token: Token | None = None) -> ParseError:
        at = token or self.peek()
        return ParseError(message, at.line, at.column)

    def at(self, text: str, ahead: int = 0) -> bool:
        token = self.peek(ahead)
        return token.kind in _TEXTUAL and token.text == text

    def accept(self, text: str) -> bool:
        if self.at(text):
            self.next()
            return True
        return False

    def expect(self, text: str) -> Token:
        if not self.at(text):
            found = self.peek()
            raise self.error(f"expected {text!r}, found {found.text or 'end of input'!r}")
        return self.next()

    def of_kind(self, kind: TokenKind, what: str) -> Token:
        token = self.peek()
        if token.kind is not kind:
            raise self.error(f"expected {what}, found {token.text or 'end of input'!r}")
        return self.next()

    def word(self) -> str:
        return self.of_kind(TokenKind.IDENT, "a lower-case identifier").text

    def text(self) -> str:
        return self.of_kind(TokenKind.CSTRING, "a quoted string").text

    def number(self) -> int:
        token = self.of_kind(TokenKind.NUMBER, "a number")
        try:
            return int(token.text)
        except ValueError as exc:
            raise self.error("number too large", token) from exc

    def signed(self) -> int:
        negative = self.accept("-")
        value = self.number()
        return -value if negative else value

    # -- small productions ---------------------------------------------------------------------
    def oid(self) -> Oid:
        self.expect("{")
        parts: list[OidComponent] = []
        while not self.at("}"):
            token = self.peek()
            if token.kind is TokenKind.IDENT:
                self.next()
                number = None
                if self.accept("("):
                    number = self.number()
                    self.expect(")")
                parts.append(OidComponent(token.text, number))
            elif token.kind is TokenKind.UPPER_IDENT and self.at(".", 1):
                self.next()
                self.next()
                parts.append(OidComponent(self.word(), None, token.text))
            elif token.kind is TokenKind.NUMBER:
                number = self.number()
                if number > _MAX_SUBID:
                    raise self.error("sub-identifier exceeds 2^32-1 (RFC 2578 3.5)", token)
                parts.append(OidComponent(None, number))
            else:
                raise self.error(
                    f"unexpected {token.text or 'end of input'!r} in an OBJECT IDENTIFIER value"
                )
        if not parts:
            raise self.error("empty OBJECT IDENTIFIER value")
        self.expect("}")
        return Oid(tuple(parts))

    def name_list(self) -> tuple[str, ...]:
        self.expect("{")
        names = [self.word()]
        while self.accept(","):
            names.append(self.word())
        self.expect("}")
        return tuple(names)

    def bound(self) -> Bound:
        if self.accept("MIN"):
            return "MIN"
        if self.accept("MAX"):
            return "MAX"
        negative = self.accept("-")
        token = self.next()
        radix = {TokenKind.NUMBER: 10, TokenKind.HSTRING: 16, TokenKind.BSTRING: 2}.get(token.kind)
        if radix is None:
            raise self.error(
                f"expected a range bound, found {token.text or 'end of input'!r}", token
            )
        try:
            value = int(token.text, radix)
        except ValueError as exc:
            raise self.error("not a usable number", token) from exc
        return -value if negative else value

    def range_list(self) -> tuple[tuple[Bound, Bound], ...]:
        items: list[tuple[Bound, Bound]] = []
        while True:
            low = self.bound()
            high = low
            if self.peek().kind is TokenKind.RANGE:
                self.next()
                high = self.bound()
            items.append((low, high))
            if not self.accept("|"):
                return tuple(items)

    def named_numbers(self) -> tuple[tuple[str, int], ...]:
        self.expect("{")
        items: list[tuple[str, int]] = []
        while True:
            name = self.word()
            self.expect("(")
            items.append((name, self.signed()))
            self.expect(")")
            if not self.accept(","):
                break
        self.expect("}")
        return tuple(items)

    def constraint(self) -> tuple[tuple[tuple[Bound, Bound], ...], tuple[tuple[Bound, Bound], ...]]:
        """``( ranges )`` or ``( SIZE ( ranges ) )``: returns (ranges, sizes)."""
        self.expect("(")
        if self.accept("SIZE"):
            self.expect("(")
            sizes = self.range_list()
            self.expect(")")
            self.expect(")")
            return (), sizes
        ranges = self.range_list()
        self.expect(")")
        return ranges, ()

    def syntax(self, depth: int = 0) -> Syntax:
        if depth > _MAX_DEPTH:
            raise self.error("types nested too deeply")
        tag = mode = None
        if self.accept("["):
            klass = ""
            for word in ("APPLICATION", "UNIVERSAL", "PRIVATE"):
                if self.accept(word):
                    klass = word + " "
                    break
            tag = f"{klass}{self.number()}"
            self.expect("]")
            for word in ("IMPLICIT", "EXPLICIT"):
                if self.accept(word):
                    mode = word
        token = self.next()
        base = token.text
        named: tuple[tuple[str, int], ...] = ()
        item_type = None
        fields: tuple[tuple[str, Syntax], ...] = ()
        if token.kind is TokenKind.KEYWORD:
            if base == "INTEGER":
                if self.at("{"):
                    named = self.named_numbers()
            elif base == "OCTET":
                self.expect("STRING")
                base = "OCTET STRING"
            elif base == "OBJECT":
                self.expect("IDENTIFIER")
                base = "OBJECT IDENTIFIER"
            elif base == "BITS":
                named = self.named_numbers()
            elif base == "SEQUENCE":
                if self.accept("OF"):
                    base = "SEQUENCE OF"
                    item = self.next()
                    if item.kind not in (TokenKind.UPPER_IDENT, TokenKind.KEYWORD):
                        raise self.error("expected a type name after SEQUENCE OF", item)
                    item_type = item.text
                else:
                    fields = self.fields(depth)
            elif base == "CHOICE":
                fields = self.fields(depth)
            elif base not in _BASE_KEYWORDS:
                raise self.error(f"{base!r} does not begin a type", token)
        elif token.kind is not TokenKind.UPPER_IDENT:
            raise self.error(f"expected a type, found {token.text or 'end of input'!r}", token)
        ranges: tuple[tuple[Bound, Bound], ...] = ()
        sizes: tuple[tuple[Bound, Bound], ...] = ()
        if self.at("("):
            ranges, sizes = self.constraint()
        return Syntax(base, named, ranges, sizes, item_type, fields, tag, mode)

    def fields(self, depth: int) -> tuple[tuple[str, Syntax], ...]:
        self.expect("{")
        items: list[tuple[str, Syntax]] = []
        while True:
            name = self.word()
            items.append((name, self.syntax(depth + 1)))
            if not self.accept(","):
                break
        self.expect("}")
        return tuple(items)

    def defval(self) -> DefVal:
        self.expect("{")
        start = self.index
        depth = 1
        while depth:
            token = self.next()
            if token.kind is TokenKind.EOF:
                raise self.error("unterminated DEFVAL", token)
            if self.is_punct(token, "{"):
                depth += 1
            elif self.is_punct(token, "}"):
                depth -= 1
        inner = self.tokens[start : self.index - 1]
        if not inner:
            return DefVal("bits", ())
        if len(inner) == 1:
            only = inner[0]
            kinds = {
                TokenKind.NUMBER: "integer",
                TokenKind.CSTRING: "cstring",
                TokenKind.HSTRING: "hstring",
                TokenKind.BSTRING: "bstring",
                TokenKind.IDENT: "identifier",
                TokenKind.KEYWORD: "keyword",
            }
            if only.kind in kinds:
                value: object = int(only.text) if only.kind is TokenKind.NUMBER else only.text
                return DefVal(kinds[only.kind], value)
        if len(inner) == 2 and self.is_punct(inner[0], "-") and inner[1].kind is TokenKind.NUMBER:
            return DefVal("integer", -int(inner[1].text))
        if self.is_punct(inner[0], "{") and self.is_punct(inner[-1], "}"):
            names = [t.text for t in inner[1:-1] if not self.is_punct(t, ",")]
            return DefVal("bits", tuple(names))
        return DefVal("composite", tuple(t.text for t in inner))

    @staticmethod
    def is_punct(token: Token, text: str) -> bool:
        return token.kind is TokenKind.PUNCT and token.text == text

    def index_clause(self) -> tuple[IndexItem, ...]:
        self.expect("{")
        items: list[IndexItem] = []
        while True:
            implied = self.accept("IMPLIED")
            if self.peek().kind is TokenKind.IDENT:
                items.append(IndexItem(self.word(), None, implied))
            else:
                items.append(IndexItem(None, self.syntax(), implied))
            if not self.accept(","):
                break
        self.expect("}")
        return tuple(items)

    def augments(self) -> str:
        self.expect("{")
        name = self.word()
        self.expect("}")
        return name

    # -- clause collection ---------------------------------------------------------------------
    def collect(self, handlers: dict[str, Callable[[], object]]) -> dict[str, object]:
        found: dict[str, object] = {}
        while self.peek().kind is TokenKind.KEYWORD and self.peek().text in handlers:
            token = self.next()
            if token.text in found:
                raise self.error(f"{token.text} given twice", token)
            found[token.text] = handlers[token.text]()
        return found

    def require(
        self, found: dict[str, object], names: Sequence[str], macro: str, at: Token
    ) -> None:
        missing = [n for n in names if n not in found]
        if missing:
            raise self.error(f"{macro} lacks {', '.join(missing)}", at)

    def status(self, allowed: frozenset[str], macro: str) -> Callable[[], str]:
        def read() -> str:
            token = self.peek()
            value = self.word()
            if value not in allowed:
                raise self.error(f"STATUS {value!r} is not valid in {macro}", token)
            return value

        return read

    # -- definitions ---------------------------------------------------------------------------
    def definition(self) -> Definition:
        first = self.peek()
        after = self.peek(1)
        if first.kind in (TokenKind.UPPER_IDENT, TokenKind.KEYWORD) and (
            after.kind is TokenKind.ASSIGN
            or (after.kind is TokenKind.UPPER_IDENT and after.text == "MACRO")
        ):
            return self.type_definition()
        if first.kind is not TokenKind.IDENT:
            raise self.error(f"expected a definition, found {first.text or 'end of input'!r}")
        self.next()
        macro = self.peek()
        if macro.kind is TokenKind.KEYWORD and macro.text in self.MACROS:
            self.next()
            return self.MACROS[macro.text](self, first.text, first)
        if self.at("OBJECT") and self.at("IDENTIFIER", 1):
            self.next()
            self.next()
            self.expect("::=")
            return ObjectIdentifierAssignment(first.text, self.oid(), first.line)
        raise self.error(
            f"{first.text!r} is followed by {macro.text or 'end of input'!r}, which starts no "
            "supported definition",
            macro,
        )

    def type_definition(self) -> Definition:
        name = self.next()
        if self.peek().kind is TokenKind.UPPER_IDENT and self.peek().text == "MACRO":
            self.next()
            self.expect("::=")
            self.expect("BEGIN")
            while not self.at("END"):
                if self.next().kind is TokenKind.EOF:
                    raise self.error(f"unterminated MACRO {name.text}", name)
            self.next()
            return MacroDefinition(name.text, name.line)
        self.expect("::=")
        if self.at("TEXTUAL-CONVENTION"):
            self.next()
            return self.textual_convention(name)
        return TypeAssignment(name.text, self.syntax(), name.line)

    def textual_convention(self, name: Token) -> TextualConvention:
        got = self.collect(
            {
                "DISPLAY-HINT": self.text,
                "STATUS": self.status(_STATUS_V2, "TEXTUAL-CONVENTION"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
                "SYNTAX": self.syntax,
            }
        )
        self.require(got, ("STATUS", "DESCRIPTION", "SYNTAX"), "TEXTUAL-CONVENTION", name)
        return TextualConvention(
            name.text,
            _str(got.get("DISPLAY-HINT")),
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            _syn(got["SYNTAX"]),
            name.line,
        )

    def module_identity_def(self, name: str, at: Token) -> ModuleIdentity:
        header = self.collect(
            {
                "LAST-UPDATED": self.text,
                "ORGANIZATION": self.text,
                "CONTACT-INFO": self.text,
                "DESCRIPTION": self.text,
            }
        )
        # REVISION clauses repeat and pair with a DESCRIPTION, so they are read apart (RFC 2578 2).
        revisions: list[Revision] = []
        # The header clauses come first, then zero or more REVISION/DESCRIPTION pairs.
        while self.at("REVISION"):
            self.next()
            date = self.text()
            self.expect("DESCRIPTION")
            revisions.append(Revision(date, self.text()))
        self.require(
            header,
            ("LAST-UPDATED", "ORGANIZATION", "CONTACT-INFO", "DESCRIPTION"),
            "MODULE-IDENTITY",
            at,
        )
        self.expect("::=")
        return ModuleIdentity(
            name,
            str(header["LAST-UPDATED"]),
            str(header["ORGANIZATION"]),
            str(header["CONTACT-INFO"]),
            str(header["DESCRIPTION"]),
            tuple(revisions),
            self.oid(),
            at.line,
        )

    def object_identity_def(self, name: str, at: Token) -> ObjectIdentity:
        got = self.collect(
            {
                "STATUS": self.status(_STATUS_V2, "OBJECT-IDENTITY"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("STATUS", "DESCRIPTION"), "OBJECT-IDENTITY", at)
        self.expect("::=")
        return ObjectIdentity(
            name,
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            self.oid(),
            at.line,
        )

    def object_type_def(self, name: str, at: Token) -> ObjectType:
        got = self.collect(
            {
                "SYNTAX": self.syntax,
                "UNITS": self.text,
                "MAX-ACCESS": self.word,
                "ACCESS": self.word,
                "STATUS": self.word,
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
                "INDEX": self.index_clause,
                "AUGMENTS": self.augments,
                "DEFVAL": self.defval,
            }
        )
        if "MAX-ACCESS" in got and "ACCESS" in got:
            raise self.error("OBJECT-TYPE has both MAX-ACCESS and ACCESS", at)
        if "MAX-ACCESS" not in got and "ACCESS" not in got:
            raise self.error("OBJECT-TYPE lacks MAX-ACCESS (SMIv2) or ACCESS (SMIv1)", at)
        smi = 2 if "MAX-ACCESS" in got else 1
        self.require(got, ("SYNTAX", "STATUS"), "OBJECT-TYPE", at)
        access = str(got["MAX-ACCESS" if smi == 2 else "ACCESS"])
        if access not in (_ACCESS_V2 if smi == 2 else _ACCESS_V1):
            raise self.error(f"access {access!r} is not valid in SMIv{smi} OBJECT-TYPE", at)
        status = str(got["STATUS"])
        if status not in (_STATUS_V2 if smi == 2 else _STATUS_V1):
            raise self.error(f"STATUS {status!r} is not valid in SMIv{smi} OBJECT-TYPE", at)
        if smi == 2 and "DESCRIPTION" not in got:
            raise self.error("SMIv2 OBJECT-TYPE lacks DESCRIPTION (RFC 2578 2)", at)
        if "INDEX" in got and "AUGMENTS" in got:
            raise self.error("OBJECT-TYPE has both INDEX and AUGMENTS", at)
        self.expect("::=")
        index = got.get("INDEX")
        defval = got.get("DEFVAL")
        return ObjectType(
            name,
            smi,
            _syn(got["SYNTAX"]),
            _str(got.get("UNITS")),
            access,
            status,
            _str(got.get("DESCRIPTION")),
            _str(got.get("REFERENCE")),
            index if isinstance(index, tuple) else (),
            _str(got.get("AUGMENTS")),
            defval if isinstance(defval, DefVal) else None,
            self.oid(),
            at.line,
        )

    def notification_type_def(self, name: str, at: Token) -> NotificationType:
        got = self.collect(
            {
                "OBJECTS": self.name_list,
                "STATUS": self.status(_STATUS_V2, "NOTIFICATION-TYPE"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("STATUS", "DESCRIPTION"), "NOTIFICATION-TYPE", at)
        self.expect("::=")
        objects = got.get("OBJECTS")
        return NotificationType(
            name,
            objects if isinstance(objects, tuple) else (),
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            self.oid(),
            at.line,
        )

    def trap_type_def(self, name: str, at: Token) -> TrapType:
        def enterprise() -> Oid:
            if self.at("{"):
                return self.oid()
            return Oid((OidComponent(self.word(), None),))

        got = self.collect(
            {
                "ENTERPRISE": enterprise,
                "VARIABLES": self.name_list,
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("ENTERPRISE",), "TRAP-TYPE", at)
        self.expect("::=")
        variables = got.get("VARIABLES")
        enterprise_value = got["ENTERPRISE"]
        if not isinstance(enterprise_value, Oid):
            raise self.error("internal: ENTERPRISE", at)
        return TrapType(
            name,
            enterprise_value,
            variables if isinstance(variables, tuple) else (),
            _str(got.get("DESCRIPTION")),
            _str(got.get("REFERENCE")),
            self.number(),
            at.line,
        )

    def object_group_def(self, name: str, at: Token) -> ObjectGroup:
        got = self.collect(
            {
                "OBJECTS": self.name_list,
                "STATUS": self.status(_STATUS_V2, "OBJECT-GROUP"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("OBJECTS", "STATUS", "DESCRIPTION"), "OBJECT-GROUP", at)
        self.expect("::=")
        objects = got["OBJECTS"]
        return ObjectGroup(
            name,
            objects if isinstance(objects, tuple) else (),
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            self.oid(),
            at.line,
        )

    def notification_group_def(self, name: str, at: Token) -> NotificationGroup:
        got = self.collect(
            {
                "NOTIFICATIONS": self.name_list,
                "STATUS": self.status(_STATUS_V2, "NOTIFICATION-GROUP"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("NOTIFICATIONS", "STATUS", "DESCRIPTION"), "NOTIFICATION-GROUP", at)
        self.expect("::=")
        notes = got["NOTIFICATIONS"]
        return NotificationGroup(
            name,
            notes if isinstance(notes, tuple) else (),
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            self.oid(),
            at.line,
        )

    def module_name_and_oid(self) -> tuple[str | None, Oid | None]:
        name = None
        oid = None
        if self.peek().kind is TokenKind.UPPER_IDENT:
            name = self.next().text
            if self.at("{"):
                oid = self.oid()
        return name, oid

    def module_compliance_def(self, name: str, at: Token) -> ModuleCompliance:
        got = self.collect(
            {
                "STATUS": self.status(_STATUS_V2, "MODULE-COMPLIANCE"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("STATUS", "DESCRIPTION"), "MODULE-COMPLIANCE", at)
        modules: list[ComplianceModule] = []
        while self.accept("MODULE"):
            mod_name, mod_oid = self.module_name_and_oid()
            mandatory: tuple[str, ...] = ()
            if self.accept("MANDATORY-GROUPS"):
                mandatory = self.name_list()
            groups: list[tuple[str, str]] = []
            objects: list[ComplianceObject] = []
            while True:
                if self.accept("GROUP"):
                    group = self.word()
                    self.expect("DESCRIPTION")
                    groups.append((group, self.text()))
                elif self.accept("OBJECT"):
                    objects.append(self.compliance_object())
                else:
                    break
            modules.append(
                ComplianceModule(mod_name, mod_oid, mandatory, tuple(groups), tuple(objects))
            )
        self.expect("::=")
        return ModuleCompliance(
            name,
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            tuple(modules),
            self.oid(),
            at.line,
        )

    def compliance_object(self) -> ComplianceObject:
        name = self.word()
        got = self.collect(
            {
                "SYNTAX": self.syntax,
                "WRITE-SYNTAX": self.syntax,
                "MIN-ACCESS": self.word,
                "DESCRIPTION": self.text,
            }
        )
        if "DESCRIPTION" not in got:
            raise self.error(f"OBJECT {name} in MODULE-COMPLIANCE lacks DESCRIPTION")
        access = _str(got.get("MIN-ACCESS"))
        if access is not None and access not in _ACCESS_V2:
            raise self.error(f"MIN-ACCESS {access!r} is not valid")
        syntax = got.get("SYNTAX")
        write = got.get("WRITE-SYNTAX")
        return ComplianceObject(
            name,
            syntax if isinstance(syntax, Syntax) else None,
            write if isinstance(write, Syntax) else None,
            access,
            str(got["DESCRIPTION"]),
        )

    def agent_capabilities_def(self, name: str, at: Token) -> AgentCapabilities:
        got = self.collect(
            {
                "PRODUCT-RELEASE": self.text,
                "STATUS": self.status(_STATUS_CAPABILITIES, "AGENT-CAPABILITIES"),
                "DESCRIPTION": self.text,
                "REFERENCE": self.text,
            }
        )
        self.require(got, ("PRODUCT-RELEASE", "STATUS", "DESCRIPTION"), "AGENT-CAPABILITIES", at)
        supports: list[SupportsModule] = []
        while self.accept("SUPPORTS"):
            mod_name, mod_oid = self.module_name_and_oid()
            if mod_name is None:
                raise self.error("SUPPORTS needs a module name")
            self.expect("INCLUDES")
            includes = self.name_list()
            variations: list[Variation] = []
            while self.accept("VARIATION"):
                variations.append(self.variation())
            supports.append(SupportsModule(mod_name, mod_oid, includes, tuple(variations)))
        self.expect("::=")
        return AgentCapabilities(
            name,
            str(got["PRODUCT-RELEASE"]),
            str(got["STATUS"]),
            str(got["DESCRIPTION"]),
            _str(got.get("REFERENCE")),
            tuple(supports),
            self.oid(),
            at.line,
        )

    def variation(self) -> Variation:
        name = self.word()
        got = self.collect(
            {
                "SYNTAX": self.syntax,
                "WRITE-SYNTAX": self.syntax,
                "ACCESS": self.word,
                "CREATION-REQUIRES": self.name_list,
                "DEFVAL": self.defval,
                "DESCRIPTION": self.text,
            }
        )
        if "DESCRIPTION" not in got:
            raise self.error(f"VARIATION {name} lacks DESCRIPTION")
        access = _str(got.get("ACCESS"))
        if access is not None and access not in _ACCESS_VARIATION:
            raise self.error(f"ACCESS {access!r} is not valid in a VARIATION")
        syntax = got.get("SYNTAX")
        write = got.get("WRITE-SYNTAX")
        creation = got.get("CREATION-REQUIRES")
        defval = got.get("DEFVAL")
        return Variation(
            name,
            syntax if isinstance(syntax, Syntax) else None,
            write if isinstance(write, Syntax) else None,
            access,
            creation if isinstance(creation, tuple) else (),
            defval if isinstance(defval, DefVal) else None,
            str(got["DESCRIPTION"]),
        )

    MACROS: ClassVar[dict[str, Callable[[_Parser, str, Token], Definition]]] = {
        "MODULE-IDENTITY": module_identity_def,
        "OBJECT-IDENTITY": object_identity_def,
        "OBJECT-TYPE": object_type_def,
        "NOTIFICATION-TYPE": notification_type_def,
        "TRAP-TYPE": trap_type_def,
        "OBJECT-GROUP": object_group_def,
        "NOTIFICATION-GROUP": notification_group_def,
        "MODULE-COMPLIANCE": module_compliance_def,
        "AGENT-CAPABILITIES": agent_capabilities_def,
    }

    # -- the module ----------------------------------------------------------------------------
    def module(self) -> Module:
        name = self.of_kind(TokenKind.UPPER_IDENT, "a module name")
        module_oid = self.oid() if self.at("{") else None
        self.expect("DEFINITIONS")
        if (self.peek().kind is TokenKind.UPPER_IDENT and self.at("TAGS", 1)) or (
            (self.at("EXPLICIT") or self.at("IMPLICIT")) and self.at("TAGS", 1)
        ):
            self.next()
            self.next()
        self.expect("::=")
        self.expect("BEGIN")
        exports: tuple[str, ...] | None = None
        if self.accept("EXPORTS"):
            exports = self.symbol_list_until_semicolon()
        imports: list[tuple[str, tuple[str, ...]]] = []
        if self.accept("IMPORTS"):
            imports = self.imports()
        definitions: list[Definition] = []
        while not self.at("END"):
            if self.peek().kind is TokenKind.EOF:
                raise self.error(f"module {name.text} has no END")
            definitions.append(self.definition())
        self.next()
        if self.peek().kind is not TokenKind.EOF:
            raise self.error("text after END")
        return Module(
            name.text,
            _infer_smi(name.text, imports, definitions),
            tuple(imports),
            exports,
            tuple(definitions),
            module_oid,
        )

    def symbol(self) -> str:
        token = self.next()
        if token.kind not in (TokenKind.IDENT, TokenKind.UPPER_IDENT, TokenKind.KEYWORD):
            raise self.error(f"expected a symbol, found {token.text or 'end of input'!r}", token)
        return token.text

    def symbol_list_until_semicolon(self) -> tuple[str, ...]:
        symbols: list[str] = []
        if self.accept(";"):
            return ()
        while True:
            symbols.append(self.symbol())
            if self.accept(";"):
                return tuple(symbols)
            self.expect(",")

    def imports(self) -> list[tuple[str, tuple[str, ...]]]:
        result: list[tuple[str, tuple[str, ...]]] = []
        symbols: list[str] = []
        while True:
            symbols.append(self.symbol())
            if self.accept(","):
                continue
            self.expect("FROM")
            module = self.of_kind(TokenKind.UPPER_IDENT, "a module name").text
            if self.at("{"):
                self.oid()  # ASN.1 allows an identifying OID after the module name; it is not kept
            result.append((module, tuple(symbols)))
            symbols = []
            if self.accept(";"):
                return result


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _syn(value: object) -> Syntax:
    if not isinstance(value, Syntax):
        raise TypeError("internal: expected Syntax")
    return value


def _infer_smi(
    name: str, imports: Sequence[tuple[str, tuple[str, ...]]], definitions: Sequence[Definition]
) -> int | None:
    """The SMI version the module's own content settles, or None."""
    for item in definitions:
        if isinstance(item, ObjectType):
            return item.smi
        if isinstance(
            item,
            ModuleIdentity
            | NotificationType
            | TextualConvention
            | ObjectGroup
            | NotificationGroup
            | ModuleCompliance
            | AgentCapabilities
            | ObjectIdentity,
        ):
            return 2
        if isinstance(item, TrapType):
            return 1
    sources = {module for module, _ in imports} | {name}
    if sources & {"SNMPv2-SMI", "SNMPv2-TC", "SNMPv2-CONF"}:
        return 2
    if sources & {"RFC1155-SMI", "RFC-1212", "RFC-1215"}:
        return 1
    return None


def parse_module(tokens: Sequence[Token]) -> Module:
    """Parse the tokens of one information module (RFC 2578 3; SMIv1 per RFC 1155 6).

    The module is ``Name DEFINITIONS ::= BEGIN [EXPORTS] [IMPORTS] definitions END``. Raises
    ``ParseError`` on anything outside the forms listed in this module's docstring.
    """
    return _Parser(tokens).module()


def parse(text: str, *, max_length: int = 5_000_000, strict_ascii: bool = False) -> Module:
    """Lex and parse the text of one information module (RFC 2578 3)."""
    return parse_module(lex(text, max_length=max_length, strict_ascii=strict_ascii))


def module_identity(tokens: Sequence[Token]) -> ModuleIdentity:
    """Parse one ``descriptor MODULE-IDENTITY ... ::= { ... }`` invocation (RFC 2578 5).

    ``tokens`` begin at the descriptor. Text after the invocation is ignored, so a caller can pass a
    whole module's tokens from the descriptor onward.
    """
    parser = _Parser(tokens)
    found = parser.definition()
    if not isinstance(found, ModuleIdentity):
        raise parser.error("not a MODULE-IDENTITY invocation", tokens[0])
    return found


def object_type(tokens: Sequence[Token]) -> ObjectType:
    """Parse one ``descriptor OBJECT-TYPE ... ::= { ... }`` invocation (RFC 2578 7; the SMIv1
    form of RFC 1155 6 and RFC 1212 4 when it is written with ACCESS).

    ``tokens`` begin at the descriptor. Text after the invocation is ignored.
    """
    parser = _Parser(tokens)
    found = parser.definition()
    if not isinstance(found, ObjectType):
        raise parser.error("not an OBJECT-TYPE invocation", tokens[0])
    return found
