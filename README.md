# miblang

<!-- PyPI badges go live with the first release. Until then a version badge renders
     "no version" on the landing page, which reads as a defect rather than a date, so
     the badges stay commented out until the tag exists.
-->

**Pre-alpha shell.** The package surface, the obligation matrix and the CI gates exist.
No protocol behaviour is implemented: every public function raises `NotImplementedError`,
and the test suite records that rather than hiding it. Read
[ROADMAP.md](ROADMAP.md) before depending on any of it.

miblang -- SMIv2 module parsing that says which edition an answer came from

snmpy carries about 150 KB of hand-maintained management-information code and not one line of grammar: mib_view.py is 40,505 bytes of hand-written per-MIB views, mib.py is 25,969 bytes of hand-copied OID constants whose own header cites RFC 1156, a HISTORIC document obsoleted by the MIB-II of RFC 1213, and across all 70 of its python files there is exactly one stray NOTIFICATION-TYPE token and no MODULE-IDENTITY or OBJECT-TYPE anywhere. Every MIB it speaks was transcribed by hand, and a transcription is where an OID goes wrong in silence. The corpus a reader would consume is published and machine-shaped: the ITU-T formal-descriptions catalogue holds 977 normative artifacts in ASN.1, MIB, GDMO, ABNF, JSON, XML, TTCN-3 and seven other languages, each row keyed by Recommendation, approval date, language, module name and OID, and each artifact served unauthenticated at HTTP 200 from a stable per-module URL (measured 2026-11-05). What is missing is a stdlib-only reader that turns those modules into an OID tree able to name the edition an answer came from. pysmi 2.0.0 does this job and is current, and it is declined as a dependency because lark, Jinja2 and requests arrive attached to it; that trade, and the creation of this shell against the no-new-shells rule, are recorded with their evidence in PORTFOLIO.md sections 5 and 7.

## The gap, with a date

PyPI was queried on 2026-11-05 for this name and for every neighbouring project. Landscape
claims rot quickly: two projects in this portfolio shipped within five days of the survey,
which is why the table below carries dates instead of adjectives.

| Project | Version | Last release | Why it is not this project |
|---|---|---|---|
| pysmi | 2.0.0 | 2026-04-26 | the incumbent, and current: a pure-Python SNMP/SMI MIB parsing and conversion library whose runtime deps are lark, Jinja2 and requests (lextudio/pysmi). Declined as a dependency rather than ignored: no project here can carry a grammar toolkit, a template engine and an HTTP client in order to read a text file. |
| pysnmp | 7.1.16 | - | what pysmi is developed against; the protocol itself is already spoken here by snmpy, which is why this project stops at what a name means |
| mibkit, smikit, mibble, pymib | - | 2026-11-05 | each free on both PyPI signals and each refused: one keystroke from 6, 5, 6 and 24 live names respectively against a snapshot of 931,439 canonical names (names.py --index). miblang has zero live neighbours. |

What this project intends to add:

- a stdlib-only SMIv2 reader, because the incumbent brings three runtime dependencies along with the parser
- an OID answer that carries its edition: which module, which version of that module, and which publisher put it where
- a way to notice that a deployed table was transcribed from an obsolete document, which is what snmpy's mib.py header admits it is
- MIB modules read from a corpus with digests rather than from a directory of files of unknown vintage

## Specification spine

Status and publication dates below were read from the RFC Editor record on 2026-11-05. A
section number is cited only where that section was read in full; everything else cites the
document, which is the honest grain size for a plan. See [docs/rfc-map.md](docs/rfc-map.md).

| Document | Status | Published | What it gives this project |
|---|---|---|---|
| RFC 2578 | Internet Standard (STD 58) | 1999-04 | SMIv2 itself: the MODULE-IDENTITY, OBJECT-TYPE, OBJECT-IDENTITY and NOTIFICATION-TYPE macros and their ASN.1 mapping, which is the grammar this parses |
| RFC 2579 | Internet Standard (STD 58) | 1999-04 | the TEXTUAL-CONVENTION macro that RFC 2578 section 7.1.5 defers to, and the initial convention set every deployed module imports |
| RFC 2580 | Internet Standard (STD 58) | 1999-04 | MODULE-COMPLIANCE, AGENT-CAPABILITY and the group forms: conformance as data rather than as prose |
| RFC 1213 | Internet Standard (STD 17) | 1991-03 | MIB-II, the module a reader has to get right first and the one snmpy's constants are a hand copy of, updated by RFC 2011, RFC 2012 and RFC 2013 |
| RFC 1902 | Draft Standard (Obsolete) | 1996-01 | the SMI text older modules were written against, obsoleted by RFC 2578 yet still parsed in practice, so the reader must accept both and say which one it saw |
| ITU-T Recommendations formal descriptions catalogue | operational catalogue, page marked for deactivation | - | 977 machine-readable normative artifacts keyed by Recommendation, approval date, language, module name and OID; measured 2026-11-05, and the module corpus this project reads once itulib mirrors it |

### Errata watch

- RFC 2579 carries 3 verified errata (rfclib, 2026-10-29): parse the corrected text, and record which one a fixture was taken from.
- RFC 2578 and RFC 2580 report no errata, but RFC 1213 is updated by RFC 2011, RFC 2012 and RFC 2013, so an interfaces or IP group answer has to name the updating document as well as the base one.
- The catalogue page announces its own deactivation in favour of MyWorkspace, and its language filter is an ASP.NET postback rather than a queryable endpoint: a GET with language=MIB still returns the unfiltered 977 rows (measured 2026-11-05), so enumeration must walk the per-recommendation listings and pin digests.

## Module layout

| Module | Responsibility |
|---|---|
| `lexer` | the comment, quoting, OID-literal and continuation rules every macro form sits inside |
| `grammar` | the RFC 2578 macro forms and the RFC 2579 TEXTUAL-CONVENTION form, kept as syntax rather than as a tree of dicts |
| `resolve` | cross-module imports and the OID tree in both directions, with the module edition attached to every answer |
| `conventions` | the RFC 2579 conventions and their SUB-TYPE ranges expressed as asn1core constraints, not as a second type system |
| `conformance` | MODULE-COMPLIANCE and AGENT-CAPABILITY reduced to an obligation set a test can check |
| `catalogue` | the ITU-T formal-description artifacts itulib mirrors: Recommendation, edition, language, module, OID and digest |

## What it does not do

- the SNMP protocol: snmpy speaks it, and miblang only answers what a name means and where it sits in the tree
- agent or manager behaviour: no transport, no table storage, no set handling
- GDMO and the ITU-T management definitions that predate SMIv2, a different notation and a different grammar even though the catalogue lists them
- MIB to Python code generation for agent frameworks: what a generated view buys over a resolver is unproven here


## Install

```bash
git clone https://github.com/b1tninja/miblang.git
cd miblang
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
```

Not published to PyPI yet. The name is reserved for this repository's trusted publisher at
the moment of the first release.

## Development

All four gates must pass, on Linux and Windows alike:

```bash
ruff check . && ruff format --check .
mypy miblang tests
pytest -q --cov
python -O -m pytest -q
```

The last line is the one that matters most in a protocol library. `-O` strips `assert`, and a
parser whose bounds checks were asserts stops being a parser under production flags. Wire
paths raise named exceptions; asserts belong in tests and nowhere else.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
