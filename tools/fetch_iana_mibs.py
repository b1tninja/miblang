"""Fetch the IANA-maintained MIB modules into a cache outside the repository.

    python tools/fetch_iana_mibs.py            fetch what is missing, verify every file, report
    python tools/fetch_iana_mibs.py --verify   verify only, never touch the network

The cache is ``$MIBLANG_DATA_CACHE`` when set, otherwise ``%LOCALAPPDATA%\\miblang-data`` on Windows and
``$XDG_CACHE_HOME/miblang-data`` (default ``~/.cache/miblang-data``) elsewhere; modules land in its ``iana``
directory as ``<module name>.mib``. Nothing is written into the repository.

The list is the "IANA-Maintained MIBs" table at https://www.iana.org/assignments/mib-modules (last updated
2026-09-30 on the day it was read, 2026-11-13), and each module is fetched from
``https://www.iana.org/assignments/<slug>/<slug>``, the plain-text file the registry links. Each file is pinned
by sha256 and size and carries the LAST-UPDATED of its MODULE-IDENTITY. IANA revises these modules (IANAifType-MIB
gains a value whenever an interface type is registered), so a changed upstream file fails the pin and is
discarded, and updating the table is a deliberate edit. Requests run one per second, smallest file first, with
a plain User-Agent that carries no personal detail.

Why this does not use the primarysource ``iana`` collection: that collection imports registries as XML from
``/assignments/<name>/<name>.xml``, and a MIB module is a text file at ``/assignments/<name>/<name>`` with no XML
form.

Terms read on 2026-11-13 at https://www.iana.org/help/licensing-terms (revised 2021-11-10): the Protocol
Registries linked from https://www.iana.org/protocols, which lists these MIB modules, may be freely used by any
party for any purpose and are dedicated under CC0 1.0; the statement excludes the RFC documents linked from
those pages, and no warranty is given. The modules carry no copyright header of their own. CC0 would permit
vendoring them; they are not vendored, because they change.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE = "https://www.iana.org/assignments/"
USER_AGENT = "portfolio-fetch/1"
INTERVAL = 1.0  # seconds between requests


@dataclass(frozen=True, slots=True)
class Pin:
    slug: str
    module: str
    size: int
    sha256: str
    last_updated: str

    @property
    def url(self) -> str:
        return f"{BASE}{self.slug}/{self.slug}"

    @property
    def filename(self) -> str:
        return f"{self.module}.mib"


#: Smallest first. Read 2026-11-13 from the IANA list; sha256 and size of the bytes served that day.
PINS = (
    Pin(
        "ianastoragemediatype-mib",
        "IANA-STORAGE-MEDIA-TYPE-MIB",
        2389,
        "91715eb50e48ab5b20b091ad1d330a72cee43bef3685933b709e34a81421334b",
        "201606170000Z",
    ),
    Pin(
        "ianamalloc-mib",
        "IANA-MALLOC-MIB",
        2456,
        "64adefc9840b104566558d8110f39e342dff5f2d9153959b9ce43bab27e251e2",
        "201405220000Z",
    ),
    Pin(
        "ianaenergyrelation-mib",
        "IANA-ENERGY-RELATION-MIB",
        2962,
        "45686b94086fe1fe7b154f3cbe7e68e441a69302f4d0ba5a9e0ab9f1225d8f2a",
        "201502090000Z",
    ),
    Pin(
        "ianaolsrv2linkmetrictype-mib",
        "IANA-OLSRv2-LINK-METRIC-TYPE-MIB",
        3089,
        "61ad094eb2921e4df615ed41f15f3baf39898dbe3e6e56992047779c6b51e506",
        "201404090000Z",
    ),
    Pin(
        "ianapowerstateset-mib",
        "IANAPowerStateSet-MIB",
        3523,
        "f679ba1680227d59b555b30a80248ea72990678ecf174cc1e8c45729f3cd1560",
        "201502090000Z",
    ),
    Pin(
        "ianaiprouteprotocol-mib",
        "IANA-RTPROTO-MIB",
        4109,
        "899410c559dd2e7ca9846ec8cc3c0e84c5f9f4c66c8b43db09d2178912eba677",
        "201604250000Z",
    ),
    Pin(
        "ianagbondtc-mib",
        "IANA-GBOND-TC-MIB",
        4314,
        "22dd0afde0bb64a33c6eae2f94c950e1787a539cef7f5ebc87de80bc15d6e4b8",
        "201706230000Z",
    ),
    Pin(
        "ianalanguage-mib",
        "IANA-LANGUAGE-MIB",
        4717,
        "fdc2329b9d311ce17bdc4bb69d3054bdff08a88ab8afa60e1e1744e1eca770eb",
        "201405220000Z",
    ),
    Pin(
        "ianasmf-mib",
        "IANA-SMF-MIB",
        6317,
        "6afc0513390635c0e4f05f355b22c2d7dd9a9889a135b3e5a044817b2da48cbe",
        "201408140000Z",
    ),
    Pin(
        "ianaentity-mib",
        "IANA-ENTITY-MIB",
        6880,
        "545cf9190c57fc58fc8bb87ab41b260a25635c0a0c0a5d0c8095eaabae77952e",
        "201507160000Z",
    ),
    Pin(
        "ianabfdtcstd-mib",
        "IANA-BFD-TC-STD-MIB",
        7104,
        "5617e0077c1e21cce1e3fc318cd2d2d1ff49c495c7b8f405f226141f3176d02d",
        "202511250000Z",
    ),
    Pin(
        "ianaaddressfamilynumbers-mib",
        "IANA-ADDRESS-FAMILY-NUMBERS-MIB",
        8517,
        "199cb8484daf5a99e1ca01ce7dfc169f4221d1eccdf5ce712e293786d80753fa",
        "202110190000Z",
    ),
    Pin(
        "ianafinisher-mib",
        "IANA-FINISHER-MIB",
        9286,
        "a6c473c5745044f6522cc7f6c80734ac82eaaae8b20e8446d7a156b087e1df89",
        "201405220000Z",
    ),
    Pin(
        "ianacharset-mib",
        "IANA-CHARSET-MIB",
        11254,
        "55d3553194e108eb3f036e1cc6f8ebd10695a0301255f99b7b0308274ccc70cc",
        "202101040000Z",
    ),
    Pin(
        "ianatn3270etc-mib",
        "IANATn3270eTC-MIB",
        12490,
        "b6d46da82a0cab1d9ff1ad9905b9b86cd74633d9dbf1861e42aa88b6411d450f",
        "201405220000Z",
    ),
    Pin(
        "ianaitualarmtc-mib",
        "IANA-ITU-ALARM-TC-MIB",
        14310,
        "ed61aad5eba4648e48ef04165b44c537f190c1bd15ff14a7d1768aaae9b8a6ce",
        "201405220000Z",
    ),
    Pin(
        "ianagmplstc-mib",
        "IANA-GMPLS-TC-MIB",
        16091,
        "ec9fd0940660498e032bb7fe49857f37c82f2a0f2196164ab6767fc564fc1fdd",
        "201511040000Z",
    ),
    Pin(
        "ianaippmmetricsregistry-mib",
        "IANA-IPPM-METRICS-REGISTRY-MIB",
        25248,
        "8a1b332cc387ec0301c32932aa2234a9fc246d590546d7aa1993f53a7542d08b",
        "201508140000Z",
    ),
    Pin(
        "ianaiftype-mib",
        "IANAifType-MIB",
        39843,
        "17b4d02e998ea023dea1fb85ebe73d65ed44dfc7180dffc286a15f956d6cec2f",
        "202610230000Z",
    ),
    Pin(
        "ianamau-mib",
        "IANA-MAU-MIB",
        95549,
        "310758ff69da3ea184fc35f86a9d9f94592f644c0e4aece33ec78bbced971bdc",
        "202607150000Z",
    ),
    Pin(
        "ianaprinter-mib",
        "IANA-PRINTER-MIB",
        109179,
        "2c14edf82df3644292faabf825db91bdd9e335a5596ade9a7e0d51d3f96fe5c4",
        "202402060000Z",
    ),
)


def cache_dir() -> Path:
    """The directory the modules are kept in: ``<cache>/iana``."""
    override = os.environ.get("MIBLANG_DATA_CACHE")
    if override:
        root = Path(override)
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "miblang-data"
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "miblang-data"
    return root / "iana"


def check(path: Path, pin: Pin) -> str | None:
    """None when ``path`` is the pinned file, else why it is not."""
    if not path.is_file():
        return "missing"
    raw = path.read_bytes()
    if len(raw) != pin.size:
        return f"size {len(raw)}, pinned {pin.size}"
    if hashlib.sha256(raw).hexdigest() != pin.sha256:
        return "sha256 differs from the pin"
    return None


def _download(pin: Pin, destination: Path) -> None:
    request = urllib.request.Request(pin.url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        raw = response.read(pin.size + 1)
    if len(raw) != pin.size or hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise SystemExit(
            f"{pin.slug}: the download does not match the pin ({len(raw)} bytes); not installed"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, delete=False, suffix=".part"
    ) as handle:
        handle.write(raw)
    Path(handle.name).replace(destination)


def main(argv: list[str]) -> int:
    verify_only = "--verify" in argv
    root = cache_dir()
    failures = 0
    requested = False
    for pin in sorted(PINS, key=lambda p: p.size):
        path = root / pin.filename
        problem = check(path, pin)
        if problem is not None and not verify_only:
            if requested:
                time.sleep(INTERVAL)
            requested = True
            _download(pin, path)
            problem = check(path, pin)
        failures += problem is not None
        print(
            f"{pin.module}  {pin.size}  {pin.sha256}  {pin.last_updated}  {'ok' if problem is None else problem}"
        )
    print(f"cache: {root}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
