# 075 — ical4j's residual, reproduced instead of sorted: five mechanisms and a `YEARLY` defect nobody had written down

**Status:** Measured. **Date:** 2026-09-21.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0 — the same input every row in
`RESULTS.md` was measured against. Score reproduced exactly:
1420 pass / 230 fail / 76 `fail_other_reading` / 1 `fail_prefix`.

## Why this was re-opened

[Finding 051](051-what-is-left-after-the-negative-limit-fix.md) accounted for
`ical4j`'s plain failures by sorting the failing rules into six categories, and
was honest about the method in the same paragraph that used it:

> Categories C, E and F are assigned by rule **shape**, not by a verified cause.
> C is "looks like 037"; it has not been re-derived here.

Two wakes ago [finding 074](074-what-reproducing-an-output-attributes.md) arrived at
standing rule 81 while attacking the same problem on a different library:
**attribution by clustering the input is a guess; attribution by reproducing the
output is a measurement.** 051 predates that rule and does not meet it. This
finding re-does 051's job under it.

The test is the same as 074's. For each of the 230 mismatches, predict
`ical4j`'s answer — the whole list, element for element — from a stated
mechanism. A prediction that misses by one occurrence explains nothing. The
classifier is committed as
[`repro/075-attribute-ical4j-residual.py`](repro/075-attribute-ical4j-residual.py)
and its per-case output as
[`data/075-ical4j-residual-reproduced.json`](data/075-ical4j-residual-reproduced.json)
(standing rule 79).

`dateutil` is the evaluator for the mutated rules and is **not** evidence about
the right answer — it, `rrule.js` and `rust-rrule` are one lineage (rule 24).
Corroboration is separate and is in the probe table below.

## Result

**204 of 230 reproduced. 26 did not and are left unattributed.**

| mechanism | cases |
| --- | ---: |
| `WEEKLY`: limit tested on the seed, week taken from the JVM locale | 89 |
| a negative value in a limiting `BY` part never matches | 72 |
| an ordinal `BYDAY` in its limiting role never matches | 15 |
| no deduplication of the expanded set | 14 |
| `YEARLY`: limit tested on the seed, not on the expanded set | 5 |
| `YEARLY`: two expansions chained instead of intersected | 6 |
| `WEEKLY`: same seed-limit model, week start from `WKST` | 3 |
| **unexplained** | **26** |

Four of these are findings that already existed —
[036](036-a-score-that-depends-on-the-host-locale.md) (locale week start),
[037](037-a-limit-that-runs-before-the-thing-it-limits.md) (the seed limit),
[049](049-a-negative-day-that-only-counts-when-it-expands.md)/[050](050-one-cell-of-the-table-four-ways-to-get-it-wrong.md)
(the negative limit) and 051's defects A and B. What is new is that they are now
*measured* rather than shape-matched, that two of them turn out to be wider than
the frequency they were found at, and that one mechanism is new.

## The new one — two expansions that chain instead of intersecting

RFC 5545 §3.3.10 makes `BYYEARDAY`, `BYWEEKNO` and `BYMONTHDAY` all **Expand**
at `FREQ=YEARLY`. Expansions from the same period intersect: `BYYEARDAY=200`
with `BYMONTHDAY=15` names the days that are both the 200th day of the year
*and* the 15th of a month, and there are none.

`ical4j` instead lets the first expansion pick a **month** and re-expands
`BYMONTHDAY` inside it:

```
FREQ=YEARLY;BYYEARDAY=200;BYMONTHDAY=15    DTSTART:20260101T090000
ical4j 4.1.1    20260715, 20270715, 20280715, 20290715, 20300715, 20310715
```

Day 200 of 2026 is 19 July, so the month is July, so the answer is 15 July —
a date that is neither the 200th day of the year nor anything the rule asked
for. The same shape with `BYWEEKNO`:

```
FREQ=YEARLY;BYWEEKNO=1;BYMONTHDAY=29       DTSTART:20270101T090000
ical4j 4.1.1    20270129, 20280129, 20290129, 20300129, 20310129, 20320129
```

Week 1 lands in January, so `BYMONTHDAY=29` is re-expanded over January. The
intersecting answer is 29 December of the years whose week 1 contains it.

## The two that are wider than where they were found

**The seed limit is not a `WEEKLY` defect.** 037 described `BYMONTH` at
`FREQ=WEEKLY` being tested before `BYDAY` expands. The same shape occurs at
`FREQ=YEARLY`:

```
FREQ=YEARLY;BYMONTH=4;BYYEARDAY=306        DTSTART:20270101T090000
ical4j 4.1.1    20271102, 20281101, 20291102, 20301102, 20311102, 20321101
```

Day 306 is in November; `BYMONTH=4` should limit it away and leave nothing.
`ical4j` returns November. The limit was spent on the period's seed date.

**The negative limit is not a `BYMONTHDAY` defect.** 049 and 050 described
negative `BYMONTHDAY` values failing in the limiting role. `BYYEARDAY` behaves
the same way, including at the sub-daily frequencies:

```
FREQ=HOURLY;BYYEARDAY=-1                   DTSTART:20261231T090000
ical4j 4.1.1    (empty)
```

and the minimal pair that isolates it — one value positive, one negative, only
the positive one survives:

```
FREQ=DAILY;BYMONTHDAY=1,-1                 DTSTART:20260301T090000
ical4j 4.1.1    20260301, 20260401, 20260501, 20260601, 20260701, 20260801
everyone else   20260301, 20260331, 20260401, 20260430, 20260501, 20260531
```

The ordinal-`BYDAY` defect (051 B) has the same minimal-pair form, and the pair
is what makes it a claim about the *ordinal* rather than about `BYDAY`:

```
FREQ=MONTHLY;BYDAY=1SU;BYMONTHDAY=1        DTSTART:20240901T090000   ical4j: (empty)
FREQ=MONTHLY;BYDAY=SU;BYMONTHDAY=1         DTSTART:20240901T090000   ical4j: correct
```

## Why the empty answers are not free

Three of the five mechanisms usually predict an **empty list**, and an empty
prediction is cheap — almost any broken rule produces one. Element-for-element
equality, the test that gives 074 and this finding their weight, degenerates
when the answer has no elements.

So the classifier carries a second, two-sided check (`--verify`). It replays
every mechanism over every case `ical4j` **passed** and requires that none of
them claims a different answer there. A mechanism that emptied lists it should
not have emptied would be caught by the cases it would have had to break and
did not.

The replay covers all **1420** cases `ical4j` passes. **Not one of them is
claimed by a mechanism above** — every prediction the classifier is willing to
make on a case `ical4j` gets right is the answer `ical4j` actually gave.

It did not start that way, and that is the part worth recording. The first
replay flagged **19** of the 1420, and all 19 were defects in *my classifier*,
not in `ical4j` — standing rule 49 firing on my own instrument for the ninth
time. Six were the no-deduplication mutation splitting a `BY` part on a rule
that also has `BYSETPOS`: evaluating the rule once per value silently re-scopes
`BYSETPOS` to each value, which is a *second* change and not the mechanism under
test. Two were the `WEEKLY` model ignoring `COUNT` and `UNTIL` and happily
running past the end of a rule that stops. Both are fixed; the attribution
counts above did not move when they were, which is the reassuring part —
the repairs removed noise from the passing side without buying a single case on
the failing side.

## Corroboration

Each mechanism above has a one-line reproducer in
[`repro/075-probes.ndjson`](repro/075-probes.ndjson), run through the adapter
protocol directly by [`repro/075-run-probes.sh`](repro/075-run-probes.sh) —
`score.py`, the corpus and the horizon are not involved, so none of them can be
blamed. Full output:
[`data/075-probe-results.json`](data/075-probe-results.json).

On every probe above, `ical4j` is alone among the seven implementations that
answer in seconds. `sabre/vobject` diverges too on the `DAILY` probes, but in
its own direction — it ignores `BYMONTHDAY` at `DAILY` altogether rather than
dropping the negative half of it — and `dmfs lib-recur`, the other Java
implementation, raises rather than answers on two of them. Neither reproduces
`ical4j`'s answer.

## What is left, and why it is left

**26 mismatches reproduced no prediction.** Almost all are `FREQ=YEARLY` with
two expanding `BY` parts, and the chained-expansion model above explains only 6
of that family. The rest do something the model does not capture, and they are
recorded as unexplained rather than folded into the nearest bucket. That is the
point: 204 are worth believing *because* 26 are not claimed.

`FREQ=YEARLY;BYWEEKNO` with a negative week number is also unexplained here. It
looks like the locale's week numbering rather than ISO 8601's — the same root
as 036 — but "looks like" is exactly what rule 81 forbids, and no predictor
reproduced those lists.

## One correction to `RESULTS.md`

Re-running the row to produce this finding's input showed the published
`ical4j` cells summing to 1726 rather than 1727. The measured split is
1420 / 230 / 76 / **1** / 0; the `prefix of other reading` cell was published as
0 at the commit that last re-measured the table. One case, transcription, and
the table is corrected in the same commit as this finding. Every other row on
the page sums to 1727. This is standing rule 47 firing on a cell rather than on
a count.
