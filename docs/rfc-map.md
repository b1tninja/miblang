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
| RFC 1902 | Draft Standard, OBSOLETE, obsoleted by RFC 2578 | 1996-01 | 2026-11-13 |
| RFC 4181 | Best Current Practice (BCP 111), current, updated by RFC 4841; 5 verified errata | 2005-09 | 2026-11-13 |
| ITU-T Rec. X.680 (02/2021), clause 12 | the lexical rules RFC 2578 leaves to ASN.1 (12.3 identifiers and 12.8 numbers read 2026-11-13 with `edition="X.680"`; 12.6 comments and 12.14 character strings not yet read) | 02/2021 | 2026-11-13 |
| ITU-T Recommendations formal descriptions catalogue | operational catalogue; the page was marked for deactivation on 2026-11-05 and a later read found a plain directory listing (html, ietf, iso, itu-t, oasis), so it needs re-measuring before M5 | - | 2026-11-05 |
| IANA-maintained MIB modules (IANAifType-MIB and the like) | not read; they come from IANA, not from RFCs | - | not yet |

RFC 1155 section 6, RFC 1212 section 4, RFC 1215 section 2, RFC 2578 section 2, RFC 2579 section 2 and RFC 2580 section 2 contain the macro definitions this parser implements, and tests/fixtures holds the text extracted from them (each file's first lines name the section and the date it was read through rfclib).

Citation rules, in the order they most often get broken:

1. Cite the document. A secondary write-up is a lead, not a source.
2. A section number is cited only if that section was read in full.
3. Errata are checked at each milestone freeze, not once at the start.
4. Where a claim came from a body outside the RFC series, that body is named here.

Re-verify with the RFC library rather than memory: `info('RFCnnnn')` for current status, `errata('RFCnnnn')` for corrections, and `read('RFCnnnn', view='normative')` for the MUST and SHOULD statements that become obligation rows.
