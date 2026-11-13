"""The bundled SMI base modules: hashes, provenance, and that each one parses."""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from miblang import bundled
from miblang.grammar import MacroDefinition, ObjectType, TextualConvention

DATA = pathlib.Path(bundled.__file__).parent / "data"
EXPECTED = ("RFC1155-SMI", "RFC1213-MIB", "SNMPv2-CONF", "SNMPv2-SMI", "SNMPv2-TC")


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
        bundled.text("IF-MIB")


def test_every_bundled_module_parses_with_its_own_name_and_dialect():
    dialect = {
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
