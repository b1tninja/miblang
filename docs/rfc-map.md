# Where every claim in this repository comes from

| Document | Status | Published | Verified against the publisher record on |
|---|---|---|---|
| RFC 2578 | Internet Standard (STD 58), current, obsoletes RFC 1902; no errata | 1999-04 | 2026-11-13 |
| RFC 2579 | Internet Standard (STD 58), current, obsoletes RFC 1903; 3 verified errata (eid 415, 416, 417) and 1 held for document update | 1999-04 | 2026-11-13 |
| RFC 2580 | Internet Standard (STD 58), current, obsoletes RFC 1904; no errata | 1999-04 | 2026-11-13 |
| RFC 1155 | Internet Standard (STD 16), current, obsoletes RFC 1065; 1 verified erratum (eid 2601, editorial, section 4.2) | 1990-05 | 2026-11-13 |
| RFC 1212 | Internet Standard (STD 16), current; no errata | 1991-03 | 2026-11-13 |
| RFC 1215 | Informational, current; no errata | 1991-03 | 2026-11-13 |
| RFC 1213 | Internet Standard (STD 17), current, obsoletes RFC 1158; updated by RFC 2011, RFC 2012, RFC 2013; no errata | 1991-03 | 2026-11-13 |
| RFC 2011 | Proposed Standard, OBSOLETE, obsoleted by RFC 4293 (updates RFC 1213) | 1996-11 | 2026-11-13 |
| RFC 2012 | Proposed Standard, OBSOLETE, obsoleted by RFC 4022 (updates RFC 1213) | 1996-11 | 2026-11-13 |
| RFC 2013 | Proposed Standard, OBSOLETE, obsoleted by RFC 4113 (updates RFC 1213) | 1996-11 | 2026-11-13 |
| RFC 4293 | Proposed Standard, current, obsoletes RFC 2011, 2465, 2466; 13 verified errata | 2006-04 | 2026-11-13 |
| RFC 4022 | Proposed Standard, current, obsoletes RFC 2012, 2452; no errata | 2005-03 | 2026-11-13 |
| RFC 4113 | Proposed Standard, current, obsoletes RFC 2013, 2454; 0 verified (2 on file) | 2005-06 | 2026-11-13 |
| RFC 1156 | Historic, current (no successor listed); the document snmpy's `mib.py` header cites | 1990-05 | 2026-11-13 |
| RFC 3584 | Best Current Practice (BCP 74), current, obsoletes RFC 2576; no errata. Section 2.1.1 (SMIv1 to SMIv2 conversion: ACCESS to MAX-ACCESS, write-only to read-write) and section 4.2.2.1 (Counter64 and SNMPv1) read in full | 2003-08 | 2026-11-13 |
| RFC 2578 sections 7.7, 7.8, 7.10, 7.1.10 and RFC 1212 section 4.1.6 | read in full 2026-11-13 for the resolver's index decoding, row and table classification (RFC 2578 7.1.10 defines Counter64 and says nothing about SNMPv1) | - | 2026-11-13 |
| RFC 2579 sections 3.5 and 4 | read in full 2026-11-13: a convention's SYNTAX cannot name another convention; an object or convention may sub-type | - | 2026-11-13 |
| RFC 1902 | Draft Standard, OBSOLETE, obsoleted by RFC 2578 | 1996-01 | 2026-11-13 |
| RFC 4181 | Best Current Practice (BCP 111), current, updated by RFC 4841; 5 verified errata | 2005-09 | 2026-11-13 |
| ITU-T Rec. X.680 (02/2021), clause 12 | the lexical rules RFC 2578 leaves to ASN.1 (12.3 identifiers and 12.8 numbers read 2026-11-13 with `edition="X.680"`; 12.6.1 to 12.6.4 comments and 12.14.1 character strings read 2026-11-13 with `edition="X.680"`: a comment ends at the next pair of hyphens or the end of the line, `/* */` comments exist in ASN.1 and not in SMI, and a pair of quotes in a `cstring` is one quote) | 02/2021 | 2026-11-13 |
| ITU-T Recommendations formal descriptions catalogue | operational catalogue; the page was marked for deactivation on 2026-11-05 and a later read found a plain directory listing (html, ietf, iso, itu-t, oasis), so it needs re-measuring before M5 | - | 2026-11-05 |
| RFC 2863 | Draft Standard, current, obsoletes RFC 2233; updated by RFC 8892; 1 verified erratum (eid 4820, technical, section 3.1.7: ifSpeed's ceiling is (2**32)-1, prose outside the module, not applied). The module is section 6, `rfc2863.txt` lines 1423 to 3549 | 2000-06 | 2026-11-13 |
| RFC 8892 | Proposed Standard, current, updates RFC 2863; no errata. Registry procedures for interface and tunnel types; the IF-MIB text is unchanged by it | 2020-08 | 2026-11-13 |
| RFC 3418 | Internet Standard (STD 62), current, obsoletes RFC 1907; 1 verified erratum (eid 276, a reference-section heading, outside the module) and 1 rejected (eid 6219, sysServices). The module is `rfc3418.txt` lines 104 to 1096; IF-MIB imports `snmpTraps` from it | 2002-12 | 2026-11-13 |
| IANA-maintained MIB modules (IANAifType-MIB and the like) | not read, and not bundled: they come from IANA, not from RFCs; the primarysource `iana` collection holds registry XML and is not imported on this machine, so the raw files at iana.org need a pinned download the owner has to approve | - | not yet |

RFC 1155 section 6, RFC 1212 section 4, RFC 1215 section 2, RFC 2578 section 2, RFC 2579 section 2 and RFC 2580 section 2 contain the macro definitions this parser implements, and tests/fixtures holds the text extracted from them (each file's first lines name the section and the date it was read through rfclib).

`miblang/data/` holds RFC1155-SMI, RFC1213-MIB, SNMPv2-SMI, SNMPv2-TC and SNMPv2-CONF as published (RFC 1155, 1213, 2578, 2579 and 2580) and, marked optional, SNMPv2-MIB and IF-MIB (RFC 3418, 2863), cut by `tools/extract_bundle.py` from the RFC Editor text in the corpus the rfclib MCP server uses (`$RFCLIB_HOME/mirror/rfc`, read only; the line ranges are those of the `.txt`, which rfclib's reader numbers differently); `MANIFEST.json` records line ranges, the sha256 of the RFC text and of each module, and the errata that touch module text and were not applied.

Citation rules, in the order they most often get broken:

1. Cite the document. A secondary write-up is a lead, not a source.
2. A section number is cited only if that section was read in full.
3. Errata are checked at each milestone freeze, not once at the start.
4. Where a claim came from a body outside the RFC series, that body is named here.

Re-verify with the RFC library rather than memory: `info('RFCnnnn')` for current status, `errata('RFCnnnn')` for corrections, and `read('RFCnnnn', view='normative')` for the MUST and SHOULD statements that become obligation rows.
