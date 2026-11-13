"""The lexer rows of ROADMAP.md: RFC 2578 3.1.1, 3.4 and 3.7, plus X.680 12.3 for identifiers."""

from __future__ import annotations

import pathlib
import re
import time

import pytest

from miblang.lexer import RESERVED, LexError, TokenKind, lex

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def kinds(text, **kw):
    return [(t.kind, t.text) for t in lex(text, **kw)[:-1]]


def test_lex_module_identity_header():
    # RFC 2578 5.7, paragraphs 2-4 (tests/fixtures/rfc2578_5_7_fizbin.mib).
    source = (FIXTURES / "rfc2578_5_7_fizbin.mib").read_text(encoding="utf-8")
    tokens = lex(source)
    assert tokens[-1].kind is TokenKind.EOF
    head = [(t.kind, t.text) for t in tokens[:12]]
    assert head == [
        (TokenKind.UPPER_IDENT, "FIZBIN-MIB"),
        (TokenKind.KEYWORD, "DEFINITIONS"),
        (TokenKind.ASSIGN, "::="),
        (TokenKind.KEYWORD, "BEGIN"),
        (TokenKind.KEYWORD, "IMPORTS"),
        (TokenKind.KEYWORD, "MODULE-IDENTITY"),
        (TokenKind.PUNCT, ","),
        (TokenKind.KEYWORD, "OBJECT-TYPE"),
        (TokenKind.PUNCT, ","),
        (TokenKind.IDENT, "experimental"),
        (TokenKind.KEYWORD, "FROM"),
        (TokenKind.UPPER_IDENT, "SNMPv2-SMI"),
    ]
    # the comment lines at the top of the fixture are skipped, so the first token is on line 3
    assert (tokens[0].line, tokens[0].column) == (3, 1)
    by_text = {t.text: t for t in tokens}
    assert (by_text["fizbin"].line, by_text["fizbin"].column) == (10, 1)
    assert tokens[tokens[0:].index(by_text["LAST-UPDATED"]) + 1].kind is TokenKind.CSTRING
    # the contact string keeps its embedded newlines
    contact = next(t for t in tokens if t.text.startswith("        Marshall"))
    assert contact.kind is TokenKind.CSTRING and "\n" in contact.text
    assert source[by_text["fizbin"].offset :].startswith("fizbin")


def reserved_from_fixture():
    text = (FIXTURES / "rfc2578_3_7.txt").read_text(encoding="utf-8")
    body = text.split("\n\n", 1)[1]
    body = re.sub(r"-\n\s+", "-", body)  # the RFC hyphenates MODULE-IDENTITY across a line
    return frozenset(body.split())


def test_reserved_list_matches_rfc_2578_3_7():
    expected = reserved_from_fixture()
    assert "MODULE-IDENTITY" in expected
    assert expected == RESERVED
    assert len(RESERVED) == 93  # measured from the fixture


def test_every_reserved_word_lexes_as_keyword():
    for word in RESERVED:
        assert kinds(word) == [(TokenKind.KEYWORD, word)]


def test_comment_to_end_of_line():
    assert kinds("a -- gone\nb") == [(TokenKind.IDENT, "a"), (TokenKind.IDENT, "b")]


def test_comment_ended_by_double_hyphen_resumes_tokens():
    assert kinds("a -- gone -- b\nc") == [
        (TokenKind.IDENT, "a"),
        (TokenKind.IDENT, "b"),
        (TokenKind.IDENT, "c"),
    ]


def test_comment_marker_inside_string_is_text():
    assert kinds('"a -- b" c') == [(TokenKind.CSTRING, "a -- b"), (TokenKind.IDENT, "c")]


def test_comment_at_end_of_input_without_newline():
    assert kinds("a -- trailing") == [(TokenKind.IDENT, "a")]


def test_cstring_with_embedded_newline_and_crlf():
    tokens = lex('x "one\r\ntwo\nthree" y')
    assert tokens[1].text == "one\r\ntwo\nthree"
    assert (tokens[2].line, tokens[2].column) == (3, 8)


def test_unterminated_string_raises_with_start_position():
    with pytest.raises(LexError) as info:
        lex('a\n  "never closed')
    assert (info.value.line, info.value.column) == (2, 3)


def test_hex_string_even_digits_only():
    assert kinds("'0A'H 'ff'h ''H") == [
        (TokenKind.HSTRING, "0A"),
        (TokenKind.HSTRING, "ff"),
        (TokenKind.HSTRING, ""),
    ]
    with pytest.raises(LexError):
        lex("'0'H")
    with pytest.raises(LexError):
        lex("'0G'H")


def test_binary_string_multiple_of_eight():
    assert kinds("'10101010'B") == [(TokenKind.BSTRING, "10101010")]
    with pytest.raises(LexError):
        lex("'1010'B")
    with pytest.raises(LexError):
        lex("'1012xxxx'b")


def test_quote_without_b_or_h_raises():
    with pytest.raises(LexError):
        lex("'abcd'")


def test_assign_and_range_tokens():
    assert kinds("::= 1..5") == [
        (TokenKind.ASSIGN, "::="),
        (TokenKind.NUMBER, "1"),
        (TokenKind.RANGE, ".."),
        (TokenKind.NUMBER, "5"),
    ]


def test_punctuation_and_negative_numbers():
    assert [t.text for t in lex("{ } ( ) [ ] , ; | . -3")[:-1]] == [*"{}()[],;|.", "-", "3"]


def test_identifier_with_internal_hyphen():
    assert kinds("mib-2 ifIn-Octets") == [
        (TokenKind.IDENT, "mib-2"),
        (TokenKind.IDENT, "ifIn-Octets"),
    ]


def test_identifier_ending_in_hyphen_raises():
    with pytest.raises(LexError, match="hyphen"):
        lex("abc- def")


def test_double_hyphen_inside_identifier_starts_comment():
    assert kinds("abc--def\nxyz") == [(TokenKind.IDENT, "abc"), (TokenKind.IDENT, "xyz")]


def test_uppercase_vs_lowercase_ident_kinds():
    assert kinds("Counter ifIndex DisplayString") == [
        (TokenKind.UPPER_IDENT, "Counter"),
        (TokenKind.IDENT, "ifIndex"),
        (TokenKind.UPPER_IDENT, "DisplayString"),
    ]


def test_empty_input_still_has_eof():
    tokens = lex("")
    assert [t.kind for t in tokens] == [TokenKind.EOF]


def test_unknown_character_raises_with_position():
    with pytest.raises(LexError) as info:
        lex("a\n  @")
    assert (info.value.line, info.value.column) == (2, 3)


def test_max_length_refused_before_scan():
    with pytest.raises(LexError, match="max_length"):
        lex("a" * 11, max_length=10)


def test_nul_byte_refused_in_string_and_outside():
    with pytest.raises(LexError):
        lex('"a\x00b"')
    with pytest.raises(LexError):
        lex("a\x00")


def test_non_ascii_in_string_policy():
    # default: admitted (published modules contain it); strict_ascii enforces RFC 2578 3.1.1
    assert kinds('"café"') == [(TokenKind.CSTRING, "café")]
    with pytest.raises(LexError):
        lex('"café"', strict_ascii=True)
    with pytest.raises(LexError):
        lex("café")  # outside a string it is never admitted


def test_bom_at_start_is_refused_explicitly():
    with pytest.raises(LexError, match="byte order mark"):
        lex("﻿a")


def test_one_million_open_quote_chars_is_linear_time():
    start = time.perf_counter()
    with pytest.raises(LexError):
        lex("'" * 1_000_000)
    with pytest.raises(LexError):
        lex('"' * 3 + "x" * 1_000_000)
    assert len(lex('""' * 100_000)) == 100_001  # 100000 empty strings and EOF
    assert time.perf_counter() - start < 2


def test_doubled_quote_policy():
    # RFC 2578 3.1.1: no quote inside a string, so a doubled quote is two strings. X.680 12.14.1
    # (read with edition="X.680"): a pair of quotes is one quote, and spacing around a line end is
    # not part of the value. The default is the RFC 2578 reading.
    assert kinds('"a""b"') == [(TokenKind.CSTRING, "a"), (TokenKind.CSTRING, "b")]
    assert kinds('"a""b"', x680_strings=True) == [(TokenKind.CSTRING, 'a"b')]
    assert kinds('""', x680_strings=True) == [(TokenKind.CSTRING, "")]
    assert kinds('""""', x680_strings=True) == [(TokenKind.CSTRING, '"')]
    assert kinds('"ab  \n   cd"', x680_strings=True) == [(TokenKind.CSTRING, "ab\ncd")]
    assert kinds('"ab  \n   cd"') == [(TokenKind.CSTRING, "ab  \n   cd")]
    with pytest.raises(LexError, match="unterminated"):
        lex('"a""b', x680_strings=True)


def test_odd_hyphen_banner():
    # X.680 12.6.3 (and RFC 2578 3.4): a comment ends at the next pair of hyphens, so an odd run
    # leaves one hyphen. Strict mode refuses it; lenient_hyphens reads the whole run as one marker.
    with pytest.raises(LexError, match="stray hyphen"):
        lex("a ----- b")
    assert kinds("a ----- b\nc", lenient_hyphens=True) == [
        (TokenKind.IDENT, "a"),
        (TokenKind.IDENT, "c"),
    ]
    assert kinds("a --------\nb", lenient_hyphens=True) == [
        (TokenKind.IDENT, "a"),
        (TokenKind.IDENT, "b"),
    ]
    assert kinds("a -- x --- b\nc", lenient_hyphens=True) == [
        (TokenKind.IDENT, "a"),
        (TokenKind.IDENT, "b"),
        (TokenKind.IDENT, "c"),
    ]
    # an even run is read pair by pair in both modes
    assert kinds("a ------\nb") == [(TokenKind.IDENT, "a"), (TokenKind.IDENT, "b")]
    # a hyphen before a digit is a negative number in both modes
    assert kinds("(-5..5)", lenient_hyphens=True)[1:3] == [
        (TokenKind.PUNCT, "-"),
        (TokenKind.NUMBER, "5"),
    ]
    with pytest.raises(LexError, match="stray hyphen"):
        lex("a - b")
