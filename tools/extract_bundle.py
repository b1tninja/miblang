#!/usr/bin/env python3
"""Rebuild ``miblang/data/`` from the RFC Editor text that rfclib mirrors.

    python tools/extract_bundle.py <mirror-dir>      # the directory holding rfc1155.txt, rfc2578.txt, ...
    python tools/extract_bundle.py <mirror-dir> --check   # exit 1 when the bundle differs

Each module is cut from the RFC by the line range recorded in ``MODULES`` (found by reading the RFC
through rfclib on 2026-11-13), then stripped of page furniture (form feeds, ``[Page n]`` footers and the
repeated ``RFC nnnn ... Month Year`` header) and de-indented. Nothing else changes: the text is the
published text, including the errata the RFC Editor lists, which are recorded in the manifest and not
applied. ``MANIFEST.json`` carries the sha256 of the RFC text file read, the line range, and the sha256 of
the module written, so a change in either is visible.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "miblang" / "data"

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
)

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


def build(mirror: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    manifest = []
    for name, rfc, first, last, status, errata in MODULES:
        raw = (mirror / f"rfc{rfc}.txt").read_bytes()
        text = clean(raw.decode("latin-1").split("\n")[first - 1 : last])
        files[f"{name}.mib"] = text
        manifest.append(
            {
                "module": name,
                "rfc": rfc,
                "status": status,
                "lines": [first, last],
                "rfc_txt_sha256": hashlib.sha256(raw).hexdigest(),
                "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
                "errata_not_applied": list(errata),
            }
        )
    files["MANIFEST.json"] = json.dumps(manifest, indent=2) + "\n"
    return files


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    files = build(Path(argv[0]))
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
