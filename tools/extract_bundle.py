#!/usr/bin/env python3
"""Rebuild ``miblang/data/`` from the RFC Editor text that rfclib mirrors.

    python tools/extract_bundle.py                        # the corpus the rfclib MCP server uses
    python tools/extract_bundle.py <mirror-dir>           # or the directory holding rfc1155.txt, rfc2578.txt, ...
    python tools/extract_bundle.py [<mirror-dir>] --check # exit 1 when the bundle differs
    python tools/extract_bundle.py --fetch --check        # the CI form: no rfclib needed

``--fetch`` reads the RFC text from a cache outside the repository (``$MIBLANG_DATA_CACHE``, else the user cache
directory, then ``rfc``), filling what is missing from ``https://www.rfc-editor.org/rfc/rfc<N>.txt`` at one
request per second. Each file is pinned by the sha256 the committed ``MANIFEST.json`` records and by the size in
``RFC_SIZES``; a download that matches neither is discarded and the run fails, so a changed upstream file is a
decision and not a surprise. The seven RFC Editor files were measured on 2026-11-13 to have the same bytes as the
rfclib mirror the manifest was first written from. RFC text is not vendored: it is the cache's, not the repository's.

With no directory the RFC text is read from the corpus rfclib already holds, read only: ``$RFCLIB_HOME/mirror/rfc``
when that variable is set (it is, in rfclibrary's own ``.mcp.json``, the server's configuration), else the
``rfclibrary`` repository beside this one (``../rfclibrary/data/mirror/rfc``). Nothing there is written or
changed. A directory that holds no ``rfc<N>.txt`` for a module named below is an error that says which path
was looked at.

Each module is cut from the RFC by the line range recorded in ``MODULES`` (the first and last line of the
module in the RFC Editor ``.txt``, found by searching that file for the ``DEFINITIONS ::= BEGIN`` and ``END``
lines; rfclib's own reader numbers lines differently, so its outline cannot be used for this), then stripped of page furniture (form feeds, ``[Page n]`` footers and the
repeated ``RFC nnnn ... Month Year`` header) and de-indented. Nothing else changes: the text is the
published text, including the errata the RFC Editor lists, which are recorded in the manifest and not
applied. ``MANIFEST.json`` carries the sha256 of the RFC text file read, the line range, and the sha256 of
the module written, so a change in either is visible.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "miblang" / "data"
RFC_SITE = "https://www.rfc-editor.org/rfc/"
USER_AGENT = "portfolio-fetch/1"  # plain, no personal detail
INTERVAL = 1.0  # seconds between requests
#: Octet size of each RFC Editor text file the bundle is cut from (measured 2026-11-13).
RFC_SIZES = {
    1155: 39693,
    1213: 142158,
    2578: 89864,
    2579: 59020,
    2580: 54234,
    2863: 155014,
    3418: 49096,
}

# name, rfc, first line, last line (1-based, inclusive in the RFC's .txt), status per rfclib on 2026-11-13,
# and the verified errata that touch the module text (not applied).
MODULES: tuple[tuple[str, int, int, int, str, tuple[str, ...]], ...] = (
    (
        "RFC1155-SMI",
        1155,
        905,
        1048,
        "STD 16, current",
        ("2601 editorial, 4.2, outside the module",),
    ),
    (
        "RFC1213-MIB",
        1213,
        647,
        3705,
        "STD 17, current; updated by RFC 2011, 2012, 2013, all obsolete",
        (),
    ),
    ("SNMPv2-SMI", 2578, 195, 623, "STD 58, current", ()),
    (
        "SNMPv2-TC",
        2579,
        106,
        1157,
        "STD 58, current",
        (
            "415 technical, 7.1.1: DESCRIPTION of RowStatus cites 7.7.1, should be 7.1.12",
            "416 editorial: DateAndTime month and day may be 0",
            "417 technical, 2: DateAndTime year range 0..65536 should be 0..65535",
        ),
    ),
    ("SNMPv2-CONF", 2580, 150, 543, "STD 58, current", ()),
    (
        "SNMPv2-MIB",
        3418,
        104,
        1096,
        "STD 62, current; obsoletes RFC 1907",
        ("276 technical: a reference-section heading outside the module",),
    ),
    (
        "IF-MIB",
        2863,
        1423,
        3549,
        "Draft Standard, current; updated by RFC 8892 (registry procedures, not the module text)",
        (
            "4820 technical, 3.1.7: the ifSpeed ceiling is (2**32)-1, not (2**31)-1; prose outside the module",
        ),
    ),
)

# The modules a ``Mib`` does not hold unless asked: each defines OIDs that RFC 1213-MIB (loaded by default)
# defines too, in another form, so loading both would report every shared descriptor twice. The manifest marks
# them ``"optional": true``; ``bundled.default_names()`` leaves them out and ``Mib.with_bundled("IF-MIB")``
# adds one.
OPTIONAL = frozenset({"IF-MIB", "SNMPv2-MIB"})

_FOOTER = re.compile(r"\[Page \d+\]\s*$")
_HEADER = re.compile(
    r"^RFC \d+ .{3,}(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\s*$"
)


def clean(lines: list[str]) -> str:
    kept = [ln.replace("\f", "").rstrip() for ln in lines]
    kept = [ln for ln in kept if not _FOOTER.search(ln) and not _HEADER.match(ln)]
    indent = min((len(ln) - len(ln.lstrip()) for ln in kept if ln.strip()), default=0)
    out: list[str] = []
    blank = 0
    for ln in kept:
        ln = ln[indent:]
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 1:
            out.append(ln)
    return "\n".join(out).strip("\n") + "\n"


def default_mirror() -> Path:
    """The RFC text directory of the corpus the rfclib MCP server uses, found without writing to it."""
    home = os.environ.get("RFCLIB_HOME")
    base = Path(home) if home else Path(__file__).resolve().parents[2] / "rfclibrary" / "data"
    return base / "mirror" / "rfc"


def cache_dir() -> Path:
    """The cache the RFC text is kept in: ``<cache>/rfc``, beside the IANA modules' ``<cache>/iana``."""
    override = os.environ.get("MIBLANG_DATA_CACHE")
    if override:
        root = Path(override)
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "miblang-data"
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "miblang-data"
    return root / "rfc"


def pinned_hashes() -> dict[int, str]:
    """The sha256 of each RFC text file, as the committed manifest records it."""
    entries = json.loads((DATA / "MANIFEST.json").read_text(encoding="ascii"))
    return {int(e["rfc"]): str(e["rfc_txt_sha256"]) for e in entries}


def check_rfc(path: Path, rfc: int, digest: str) -> str | None:
    """None when ``path`` is the pinned RFC text, else why it is not."""
    if not path.is_file():
        return "not in the cache"
    data = path.read_bytes()
    if len(data) != RFC_SIZES[rfc]:
        return f"size {len(data)}, pinned {RFC_SIZES[rfc]}"
    if hashlib.sha256(data).hexdigest() != digest:
        return "sha256 differs from the manifest's"
    return None


def fetch_rfcs(root: Path | None = None, *, network: bool = True) -> Path:
    """Make sure every RFC the bundle is cut from is in the cache and matches its pin; return the cache.

    Missing or mismatched files are fetched when ``network`` is true, one request per second, into a temporary
    file that is installed only when it matches. Raises :class:`SystemExit` naming the file when it cannot."""
    root = root or cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    pins = pinned_hashes()
    first = True
    for module in MODULES:
        rfc = module[1]
        target = root / f"rfc{rfc}.txt"
        if check_rfc(target, rfc, pins[rfc]) is None:
            continue
        if not network:
            raise SystemExit(f"{target}: {check_rfc(target, rfc, pins[rfc])}; run with --fetch")
        if not first:
            time.sleep(INTERVAL)
        first = False
        request = urllib.request.Request(  # noqa: S310 - https, fixed host
            f"{RFC_SITE}rfc{rfc}.txt", headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            data = response.read(RFC_SIZES[rfc] + 1)
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        problem = check_rfc(temporary, rfc, pins[rfc])
        if problem is not None:
            temporary.unlink()
            raise SystemExit(f"rfc{rfc}.txt from {RFC_SITE}: {problem}; not installed")
        temporary.replace(target)
    return root


def build(mirror: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    manifest = []
    for name, rfc, first, last, status, errata in MODULES:
        source = mirror / f"rfc{rfc}.txt"
        if not source.is_file():
            raise SystemExit(f"no RFC text at {source}: pass the directory that holds rfc{rfc}.txt")
        raw = source.read_bytes()
        text = clean(raw.decode("latin-1").split("\n")[first - 1 : last])
        files[f"{name}.mib"] = text
        entry: dict[str, object] = {
            "module": name,
            "rfc": rfc,
            "status": status,
            "lines": [first, last],
            "rfc_txt_sha256": hashlib.sha256(raw).hexdigest(),
            "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
            "errata_not_applied": list(errata),
        }
        if name in OPTIONAL:
            entry["optional"] = True
        manifest.append(entry)
    files["MANIFEST.json"] = json.dumps(manifest, indent=2) + "\n"
    return files


def main(argv: list[str]) -> int:
    paths = [a for a in argv if not a.startswith("--")]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    if "--fetch" in argv:
        if paths:
            raise SystemExit("--fetch reads its own cache: give no directory")
        source = fetch_rfcs()
    else:
        source = Path(paths[0]) if paths else default_mirror()
    files = build(source)
    if "--check" in argv:
        bad = [
            n
            for n, t in files.items()
            if not (DATA / n).exists() or (DATA / n).read_bytes() != t.encode("ascii")
        ]
        print("bundle differs: " + ", ".join(bad) if bad else "bundle matches")
        return 1 if bad else 0
    DATA.mkdir(exist_ok=True)
    for name, text in files.items():
        (DATA / name).write_bytes(text.encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
