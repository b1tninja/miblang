"""The grammar rows of ROADMAP.md. Real text comes from the RFCs (tests/fixtures, each file names its
section and the date it was read through rfclib); everything else is a small invented module."""

from __future__ import annotations

import pathlib

import pytest

from miblang import grammar
from miblang.grammar import (
    AgentCapabilities,
    MacroDefinition,
    ModuleCompliance,
    ModuleIdentity,
    NotificationGroup,
    NotificationType,
    ObjectGroup,
    ObjectIdentifierAssignment,
    ObjectIdentity,
    ObjectType,
    ParseError,
    TextualConvention,
    TrapType,
    TypeAssignment,
    parse,
)
from miblang.lexer import lex

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def wrap(body: str, name: str = "TEST-MIB", imports: str = "") -> str:
    return f"{name} DEFINITIONS ::= BEGIN\n{imports}\n{body}\nEND\n"


V2_HEAD = "IMPORTS OBJECT-TYPE, Integer32 FROM SNMPv2-SMI;"


def only(text):
    module = parse(text)
    assert len(module.definitions) == 1
    return module.definitions[0]


# -- module header, IMPORTS, OBJECT IDENTIFIER assignments ------------------------------------------


def test_module_header_and_imports():
    module = parse(
        wrap(
            "",
            "ACME-MIB",
            "IMPORTS a, B, Counter32 FROM X-MIB c FROM Y-MIB; -- two modules, one list each",
        )
    )
    assert module.name == "ACME-MIB"
    assert module.imports == (("X-MIB", ("a", "B", "Counter32")), ("Y-MIB", ("c",)))
    assert module.exports is None
    assert module.definitions == ()
    assert module.smi is None


def test_empty_imports_and_no_imports_and_module_oid():
    assert parse("M DEFINITIONS ::= BEGIN END").imports == ()
    module = parse("M { 1 3 6 1 4 1 99 } DEFINITIONS IMPLICIT TAGS ::= BEGIN END")
    assert module.module_oid is not None
    assert [c.number for c in module.module_oid.components] == [1, 3, 6, 1, 4, 1, 99]


def test_oid_assignments_with_named_numbers_and_qualified_names():
    # RFC 2578 3.6 paragraph 5 (the legal examples)
    text = wrap(
        "mib         OBJECT IDENTIFIER ::= { mgmt 1 }  -- from RFC1156\n"
        "fredRouter  OBJECT IDENTIFIER ::= { flintStones 1 1 }\n"
        "barneySwitch OBJECT IDENTIFIER ::= { flintStones bedrock(2) 1 }\n"
        "viaModule OBJECT IDENTIFIER ::= { OTHER-MIB.thing 4 }\n"
    )
    mib, fred, barney, via = parse(text).definitions
    assert isinstance(mib, ObjectIdentifierAssignment) and mib.name == "mib"
    assert [(c.name, c.number) for c in mib.oid.components] == [("mgmt", None), (None, 1)]
    assert [(c.name, c.number) for c in barney.oid.components] == [
        ("flintStones", None),
        ("bedrock", 2),
        (None, 1),
    ]
    assert [c.number for c in fred.oid.components] == [None, 1, 1]
    assert (via.oid.components[0].module, via.oid.components[0].name) == ("OTHER-MIB", "thing")


def test_oid_subidentifier_limit_and_empty_oid():
    # RFC 2578 3.5: a sub-identifier is at most 2^32-1
    parse(wrap("x OBJECT IDENTIFIER ::= { a 4294967295 }"))
    with pytest.raises(ParseError, match="2\\^32-1"):
        parse(wrap("x OBJECT IDENTIFIER ::= { a 4294967296 }"))
    with pytest.raises(ParseError, match="empty"):
        parse(wrap("x OBJECT IDENTIFIER ::= { }"))


def test_module_without_end_and_trailing_text():
    with pytest.raises(ParseError, match="no END"):
        parse("M DEFINITIONS ::= BEGIN")
    with pytest.raises(ParseError, match="after END"):
        parse("M DEFINITIONS ::= BEGIN END extra")


def test_exports_clause_is_kept_for_smiv1():
    module = parse("M DEFINITIONS ::= BEGIN EXPORTS -- EVERYTHING\n a, B;\nEND")
    assert module.exports == ("a", "B")


# -- MODULE-IDENTITY (RFC 2578 5) ----------------------------------------------------------------------


def test_module_identity_from_rfc2578_5_7():
    module = parse(fixture("rfc2578_5_7_fizbin.mib"))
    ident = module.definitions[0]
    assert isinstance(ident, ModuleIdentity)
    assert module.imports == (("SNMPv2-SMI", ("MODULE-IDENTITY", "OBJECT-TYPE", "experimental")),)
    assert ident.name == "fizbin"
    assert ident.last_updated == "199505241811Z"
    assert ident.organization == "IETF SNMPv2 Working Group"
    assert "Marshall T. Rose" in ident.contact_info
    assert ident.contact_info.endswith("mrose@dbc.mtview.ca.us")
    assert [r.date for r in ident.revisions] == ["9505241811Z", "9210070433Z"]
    assert ident.revisions[1].description.startswith("The initial version")
    assert [(c.name, c.number) for c in ident.oid.components] == [
        ("experimental", None),
        ("xx", None),
    ]
    assert module.smi == 2


def test_module_identity_function_on_a_token_slice():
    tokens = lex(fixture("rfc2578_5_7_fizbin.mib"))
    start = next(i for i, t in enumerate(tokens) if t.text == "fizbin")
    assert grammar.module_identity(tokens[start:]).name == "fizbin"
    with pytest.raises(ParseError, match="not a MODULE-IDENTITY"):
        grammar.module_identity(lex("x OBJECT IDENTIFIER ::= { a 1 }"))


def test_module_identity_requires_each_clause():
    text = (
        'm MODULE-IDENTITY LAST-UPDATED "9505241811Z" ORGANIZATION "o" DESCRIPTION "d" ::= { a 1 }'
    )
    with pytest.raises(ParseError, match="CONTACT-INFO"):
        parse(wrap(text))


def test_duplicate_clause_is_refused():
    text = (
        'm MODULE-IDENTITY LAST-UPDATED "9505241811Z" LAST-UPDATED "9505241811Z" ORGANIZATION "o" '
        'CONTACT-INFO "c" DESCRIPTION "d" ::= { a 1 }'
    )
    with pytest.raises(ParseError, match="given twice"):
        parse(wrap(text))


# -- OBJECT-IDENTITY and OBJECT-TYPE (RFC 2578 6, 7) ---------------------------------------------------


def test_object_identity_from_rfc2578_zero_dot_zero():
    module = parse(fixture("rfc2578_snmpv2_smi.mib"))
    zero = module.find("zeroDotZero")
    assert isinstance(zero, ObjectIdentity)
    assert zero.status == "current" and zero.description == "A value used for null identifiers."
    assert [c.number for c in zero.oid.components] == [0, 0]
    assert zero.reference is None


def test_snmpv2_smi_module_from_rfc2578_section_2():
    module = parse(fixture("rfc2578_snmpv2_smi.mib"))
    assert module.name == "SNMPv2-SMI" and module.smi == 2
    macros = [d.name for d in module.definitions if isinstance(d, MacroDefinition)]
    assert macros == ["MODULE-IDENTITY", "OBJECT-IDENTITY", "OBJECT-TYPE", "NOTIFICATION-TYPE"]
    gauge = module.find("Gauge32")
    assert isinstance(gauge, TypeAssignment)
    assert gauge.syntax.tag == "APPLICATION 2" and gauge.syntax.tag_mode == "IMPLICIT"
    assert gauge.syntax.base == "INTEGER" and gauge.syntax.ranges == ((0, 4294967295),)
    assert module.find("Integer32").syntax.ranges == ((-2147483648, 2147483647),)
    ext = module.find("ExtUTCTime")
    assert ext.syntax.base == "OCTET STRING" and ext.syntax.sizes == ((11, 11), (13, 13))
    syntax = module.find("ObjectSyntax")
    assert [n for n, _ in syntax.syntax.fields] == ["simple", "application-wide"]
    internet = module.find("internet")
    assert [(c.name, c.number) for c in internet.oid.components] == [("dod", None), (None, 1)]
    assert module.find("transmission") is not None
    assert len(module.definitions) == 34


def test_object_type_table_from_rfc2578_7_11():
    body = fixture("rfc2578_7_11_eval.txt")
    module = parse(wrap(body, "EVAL-MIB", V2_HEAD))
    by_name = {d.name: d for d in module.definitions}
    slot = by_name["evalSlot"]
    assert isinstance(slot, ObjectType) and slot.smi == 2
    assert slot.syntax.base == "Integer32" and slot.syntax.ranges == ((0, 2147483647),)
    assert slot.access == "read-only" and slot.status == "current"
    table = by_name["evalTable"]
    assert table.syntax.base == "SEQUENCE OF" and table.syntax.item_type == "EvalEntry"
    assert table.access == "not-accessible"
    entry = by_name["evalEntry"]
    assert [i.name for i in entry.index] == ["evalIndex"]
    row = by_name["EvalEntry"]
    assert isinstance(row, TypeAssignment) and row.syntax.base == "SEQUENCE"
    assert [name for name, _ in row.syntax.fields] == [
        "evalIndex",
        "evalString",
        "evalValue",
        "evalStatus",
    ]
    assert by_name["evalValue"].defval.kind == "integer" and by_name["evalValue"].defval.value == 0
    assert by_name["evalStatus"].defval.kind == "identifier"
    assert by_name["evalStatus"].defval.value == "active"
    assert module.smi == 2


def test_object_type_function_on_a_token_slice():
    tokens = lex(wrap(fixture("rfc2578_7_11_eval.txt"), "EVAL-MIB", V2_HEAD))
    start = next(
        i
        for i, t in enumerate(tokens)
        if t.text == "evalIndex" and tokens[i + 1].text == "OBJECT-TYPE"
    )
    found = grammar.object_type(tokens[start:])
    assert found.name == "evalIndex" and found.syntax.ranges == ((1, 2147483647),)
    with pytest.raises(ParseError, match="not an OBJECT-TYPE"):
        grammar.object_type(lex("x OBJECT IDENTIFIER ::= { a 1 }"))


def object_text(clauses: str) -> str:
    return wrap(f"x OBJECT-TYPE {clauses} ::= {{ a 1 }}", imports=V2_HEAD)


GOOD = 'SYNTAX Integer32 MAX-ACCESS read-only STATUS current DESCRIPTION "d"'


def test_object_type_clause_order_is_free_and_optional_clauses_read():
    obj = only(
        object_text(
            'DESCRIPTION "d" STATUS deprecated MAX-ACCESS read-write UNITS "seconds" '
            'REFERENCE "r" DEFVAL { -5 } SYNTAX Integer32 (-10..10 | 20)'
        )
    )
    assert isinstance(obj, ObjectType)
    assert (obj.units, obj.reference, obj.status, obj.access) == (
        "seconds",
        "r",
        "deprecated",
        "read-write",
    )
    assert obj.syntax.ranges == ((-10, 10), (20, 20))
    assert obj.defval is not None and obj.defval.value == -5


def test_object_type_refusals():
    with pytest.raises(ParseError, match="lacks MAX-ACCESS"):
        parse(object_text('SYNTAX Integer32 STATUS current DESCRIPTION "d"'))
    with pytest.raises(ParseError, match="both MAX-ACCESS and ACCESS"):
        parse(object_text(GOOD + " ACCESS read-only"))
    with pytest.raises(ParseError, match="lacks SYNTAX"):
        parse(object_text('MAX-ACCESS read-only STATUS current DESCRIPTION "d"'))
    with pytest.raises(ParseError, match="lacks DESCRIPTION"):
        parse(object_text("SYNTAX Integer32 MAX-ACCESS read-only STATUS current"))
    with pytest.raises(ParseError, match="not valid in SMIv2"):
        parse(object_text(GOOD.replace("read-only", "write-only")))
    with pytest.raises(ParseError, match="STATUS 'mandatory' is not valid in SMIv2"):
        parse(object_text(GOOD.replace("current", "mandatory")))
    with pytest.raises(ParseError, match="both INDEX and AUGMENTS"):
        parse(object_text(GOOD + " INDEX { a } AUGMENTS { b }"))


def test_syntax_forms_enum_bits_size_and_defval_kinds():
    text = wrap(
        'e OBJECT-TYPE SYNTAX INTEGER { up(1), down(2), testing(-1) } MAX-ACCESS read-write STATUS current DESCRIPTION "d" DEFVAL { up } ::= { a 1 }\n'
        'b OBJECT-TYPE SYNTAX BITS { one(0), two(1) } MAX-ACCESS read-write STATUS current DESCRIPTION "d" DEFVAL { { one, two } } ::= { a 2 }\n'
        'b2 OBJECT-TYPE SYNTAX BITS { one(0) } MAX-ACCESS read-write STATUS current DESCRIPTION "d" DEFVAL { { } } ::= { a 3 }\n'
        "s OBJECT-TYPE SYNTAX OCTET STRING (SIZE (0..255 | 300)) MAX-ACCESS read-write STATUS current DESCRIPTION \"d\" DEFVAL { 'ffffffffffff'H } ::= { a 4 }\n"
        'd OBJECT-TYPE SYNTAX DisplayString MAX-ACCESS read-write STATUS current DESCRIPTION "d" DEFVAL { "SNMP agent" } ::= { a 5 }\n'
        'o OBJECT-TYPE SYNTAX OBJECT IDENTIFIER MAX-ACCESS read-write STATUS current DESCRIPTION "d" DEFVAL { sysDescr } ::= { a 6 }\n',
        imports=V2_HEAD,
    )
    e, b, b2, s, d, o = parse(text).definitions
    assert e.syntax.named_numbers == (("up", 1), ("down", 2), ("testing", -1))
    assert e.defval.kind == "identifier"
    assert b.syntax.base == "BITS" and b.syntax.named_numbers == (("one", 0), ("two", 1))
    assert (b.defval.kind, b.defval.value) == ("bits", ("one", "two"))
    assert (b2.defval.kind, b2.defval.value) == ("bits", ())
    assert s.syntax.sizes == ((0, 255), (300, 300)) and s.defval.kind == "hstring"
    assert (d.defval.kind, d.defval.value) == ("cstring", "SNMP agent")
    assert o.syntax.base == "OBJECT IDENTIFIER" and o.defval.value == "sysDescr"


def test_index_implied_and_augments():
    text = wrap(
        'r OBJECT-TYPE SYNTAX R MAX-ACCESS not-accessible STATUS current DESCRIPTION "d" INDEX { IMPLIED nm } ::= { t 1 }\n'
        'r2 OBJECT-TYPE SYNTAX R2 MAX-ACCESS not-accessible STATUS current DESCRIPTION "d" AUGMENTS { r } ::= { t 2 }\n',
        imports=V2_HEAD,
    )
    r, r2 = parse(text).definitions
    assert r.index[0].implied and r.index[0].name == "nm"
    assert r2.augments == "r" and r2.index == ()


# -- NOTIFICATION-TYPE (RFC 2578 8) ------------------------------------------------------------------


def test_notification_type_from_rfc2578_8_6():
    module = parse(wrap(fixture("rfc2578_8_6_notification.txt"), "ENTITY-MIB"))
    note = module.find("entConfigChange")
    assert isinstance(note, NotificationType)
    assert note.status == "current" and note.objects == () and note.reference is None
    assert note.description.startswith("An entConfigChange trap is sent")
    assert [(c.name, c.number) for c in note.oid.components] == [
        ("entityMIBTrapPrefix", None),
        (None, 1),
    ]
    prefix = module.find("entityMIBTrapPrefix")
    assert isinstance(prefix, ObjectIdentifierAssignment)


def test_notification_type_with_objects():
    note = only(
        wrap(
            'n NOTIFICATION-TYPE OBJECTS { a, b } STATUS current DESCRIPTION "d" REFERENCE "r" ::= { p 1 }'
        )
    )
    assert (
        isinstance(note, NotificationType) and note.objects == ("a", "b") and note.reference == "r"
    )


# -- TEXTUAL-CONVENTION (RFC 2579) --------------------------------------------------------------------


def test_textual_conventions_from_rfc2579_section_2():
    module = parse(fixture("rfc2579_snmpv2_tc_excerpt.mib"))
    assert module.name == "SNMPv2-TC" and module.smi == 2
    assert [d.name for d in module.definitions if isinstance(d, MacroDefinition)] == [
        "TEXTUAL-CONVENTION"
    ]
    display = module.find("DisplayString")
    assert isinstance(display, TextualConvention)
    assert display.display_hint == "255a" and display.status == "current"
    assert display.syntax.base == "OCTET STRING" and display.syntax.sizes == ((0, 255),)
    assert "NVT ASCII" in display.description
    mac = module.find("MacAddress")
    assert mac.syntax.sizes == ((6, 6),) and mac.display_hint == "1x:"
    truth = module.find("TruthValue")
    assert truth.syntax.named_numbers == (("true", 1), ("false", 2))
    assert truth.display_hint is None
    assert module.find("InstancePointer").status == "obsolete"
    assert module.find("VariablePointer").syntax.base == "OBJECT IDENTIFIER"


def test_textual_convention_requires_syntax():
    with pytest.raises(ParseError, match="lacks SYNTAX"):
        parse(wrap('T ::= TEXTUAL-CONVENTION STATUS current DESCRIPTION "d"'))


# -- RFC 2580 ---------------------------------------------------------------------------------------


def test_conformance_macros_from_rfc2580_examples():
    module = parse(wrap(fixture("rfc2580_examples.txt"), "XYZ-MIB"))
    group = module.find("snmpGroup")
    assert isinstance(group, ObjectGroup) and len(group.objects) == 7
    assert group.objects[0] == "snmpInPkts" and group.objects[-1] == "snmpEnableAuthenTraps"
    assert [(c.name, c.number) for c in group.oid.components] == [
        ("snmpMIBGroups", None),
        (None, 8),
    ]
    notes = module.find("snmpBasicNotificationsGroup")
    assert isinstance(notes, NotificationGroup)
    assert notes.notifications == ("coldStart", "authenticationFailure")
    compliance = module.find("xyzMIBCompliance")
    assert isinstance(compliance, ModuleCompliance)
    (mod,) = compliance.modules
    assert mod.name is None and len(mod.mandatory_groups) == 5
    assert mod.groups[0][0] == "xyzV1Group" and "implement XYZv1" in mod.groups[0][1]
    caps = module.find("exampleAgent")
    assert isinstance(caps, AgentCapabilities)
    assert caps.product_release == "ACME Agent release 1.1 for 4BSD."
    assert [s.name for s in caps.supports] == [
        "SNMPv2-MIB",
        "IF-MIB",
        "IP-MIB",
        "TCP-MIB",
        "UDP-MIB",
        "EVAL-MIB",
    ]
    if_mib = caps.supports[1]
    assert if_mib.includes == ("ifGeneralGroup", "ifPacketGroup")
    assert if_mib.variations[0].syntax.named_numbers == (("up", 1), ("down", 2))
    ip = caps.supports[2]
    assert [v.name for v in ip.variations] == [
        "ipDefaultTTL",
        "ipInAddrErrors",
        "ipNetToMediaEntry",
    ]
    assert ip.variations[0].syntax.ranges == ((255, 255),)
    assert ip.variations[1].access == "not-implemented"
    assert ip.variations[2].creation_requires == ("ipNetToMediaPhysAddress",)
    assert caps.supports[4].variations == ()
    assert module.smi == 2


def test_module_compliance_with_named_module_and_object_refinement():
    text = wrap(
        'c MODULE-COMPLIANCE STATUS current DESCRIPTION "d" '
        "MODULE OTHER-MIB { o 1 } MANDATORY-GROUPS { g1 } "
        'OBJECT thing SYNTAX Integer32 (1..4) WRITE-SYNTAX Integer32 (1..2) MIN-ACCESS read-only DESCRIPTION "x" '
        "MODULE MANDATORY-GROUPS { g2 } ::= { cc 1 }"
    )
    comp = only(text)
    assert isinstance(comp, ModuleCompliance)
    first, second = comp.modules
    assert first.name == "OTHER-MIB" and first.oid is not None and first.mandatory_groups == ("g1",)
    ref = first.objects[0]
    assert ref.name == "thing" and ref.min_access == "read-only"
    assert ref.syntax.ranges == ((1, 4),) and ref.write_syntax.ranges == ((1, 2),)
    assert second.name is None and second.mandatory_groups == ("g2",)


def test_conformance_refusals():
    with pytest.raises(ParseError, match="MIN-ACCESS"):
        parse(
            wrap(
                'c MODULE-COMPLIANCE STATUS current DESCRIPTION "d" MODULE OBJECT t MIN-ACCESS not-implemented DESCRIPTION "x" ::= { a 1 }'
            )
        )
    with pytest.raises(ParseError, match="lacks DESCRIPTION"):
        parse(
            wrap('c MODULE-COMPLIANCE STATUS current DESCRIPTION "d" MODULE OBJECT t ::= { a 1 }')
        )
    with pytest.raises(ParseError, match="not valid in AGENT-CAPABILITIES"):
        parse(
            wrap(
                'a AGENT-CAPABILITIES PRODUCT-RELEASE "p" STATUS deprecated DESCRIPTION "d" ::= { a 1 }'
            )
        )
    with pytest.raises(ParseError, match="lacks OBJECTS"):
        parse(wrap('g OBJECT-GROUP STATUS current DESCRIPTION "d" ::= { a 1 }'))


# -- SMIv1 (RFC 1155, 1212, 1215) ---------------------------------------------------------------------


def test_rfc1155_smi_module():
    module = parse(fixture("rfc1155_smi.mib"))
    assert module.name == "RFC1155-SMI" and module.smi == 1
    assert (
        module.exports is not None
        and "NetworkAddress" in module.exports
        and len(module.exports) == 17
    )
    internet = module.find("internet")
    assert [(c.name, c.number) for c in internet.oid.components] == [
        ("iso", None),
        ("org", 3),
        ("dod", 6),
        (None, 1),
    ]
    assert [d.name for d in module.definitions if isinstance(d, MacroDefinition)] == ["OBJECT-TYPE"]
    counter = module.find("Counter")
    assert counter.syntax.tag == "APPLICATION 1" and counter.syntax.ranges == ((0, 4294967295),)
    address = module.find("NetworkAddress")
    assert address.syntax.base == "CHOICE" and address.syntax.fields[0][0] == "internet"
    opaque = module.find("Opaque")
    assert opaque.syntax.base == "OCTET STRING" and opaque.syntax.tag == "APPLICATION 4"


def test_smiv1_object_types_from_rfc1212_4_2():
    head = "IMPORTS ObjectName FROM RFC1155-SMI;"
    module = parse(wrap(fixture("rfc1212_4_2_ipnettomedia.txt"), "RFC1213-MIB", head))
    assert module.smi == 1
    table = module.find("ipNetToMediaTable")
    assert isinstance(table, ObjectType) and table.smi == 1
    assert table.access == "not-accessible" and table.status == "mandatory"
    entry = module.find("ipNetToMediaEntry")
    assert [i.name for i in entry.index] == ["ipNetToMediaIfIndex", "ipNetToMediaNetAddress"]
    kind = module.find("ipNetToMediaType")
    assert kind.syntax.named_numbers[0] == ("other", 1)
    assert kind.description == "The type of mapping."
    assert module.find("IpNetToMediaEntry").syntax.fields[1] == (
        "ipNetToMediaPhysAddress",
        grammar.Syntax("OCTET STRING"),
    )


def test_smiv1_description_is_optional_and_v1_status_words():
    obj = only(wrap("x OBJECT-TYPE SYNTAX INTEGER ACCESS read-write STATUS optional ::= { a 1 }"))
    assert isinstance(obj, ObjectType) and obj.smi == 1 and obj.description is None
    with pytest.raises(ParseError, match="not valid in SMIv1"):
        parse(wrap("x OBJECT-TYPE SYNTAX INTEGER ACCESS read-create STATUS mandatory ::= { a 1 }"))
    with pytest.raises(ParseError, match="not valid in SMIv1"):
        parse(wrap("x OBJECT-TYPE SYNTAX INTEGER ACCESS read-only STATUS current ::= { a 1 }"))


def test_smiv1_index_types_and_defval_forms():
    # RFC 1212 4 (IndexType may be a type) and 4.1.7 (DEFVAL examples)
    text = wrap(
        "e OBJECT-TYPE SYNTAX E ACCESS not-accessible STATUS mandatory "
        'DESCRIPTION "d" INDEX { INTEGER, OCTET STRING (SIZE (6)), IpAddress, ifIndex } ::= { t 1 }\n'
        "n OBJECT-TYPE SYNTAX NetworkAddress ACCESS read-write STATUS mandatory "
        "DEFVAL { { internet 'c0210415'h } } ::= { t 2 }\n"
        "m OBJECT-TYPE SYNTAX IpAddress ACCESS read-write STATUS mandatory DEFVAL { 'c0210415'h } ::= { t 3 }\n"
        "o OBJECT-TYPE SYNTAX OBJECT IDENTIFIER ACCESS read-write STATUS mandatory DEFVAL { { system 2 } } ::= { t 4 }\n"
        "z OBJECT-TYPE SYNTAX INTEGER (0..MAX) ACCESS read-write STATUS mandatory DEFVAL { NULL } ::= { t 5 }\n"
    )
    e, n, m, o, z = parse(text).definitions
    assert [(i.name, i.syntax.base if i.syntax else None) for i in e.index] == [
        (None, "INTEGER"),
        (None, "OCTET STRING"),
        (None, "IpAddress"),
        ("ifIndex", None),
    ]
    assert e.index[1].syntax.sizes == ((6, 6),)
    assert n.defval.kind == "bits" and n.defval.value == ("internet", "c0210415")
    assert m.defval.kind == "hstring"
    assert o.defval.value == ("system", "2")
    assert z.syntax.ranges == ((0, "MAX"),)
    assert z.defval.kind == "keyword" and z.defval.value == "NULL"


def test_trap_type_from_rfc1215_2_2():
    module = parse(wrap(fixture("rfc1215_2_2_traps.txt")))
    assert module.smi == 1
    link = module.find("myLinkDown")
    assert isinstance(link, TrapType)
    assert link.enterprise.components[0].name == "myEnterprise"
    assert link.variables == ("ifIndex",) and link.number == 2
    assert link.description is not None and link.description.startswith("A myLinkDown trap")
    cold = module.find("coldStart")
    assert (
        cold.number == 0 and cold.variables == () and cold.enterprise.components[0].name == "snmp"
    )
    with pytest.raises(ParseError, match="lacks ENTERPRISE"):
        parse(wrap('t TRAP-TYPE DESCRIPTION "d" ::= 1'))


# -- hostile input -----------------------------------------------------------------------------------


def test_deeply_nested_sequence_is_refused_not_a_recursion_error():
    nested = "X ::= " + "SEQUENCE { a " * 200 + "INTEGER" + " }" * 200
    with pytest.raises(ParseError, match="nested too deeply"):
        parse(wrap(nested))


def test_unterminated_and_garbage_input_raise_parse_errors_with_positions():
    for text in (
        "M DEFINITIONS ::= BEGIN x OBJECT-TYPE SYNTAX",
        "M DEFINITIONS ::= BEGIN x OBJECT-TYPE ::= END",
        "M DEFINITIONS ::= BEGIN 123 END",
        "M DEFINITIONS ::= BEGIN x INTEGER ::= 5 END",
        "M DEFINITIONS ::= BEGIN X MACRO ::= BEGIN",
        "",
    ):
        with pytest.raises((ParseError, ValueError)) as info:
            parse(text)
        assert hasattr(info.value, "line")


def test_huge_number_in_oid_is_a_parse_error():
    with pytest.raises(ParseError):
        parse(wrap("x OBJECT IDENTIFIER ::= { a " + "9" * 5000 + " }"))
