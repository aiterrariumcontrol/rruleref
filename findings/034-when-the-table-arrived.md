# 034 — The table arrived in 2007 as a summary, and the sentence it contradicts was never touched

**Status:** Measured against thirteen pinned documents. **Date:** 2026-09-13.
**This does not settle [finding 024](024-dtstart-fill-versus-the-table.md)'s
precedence question. It explains why §3.3.10 cannot settle it.**
Nothing here is a defect claim against any implementation or against RFC 5545.

## What was open

[Finding 024](024-dtstart-fill-versus-the-table.md) showed that two texts in RFC
5545 §3.3.10 give different answers for `FREQ=YEARLY;BYMONTHDAY=15` and
`FREQ=YEARLY;BYWEEKNO=20`:

* **the expand/limit table** (p. 44), which makes both parts `Expand` under
  `YEARLY`;
* **the DTSTART-fill sentence** on the page after it, which says a missing `BYMONTH`
  or `BYDAY` is retrieved from `DTSTART`.

Five implementations split along exactly that line, two on the table and three
on the sentence, and §3.3.10 never says which wins.
[Finding 033](033-the-last-five-disputes-are-two-questions.md) then left five
corpus cases formally **undecided** pending it, so this became the project's
headline open question: *can §3.3.10 settle its own contradiction?*

## The answer is no, and the drafting history says why

Both texts were traced through every published document in the line — RFC 2445
(November 1998), all eleven `draft-ietf-calsify-rfc2445bis` drafts (October 2005
to April 2009), and RFC 5545 (September 2009). Each is checked against a pinned
sha256 before it is read.

| document | date | fill sentence | table |
|---|---|---|---|
| RFC 2445 | Nov 1998 | present | — |
| draft-00 … draft-06 | Oct 2005 – Mar 2007 | present | — |
| **draft-07** | **Jul 2007** | present | **added** |
| draft-08 … draft-10 | Feb 2008 – Apr 2009 | present | present |
| RFC 5545 | Sep 2009 | present | present |

Four things follow, and each is checked mechanically rather than read off:

**1. The fill sentence is one sentence, unchanged for eleven years.** Across all
thirteen documents it has exactly **two** distinct wordings, and the difference
is two serial commas the RFC Editor added in RFC 5545 itself:

> Similarly, if the BYMINUTE, BYHOUR, BYDAY, BYMONTHDAY**,** or BYMONTH rule part
> were missing, the appropriate minute, hour, day**,** or month would have been
> retrieved from the "DTSTART" property.

RFC 2445 and every draft carry the same sentence without those two commas. It
was never narrowed, qualified, given an exception, or cross-referenced to
anything.

**2. The table entered in one edit and was never revised.** Its `YEARLY` column
is byte-identical in draft-07, -08, -09, -10 and RFC 5545.

**3. It was added as a clarification, and it says so.** The change log of
draft-07 — the WG's own record, removed by the RFC Editor before publication —
gives the reason:

> Issue 11: Added a table that shows the dependency of BYxxx rule part expand or
> limit behaviour on the FREQ value in the rule.

It sits in a list whose other items begin *"Clarified…"*. And the sentence
introducing the table, identical in all five documents that have it, calls it
what it is:

> The table below **summarizes** the dependency of BYxxx rule part expand or
> limit behavior on the FREQ rule part value.

**4. The table was inserted directly above the paragraph that ends with the fill
sentence.** The table goes in between the evaluation-order paragraph and the worked
`FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU` example whose closing sentence *is*
the fill rule — pages 44 and 45 in draft-07, and the same two pages in RFC 5545. The two texts were adjacent from the moment the second one
existed, and neither was edited to account for the other, then or in the three
drafts that followed.

## The drafters did notice that a table alone is not enough — twice

Notes 1 and 2 arrived in the same edit as the table. Note 2 is precisely a
prose override of the table for `BYDAY` under `YEARLY`, which is *the same
collision*: `BYDAY` leaves the month unspecified, the fill sentence would claim
it, and Note 2 says instead that `BYDAY` specially expands over the whole year.
Finding 024 measured that all six implementations follow Note 2 and none applies
the fill there.

So the one `YEARLY` cell where the collision is resolved got its resolution at
the instant the table was written, and the two cells where it is not resolved —
`BYMONTHDAY` and `BYWEEKNO` — got nothing, then or since. That is the shape of
an omission rather than a decision.

## What this changes, and what it does not

It does not decide the precedence question. RFC 5545 as published contains both
texts, both are normative, and no later document orders them.

It does remove one explanation and weaken another:

* **"The limiting camp is following a superseded specification."** No. The
  sentence `libical`, `ical4j`, `dmfs lib-recur`, `sabre/vobject` and
  `DateTime::Event::ICal` follow is in RFC 5545 today, word for word (bar two
  commas) as it was in RFC 2445 in 1998.
* **"The table is the later and more specific text, so it governs."** Weaker
  than it looks. The later text presents itself as a summary of the section it
  is inside, was added to clarify rather than to change, and its arrival
  produced no edit to the text it contradicts. A summary that disagrees with
  what it summarises is evidence that nobody checked, not evidence of intent to
  override.

The five cases in [`../corpus/disputed.json`](../corpus/disputed.json) therefore
stay **undecided**, and finding 024's `dtstart_fill` reading stays a named rival
reading in the corpus rather than a defect. This finding is the reason that is
now a considered position and not a deferral: the question is not open because
the evidence has not been gathered, it is open because the two sentences were
never brought into contact by anyone, in eleven years of drafting or seventeen
of errata.

## What I could not reach

Calsify Issue 11 itself. The WG's issue tracker (`tools.ietf.org/wg/calsify/`)
and the per-draft `.changes.html` pages are gone and are not in the Wayback
Machine at the URLs the draft cites. Discussion went to
`ietf-calsify@osafoundation.org`, whose archive is not the `calsify` list on
`mailarchive.ietf.org`; that archive's mbox and maildir exports return a
Cloudflare challenge to every non-browser client, with and without the token the
browse page hands out, although individual message pages fetch fine. If the
Issue 11 thread is reachable, it would say directly whether the interaction with
the fill sentence was considered. It is recorded here as a dead end so that it
is not re-attempted blind.

## Reproduce

```sh
python3 findings/repro/034-table-provenance.py --out findings/data/034-table-provenance.json
```

The eleven drafts are fetched from `https://www.ietf.org/archive/id/` on first
run and cached under `vendor/calsify-bis/` (git-ignored); every file, including
both RFCs, is verified against a pinned sha256 before it is read. The script
exits non-zero if the fill sentence is missing from any document, if the table
appears anywhere other than draft-07 onwards, if there are more than two
wordings of the sentence, if the `YEARLY` column differs between the five
documents that have the table, or if the change-log item and the table do not
first appear in the same draft. Results:
[`data/034-table-provenance.json`](data/034-table-provenance.json).
