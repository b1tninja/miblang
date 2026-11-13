"""The bundled SMI base modules: hashes, provenance, and that each one parses."""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import pathlib
import re
import sys

import pytest

from miblang import bundled
from miblang.grammar import MacroDefinition, ObjectType, TextualConvention
from miblang.resolve import Mib

DATA = pathlib.Path(bundled.__file__).parent / "data"
EXPECTED = (
    "IF-MIB",
    "RFC1155-SMI",
    "RFC1213-MIB",
    "SNMPv2-CONF",
    "SNMPv2-MIB",
    "SNMPv2-SMI",
    "SNMPv2-TC",
)
OPTIONAL = ("IF-MIB", "SNMPv2-MIB")


def test_bundle_names_and_manifest_hashes():
    assert bundled.names() == EXPECTED
    for name in EXPECTED:
        entry = bundled.manifest()[name]
        assert hashlib.sha256((DATA / f"{name}.mib").read_bytes()).hexdigest() == entry["sha256"]
        assert len(str(entry["rfc_txt_sha256"])) == 64
        assert entry["status"]


def test_tampered_module_is_refused(monkeypatch):
    real = bundled.manifest()
    fake = {k: dict(v) for k, v in real.items()}
    fake["SNMPv2-TC"]["sha256"] = "0" * 64
    monkeypatch.setattr(bundled, "manifest", lambda: fake)
    with pytest.raises(bundled.BundleError, match="sha256"):
        bundled.text("SNMPv2-TC")
    with pytest.raises(bundled.BundleError, match="no bundled"):
        bundled.text("NO-SUCH-MIB")


def test_every_bundled_module_parses_with_its_own_name_and_dialect():
    dialect = {
        "IF-MIB": 2,
        "SNMPv2-MIB": 2,
        "RFC1155-SMI": 1,
        "RFC1213-MIB": 1,
        "SNMPv2-SMI": 2,
        "SNMPv2-TC": 2,
        "SNMPv2-CONF": 2,
    }
    for name in EXPECTED:
        module = bundled.load_module(name)
        assert module.name == name and module.smi == dialect[name]


def test_bundled_modules_hold_the_rfc_definitions():
    tc = bundled.load_module("SNMPv2-TC")
    assert isinstance(tc.find("RowStatus"), TextualConvention)
    assert isinstance(tc.find("DateAndTime"), TextualConvention)
    assert len([d for d in tc.definitions if isinstance(d, TextualConvention)]) == 16
    conf = bundled.load_module("SNMPv2-CONF")
    macros = [d.name for d in conf.definitions if isinstance(d, MacroDefinition)]
    assert macros == [
        "OBJECT-GROUP",
        "NOTIFICATION-GROUP",
        "MODULE-COMPLIANCE",
        "AGENT-CAPABILITIES",
    ]
    mib2 = bundled.load_module("RFC1213-MIB")
    objects = [d for d in mib2.definitions if isinstance(d, ObjectType)]
    assert len(objects) > 150 and mib2.find("sysDescr") is not None


def test_errata_recorded_not_applied():
    tc = bundled.manifest()["SNMPv2-TC"]
    assert [e.split()[0] for e in tc["errata_not_applied"]] == ["415", "416", "417"]
    assert "0..65536" in bundled.text("SNMPv2-TC")  # the published text, uncorrected
    assert json.loads((DATA / "MANIFEST.json").read_text())[0]["module"] == "RFC1155-SMI"


# --------------------------------------------------------------------------- IF-MIB (RFC 2863) and SNMPv2-MIB


def _fetch_tool():
    """tools/fetch_iana_mibs.py, loaded once and shared with tests/test_iana_mibs.py."""
    if "fetch_iana_mibs" in sys.modules:
        return sys.modules["fetch_iana_mibs"]
    spec = importlib.util.spec_from_file_location(
        "fetch_iana_mibs",
        pathlib.Path(__file__).resolve().parents[1] / "tools" / "fetch_iana_mibs.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fetch_iana_mibs"] = module
    spec.loader.exec_module(module)
    return module


def _ianaiftype():
    """The cached IANAifType-MIB and its pin; the test skips, loudly, when the cache is absent."""
    fetch = _fetch_tool()
    pin = next(p for p in fetch.PINS if p.module == "IANAifType-MIB")
    path = fetch.cache_dir() / pin.filename
    problem = fetch.check(path, pin)
    if problem is not None:
        pytest.skip(
            f"SKIPPED LOUDLY: {pin.filename} in {fetch.cache_dir()}: {problem}; run tools/fetch_iana_mibs.py"
        )
    return path, pin


def _smiv2_mib() -> Mib:
    """The SMIv2 modules and nothing from RFC 1213: the IF-MIB and SNMPv2-MIB below replace MIB-II's groups."""
    mib = Mib()
    for name in ("SNMPv2-SMI", "SNMPv2-TC", "SNMPv2-CONF", "SNMPv2-MIB", "IF-MIB"):
        mib.add(bundled.load_module(name))
    return mib


def test_if_mib_and_snmpv2_mib_are_optional_and_the_default_mib_does_not_hold_them():
    assert bundled.default_names() == tuple(n for n in EXPECTED if n not in OPTIONAL)
    for name in OPTIONAL:
        assert bundled.manifest()[name]["optional"] is True
    for name in bundled.default_names():
        assert "optional" not in bundled.manifest()[name]
    plain = Mib.with_bundled()
    assert set(plain.modules) == set(bundled.default_names())
    assert plain.problems == []
    both = Mib.with_bundled("SNMPv2-MIB", "IF-MIB")
    assert {"IF-MIB", "SNMPv2-MIB"} <= set(both.modules)
    with pytest.raises(bundled.BundleError, match="no bundled"):
        Mib.with_bundled("NO-SUCH-MIB")


def test_if_mib_manifest_names_the_rfc_the_lines_and_the_errata_not_applied():
    entry = bundled.manifest()["IF-MIB"]
    assert entry["rfc"] == 2863
    assert "Draft Standard" in str(entry["status"])
    assert "RFC 8892" in str(entry["status"])
    first, last = entry["lines"]
    assert (first, last) == (1423, 3549)  # DEFINITIONS ::= BEGIN to END in rfc2863.txt
    assert [e.split()[0] for e in entry["errata_not_applied"]] == ["4820"]
    text = bundled.text("IF-MIB")
    assert text.startswith("IF-MIB DEFINITIONS ::= BEGIN\n")
    assert text.endswith("\nEND\n")
    assert "\f" not in text
    assert "[Page" not in text
    assert not re.search(
        r"^RFC \d+ .*\d{4}$", text, re.MULTILINE
    )  # the running page header is gone
    snmp = bundled.manifest()["SNMPv2-MIB"]
    assert snmp["rfc"] == 3418
    assert snmp["lines"] == [104, 1096]
    assert bundled.text("SNMPv2-MIB").startswith("SNMPv2-MIB DEFINITIONS ::= BEGIN\n")


def test_if_mib_parses_with_the_definitions_rfc_2863_lists():
    module = bundled.load_module("IF-MIB")
    assert module.name == "IF-MIB"
    assert module.smi == 2
    kinds = collections.Counter(type(d).__name__ for d in module.definitions)
    assert kinds["ObjectType"] == 66
    assert kinds["TextualConvention"] == 3  # OwnerString, InterfaceIndex, InterfaceIndexOrZero
    assert kinds["NotificationType"] == 2  # linkDown, linkUp
    assert kinds["ModuleCompliance"] == 3
    # Counted from the text, not from the parser: each OBJECT-TYPE macro use is one line with that word,
    # and the module also names the macro once, in its IMPORTS.
    uses = [ln for ln in bundled.text("IF-MIB").splitlines() if "OBJECT-TYPE" in ln]
    assert len(uses) == kinds["ObjectType"] + 1


def test_if_mib_resolves_with_ianaiftype():
    """The real IF-MIB, cut from RFC 2863, resolved against the real IANAifType-MIB (the cached registry)."""
    path, pin = _ianaiftype()
    mib = _smiv2_mib()
    mib.add_text(path.read_text("ascii"), path=str(path), sha256=pin.sha256)
    assert (
        mib.problems == []
    )  # every import of IF-MIB is defined: SMI, TC, CONF, SNMPv2-MIB, IANAifType-MIB

    if_type = mib.resolve("IF-MIB::ifType")
    assert if_type.oid == (1, 3, 6, 1, 2, 1, 2, 2, 1, 3)
    assert if_type.role == "column"
    info = if_type.type
    assert info is not None
    assert (info.name, info.base, info.textual_convention) == (
        "IANAifType",
        "INTEGER",
        "IANAifType",
    )
    assert info.resolved
    assert dict(info.named_numbers)["ethernetCsmacd"] == 6
    assert dict(info.named_numbers)["softwareLoopback"] == 24

    # the same OIDs answer in IF-MIB's own terms, as the SMIv2 definitions say them
    assert mib.resolve("ifHighSpeed").dotted == "1.3.6.1.2.1.31.1.1.1.15"
    speed = mib.resolve("ifSpeed").type
    assert speed is not None
    assert speed.name == "Gauge32"
    assert speed.ranges == (
        (0, 4294967295),
    )  # (2**32)-1, which is what erratum 4820 says the prose should
    hint = mib.resolve("ifPhysAddress").type
    assert hint is not None
    assert (hint.name, hint.display_hint) == ("PhysAddress", "1x:")
    assert dict(mib.resolve("ifAdminStatus").type.named_numbers) == {
        "up": 1,
        "down": 2,
        "testing": 3,
    }

    # instances: a plain index, an AUGMENTS table and a two-column index
    one = mib.index("1.3.6.1.2.1.2.2.1.3.7")
    assert one is not None
    assert (one.object.name, one.object.module) == ("ifType", "IF-MIB")
    assert [(v.name, v.value) for v in one.index] == [("ifIndex", 7)]
    augmented = mib.index("1.3.6.1.2.1.31.1.1.1.1.5")
    assert augmented is not None
    assert (augmented.object.name, [v.value for v in augmented.index]) == ("ifName", [5])
    stack = mib.index("1.3.6.1.2.1.31.1.2.1.3.2.1")
    assert stack is not None
    assert [(v.name, v.value) for v in stack.index] == [
        ("ifStackHigherLayer", 2),
        ("ifStackLowerLayer", 1),
    ]

    # the notifications live under snmpTraps, which SNMPv2-MIB defines
    link_down = mib.resolve("IF-MIB::linkDown")
    assert link_down.dotted == "1.3.6.1.6.3.1.1.5.3"
    assert link_down.definition.objects == ("ifIndex", "ifAdminStatus", "ifOperStatus")

    # provenance names the RFC, the bundled hash and the module's own revision; IANAifType's names its file
    answer = mib.provenance("1.3.6.1.2.1.2.2.1.3.7")
    assert answer.module == "IF-MIB"
    assert answer.rfc == 2863
    assert answer.source == "bundled"
    assert answer.sha256 == bundled.manifest()["IF-MIB"]["sha256"]
    assert answer.revision == "200006140000Z"
    ianaa = mib.provenance("1.3.6.1.2.1.30")
    assert ianaa.module == "IANAifType-MIB"
    assert ianaa.path == str(path)
    assert ianaa.sha256 == pin.sha256


def test_if_mib_without_ianaiftype_reports_the_import_it_cannot_resolve():
    mib = _smiv2_mib()
    info = mib.resolve("IF-MIB::ifType").type
    assert info is not None
    assert not info.resolved
    assert any("IANAifType" in p for p in mib.problems)
    assert not any(
        "snmpTraps" in p for p in mib.problems
    )  # SNMPv2-MIB is bundled, so that import resolves
    assert mib.resolve("IF-MIB::linkUp").dotted == "1.3.6.1.6.3.1.1.5.4"


def test_a_mib_holding_rfc_1213_and_if_mib_answers_a_bare_oid_from_the_smiv2_module_and_reports_the_overlap():
    """PORTFOLIO section 9 item 15: the SMIv2 module wins an overlapping OID, and the overlap is reported."""
    mib = Mib.with_bundled("SNMPv2-MIB", "IF-MIB")
    assert mib.resolve("IF-MIB::ifSpeed").module == "IF-MIB"
    assert mib.resolve("RFC1213-MIB::ifSpeed").module == "RFC1213-MIB"
    assert mib.provenance("1.3.6.1.2.1.2.2.1.5.1").module == "IF-MIB"
    assert mib.resolve("1.3.6.1.2.1.2.2.1.5").module == "IF-MIB"
    assert mib.resolve("1.3.6.1.2.1.1.1").module == "SNMPv2-MIB"
    assert [o.module for o in mib.objects_at((1, 3, 6, 1, 2, 1, 2, 2, 1, 5))] == [
        "IF-MIB",
        "RFC1213-MIB",
    ]
    overlaps = [p for p in mib.problems if p.startswith("OID overlap")]
    assert any("IF-MIB and RFC1213-MIB both define" in p for p in overlaps)
    assert any("SNMPv2-MIB and RFC1213-MIB both define" in p for p in overlaps)
    assert all("IANAifType" in p or p.startswith("OID overlap") for p in mib.problems)
    # no SMIv2 module loaded: the bundle alone has no overlap to report
    assert not [p for p in Mib.with_bundled().problems if "overlap" in p]


def test_the_bundle_matches_what_extract_bundle_cuts_from_the_rfclib_corpus():
    """tools/extract_bundle.py with no argument reads the corpus the rfclib MCP server uses, read only."""
    spec = importlib.util.spec_from_file_location(
        "extract_bundle",
        pathlib.Path(__file__).resolve().parents[1] / "tools" / "extract_bundle.py",
    )
    assert spec is not None
    assert spec.loader is not None
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    mirror = tool.default_mirror()
    if not (mirror / "rfc2863.txt").is_file():
        pytest.skip(
            f"SKIPPED LOUDLY: no RFC text in {mirror}; set RFCLIB_HOME to the data directory of the rfclib server"
        )
    files = tool.build(mirror)
    assert sorted(files) == sorted([*(f"{n}.mib" for n in EXPECTED), "MANIFEST.json"])
    for name, text in files.items():
        assert (DATA / name).read_bytes() == text.encode("ascii"), name


def _extract_tool():
    spec = importlib.util.spec_from_file_location(
        "extract_bundle_fetch",
        pathlib.Path(__file__).resolve().parents[1] / "tools" / "extract_bundle.py",
    )
    assert spec is not None
    assert spec.loader is not None
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def test_the_bundle_matches_what_is_cut_from_the_pinned_rfc_editor_text():
    """``extract_bundle.py --fetch --check``, the CI form: the RFC text comes from a cache outside the
    repository, each file pinned by the manifest's sha256 and the tool's size, and the bundle is rebuilt from it
    byte for byte. This test never touches the network; it skips loudly when the cache is not filled."""
    tool = _extract_tool()
    root = tool.cache_dir()
    pins = tool.pinned_hashes()
    for _, rfc, *_ in tool.MODULES:
        problem = tool.check_rfc(root / f"rfc{rfc}.txt", rfc, pins[rfc])
        if problem is not None:
            pytest.skip(
                f"SKIPPED LOUDLY: rfc{rfc}.txt in {root}: {problem}; run tools/extract_bundle.py --fetch --check"
            )
    files = tool.build(tool.fetch_rfcs(root, network=False))
    assert sorted(files) == sorted([*(f"{n}.mib" for n in EXPECTED), "MANIFEST.json"])
    for name, text in files.items():
        assert (DATA / name).read_bytes() == text.encode("ascii"), name


def test_every_rfc_the_bundle_is_cut_from_has_a_pinned_size_and_hash():
    tool = _extract_tool()
    rfcs = {module[1] for module in tool.MODULES}
    assert rfcs == set(tool.RFC_SIZES)
    assert rfcs == set(tool.pinned_hashes())
    assert all(len(h) == 64 for h in tool.pinned_hashes().values())


def test_a_download_that_does_not_match_its_pin_is_discarded_not_installed(tmp_path, monkeypatch):
    tool = _extract_tool()
    monkeypatch.setattr(tool, "INTERVAL", 0.0)

    class Reply:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, limit: int) -> bytes:
            return self.data[:limit]

    asked = []

    def wrong(request, timeout):
        asked.append(request.full_url)
        return Reply(b"x" * tool.RFC_SIZES[1155])  # the right size, the wrong bytes

    monkeypatch.setattr(tool.urllib.request, "urlopen", wrong)
    with pytest.raises(SystemExit, match="sha256 differs"):
        tool.fetch_rfcs(tmp_path)
    assert asked == ["https://www.rfc-editor.org/rfc/rfc1155.txt"]  # stopped at the first bad file
    assert list(tmp_path.iterdir()) == []  # nothing installed, and the temporary file is gone

    def short(request, timeout):
        return Reply(b"short")

    monkeypatch.setattr(tool.urllib.request, "urlopen", short)
    with pytest.raises(SystemExit, match="size 5"):
        tool.fetch_rfcs(tmp_path)
    with pytest.raises(SystemExit, match="not in the cache"):
        tool.fetch_rfcs(tmp_path, network=False)
