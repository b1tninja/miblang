# Specification completeness -- and the roadmap it implies

This is the project's north star: every protocol obligation miblang could plausibly take on,
with an honest status against the code at `HEAD`. It is blunt about gaps on purpose. A
roadmap that overstates its coverage is not a plan, it is marketing.

**The honesty rule:** a row may read `[ok]` only when a named test would fail if the
behaviour regressed. Reading the code and agreeing with it is not enough. That is how
"decoded but never sent" quietly becomes "implemented".

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is
missing stated -- `[ ]` not implemented -- `[no]` deliberate non-goal.

A Where cell marked `(to be written)` names the test that will pin the row once it exists; no
such test has been written yet, and the row cannot leave `[ ]` until it has. The Milestone
column places the row on the ladder in section 2, and `-` means it is not placed yet.

Update the affected row in the same commit that changes the behaviour. A row and its test
drift apart within one release, and the document becomes useless exactly when it is needed.

## 1. Obligations

| Obligation | Spec | Status | Where | Milestone |
|---|---|---|---|---|
| `lexer.lex()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_lex` (to be written) | M1 |
| `grammar.module_identity()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_module_identity` (to be written) | M1 |
| `grammar.object_type()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_object_type` (to be written) | M1 |
| `resolve.load()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_load` (to be written) | M2 |
| `resolve.resolve()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_resolve` (to be written) | M2 |
| `resolve.index()` | RFC 2578 | `[ ]` | `tests/test_obligations.py::test_index` (to be written) | M2 |
| `conventions.textual_convention()` | RFC 2579 | `[ ]` | `tests/test_obligations.py::test_textual_convention` (to be written) | M3 |
| `conformance.compliance()` | RFC 2580 | `[ ]` | `tests/test_obligations.py::test_compliance` (to be written) | M4 |
| `catalogue.modules_of()` | ITU-T | `[ ]` | `tests/test_obligations.py::test_modules_of` (to be written) | M5 |
| `resolve.provenance()` | design | `[ ]` | `tests/test_obligations.py::test_provenance` (to be written) | M5 |

## 2. Milestones

- M1 tokenizer plus the MODULE-IDENTITY, OBJECT-TYPE and TEXTUAL-CONVENTION forms, proven against published modules byte for byte
- M2 cross-module imports and the resolver, answering name to OID and OID to name with the edition attached
- M3 the RFC 2579 conventions and their SUB-TYPE ranges as asn1core constraints rather than a parallel type system
- M4 RFC 2580 conformance statements reduced to an obligation set
- M5 the ITU-T formal-description catalogue through itulib, with digest verification and edition pinning: blocked until itulib mirrors artifacts as well as prose
- M6 publication: 0.1.0 with a measured claim, how many published modules parse and how many fail and why

Every milestone is accepted by its rows above flipping to `[ok]` with a named test, not by
the code existing. Coverage in `pyproject.toml` ratchets in the same commit.

## 3. Errata watch

- RFC 2579 carries 3 verified errata (rfclib, 2026-10-29): parse the corrected text, and record which one a fixture was taken from.
- RFC 2578 and RFC 2580 report no errata, but RFC 1213 is updated by RFC 2011, RFC 2012 and RFC 2013, so an interfaces or IP group answer has to name the updating document as well as the base one.
- The catalogue page announces its own deactivation in favour of MyWorkspace, and its language filter is an ASP.NET postback rather than a queryable endpoint: a GET with language=MIB still returns the unfiltered 977 rows (measured 2026-11-05), so enumeration must walk the per-recommendation listings and pin digests.

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| the SNMP protocol: snmpy speaks it, and miblang only answers what a name means and where it sits in the tree | `[no]` | a named document requires it |
| agent or manager behaviour: no transport, no table storage, no set handling | `[no]` | a named document requires it |
| GDMO and the ITU-T management definitions that predate SMIv2, a different notation and a different grammar even though the catalogue lists them | `[no]` | a named document requires it |
| MIB to Python code generation for agent frameworks: what a generated view buys over a resolver is unproven here | `[no]` | a named document requires it |

## 5. Open questions

- M5 depends on itulib mirroring artifacts and not only prose: its registry is 16 editions of the ASN.1 series today, so the catalogue work is a prerequisite rather than a rung, and no M5 row can be closed before it
- whether snmpy's hand-written mib_view.py is regenerated from miblang output, retired module by module in favour of the resolver, or left alone: the 40,505 bytes exist and one of the three has to be said out loud

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
