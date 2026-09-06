# 008 — BYWEEKNO and the weeks that straddle a year boundary

**Status:** Adjudicated. All five remaining `BYWEEKNO` disputes from
[finding 004](004-bysetpos-first-period-truncation.md) resolve the same way,
and the cause is a `python-dateutil` defect that **is already reported
upstream** — `dateutil/dateutil`
[PR #1537](https://github.com/dateutil/dateutil/pull/1537), open since
2026-07-15, with the same root-cause analysis I arrived at independently.
**Nothing here is a new discovery.** What is new is independent corroboration
from cases the PR does not test, and one *further* defect that survives the
fix.

**Date:** 2026-09-06. **Affects:** `python-dateutil` 2.9.0.post0.
**Nothing has been sent upstream.** No authorization exists to comment on
#1537.

## The primary source

RFC 5545 §3.3.10 defines the numbering it means, and then states a fact about
it that is directly testable:

> The BYWEEKNO rule part specifies a COMMA-separated list of ordinals
> specifying weeks of the year. Valid values are 1 to 53 or -53 to -1. This
> corresponds to weeks according to week numbering as defined in
> [ISO.8601.2004]. A week is defined as a seven day period, starting on the day
> of the week defined to be the week start (see WKST). Week number one of the
> calendar year is the first week that contains at least four (4) days in that
> calendar year.
>
> Note: Assuming a Monday week start, week 53 can only occur when Thursday is
> January 1 or if it is a leap year and Wednesday is January 1.

`src/byweekno_check.py` implements that definition and nothing else. For
`WKST=MO` it is checked against Python's `date.isocalendar()` over 109,938
consecutive days (1900-01-01 … 2200-12-31), **all equal** — so the ground truth
in this finding is not supplied by this project's own expander, and the
lineage objection of [finding 003](003-implementation-lineage.md) does not
apply to it.

## Defect A — the previous year's last week is numbered one too high

For `WKST=MO`, `FREQ=YEARLY;BYWEEKNO=53` over 1970–2100 emits **18 days that
are in ISO week 52**, and `BYWEEKNO=52` **misses those same 18 days**. They are
the first two days of years that begin on a Saturday whose predecessor has only
52 weeks: `1983-01-01/02`, `1994-01-01/02`, `2011-01-01/02`, `2022-01-01/02`,
`2039-01-01/02`, `2050-01-01/02`, … These are ordinary dates, two of them in
the past.

Each is January 1–2 of a year that starts on a Saturday, so under `WKST=MO`
they belong to the previous year's last week. RFC 5545's own note settles which
number that week has: 2038 began on a **Friday** and is not a leap year, so
2038 has **no week 53**, and `2039-01-01` cannot match `BYWEEKNO=53` under any
reading of which year owns it.

The cause is `dateutil/rrule.py` `_iterinfo.rebuild()` (2.9.0.post0, line 1210):

```python
lnumweeks = 52+(self.yearlen-no1wkst) % 7//4
```

which computes the *previous* year's week count from the *current* year's
length and offset, and hardcodes `52` where the parallel current-year block a
few lines above uses `div` from `divmod(wyearlen, 7)`. PR #1537 replaces it
with the previous year's own `lyearlen` / `lno1wkst` and a real `divmod`.

The same failure appears under other week starts — 22 days for `WKST=SU`, 18
for `WKST=WE` — so it is not specific to the ISO default.

## What this project adds: the five disputes

`corpus/disputed.json` had five synchronized disputes left unadjudicated after
finding 004. Their expected values were produced by `src/naive.py`, written
from the RFC text, with no code shared with `dateutil`. Re-running them against
`dateutil` 2.9.0.post0 and against the same version with PR #1537's diff
applied:

| rule | DTSTART | 2.9.0.post0 | with #1537 |
| --- | --- | --- | --- |
| `FREQ=YEARLY;BYMONTH=1,5;BYWEEKNO=1,52;WKST=SU;BYSETPOS=2` | 20270102 | differs | **agrees** |
| `FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52` | 20280101 | differs | **agrees** |
| `FREQ=YEARLY;BYWEEKNO=53;BYYEARDAY=1,200` | 20270101 | differs | **agrees** |
| `FREQ=YEARLY;BYYEARDAY=60,1;BYWEEKNO=-2,53` | 20270101 | differs | **agrees** |
| `FREQ=YEARLY;INTERVAL=3;BYWEEKNO=52,-2;BYSETPOS=1` | 20291217 | differs | **agrees** |

All five, exactly. None of them is the reproduction in #1537: they combine the
misnumbered week with `BYMONTH`, `BYYEARDAY`, `BYSETPOS`, `INTERVAL=3` and a
non-default `WKST`, and two of them are cases where the wrong week number
changes *which* occurrence `BYSETPOS` selects rather than merely adding or
removing one. That the fix repairs all five and over-corrects none is evidence
about the fix that the PR's own single regression test cannot give.

**With this, all 13 synchronized disputes in the corpus are accounted for:** 8
by the `BYSETPOS` first-period mechanism of finding 004 (which stays *unsettled*
— §3.8.5.3 makes its applicability turn on the reading under dispute), and
these 5 by defect A.

## Defect B — negative BYWEEKNO never reaches next year's week 1

This one survives PR #1537.

`FREQ=YEARLY;BYWEEKNO=-53` misses **65 days** under `WKST=MO` (64 under `SU`,
68 under `WE`) — for example `1975-12-29/30`, which are week 1 of 1976, a
53-week year, so `-53` denotes exactly that week. Applying PR #1537 changes
nothing here.

This is dateutil being inconsistent with itself rather than obviously wrong
against the RFC:

* `BYWEEKNO=1` **does** match `1975-12-29`. `rebuild()` has an explicit "Check
  week number 1 of next year as well" block, so dateutil already commits to the
  reading in which a day's week number is resolved against the year that *owns*
  the week, not the calendar year the day sits in.
* `BYWEEKNO=53` and `BYWEEKNO=-1` **do** look backwards into the previous
  year's last week, the same reading in the other direction.
* Only negative values pointing *forwards* are dropped. The source says so:
  the block carries the comment `# TODO: Check -numweeks for next year.`

So this is not a discovery either — it is a gap the code labels itself.

**And I am not certain it is a defect.** It turns on a question RFC 5545 does
not answer: when `FREQ=YEARLY` expands year *Y*, is a negative `BYWEEKNO`
counted back from the number of weeks in *Y*, or from the number of weeks in
the year that owns the candidate day's week? Under the first reading `-53`
denotes nothing in a 52-week year and dateutil is right. Under the second — the
one dateutil itself uses everywhere else — it denotes week 1 of the next year
and dateutil is wrong. §3.3.10 says only "weeks of the year" and defines
numbering per calendar year; it never says which year an expansion's negative
index counts within. I am recording the asymmetry, not adjudicating it.

## Reproduce

```sh
PYTHONPATH=src python3 src/byweekno_check.py      # exits non-zero on mismatch
```

Sweeps `BYWEEKNO` ∈ {1, 20, 52, 53, -1, -2, -53} × `WKST` ∈ {MO, SU, WE} over
1970–2100 against the RFC's definition, after self-checking that definition
against `date.isocalendar()`. Recorded output:
`findings/data/008-byweekno-sweep.json` (stock) and
`findings/data/008-byweekno-sweep-patched.json` (with #1537 applied).

## What the evidence bar caught this time

I had a reproducible, systematic, primary-source-backed defect in a widely used
library within about twenty minutes, and it was **already reported, with the
same root cause, seven weeks earlier**. That is the fourth item of the bar
("existing reports searched") doing the only job it has, for the second time in
two days — the first was [Errata 3883](https://www.rfc-editor.org/errata/eid3883)
in finding 005. The rate at which this happens is itself information about how
much of what I find is new.
