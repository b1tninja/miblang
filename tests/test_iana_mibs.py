"""The IANA-maintained MIB modules, read from a cache outside the repository.

``tools/fetch_iana_mibs.py`` fetches the 21 modules of IANA's "IANA-Maintained MIBs" table into
``$MIBLANG_DATA_CACHE`` (else the user cache directory), each pinned by sha256 and size. Every test here skips,
loudly, when the cache is absent or a file does not match its pin. Nothing from the modules is copied into the
repository. The module that imports IANAifType-MIB is the real IF-MIB, bundled from RFC 2863 (``miblang.bundled``);
tests/test_bundled.py holds the detailed end-to-end resolution test, this file the one over the whole IANA set.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest

from miblang import bundled
from miblang.grammar import ModuleIdentity
from miblang.resolve import Mib

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "fetch_iana_mibs.py"
_spec = importlib.util.spec_from_file_location("fetch_iana_mibs", _TOOL)
assert _spec is not None
assert _spec.loader is not None
fetch = importlib.util.module_from_spec(_spec)
sys.modules["fetch_iana_mibs"] = fetch
_spec.loader.exec_module(fetch)


def _cached(pin) -> Path:
    root = fetch.cache_dir()
    problem = fetch.check(root / pin.filename, pin)
    if problem is not None:
        pytest.skip(
            f"SKIPPED LOUDLY: {pin.filename} in {root}: {problem}; run tools/fetch_iana_mibs.py"
        )
    return root / pin.filename


def _pin(module: str):
    return next(p for p in fetch.PINS if p.module == module)


def _all() -> list[Path]:
    return [_cached(pin) for pin in fetch.PINS]


def test_the_pin_table_names_the_21_modules_of_the_iana_list():
    assert len(fetch.PINS) == 21
    assert len({p.module for p in fetch.PINS}) == 21
    assert [p.size for p in fetch.PINS] == sorted(p.size for p in fetch.PINS)
    assert all(re.fullmatch(r"[0-9a-f]{64}", p.sha256) for p in fetch.PINS)
    assert all(p.url == f"https://www.iana.org/assignments/{p.slug}/{p.slug}" for p in fetch.PINS)
    assert _pin("IANAifType-MIB").size == 39843


def test_every_iana_module_parses_as_smiv2_with_its_pinned_revision():
    for path in _all():
        mib = Mib()
        module = mib.add_text(path.read_text("ascii"))
        pin = next(p for p in fetch.PINS if p.filename == path.name)
        assert module.name == pin.module
        assert module.smi == 2
        identity = next(d for d in module.definitions if isinstance(d, ModuleIdentity))
        assert identity.last_updated == pin.last_updated


def test_the_whole_set_loads_with_the_bundle_and_every_import_is_defined():
    mib = Mib.with_bundled()
    for path in _all():
        mib.add_text(path.read_text("ascii"), path=str(path))
    assert len(mib.modules) == 26
    assert mib.resolve("IANAifType-MIB::ianaifType").oid == (1, 3, 6, 1, 2, 1, 30)
    assert mib.resolve("IANA-MAU-MIB::ianaMauMIB").oid == (1, 3, 6, 1, 2, 1, 154)
    assert mib.problems == []


def test_ianaiftype_enumeration_matches_the_text_read_independently():
    path = _cached(_pin("IANAifType-MIB"))
    text = path.read_text("ascii")
    start = text.index("IANAifType ::= TEXTUAL-CONVENTION")
    block_start = text.index("INTEGER {", start)
    block = re.sub(r"--[^\n]*", "", text[block_start + 9 : text.index("}", block_start)])
    expected = {
        name: int(number)
        for name, number in re.findall(r"([A-Za-z][A-Za-z0-9-]*)\s*\((\d+)\)", block)
    }
    mib = Mib.with_bundled()
    mib.add_text(text)
    info = mib.type_info(mib._modules["IANAifType-MIB"].find("IANAifType").syntax, "IANAifType-MIB")
    assert dict(info.named_numbers) == expected
    assert len(expected) == 305
    assert expected["ethernetCsmacd"] == 6
    assert expected["other"] == 1


def test_a_module_that_imports_ianaiftype_resolves_end_to_end():
    """The real IF-MIB (RFC 2863, bundled) against the cached IANAifType-MIB, with the whole IANA set loaded."""
    iana = _cached(_pin("IANAifType-MIB"))
    mib = Mib()
    for name in ("SNMPv2-SMI", "SNMPv2-TC", "SNMPv2-CONF", "SNMPv2-MIB", "IF-MIB"):
        mib.add(bundled.load_module(name))
    for path in _all():
        mib.add_text(
            path.read_text("ascii"),
            path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    assert mib.problems == []
    column = mib.resolve("IF-MIB::ifType")
    assert column.oid == (1, 3, 6, 1, 2, 1, 2, 2, 1, 3)
    assert column.role == "column"
    info = column.type
    assert info is not None
    assert info.name == "IANAifType"
    assert info.base == "INTEGER"
    assert info.textual_convention == "IANAifType"
    assert info.resolved
    assert len(info.named_numbers) == 305
    assert dict(info.named_numbers)["ethernetCsmacd"] == 6
    instance = mib.index("1.3.6.1.2.1.2.2.1.3.7")
    assert instance is not None
    assert instance.object.name == "ifType"
    assert [v.value for v in instance.index] == [7]
    # the IF-MIB answer is bundled, with the manifest hash and the module's own revision; IANAifType's is a file
    answer = mib.provenance("1.3.6.1.2.1.2.2.1.3.7")
    assert answer.module == "IF-MIB"
    assert answer.source == "bundled"
    assert answer.sha256 == bundled.manifest()["IF-MIB"]["sha256"]
    assert answer.revision == "200006140000Z"
    ianaa = mib.provenance("1.3.6.1.2.1.30")
    assert ianaa.module == "IANAifType-MIB"
    assert ianaa.path == str(iana)
    assert ianaa.sha256 == _pin("IANAifType-MIB").sha256
    assert ianaa.revision == _pin("IANAifType-MIB").last_updated


def test_a_changed_iana_file_is_refused_by_the_pin(tmp_path):
    pin = _pin("IANA-STORAGE-MEDIA-TYPE-MIB")
    path = _cached(pin)
    changed = tmp_path / pin.filename
    changed.write_bytes(path.read_bytes() + b"\n")
    assert fetch.check(changed, pin) is not None
    assert fetch.check(path, pin) is None
