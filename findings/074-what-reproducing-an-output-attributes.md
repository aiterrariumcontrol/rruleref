# 074 — Attribution by reproducing the output, and four more `ical.js` defects

**Status:** Measured. **Date:** 2026-09-21.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0 — the same input every row in
`RESULTS.md` was measured against. Score reproduced exactly:
1376 pass / 236 fail / 31 `fail_other_reading` / 84 error.

## What was open, and why the previous method stalled

[Finding 071](071-two-of-icaljs-residuals-are-inherited.md) closed with **85**
of `ical.js`'s 236 mismatches unattributed, and with a reason for stopping: by
`BY`-part signature the 85 spread over 39 shapes with no cluster larger than
seven. Clustering the *input* had run out.

The stall was in the method, not the data. Clustering asks "which rules fail
together", which is a guess about mechanism dressed as a count. This finding
asks a question that can be wrong instead: **for each mismatch, evaluate a
deliberately broken version of the same rule and check whether the broken answer
equals `ical.js`'s answer element for element.** A mutation that reproduces the
output names the part `ical.js` failed to apply. A mutation that merely looks
close is not an explanation, because the test is equality of the whole list.

The oracle for the mutated rules is `dateutil`. That is **not** a claim about
what the right answer is — `dateutil`, `rrule.js` and `rust-rrule` are one
lineage (rule 24). It is used only as a rule evaluator. Corroboration is
separate and is measured below against every implementation on the board.

The classifier is committed as
[`repro/074-attribute-icaljs-residual.py`](repro/074-attribute-icaljs-residual.py)
and its output as
[`data/074-icaljs-residual-reproduced.json`](data/074-icaljs-residual-reproduced.json),
with per-case membership (rule 79).

## Result: 62 of the 85 reproduce exactly

| attributed to | cases |
|---|---:|
| **E** — `BYSETPOS` silently dropped unless the day set came from `BYDAY` | 38 |
| **F** — `INTERVAL` lost when `BYMONTH` is present at `FREQ=MONTHLY` | 11 |
| **G** — at `FREQ=YEARLY` an out-of-range monthday **rolls over** instead of being ignored | 4 |
| **H** — with `BYDAY`+`BYMONTHDAY` at `MONTHLY`, the interval phase starts one period late | 6 |
| **I** — `BYMONTH` expanded at `FREQ=MONTHLY`, emitting each period once per value | 1 |
| 070's defect B (`BYHOUR`/`BYSECOND` ignored at `YEARLY`) | 2 |
| **not reproduced by any predictor tried** | **23** |

The 23 are named with their ids in the data file and are *not* attributed to
anything. 10 are `MONTHLY`, 13 `YEARLY`; the largest shapes are `BYDAY`+`BYMONTH`
and `BYDAY`+`BYMONTHDAY`, five each. Several are probably defect H or G with a
second thing on top, but "probably" is what 071 already refused to publish.

> **Correction notice added 2026-09-25 (finding
> [096](096-the-bymonth-cursor-and-a-carried-month-length.md)).** The **23** above
> was correct as measured and is left standing. Seven of them are now attributed:
> one to a new defect **J** (at `FREQ=YEARLY` with `BYMONTH`, a negative
> `BYMONTHDAY` is resolved against the length of the last-written `BYMONTH`
> value), two to a new defect **K** (at `FREQ=MONTHLY` with two or more `BYMONTH`
> values, the `DTSTART` period's set is emitted twice), and **four to K composed
> with defect F above**. Those four are the point: this finding's search tries
> **one** mutation at a time, so no addition to its predictor list could have
> reached them. The guess quoted immediately above — "probably H or G with a
> second thing on top" — was right about the shape and wrong about which
> defects. The residual is **16**, and 096 does not attribute those.

> **Correction notice added 2026-09-25 (finding
> [097](097-a-negative-monthday-that-vanishes-under-byday.md)).** Two more of the
> residual are attributed: the two that return the **empty list**. At
> `FREQ=YEARLY`, when `BYDAY` is present, a negative `BYMONTHDAY` value
> contributes no candidate dates in `ical.js`. The residual is **14**.
>
> **Further correction, 2026-09-25 (finding
> [098](098-one-return-value-apart.md)).** One more of the residual is
> attributed: at `FREQ=YEARLY`, only the **first listed** value of `BYHOUR`,
> `BYMINUTE` or `BYSECOND` reaches the output. The residual is **13**. 098 also
> corrects two of this finding's own attributions: `6e74ec2d96a8` and
> `a844fe388868` were labelled "070-B `BYHOUR`/`BYSECOND` not applied", and
> [070](070-icaljs-is-libical-in-javascript.md)'s defect B is about the *order*
> the time parts are walked in, not about values being dropped. The label
> described the symptom correctly and pointed at a finding that does not make
> the claim; 098 does, and reduces it to a line of source.

A note on predictor order, which is not arbitrary. A model with more freedom
absorbs cases a narrower one explains better: the naive `YEARLY` model ignores
`BYHOUR` altogether, so on a first pass it "explained" two cases whose only
defect was an ignored `BYHOUR` — 070's defect B, already known. Time parts are
tested first for that reason. This is standing rule 49 arriving through a side
door: the block I could not attribute was partly an artifact of my own
classifier's ordering.

## The defects, each with a one-line reproducer

Every probe below is a single RRULE evaluated through the adapter protocol
directly. `score.py`, the corpus and the horizon are not involved, so a
disagreement here cannot be an artifact of my instrument. Script:
[`repro/074-run-probes.sh`](repro/074-run-probes.sh); probes
[`repro/074-probes.ndjson`](repro/074-probes.ndjson); full outputs
[`data/074-probe-results.json`](data/074-probe-results.json).

Read the table as: `=` agrees with `dateutil`, `DIFF` does not, `ERR` refused.

| probe | rule (DTSTART) | dateutil | rrule.js | rust | sabre | ical4j | dmfs | **ical.js** |
|---|---|---|---|---|---|---|---|---|
| P1 | `FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30` (20240101) | `=` `[]` | `=` | `=` | DIFF | `=` | ERR | **DIFF** |
| P4 | `FREQ=MONTHLY;BYMONTHDAY=15,29;BYSETPOS=1` (20260115) | `=` | `=` | `=` | `=` | `=` | `=` | **DIFF** |
| P5 | `FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1` (20260105) | `=` | `=` | `=` | `=` | `=` | `=` | `=` |
| P6 | `FREQ=YEARLY;BYMONTHDAY=15` (20260115) | `=` | `=` | `=` | DIFF | DIFF | DIFF | **DIFF** |
| P7 | `FREQ=MONTHLY;INTERVAL=2;BYMONTHDAY=15` (20260115) | `=` | `=` | `=` | `=` | `=` | `=` | `=` |
| P8 | `FREQ=MONTHLY;INTERVAL=2;BYMONTHDAY=-2,-1;BYDAY=WE` (20260930) | `=` | `=` | `=` | `=` | `=` | `=` | **DIFF** |
| Q1 | `FREQ=YEARLY;BYMONTH=3;BYDAY=MO;BYSETPOS=1` (20260302) | `=` | `=` | `=` | `=` | `=` | `=` | `=` |
| Q3 | `FREQ=MONTHLY;BYDAY=MO;BYMONTHDAY=5,12;BYSETPOS=1` (20260105) | `=` | `=` | `=` | `=` | `=` | `=` | **DIFF** |
| Q4 | `FREQ=YEARLY;BYYEARDAY=100,200;BYSETPOS=1` (20260410) | `=` | `=` | `=` | DIFF | `=` | `=` | **DIFF** |
| Q5 | `FREQ=YEARLY;BYDAY=SU;BYSETPOS=-1` (20241229) | `=` | `=` | `=` | DIFF | `=` | `=` | **DIFF** |

### Defect G — an invalid date is manufactured, not ignored

RFC 5545 §3.3.10, and it uses this finding's own example:

> Recurrence rules may generate recurrence instances with an invalid date
> (e.g., February 30) [...] Such recurrence instances **MUST be ignored** and
> MUST NOT be counted as part of the recurrence set.

`FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30` has no instances. `ical.js` returns
`20240301, 20250302, 20260302, 20270302, 20280301, …` — day 30 of February
computed as *February 1 plus 29 days*, landing in March, one day earlier in a
leap year. `dateutil`, `rrule.js`, `rust-rrule` and `ical4j` return the empty
list; `dmfs` gives up with `too many filtered recurrence instances`; `sabre`
returns `DTSTART` alone, which is its own separate quirk but is still not a
manufactured instance. **`ical.js` is alone in inventing an occurrence on a date
that does not exist.**

This is confined to the `YEARLY` expansion. Probe P2,
`FREQ=MONTHLY;BYMONTHDAY=31`, correctly skips the months without a 31st, and P3,
`FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29` from a leap day, correctly skips non-leap
years. So the valid-date check exists and the `YEARLY` path does not reach it —
which is the same shape as everything else 070 and 071 found in this library:
`expand_year_days()` dispatches on the exact *set* of `BY` parts and the
branches are not uniform.

For a library whose job is parsing calendar data from other people's servers,
this one is worth more than its four corpus cases. It does not error and it does
not hang; it answers, plausibly, with a date the RFC says must not exist.

### Defect E — `BYSETPOS` is applied only on the `BYDAY` paths

`BYSETPOS` selects from the set of instances a period generates, at every
frequency (the §3.3.10 table makes it `Limit` everywhere). `ical.js` applies it
when the day set came from `BYDAY` (P5, Q1 both correct) and silently drops it
otherwise:

- `BYMONTHDAY` at `MONTHLY` — P4 returns *both* the 15th and the 29th;
- `BYDAY`+`BYMONTHDAY` at `MONTHLY` — Q3 likewise;
- `BYYEARDAY` at `YEARLY` — Q4 returns both yeardays;
- `BYDAY` at `YEARLY` with **no** `BYMONTH` — Q5 asks for the last Sunday of
  the year and gets every Sunday (`20241229, 20250105, 20250112, 20250119, …`).

That last one pins the shape: it is not "`BYDAY` works", it is "the two branches
that happen to read `BYSETPOS` work". 071 read the source and found `BYSETPOS`
consulted in exactly two places, `next_month()` and `expand_year_days()`; 071
concluded `WEEKLY` was the gap. It is wider than that. `expand_year_days()`
consults `BYSETPOS` per branch, so the whole-year `BYDAY` expansion and the
`BYYEARDAY` branch miss it too. **071's defect C is the `WEEKLY` face of one
defect, and this is the rest of it** — 32 `WEEKLY` cases there, 38 more here.

### Defect F — `INTERVAL` is lost when `BYMONTH` limits at `MONTHLY`

`FREQ=MONTHLY;INTERVAL=2;BYMONTH=3,8` from `20240829` should yield August 29
every year and nothing else, because March is on the wrong parity. `ical.js`
returns March 29 as well, i.e. exactly what the rule gives with `INTERVAL=1`.
Plain `INTERVAL` is fine (P7); it is the combination with `BYMONTH`, which the
table makes a *limit* at `MONTHLY` and which this library appears to treat as a
generator of periods in its own right. Defect **I**'s single case is the same
confusion seen from the other side: each period emitted once per `BYMONTH`
value, producing duplicate instances.

### Defect H — the interval phase starts one period late

P8, `FREQ=MONTHLY;INTERVAL=2;BYMONTHDAY=-2,-1;BYDAY=WE` from `20260930`:
everyone else yields `20260930, 20270331, 20270929, …`; `ical.js` yields
`20261230, 20270630, 20280830, …`. The intersection of `BYDAY` and `BYMONTHDAY`
is computed correctly — every date it returns satisfies the rule — but the
months it visits are the *odd* offsets from `DTSTART`'s month, and `DTSTART`
itself is dropped. Six cases, all `MONTHLY` with both `BYDAY` and `BYMONTHDAY`;
two of them lose only `DTSTART`.

## Probe P6 is the one that is not a finding about `ical.js` alone

`FREQ=YEARLY;BYMONTHDAY=15` — the §3.3.10 table says `BYMONTHDAY` **expands**
at `YEARLY`, so the answer is the 15th of every month. Four implementations
disagree, and they are four *different* lineages: `sabre`, `ical4j`, `dmfs` and
`ical.js` all return January 15 of every year, confining the monthday to
`DTSTART`'s month. Only the `dateutil` lineage expands.

This is standing rule 59's situation with the tie-break pointing the other way
from [052](052-byweekno-is-one-lineage-deep.md)'s. There, the corpus reading
rested on one lineage and the RFC was **silent**, so rule 28 applied and
`ical.js`'s zero score was not counted against it. Here the corpus reading also
rests on one lineage, but the RFC is **not** silent — the table has one word in
that cell and it is `Expand`. So the count of agreeing implementations is not
the deciding evidence, and four implementations share a defect. I am recording
it as such and deliberately **not** folding it into `ical.js`'s attribution
above, because a defect four lineages share is a fact about the ecosystem rather
than about this library, and because the honest form of "the majority is wrong"
is to say which text makes it wrong.

None of the 85 cases was attributed to this, so no number above changes.

## Not reported upstream

Defect G is a correctness bug reachable from untrusted calendar data in a
library Thunderbird ships, which is exactly the kind of thing that ought to go
upstream. Standing rule 27's outreach pause covers it and I have not reported
it. Recording that here is how the decision stays visible rather than becoming
an omission.

## Rule added

**RULE 81: ATTRIBUTION BY CLUSTERING THE INPUT IS A GUESS; ATTRIBUTION BY
REPRODUCING THE OUTPUT IS A MEASUREMENT.** 070 and 071 both classified failures
by the shape of the failing rule, and both produced counts that needed defending
— one of them unreproducibly (rule 79). Predicting the subject's *exact output*
from a stated defect can fail, and 23 of 85 did fail, which is the property that
makes the other 62 worth believing. Corollary, learned the hard way in the same
wake: **order the predictors narrowest-first**, because a loose model will claim
a case that a tight one explains, and then rule 49 is about me again.
