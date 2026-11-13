"""The M2 resolver: names to OIDs across IMPORTS, instance OIDs to objects, the type chain,
object metadata, table/row/column classification and provenance."""

from __future__ import annotations

import hashlib

import pytest

from miblang import bundled
from miblang.resolve import (
    Mib,
    ResolveError,
    index,
    load,
    parse_oid,
    provenance,
    resolve,
    revision_key,
)

TEST_MIB = """
TEST-MIB DEFINITIONS ::= BEGIN
IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, Counter64, Integer32, IpAddress, enterprises
        FROM SNMPv2-SMI
    DisplayString, RowStatus, TruthValue
        FROM SNMPv2-TC;

testMIB MODULE-IDENTITY
    LAST-UPDATED "202611130000Z"
    ORGANIZATION "x"
    CONTACT-INFO "x"
    DESCRIPTION "x"
    ::= { enterprises 99999 }

testObjects OBJECT IDENTIFIER ::= { testMIB 1 }

testName OBJECT-TYPE
    SYNTAX DisplayString (SIZE (1..32))
    MAX-ACCESS read-write
    STATUS current
    DESCRIPTION "x"
    ::= { testObjects 1 }

testBigCounter OBJECT-TYPE
    SYNTAX Counter64
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "x"
    ::= { testObjects 2 }

testTable OBJECT-TYPE
    SYNTAX SEQUENCE OF TestEntry
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    ::= { testObjects 3 }

testEntry OBJECT-TYPE
    SYNTAX TestEntry
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    INDEX { testIndex, testLabel, IMPLIED testTail }
    ::= { testTable 1 }

TestEntry ::= SEQUENCE {
    testIndex Integer32,
    testLabel OCTET STRING,
    testTail OCTET STRING,
    testStatus RowStatus
}

testIndex OBJECT-TYPE
    SYNTAX Integer32 (1..100)
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    ::= { testEntry 1 }

testLabel OBJECT-TYPE
    SYNTAX OCTET STRING (SIZE (0..16))
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    ::= { testEntry 2 }

testTail OBJECT-TYPE
    SYNTAX OCTET STRING (SIZE (0..16))
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    ::= { testEntry 3 }

testStatus OBJECT-TYPE
    SYNTAX RowStatus
    MAX-ACCESS read-create
    STATUS current
    DESCRIPTION "x"
    ::= { testEntry 4 }

testExtTable OBJECT-TYPE
    SYNTAX SEQUENCE OF TestExtEntry
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    ::= { testObjects 4 }

testExtEntry OBJECT-TYPE
    SYNTAX TestExtEntry
    MAX-ACCESS not-accessible
    STATUS current
    DESCRIPTION "x"
    AUGMENTS { testEntry }
    ::= { testExtTable 1 }

TestExtEntry ::= SEQUENCE { testExtFlag TruthValue }

testExtFlag OBJECT-TYPE
    SYNTAX TruthValue
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "x"
    ::= { testExtEntry 1 }
END
"""

TC_OVER_TC = """
X DEFINITIONS ::= BEGIN
IMPORTS DisplayString, TEXTUAL-CONVENTION FROM SNMPv2-TC
        OBJECT-TYPE FROM SNMPv2-SMI;
Nested ::= TEXTUAL-CONVENTION
    STATUS current
    DESCRIPTION "x"
    SYNTAX DisplayString
o OBJECT-TYPE
    SYNTAX Nested
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "x"
    ::= { iso 3 }
END
"""


@pytest.fixture(scope="module")
def mib(tmp_path_factory):
    path = tmp_path_factory.mktemp("mibs") / "TEST-MIB.mib"
    path.write_text(TEST_MIB, encoding="ascii")
    return load(path)


def test_load(mib):
    assert "SNMPv2-SMI" in mib.modules and "TEST-MIB" in mib.modules
    assert mib.resolve("testMIB").dotted == "1.3.6.1.4.1.99999"
    assert mib.resolve("TEST-MIB::testName").dotted == "1.3.6.1.4.1.99999.1.1"
    assert mib.problem_list == ()


def test_resolve():
    sys_descr = resolve("sysDescr")
    assert sys_descr.dotted == "1.3.6.1.2.1.1.1" and sys_descr.module == "RFC1213-MIB"
    assert resolve("1.3.6.1.2.1.1.1").name == "sysDescr"
    assert resolve(".1.3.6.1.2.1.1.1").name == "sysDescr"
    assert resolve("SNMPv2-SMI::mib-2").dotted == "1.3.6.1.2.1"
    assert resolve("RFC1155-SMI::internet").dotted == "1.3.6.1"
    with pytest.raises(ResolveError, match="no object named"):
        resolve("noSuchThing")
    with pytest.raises(ResolveError, match="no object at"):
        resolve("1.3.6.1.99")
    with pytest.raises(ResolveError, match="not a dotted OID"):
        resolve("1.3.x")
    with pytest.raises(ResolveError, match="not a dotted OID"):
        parse_oid("1.4294967296")


def test_same_name_in_two_modules_needs_a_prefix():
    mib = Mib.with_bundled()
    mib.add_text(
        "OTHER DEFINITIONS ::= BEGIN IMPORTS enterprises FROM SNMPv2-SMI;"
        " sysDescr OBJECT IDENTIFIER ::= { enterprises 7 } END"
    )
    with pytest.raises(ResolveError, match=r"use MODULE::sysDescr"):
        mib.resolve("sysDescr")
    assert mib.resolve("OTHER::sysDescr").dotted == "1.3.6.1.4.1.7"
    assert mib.resolve("RFC1213-MIB::sysDescr").dotted == "1.3.6.1.2.1.1.1"


def test_unresolvable_and_circular_names_are_reported_not_guessed():
    mib = Mib()
    mib.add_text(
        "A DEFINITIONS ::= BEGIN x OBJECT IDENTIFIER ::= { y 1 } y OBJECT IDENTIFIER ::= { x 1 } END"
    )
    mib.add_text("B DEFINITIONS ::= BEGIN z OBJECT IDENTIFIER ::= { ghost 1 } END")
    with pytest.raises(ResolveError):
        mib.resolve("A::x")
    with pytest.raises(ResolveError):
        mib.resolve("B::z")
    problems = " | ".join(mib.problem_list)
    assert "in terms of itself" in problems and "cannot resolve ghost" in problems


def test_index_instance_suffix():
    # ifTable row 7, column ifDescr: the instance OID splits into the object and ifIndex 7.
    hit = index("1.3.6.1.2.1.2.2.1.2.7")
    assert hit is not None and hit.object.name == "ifDescr" and hit.object.role == "column"
    assert hit.suffix == (7,)
    assert [(v.name, v.value) for v in hit.index] == [("ifIndex", 7)] and hit.problem is None
    # a scalar is instanced as .0
    sys_descr = index("1.3.6.1.2.1.1.1.0")
    assert sys_descr is not None and sys_descr.object.name == "sysDescr"
    assert sys_descr.problem is None
    bad = index("1.3.6.1.2.1.1.1.5")
    assert bad is not None and bad.problem is not None and ".0" in bad.problem
    # two index objects, the second an IpAddress (RFC 1212 4.1.6)
    media = index("1.3.6.1.2.1.4.22.1.2.3.10.0.0.1")
    assert media is not None
    assert [(v.name, v.value) for v in media.index] == [
        ("ipNetToMediaIfIndex", 3),
        ("ipNetToMediaNetAddress", "10.0.0.1"),
    ]
    # tcpConnTable: four index objects, and a trailing sub-identifier is reported
    conn = index("1.3.6.1.2.1.6.13.1.1.1.2.3.4.80.5.6.7.8.443")
    assert conn is not None and conn.problem is None and len(conn.index) == 4
    extra = index("1.3.6.1.2.1.6.13.1.1.1.2.3.4.80.5.6.7.8.443.9")
    assert extra is not None and extra.problem is not None and "remain" in extra.problem
    # nothing covers an OID outside the loaded tree
    assert index("1.2.3") is None


def test_index_decoding_string_and_implied_forms(mib):
    # INDEX { testIndex, testLabel, IMPLIED testTail }: integer, length-prefixed string, implied string.
    hit = mib.index("1.3.6.1.4.1.99999.1.3.1.4.5.2.65.66.67.68")
    assert hit is not None and hit.object.name == "testStatus" and hit.problem is None
    assert [(v.name, v.value) for v in hit.index] == [
        ("testIndex", 5),
        ("testLabel", b"AB"),
        ("testTail", b"CD"),
    ]
    short = mib.index("1.3.6.1.4.1.99999.1.3.1.4.5.9.65")
    assert short is not None and short.problem is not None and "testLabel" in short.problem
    # AUGMENTS: the augmenting row is identified by the base row's INDEX
    aug = mib.index((1, 3, 6, 1, 4, 1, 99999, 1, 4, 1, 1, 5, 0))
    assert aug is not None and aug.object.name == "testExtFlag"
    assert [v.name for v in aug.index] == ["testIndex", "testLabel", "testTail"]
    assert aug.index[2].value == b""


def test_tc_chain(mib):
    status = mib.resolve("testStatus").type
    assert status is not None
    assert status.name == "RowStatus" and status.chain == ("RowStatus",)
    assert status.base == "INTEGER" and status.textual_convention == "RowStatus"
    assert ("active", 1) in status.named_numbers and ("destroy", 6) in status.named_numbers
    name = mib.resolve("testName").type
    assert name is not None
    # the object's own SIZE wins over DisplayString's (0..255): each refinement narrows (RFC 2578 9)
    assert name.sizes == ((1, 32),) and name.display_hint == "255a" and name.base == "OCTET STRING"
    assert name.textual_convention == "DisplayString" and name.smi_type == "OCTET STRING"
    index_type = mib.resolve("testIndex").type
    assert index_type is not None and index_type.smi_type == "Integer32"
    assert index_type.ranges == ((1, 100),)
    flag = mib.resolve("testExtFlag").type
    assert flag is not None and flag.textual_convention == "TruthValue" and flag.base == "INTEGER"


def test_tc_defined_over_tc_is_noted():
    mib = Mib.with_bundled()
    mib.add_text(TC_OVER_TC)
    nested = mib.resolve("X::o").type
    assert nested is not None and nested.chain == ("Nested", "DisplayString")
    assert nested.textual_convention == "Nested" and any("3.5" in n for n in nested.notes)


def test_resolve_metadata():
    sys_contact = resolve("sysContact")
    assert sys_contact.access == "read-write" and sys_contact.max_access == "read-write"
    assert sys_contact.status == "mandatory" and sys_contact.kind == "object-type"
    assert sys_contact.smi == 1
    assert sys_contact.type is not None and sys_contact.type.name == "DisplayString"
    # SMIv1 write-only reads as SMIv2 read-write (RFC 3584 2.1.1)
    mib = Mib()
    mib.add_text(
        "W DEFINITIONS ::= BEGIN IMPORTS OBJECT-TYPE FROM RFC-1212; w OBJECT-TYPE SYNTAX INTEGER"
        " ACCESS write-only STATUS mandatory ::= { iso 3 } END"
    )
    write_only = mib.resolve("W::w")
    assert write_only.access == "write-only" and write_only.max_access == "read-write"
    assert resolve("system").access is None and resolve("system").is_notification is False


def test_table_classification(mib):
    names = [
        "testName",
        "testTable",
        "testEntry",
        "testIndex",
        "testStatus",
        "testExtEntry",
        "testExtFlag",
    ]
    assert {n: mib.resolve(n).role for n in names} == {
        "testName": "scalar",
        "testTable": "table",
        "testEntry": "row",
        "testIndex": "column",
        "testStatus": "column",
        "testExtEntry": "row",
        "testExtFlag": "column",
    }
    assert resolve("ifTable").role == "table" and resolve("ifEntry").role == "row"
    assert resolve("ifDescr").role == "column" and resolve("sysDescr").role == "scalar"
    assert resolve("system").role is None


def test_smiv2_only_syntax(mib):
    assert mib.resolve("testBigCounter").smiv2_only is True
    assert mib.resolve("testName").smiv2_only is False
    assert mib.resolve("testStatus").smiv2_only is False


def test_provenance_obsolete_source():
    tcp = provenance("1.3.6.1.2.1.6.5.0")
    assert tcp.flagged and tcp.rfc == 1213 and tcp.updated_by == ("RFC 2012",)
    assert tcp.current_replacement == ("RFC 4022",)
    ip = provenance("1.3.6.1.2.1.4.3.0")
    assert ip.updated_by == ("RFC 2011",) and ip.current_replacement == ("RFC 4293",)
    plain = provenance("1.3.6.1.2.1.1.1.0")
    assert plain.module == "RFC1213-MIB" and not plain.flagged
    with pytest.raises(ResolveError):
        provenance("1.2.3")


def test_import_of_missing_symbol():
    # RFC 2578 3.2: an IMPORTS entry names the descriptor and the module that defines it.
    source = TEST_MIB.replace("TEST-MIB", "BAD-MIB").replace(
        "DisplayString, RowStatus, TruthValue", "DisplayString, NoSuchTC, RowStatus, TruthValue"
    )
    mib = Mib.with_bundled()
    mib.add_text(source)
    mib.resolve("BAD-MIB::testName")
    assert any(
        "BAD-MIB: imports NoSuchTC from SNMPv2-TC, which is loaded and does not define it" in p
        for p in mib.problems
    )
    assert not any("DisplayString" in p for p in mib.problems)
    # a source module that is not loaded cannot be checked, so it is not reported
    other = Mib.with_bundled()
    other.add_text(source.replace("FROM SNMPv2-TC;", "FROM NOT-LOADED-MIB;"))
    other.resolve("BAD-MIB::testBigCounter")
    assert not any("does not define it" in p for p in other.problems)


def test_the_bundled_modules_import_nothing_they_do_not_define():
    mib = Mib.with_bundled()
    mib.resolve("sysDescr")
    assert not [p for p in mib.problems if "does not define" in p]


def test_a_descriptor_imported_from_two_modules_needs_a_prefix():
    first = (
        "ONE-MIB DEFINITIONS ::= BEGIN IMPORTS OBJECT-IDENTITY FROM SNMPv2-SMI; "
        'dup OBJECT-IDENTITY STATUS current DESCRIPTION "x" ::= { 1 3 6 1 4 1 99998 1 } END'
    )
    second = first.replace("ONE-MIB", "TWO-MIB").replace("99998", "99997")
    third = (
        "THREE-MIB DEFINITIONS ::= BEGIN IMPORTS dup FROM ONE-MIB dup FROM TWO-MIB "
        "OBJECT-IDENTITY FROM SNMPv2-SMI; "
        'three OBJECT-IDENTITY STATUS current DESCRIPTION "x" ::= { 1 3 6 1 4 1 99996 1 } END'
    )
    mib = Mib.with_bundled()
    for text in (first, second, third):
        mib.add_text(text)
    mib.resolve("THREE-MIB::three")
    assert any(
        "THREE-MIB: dup is imported from ONE-MIB and TWO-MIB" in p and "module.descriptor" in p
        for p in mib.problems
    )


def test_provenance_file_modules(tmp_path):
    path = tmp_path / "TEST-MIB.mib"
    raw = TEST_MIB.encode("ascii")
    path.write_bytes(raw)
    mib = load(path)
    got = mib.provenance("1.3.6.1.4.1.99999.1.1.0")
    assert got.module == "TEST-MIB"
    assert got.source == "file"
    assert got.path == str(path)
    assert got.sha256 == hashlib.sha256(raw).hexdigest()
    assert got.revision == "202611130000Z"
    assert got.rfc is None
    # a bundled module reports its manifest hash and the module's own revision, and no file
    bundled_answer = mib.provenance("1.3.6.1.2.1.1.1.0")
    assert bundled_answer.source == "bundled"
    assert bundled_answer.path is None
    assert bundled_answer.sha256 == bundled.manifest()["RFC1213-MIB"]["sha256"]
    # text added with no origin says so
    plain = Mib.with_bundled()
    plain.add_text(TEST_MIB)
    unknown = plain.provenance("1.3.6.1.4.1.99999.1.1.0")
    assert unknown.source == "text"
    assert unknown.path is None
    assert unknown.sha256 is None
    assert unknown.revision == "202611130000Z"
    assert "no provenance recorded" in unknown.note


# --- SMIv1 TRAP-TYPE placed in the tree (RFC 1215 2.1.5, RFC 3584 3.1) ------------------------------------

# The two usage examples of RFC 1215 2.2 (read through rfclib 2026-11-13), the second as the standard traps.
TRAPS_MIB = """
TRAPS-MIB DEFINITIONS ::= BEGIN
IMPORTS enterprises FROM RFC1155-SMI
        snmp FROM RFC1213-MIB
        TRAP-TYPE FROM RFC-1215;

myEnterprise OBJECT IDENTIFIER ::= { enterprises 9999 }

myLinkDown TRAP-TYPE
    ENTERPRISE  myEnterprise
    VARIABLES   { ifIndex }
    DESCRIPTION "a link failed"
    ::= 2

coldStart TRAP-TYPE ENTERPRISE snmp DESCRIPTION "cold" ::= 0
warmStart TRAP-TYPE ENTERPRISE snmp DESCRIPTION "warm" ::= 1
linkDown TRAP-TYPE ENTERPRISE snmp VARIABLES { ifIndex } DESCRIPTION "down" ::= 2
linkUp TRAP-TYPE ENTERPRISE snmp VARIABLES { ifIndex } DESCRIPTION "up" ::= 3
authenticationFailure TRAP-TYPE ENTERPRISE snmp DESCRIPTION "auth" ::= 4
egpNeighborLoss TRAP-TYPE ENTERPRISE snmp VARIABLES { egpNeighAddr } DESCRIPTION "egp" ::= 5
END
"""


def test_trap_oid():
    mib = Mib.with_bundled()
    mib.add_text(TRAPS_MIB)
    # an enterprise-specific trap is enterprise.0.specific-trap (RFC 3584 3.1 item 2)
    mine = mib.resolve("myLinkDown")
    assert mine.kind == "trap-type"
    assert mine.dotted == "1.3.6.1.4.1.9999.0.2"
    assert mine.is_notification
    assert mine.edition is None  # an SMIv1 module has no MODULE-IDENTITY
    # a generic trap is snmpTraps.(generic-trap + 1) (RFC 3584 3.1 item 3, its table)
    expected = {
        "coldStart": "1.3.6.1.6.3.1.1.5.1",
        "warmStart": "1.3.6.1.6.3.1.1.5.2",
        "linkDown": "1.3.6.1.6.3.1.1.5.3",
        "linkUp": "1.3.6.1.6.3.1.1.5.4",
        "authenticationFailure": "1.3.6.1.6.3.1.1.5.5",
        "egpNeighborLoss": "1.3.6.1.6.3.1.1.5.6",
    }
    for name, oid in expected.items():
        assert mib.resolve(name).dotted == oid, name
    # the OID answers back to the trap, the way a received snmpTrapOID would be looked up
    assert mib.resolve("1.3.6.1.4.1.9999.0.2").name == "myLinkDown"
    assert mib.resolve("1.3.6.1.6.3.1.1.5.3").name == "linkDown"
    assert mib.resolve("TRAPS-MIB::linkUp").oid == (1, 3, 6, 1, 6, 3, 1, 1, 5, 4)
    assert not [p for p in mib.problems if "TRAPS-MIB" in p and "ifIndex" not in p]


def test_a_generic_trap_number_above_five_is_refused_not_guessed():
    mib = Mib.with_bundled()
    mib.add_text(
        TRAPS_MIB.replace("egpNeighborLoss TRAP-TYPE", "bogus TRAP-TYPE").replace("::= 5", "::= 6")
    )
    with pytest.raises(ResolveError):
        mib.resolve("bogus")
    assert any("generic trap" in p for p in mib.problems)


def test_a_trap_with_an_unresolvable_enterprise_is_reported():
    mib = Mib.with_bundled()
    mib.add_text(TRAPS_MIB.replace("ENTERPRISE  myEnterprise", "ENTERPRISE  nowhere"))
    with pytest.raises(ResolveError):
        mib.resolve("myLinkDown")
    assert any("nowhere" in p for p in mib.problems)


# --- two editions of one module (RFC 2578 2, 5.1, 5.5) ------------------------------------------------------


def _edition(last_updated: str, *, extra: bool = False, revision: str | None = None) -> str:
    body = ""
    if extra:
        body = """
exTwo OBJECT-TYPE SYNTAX Integer32 MAX-ACCESS read-only STATUS current DESCRIPTION "added later"
    ::= { exMIB 2 }"""
    return f"""
EX-MIB DEFINITIONS ::= BEGIN
IMPORTS MODULE-IDENTITY, OBJECT-TYPE, Integer32, enterprises FROM SNMPv2-SMI;
exMIB MODULE-IDENTITY
    LAST-UPDATED "{last_updated}"
    ORGANIZATION "x"
    CONTACT-INFO "x"
    DESCRIPTION "x"
    REVISION "{revision or last_updated}"
    DESCRIPTION "r"
    ::= {{ enterprises 4242 }}
exOne OBJECT-TYPE SYNTAX Integer32 MAX-ACCESS read-only STATUS current DESCRIPTION "x"
    ::= {{ exMIB 1 }}{body}
END
"""


def test_two_editions_of_one_module():
    mib = Mib.with_bundled()
    mib.add_text(_edition("200101010000Z"))
    mib.add_text(_edition("200507010000Z", extra=True))
    assert mib.editions("EX-MIB") == ("200507010000Z", "200101010000Z")
    assert mib.resolve("exOne").edition == "200507010000Z"  # the edition is on every answer
    assert mib.resolve("exTwo").edition == "200507010000Z"
    assert mib.provenance("1.3.6.1.4.1.4242.2").revision == "200507010000Z"
    assert mib.modules.count("EX-MIB") == 1
    assert not [p for p in mib.problems if "EX-MIB" in p]


def test_the_latest_last_updated_answers_even_when_it_was_added_first():
    mib = Mib.with_bundled()
    mib.add_text(_edition("200507010000Z", extra=True))
    mib.add_text(_edition("200101010000Z"))
    assert mib.resolve("exTwo").edition == "200507010000Z"
    assert mib.editions("EX-MIB") == ("200507010000Z", "200101010000Z")
    # nothing is silent: the problem says which edition answers and why
    assert any("EX-MIB" in p and "200507010000Z answers" in p for p in mib.problems)


def test_choosing_an_edition_gives_a_copy_that_answers_from_it():
    mib = Mib.with_bundled()
    mib.add_text(_edition("200101010000Z"))
    mib.add_text(_edition("200507010000Z", extra=True))
    older = mib.at_edition("EX-MIB", "200101010000Z")
    assert older.resolve("exOne").edition == "200101010000Z"
    with pytest.raises(ResolveError):
        older.resolve("exTwo")  # not in the older edition
    assert mib.resolve("exTwo")  # the original is untouched
    # the two ExtUTCTime spellings of one date are one edition: 1998-05-01 as YYMMDDHHMMZ and YYYYMMDDHHMMZ
    legacy = Mib.with_bundled()
    legacy.add_text(_edition("9805010000Z"))
    assert legacy.at_edition("EX-MIB", "199805010000Z").resolve("exOne").edition == "9805010000Z"
    with pytest.raises(ResolveError, match="no loaded edition"):
        mib.at_edition("EX-MIB", "199901010000Z")
    with pytest.raises(ResolveError, match="not loaded"):
        mib.at_edition("NOPE-MIB", "200101010000Z")


def test_two_digit_years_are_nineteen_hundreds_and_four_digit_years_are_any():
    # RFC 2578 2: YY is "only years between 1900-1999", YYYY is "any year"
    assert revision_key("9805010000Z") == (1998, 5, 1, 0, 0)
    assert revision_key("200507010930Z") == (2005, 7, 1, 9, 30)
    for bad in (
        None,
        "",
        "20050701Z",
        "200513010000Z",
        "200507010960Z",
        "2005070100000Z",
        "200507010000",
    ):
        assert revision_key(bad) is None
    mib = Mib.with_bundled()
    mib.add_text(_edition("9912310000Z"))  # 1999
    mib.add_text(_edition("200001010000Z"))  # 2000 is later, though "00" sorts below "99" as text
    assert mib.resolve("exOne").edition == "200001010000Z"


def test_equal_editions_the_last_added_answers_and_a_conflict_is_reported():
    mib = Mib.with_bundled()
    mib.add_text(_edition("200101010000Z"))
    mib.add_text(_edition("200101010000Z", extra=True))  # same LAST-UPDATED, different text
    assert mib.resolve("exTwo").edition == "200101010000Z"
    assert any("share LAST-UPDATED" in p for p in mib.problems)
    # the identical text added again is one edition, not a conflict
    again = Mib.with_bundled()
    again.add_text(_edition("200101010000Z"))
    again.add_text(_edition("200101010000Z"))
    assert again.editions("EX-MIB") == ("200101010000Z",)
    assert not [p for p in again.problems if "EX-MIB" in p]


def test_a_module_with_no_identity_loses_to_one_with_a_last_updated():
    smiv1 = "EX-MIB DEFINITIONS ::= BEGIN\nIMPORTS enterprises FROM RFC1155-SMI;\nexMIB OBJECT IDENTIFIER ::= { enterprises 4242 }\nEND\n"
    mib = Mib.with_bundled()
    mib.add_text(_edition("200101010000Z"))
    mib.add_text(smiv1)  # added last, but it has no LAST-UPDATED to rank by
    assert mib.editions("EX-MIB") == ("200101010000Z", None)
    assert mib.resolve("exOne").edition == "200101010000Z"
    assert mib.at_edition("EX-MIB", None).resolve("exMIB").edition is None
