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
| `lexer.lex()` | RFC 2578 sec. 3.1.1, 3.4, 3.7; X.680 12.3 | `[ok]` | `tests/test_lexer.py::test_lex_module_identity_header`; `tests/test_lexer.py::test_reserved_list_matches_rfc_2578_3_7`; `tests/test_lexer.py::test_one_million_open_quote_chars_is_linear_time` | M1 |
| `grammar.parse_module()` module header, `IMPORTS`, SMIv1 `EXPORTS` | RFC 2578 sec. 3, 3.2, 3.3; RFC 1155 sec. 6 | `[ok]` | `tests/test_grammar.py::test_module_header_and_imports`; `tests/test_grammar.py::test_exports_clause_is_kept_for_smiv1` | M1 |
| `grammar.parse()` OBJECT IDENTIFIER assignments | RFC 2578 sec. 3.5, 3.6 | `[ok]` | `tests/test_grammar.py::test_oid_assignments_with_named_numbers_and_qualified_names`; `tests/test_grammar.py::test_oid_subidentifier_limit_and_empty_oid` | M1 |
| `grammar.module_identity()` | RFC 2578 sec. 5 | `[ok]` | `tests/test_grammar.py::test_module_identity_from_rfc2578_5_7` | M1 |
| `grammar.parse()` OBJECT-IDENTITY | RFC 2578 sec. 6 | `[ok]` | `tests/test_grammar.py::test_object_identity_from_rfc2578_zero_dot_zero` | M1 |
| `grammar.object_type()` | RFC 2578 sec. 7 | `[ok]` | `tests/test_grammar.py::test_object_type_table_from_rfc2578_7_11`; `tests/test_grammar.py::test_object_type_refusals` | M1 |
| `grammar.parse()` NOTIFICATION-TYPE | RFC 2578 sec. 8 | `[ok]` | `tests/test_grammar.py::test_notification_type_from_rfc2578_8_6` | M1 |
| `grammar.parse()` TEXTUAL-CONVENTION syntax | RFC 2579 sec. 2, 3 | `[ok]` | `tests/test_grammar.py::test_textual_conventions_from_rfc2579_section_2` | M1 |
| `grammar.parse()` OBJECT-GROUP, NOTIFICATION-GROUP, MODULE-COMPLIANCE, AGENT-CAPABILITIES syntax | RFC 2580 sec. 2 to 6 | `[ok]` | `tests/test_grammar.py::test_conformance_macros_from_rfc2580_examples` | M1 |
| `grammar.parse()` the SNMPv2-SMI base module, with MACRO definitions skipped | RFC 2578 sec. 2 | `[ok]` | `tests/test_grammar.py::test_snmpv2_smi_module_from_rfc2578_section_2` | M1 |
| `grammar.parse()` SMIv1 OBJECT-TYPE (ACCESS, mandatory/optional, INDEX types, DEFVAL forms) | RFC 1155 sec. 6; RFC 1212 sec. 4 | `[ok]` | `tests/test_grammar.py::test_smiv1_object_types_from_rfc1212_4_2`; `tests/test_grammar.py::test_smiv1_index_types_and_defval_forms` | M1 |
| `grammar.parse()` SMIv1 TRAP-TYPE | RFC 1215 sec. 2 | `[ok]` | `tests/test_grammar.py::test_trap_type_from_rfc1215_2_2` | M1 |
| `grammar.parse()` the RFC1155-SMI base module | RFC 1155 sec. 6 | `[ok]` | `tests/test_grammar.py::test_rfc1155_smi_module` | M1 |
| `lexer.lex()` doubled quote inside a string: two strings under RFC 2578 3.1.1 (default), one escaped quote with `x680_strings=True` and X.680 12.14.1 line-end spacing rule | RFC 2578 sec. 3.1.1; X.680 12.14.1 (read 2026-11-13, `edition="X.680"`) | `[ok]` | `tests/test_lexer.py::test_doubled_quote_policy` | M1 |
| `lexer.lex()` odd runs of hyphens (banner comments such as `-----`): refused as a stray hyphen by default (the pair-by-pair reading of X.680 12.6.3), one marker with `lenient_hyphens=True` | RFC 2578 sec. 3.4; X.680 12.6.3 (read 2026-11-13) | `[ok]` | `tests/test_lexer.py::test_odd_hyphen_banner` | M1 |
| `grammar.parse()` refuses SMIv1 macros in an SMIv2 module and the reverse | RFC 2578 sec. 3 paragraph 8 | `[ ]` | `tests/test_grammar.py::test_mixed_smi_dialects_refused` (to be written) | M1 |
| `grammar.parse()` refuses `EXPORTS` in an SMIv2 module | RFC 2578 sec. 3.3 | `[ ]` | `tests/test_grammar.py::test_exports_refused_in_smiv2` (to be written) | M1 |
| `grammar.parse()` descriptor rules: no hyphen in an SMIv2 descriptor, at most 64 characters, module name form | RFC 2578 sec. 3, 3.1 | `[ ]` | `tests/test_grammar.py::test_descriptor_rules` (to be written) | M1 |
| `grammar.parse()` SMIv2 sub-typing rules: ranges ascending and disjoint, no MIN/MAX, SIZE only on OCTET STRING | RFC 2578 sec. 9, 11.1, 11.2 | `[ ]` | `tests/test_grammar.py::test_subtyping_rules` (to be written) | M3 |
| `grammar.parse()` lenient mode for modules found in the wild: out-of-order clauses and the other deviations RFC 4181 and snmpy's consumers meet | RFC 4181 | `[ ]` | `tests/test_grammar.py::test_lenient_mode` (to be written) | M6 |
| `bundled`: RFC1155-SMI, RFC1213-MIB, SNMPv2-SMI, SNMPv2-TC and SNMPv2-CONF bundled as sha256-pinned data cut from the RFC text by `tools/extract_bundle.py`, with provenance and errata recorded in `miblang/data/MANIFEST.json` | RFC 1155, 1213, 2578, 2579, 2580 | `[ok]` | `tests/test_bundled.py::test_bundle_names_and_manifest_hashes`; `tests/test_bundled.py::test_tampered_module_is_refused`; `tests/test_bundled.py::test_every_bundled_module_parses_with_its_own_name_and_dialect`; `tests/test_bundled.py::test_errata_recorded_not_applied` | M2 |
| `bundled` RFC-1212 and RFC-1215 as modules: neither RFC has a `DEFINITIONS` wrapper (each gives its macro inside running text, RFC 1212 section 4 and RFC 1215 section 2), so no published module exists to bundle verbatim; the grammar already skips those macros by name | RFC 1212, RFC 1215 | `[no]` | `tests/test_grammar.py::test_smiv1_object_types_from_rfc1212_4_2` | M2 |
| `resolve.load()` reads a module file (UTF-8, else Latin-1) into a `Mib` that already holds the bundled modules, with extra `imports`; IMPORTS are followed across modules and every OID-valued definition resolved | RFC 2578 sec. 3.2, 3.5 | `[ok]` | `tests/test_resolve.py::test_load` | M2 |
| `resolve.resolve()` a name, `MODULE::name` or dotted OID to an `Object`; a name defined in two loaded modules with different OIDs is refused without a prefix; unresolvable and circular names are reported in `problems`, never guessed | RFC 2578 sec. 3.5, 4 | `[ok]` | `tests/test_resolve.py::test_resolve`; `tests/test_resolve.py::test_same_name_in_two_modules_needs_a_prefix`; `tests/test_resolve.py::test_unresolvable_and_circular_names_are_reported_not_guessed` | M2 |
| `resolve.index()` instance OID to object by longest prefix, row index decoded from INDEX or AUGMENTS (integer, fixed and variable strings, IMPLIED, object identifier, IpAddress, NetworkAddress kind 1) | RFC 2578 sec. 7.7, 7.8; RFC 1212 sec. 4.1.6 | `[ok]` | `tests/test_resolve.py::test_index_instance_suffix`; `tests/test_resolve.py::test_index_decoding_string_and_implied_forms` | M2 |
| `resolve.index()` a scalar is instanced as `.0`, anything else under a scalar is reported in `Instance.problem` | RFC 1212 sec. 4.1.6 paragraph 2 | `[ok]` | `tests/test_resolve.py::test_index_instance_suffix` | M2 |
| `resolve.resolve()` TC chain to the base type: `TypeInfo` carries the chain, primitive, SMI base type, the outermost SIZE, range or enumeration, and the nearest DISPLAY-HINT; a convention defined over another convention is noted as against RFC 2579 sec. 3.5 | RFC 2579 sec. 3.5, 4; RFC 2578 sec. 9 | `[ok]` | `tests/test_resolve.py::test_tc_chain`; `tests/test_resolve.py::test_tc_defined_over_tc_is_noted` | M2 |
| `resolve.resolve()` object metadata: syntax name, status, ACCESS and MAX-ACCESS as one vocabulary (SMIv1 write-only reads as read-write), notification flag | RFC 2578 sec. 7.3; RFC 1212 sec. 4.1.2; RFC 3584 sec. 2.1.1 item 5 | `[ok]` | `tests/test_resolve.py::test_resolve_metadata` | M2 |
| `resolve.resolve()` table, row and column classification from SEQUENCE OF, INDEX and AUGMENTS | RFC 2578 sec. 7.10, 7.7, 7.8 | `[ok]` | `tests/test_resolve.py::test_table_classification` | M2 |
| `resolve.resolve()` SMIv2-only syntax (Counter64, directly or through a convention) reported per object (`Object.smiv2_only`); the earlier citation of RFC 2578 sec. 7.1.10 was wrong, that section defines the type and says nothing about SNMPv1; the rule is RFC 3584 sec. 4.2.2.1 | RFC 3584 sec. 4.2.2.1 | `[ok]` | `tests/test_resolve.py::test_smiv2_only_syntax` | M2 |
| `resolve.provenance()` which bundled document an OID came from, flagging the RFC 1213 groups that RFC 2011, 2012 and 2013 updated (all three obsolete: RFC 4293, 4022, 4113); a module that is not bundled reports no provenance, and RFC 1156 is not a bundled source | RFC 1213; RFC 4293; RFC 4022; RFC 4113 | `[ok]` | `tests/test_resolve.py::test_provenance_obsolete_source` | M2 |
| `conventions.textual_convention()` | RFC 2579 | `[ ]` | `tests/test_obligations.py::test_textual_convention` (to be written) | M3 |
| `conventions.textual_convention()` RFC 2579 errata 415, 416, 417 (RowStatus reference to 7.1.12, DateAndTime month and day 0, year 0..65535) | RFC 2579 errata | `[ ]` | `tests/test_obligations.py::test_rfc2579_errata_fixtures` (to be written) | M3 |
| `conformance.compliance()` | RFC 2580 | `[ ]` | `tests/test_obligations.py::test_compliance` (to be written) | M4 |
| `catalogue.modules_of()` | ITU-T | `[ ]` | `tests/test_obligations.py::test_modules_of` (to be written) | M5 |
| `resolve.provenance()` for modules loaded from files or added with a `path` and `sha256`: the answer carries `source` (`bundled`, `file` or `text`), the file path, the sha256 of the bytes read and the module's own LAST-UPDATED as `revision`; a bundled module reports its manifest hash and its revision, and text added with no origin says there is none | design | `[ok]` | `tests/test_resolve.py::test_provenance_file_modules`; `tests/test_iana_mibs.py::test_a_module_that_imports_ianaiftype_resolves_end_to_end` | M5 |
| `resolve.load()` over the 21 IANA-maintained MIB modules (IANAifType-MIB, IANA-MAU-MIB, IANA-PRINTER-MIB and the rest of the "IANA-Maintained MIBs" table at iana.org/assignments/mib-modules, read 2026-11-13): `tools/fetch_iana_mibs.py` fetches them into `$MIBLANG_DATA_CACHE` (else the user cache directory) at one request per second, each pinned by sha256 and size with its LAST-UPDATED; the tests skip loudly when the cache is absent. All 21 parse as SMIv2 with their pinned revision, load together with the bundle with no import problem, and IANAifType's 305 named numbers equal an independent read of the text. A module that imports IANAifType-MIB resolves end to end (an invented IF-MIB-shaped module; the real IF-MIB is below). Terms: the registries are CC0 under the IANA and IETF joint statement of 2021-11-10 (iana.org/help/licensing-terms, read 2026-11-13); the modules are not vendored. primarysource's `iana` collection imports registries as XML and has no form for these text files | IANA joint licensing statement; RFC 2578 sec. 3.2 | `[ok]` | `tests/test_iana_mibs.py::test_every_iana_module_parses_as_smiv2_with_its_pinned_revision`; `tests/test_iana_mibs.py::test_the_whole_set_loads_with_the_bundle_and_every_import_is_defined`; `tests/test_iana_mibs.py::test_ianaiftype_enumeration_matches_the_text_read_independently`; `tests/test_iana_mibs.py::test_a_module_that_imports_ianaiftype_resolves_end_to_end` | M5 |
| `resolve.Mib` places an SMIv1 TRAP-TYPE in the tree as a notification (enterprise, then 0, then the trap number) so a trap OID received from an SNMPv2 translation resolves | RFC 1215 sec. 2; RFC 3584 (mapping section not yet read for this row) | `[ ]` | `tests/test_resolve.py::test_trap_type_oid` (to be written) | M2 |
| `resolve.Mib` reports an IMPORTS entry whose source module is loaded but does not define the symbol, and a descriptor imported from two modules (RFC 2578 3.2 resolves that with a `module.descriptor` prefix); a source module that is not loaded is not checked, and the bundled modules and the 21 IANA modules produce no such problem | RFC 2578 sec. 3.2 | `[ok]` | `tests/test_resolve.py::test_import_of_missing_symbol`; `tests/test_resolve.py::test_a_descriptor_imported_from_two_modules_needs_a_prefix`; `tests/test_resolve.py::test_the_bundled_modules_import_nothing_they_do_not_define` | M2 |
| The real IF-MIB (RFC 2863, status Draft Standard, current, updated by RFC 8892, 1 verified erratum 4820 in section 3.1.7 prose outside the module) bundled and resolved against IANAifType-MIB: needs `tools/extract_bundle.py` run over an RFC text mirror, which is not on this machine (rfclib's reader is not a file mirror); the module is section 6, lines 1446 to 3613 of the RFC text per rfclib's outline | RFC 2863 sec. 6 | `[ ]` | `tests/test_bundled.py::test_if_mib_resolves_with_ianaiftype` (to be written) | M5 |
| Module revision history: `provenance` reports only the MODULE-IDENTITY LAST-UPDATED, and the REVISION clauses (IANAifType-MIB carries one per registered type) are parsed but not exposed per module; a module with no MODULE-IDENTITY (SMIv1) has no revision | RFC 2578 sec. 5.1 | `[ ]` | `tests/test_resolve.py::test_module_revisions` (to be written) | M5 |
| `resolve.Mib` module revision handling: two loaded editions of one module name, chosen by LAST-UPDATED, with the edition attached to every answer | RFC 2578 sec. 5.1, 5.5 | `[ ]` | `tests/test_resolve.py::test_two_editions_of_one_module` (to be written) | M5 |
| `tools/extract_bundle.py --check` runs in CI against a pinned RFC text source instead of a local rfclib mirror | design | `[ ]` | (to be written) | M6 |

Placement of rows in the milestone column that this pass added: the parse rows are M1 because they
are syntax; the resolver rows that came out of reading snmpy are M2 and M3 because each needs the
object tree or the textual-convention chain.

## 2. Milestones

- M1 tokenizer plus the MODULE-IDENTITY, OBJECT-TYPE and TEXTUAL-CONVENTION forms, proven against published modules byte for byte, and the SMIv1 forms (RFC 1155, RFC 1212, RFC 1215): tokenizer, module header, IMPORTS, OBJECT IDENTIFIER assignments and every macro of RFC 2578, 2579, 2580 parse as syntax (first pass done 2026-11-13, against text extracted from the RFCs through rfclib; the 'byte for byte against published modules' claim waits for the M6 corpus)
- M2 cross-module imports and the resolver, answering name to OID and OID to name with the edition attached (second pass 2026-11-13: `resolve` module, five base modules bundled; the IANA modules and edition handling remain)
- M3 the RFC 2579 conventions and their SUB-TYPE ranges as asn1core constraints rather than a parallel type system
- M4 RFC 2580 conformance statements reduced to an obligation set
- M5 the ITU-T formal-description catalogue through itulib, with digest verification and edition pinning: blocked until itulib mirrors artifacts as well as prose
- M6 publication: 0.1.0 with a measured claim, how many published modules parse and how many fail and why

Every milestone is accepted by its rows above flipping to `[ok]` with a named test, not by
the code existing. Coverage in `pyproject.toml` ratchets in the same commit.

## 3. Errata watch

- RFC 2579 carries 3 verified errata (rfclib, 2026-10-29): parse the corrected text, and record which one a fixture was taken from.
- RFC 2578 and RFC 2580 report no errata, but RFC 1213 is updated by RFC 2011, RFC 2012 and RFC 2013, so an interfaces or IP group answer has to name the updating document as well as the base one.
- RFC 2579 also has 1 erratum held for document update besides the 3 verified (rfclib, 2026-11-13); the held one is not authoritative yet, so the roadmap row for the errata fixtures names only 415, 416 and 417.
- RFC 1155 carries 1 verified erratum (eid 2601, editorial, section 4.2: "subject type" should read "object type"); it changes no grammar. RFC 1212 and RFC 1215 report none. RFC 4181 carries 5 verified (one technical, eid 173, an enumeration rule in 4.6.1.1; the rest typographical) and is updated by RFC 4841; it is guidance on authoring, not grammar.
- RFC 1213 is updated by RFC 2011, RFC 2012 and RFC 2013, and all three are now OBSOLETE: RFC 4293, RFC 4022 and RFC 4113 replace them (rfclib, 2026-11-13). RFC 1156 is HISTORIC (rfclib lists no successor; RFC 1213 obsoletes RFC 1158) and is what snmpy's `mib.py` still cites. An interfaces, IP, TCP or UDP answer names the current document.
- RFC 1902 is OBSOLETE (obsoleted by RFC 2578). RFC 1215 is Informational, not a standard; TRAP-TYPE is parsed because deployed MIBs use it, not because a standard requires it.
- RFC 2579 module text is bundled verbatim; errata 415 (RowStatus DESCRIPTION cites 7.7.1, should be 7.1.12), 416 (DateAndTime month and day may be 0) and 417 (year 0..65535, the text says 0..65536) touch DESCRIPTION text and a field table inside it, not syntax, and are recorded in `miblang/data/MANIFEST.json` as not applied (rfclib, 2026-11-13).
- RFC 2576 is obsolete: RFC 3584 (BCP 74) obsoletes it and is the current coexistence document, so rows that need the SMIv1 to SMIv2 mapping (access, status, Counter64) cite RFC 3584. RFC 3584 reports no errata.
- RFC 2579 sec. 3.5 says a textual convention's SYNTAX cannot name another convention, so the type chain from an object is at most one convention deep in a conforming module; `TypeInfo.notes` flags a module that breaks it.
- X.680 (02/2021, read with `edition="X.680"`): 12.6.3 a comment ends at the next pair of adjacent hyphens or the end of the line and contains no other pair; 12.6.4 adds `/* */` comments, which SMI does not use and the lexer does not read; 12.14.1 a pair of quotes inside a `cstring` is one quote and spacing around a line end is not part of the value. RFC 2578 3.1.1 forbids the quote character inside a string, so the two readings differ and the lexer takes RFC 2578 by default.
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
- decided 2026-11-13 (PORTFOLIO.md section 9 item 15): SMIv1 is in scope, and snmpy is legacy and is not edited. snmpy's hand-written `mib.py`, `mib_lookup.py`, `mib_registry.py`, `mib_view.py` and `smi.py` are read as evidence of what a consumer needs; each need is a row in section 1, not a task in snmpy
- itulib usability note (checked 2026-11-13 with the itulib tools): `itu_search`, `itu_outline` and `itu_read` default to `edition="X.690"`, so a call that omits `edition` for X.680 returns X.690 content. With `edition="X.680"` the same calls return the X.680 clause 12 outline (39 entries) and the text of 12.3 (identifiers) and 12.8 (numbers). An earlier review reported this as a corpus bug; it is an easy-to-miss default. M5 and any ASN.1 notation row must pass the edition explicitly
- `docs/plan.md` (generated) still says itulib "does not exist yet" and that there is no itulib directory; the itulib tools answer today. The statement is stale; it is fixed in the portfolio plan and regenerated, not edited here
- `docs/plan.md` lists asn1core as a dependency for the SUB-TYPE rows while `pyproject.toml` declares the `conventions` extra; the parser written in this pass keeps ranges as plain tuples and needs neither, so the dependency begins at M3
- whether snmpy's hand-written mib_view.py is regenerated from miblang output, retired module by module in favour of the resolver, or left alone: the 40,505 bytes exist and one of the three has to be said out loud

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
