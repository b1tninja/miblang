"""the comment, quoting, OID-literal and continuation rules every macro form sits inside.

``lex`` turns the text of an information module into tokens. It knows nothing about macros:
the grammar module consumes what it produces.

The rules come from three places, each cited where it is applied:

* RFC 2578 section 3.1.1 (character, binary and hexadecimal strings), 3.4 (comments) and 3.7
  (reserved keywords), read through rfclib on 2026-11-13.
* Rec. ITU-T X.680 (02/2021) clause 12.3 for identifiers (letters, digits and hyphens; a hyphen is
  never the last character and never directly followed by another), read through itulib with
  ``edition="X.680"`` (the itulib tools default to X.690, so the edition must be passed).
* SMIv1 (RFC 1155, RFC 1212, RFC 1215) adds no lexical item: its macros use the same strings,
  numbers and comments, so one lexer serves both.

Two deliberate readings, both recorded in ROADMAP.md:

* A comment runs to the next pair of adjacent hyphens or the end of the line (RFC 2578 3.4). A run of
  hyphens is therefore read pair by pair, exactly as the text says.
* A quote character cannot occur inside a character string (RFC 2578 3.1.1), so ``""`` is an empty
  string followed by another string, not an escaped quote.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "RESERVED",
    "LexError",
    "Token",
    "TokenKind",
    "lex",
]

# RFC 2578 section 3.7 paragraph 2, verbatim apart from the hyphenation of MODULE-IDENTITY across a
# line break in the RFC text. tests/fixtures/rfc2578_3_7.txt holds the RFC text and a test compares.
RESERVED: frozenset[str] = frozenset(
    """
    ABSENT ACCESS AGENT-CAPABILITIES ANY APPLICATION AUGMENTS BEGIN
    BIT BITS BOOLEAN BY CHOICE COMPONENT COMPONENTS CONTACT-INFO
    CREATION-REQUIRES Counter32 Counter64 DEFAULT DEFINED
    DEFINITIONS DEFVAL DESCRIPTION DISPLAY-HINT END ENUMERATED
    ENTERPRISE EXPLICIT EXPORTS EXTERNAL FALSE FROM GROUP Gauge32
    IDENTIFIER IMPLICIT IMPLIED IMPORTS INCLUDES INDEX INTEGER
    Integer32 IpAddress LAST-UPDATED MANDATORY-GROUPS MAX MAX-ACCESS
    MIN MIN-ACCESS MINUS-INFINITY MODULE MODULE-COMPLIANCE MODULE-IDENTITY
    NOTIFICATION-GROUP NOTIFICATION-TYPE NOTIFICATIONS NULL
    OBJECT OBJECT-GROUP OBJECT-IDENTITY OBJECT-TYPE OBJECTS OCTET OF
    OPTIONAL ORGANIZATION Opaque PLUS-INFINITY PRESENT PRIVATE
    PRODUCT-RELEASE REAL REFERENCE REVISION SEQUENCE SET SIZE STATUS
    STRING SUPPORTS SYNTAX TAGS TEXTUAL-CONVENTION TRAP-TYPE TRUE
    TimeTicks UNITS UNIVERSAL Unsigned32 VARIABLES VARIATION WITH
    WRITE-SYNTAX
    """.split()  # noqa: SIM905 - kept as the RFC lays it out so a diff against the fixture is readable
)


class TokenKind(Enum):
    IDENT = "ident"  # initial lower-case letter: a value or object name
    UPPER_IDENT = "upper-ident"  # initial upper-case letter: a type, module or macro name
    KEYWORD = "keyword"  # a word in RESERVED
    NUMBER = "number"
    CSTRING = "cstring"  # text is the content between the quotes
    BSTRING = "bstring"  # text is the binary digits
    HSTRING = "hstring"  # text is the hexadecimal digits
    PUNCT = "punct"
    ASSIGN = "assign"  # ::=
    RANGE = "range"  # ..
    EOF = "eof"


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    text: str
    line: int  # 1-based
    column: int  # 1-based
    offset: int  # 0-based index into the source text


class LexError(ValueError):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
_NUMBER = re.compile(r"[0-9]+")
_SPACE = re.compile(r"[ \t\r\n\f\v]+")
_BAD_ASCII = re.compile(r"[^\t\n\r\x20-\x7e]")
_BAD_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PUNCT = frozenset("{}()[],;|.-")


def lex(text: str, *, max_length: int = 5_000_000, strict_ascii: bool = False) -> list[Token]:
    """Tokenise an information module (RFC 2578 sections 3.1.1, 3.4 and 3.7).

    The result always ends with an ``EOF`` token. Unknown characters raise ``LexError`` and are
    never skipped. Input longer than ``max_length`` is refused before scanning.

    ``strict_ascii=True`` enforces RFC 2578 3.1.1 ("any 7-bit displayable ASCII characters") inside
    character strings. The default, ``False``, admits non-ASCII text inside strings because
    published modules contain it, but NUL and other control characters (other than tab, CR and LF)
    are always refused. A leading byte order mark is refused, not skipped.
    """
    if len(text) > max_length:
        raise LexError(f"input of {len(text)} characters exceeds max_length {max_length}", 1, 1)
    if text.startswith("﻿"):
        raise LexError("byte order mark at start of input", 1, 1)
    line_starts = [0]
    line_starts.extend(i + 1 for i, ch in enumerate(text) if ch == "\n")

    def where(offset: int) -> tuple[int, int]:
        row = bisect_right(line_starts, offset) - 1
        return row + 1, offset - line_starts[row] + 1

    def fail(message: str, offset: int) -> LexError:
        line, column = where(offset)
        return LexError(message, line, column)

    def make(kind: TokenKind, value: str, offset: int) -> Token:
        line, column = where(offset)
        return Token(kind, value, line, column, offset)

    bad_in_string = _BAD_ASCII if strict_ascii else _BAD_CONTROL
    tokens: list[Token] = []
    pos = 0
    end = len(text)
    while pos < end:
        ch = text[pos]
        if ch in " \t\r\n\f\v":
            space = _SPACE.match(text, pos)
            if space is None:
                raise fail("internal: whitespace not matched", pos)
            pos = space.end()
            continue
        if text.startswith("--", pos):
            # RFC 2578 3.4: ends at the next pair of adjacent hyphens or at end of line.
            stop_pair = text.find("--", pos + 2)
            stop_line = end
            for terminator in ("\n", "\r"):
                found = text.find(terminator, pos + 2)
                if found != -1:
                    stop_line = min(stop_line, found)
            pos = stop_pair + 2 if stop_pair != -1 and stop_pair < stop_line else stop_line
            continue
        if ch.isascii() and ch.isalpha():
            word_match = _WORD.match(text, pos)
            if word_match is None:
                raise fail("internal: word not matched", pos)
            word = word_match.group()
            # X.680 12.3: a hyphen is not the last character and is not followed by another
            # hyphen. A double hyphen therefore ends the word and begins a comment.
            double = word.find("--")
            if double != -1:
                word = word[:double]
            if word.endswith("-"):
                raise fail(f"identifier {word!r} ends in a hyphen", pos)
            if word in RESERVED:
                kind = TokenKind.KEYWORD
            elif word[0].isupper():
                kind = TokenKind.UPPER_IDENT
            else:
                kind = TokenKind.IDENT
            tokens.append(make(kind, word, pos))
            pos += len(word)
            continue
        if ch.isascii() and ch.isdigit():
            number = _NUMBER.match(text, pos)
            if number is None:
                raise fail("internal: number not matched", pos)
            tokens.append(make(TokenKind.NUMBER, number.group(), pos))
            pos = number.end()
            continue
        if ch == '"':
            close = text.find('"', pos + 1)
            if close == -1:
                raise fail("unterminated character string", pos)
            body = text[pos + 1 : close]
            bad = bad_in_string.search(body)
            if bad is not None:
                raise fail(
                    f"character {bad.group()!r} not allowed in a character string",
                    pos + 1 + bad.start(),
                )
            tokens.append(make(TokenKind.CSTRING, body, pos))
            pos = close + 1
            continue
        if ch == "'":
            close = text.find("'", pos + 1)
            if close == -1 or close + 1 >= end or text[close + 1] not in "BbHh":
                raise fail("quote does not begin a binary or hexadecimal string", pos)
            body = text[pos + 1 : close]
            if text[close + 1] in "Bb":
                if body.strip("01") or len(body) % 8:
                    raise fail("binary string needs a multiple of eight 0/1 digits", pos)
                tokens.append(make(TokenKind.BSTRING, body, pos))
            else:
                if body.strip("0123456789abcdefABCDEF") or len(body) % 2:
                    raise fail("hexadecimal string needs an even number of hex digits", pos)
                tokens.append(make(TokenKind.HSTRING, body, pos))
            pos = close + 2
            continue
        if text.startswith("::=", pos):
            tokens.append(make(TokenKind.ASSIGN, "::=", pos))
            pos += 3
            continue
        if text.startswith("..", pos):
            tokens.append(make(TokenKind.RANGE, "..", pos))
            pos += 2
            continue
        if ch in _PUNCT:
            tokens.append(make(TokenKind.PUNCT, ch, pos))
            pos += 1
            continue
        raise fail(f"unexpected character {ch!r}", pos)
    tokens.append(make(TokenKind.EOF, "", end))
    return tokens
