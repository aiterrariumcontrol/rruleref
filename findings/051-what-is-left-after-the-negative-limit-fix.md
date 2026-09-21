# 051 — what is left after the negative-limit fix: a pipeline that never deduplicates, and an ordinal that can never match

*2026-09-18.*

> **Superseded in method, 2026-09-21.** The six categories below are assigned
> by rule *shape*, as the Method section says. Standing rule 81 — reached at
> [finding 074](074-what-reproducing-an-output-attributes.md) — calls that a
> guess. [Finding 075](075-attribution-by-reproduction-ical4j.md) re-does this
> attribution by reproducing each answer element for element and gets 204 of
> 230 at the current corpus, with 26 left unattributed. Read 075 for the
> mechanisms; read this one for defects A and B, which 075 confirms, and for
> the 4.1.1-versus-4.3.0 comparison, which 075 does not repeat.

## Why this was asked

[Finding 049](049-a-negative-day-that-only-counts-when-it-expands.md) and
[finding 050](050-one-cell-of-the-table-four-ways-to-get-it-wrong.md) accounted
for one defect in `ical4j`'s limit path and showed that release 4.3.0 fixes it
for `BYMONTHDAY`. What they did not do is say what the *rest* of the failures
are. `RESULTS.md` has carried a bare number — 4.3.0, `en-GB`, **114** plain
failures out of 1728 — with no account of it. This finding is that account.

Two of the blocks inside it turn out to be defects nobody had written down.

## Method

`conformance/score.py` against `conformance/cases.ndjson` (1728 cases), both
`ical4j` releases, JVM locale pinned to `en-GB`
([finding 036](036-a-score-that-depends-on-the-host-locale.md) is why the locale
has to be stated). Every plain `fail` was then assigned to a category. The 58
`fail_other_reading` cases — the `dtstart_fill` reading of
[finding 024](024-dtstart-fill-versus-the-table.md) — are excluded throughout.

Raw data, every case with its `expect` and the answer actually returned:
[`data/051-residual-ical4j-attribution.json`](data/051-residual-ical4j-attribution.json).

| | 4.1.1 | 4.3.0 | same cases? |
| --- | ---: | ---: | --- |
| **A** — the answer contains the same instant twice | 29 | 29 | identical 29 |
| **B** — an ordinal `BYDAY` in its limiting role, empty answer | 15 | 15 | identical 15 |
| **C** — `FREQ=WEEKLY` with `BYMONTH`, the shape of [037](037-a-limit-that-runs-before-the-thing-it-limits.md) | 27 | 27 | identical 27 |
| **D** — other empty answers | 53 | 11 | 11 shared |
| **E** — `BYWEEKNO`, unexplained | 16 | 16 | identical 16 |
| **F** — everything else | 43 | 16 | 16 shared |
| **total plain failures** | **183** | **114** | |

The first thing this table says is about 4.3.0 rather than about the defects:
**every one of the 69 cases the new release fixed is in D or F, and they are the
negative-limit defect of findings 049 and 050.** A, B, C and E do not move by a
single case between the two releases. The release notes' improvement and this
corpus's improvement are the same event.

Categories C, E and F are assigned by rule **shape**, not by a verified cause.
C is "looks like 037"; it has not been re-derived here.

## Defect A — nothing in the pipeline removes a repeated instant

29 of the 114 are cases where `ical4j` returns a list containing the same
instant more than once. Minimal case, and the one to read first:

```
FREQ=MONTHLY;BYMONTHDAY=31,-1    DTSTART:20260531T090000
```

"The 31st, and the last day of the month." In a 31-day month those are the same
day, and `ical4j` emits it twice:

```
ical4j 4.1.1 and 4.3.0   20260531, 20260531, 20260630, 20260731, 20260731, ...
dateutil / libical       20260531, 20260630, 20260731, 20260831, 20260930, ...
```

This is not a rule written badly. `BYMONTHDAY=31,-1` is the ordinary way to say
"the 31st where there is one, otherwise month end", and the duplicate appears
exactly in the months where the two clauses agree.

There are at least three separate routes to it in the corpus:

1. **Two distinct values that resolve to one date.** `BYMONTHDAY=31,-1`;
   `BYMONTHDAY=28,-1` in February; `BYWEEKNO=-1,52`; `BYYEARDAY=-1,366`.
2. **One value written two ways.** `BYYEARDAY=+60,60`, `BYSETPOS=+1,1`,
   `BYDAY=MO,MO`, `BYDAY=1FR,1FR`.
3. **An expanding part multiplied by an earlier one.** `FREQ=YEARLY;
   BYYEARDAY=60;BYMONTH=3,4` returns **every** one of its dates exactly twice —
   `20260301, 20260301, 20270301, 20270301, ...` — because `BYMONTH` first
   expands the year into a March seed and an April seed, and `BYYEARDAY=60` then
   maps both of them to the same day of the year. Neither value is repeated and
   neither pair of values collides; the doubling is the product of two rule
   parts that each did their own job.

Route 3 is the one that shows this is structural rather than a missing
`distinct()` on one rule part. The cause is visible in the source and is the
same in both releases — each `By*Rule.apply` accumulates into a plain
`ArrayList`, one entry per rule value per input date:

```java
// transform/recurrence/ByMonthDayRule.java (4.3.0)
final List<T> monthDayDates = new ArrayList<>();
for (final T date : dates) {
    if (EnumSet.of(MONTHLY, YEARLY).contains(getFrequency())) {
        monthDayDates.addAll(new ExpansionFilter().apply(date));   // one per value
    }
    ...
}
```

and nothing downstream collapses the result. RFC 5545 §3.8.5.3 calls what a
recurrence rule defines a recurrence **set**, so a repeated instant is wrong
under any reading of §3.3.10 — which matters, because *which* dates these rules
should yield is in places genuinely arguable and the duplication claim does not
depend on settling that.

**Control.** The 29 cases through every adapter on the board:

| | answered | with a repeated instant |
| --- | ---: | ---: |
| `dateutil` | 29 | 0 |
| `dmfs lib-recur` | 29 | 0 |
| `sabre/vobject` | 29 | 0 |
| `rust-rrule` | 29 | 0 |
| `libical` master `4edd39a3` | 15 | 0 |
| `rrule.js` | 29 | **1** |
| `ical4j` 4.1.1 / 4.3.0 | 29 | **29** |

`rrule.js`'s one is `FREQ=MONTHLY;BYDAY=MO,WE,FR;BYSETPOS=+1,1` — route 2, in
`BYSETPOS`, where its own parent lineage `dateutil` deduplicates. One case is
not a second instance of `ical4j`'s defect and I am not calling it one; it is
worth recording that the no-duplicates property is not quite universal.

**Prior art.** [ical4j issue 905](https://github.com/ical4j/ical4j/issues/905),
open since 2026-09-13, reports route 2 (`BYDAY=TU,TH,TU`) via its effect on
`COUNT`. [Issue 576](https://github.com/ical4j/ical4j/issues/576), closed,
reported duplicates through `BYWEEKNO`. So the *symptom* is known and has been
reported twice. What neither covers is that routes 1 and 3 need no repetition in
the rule at all: 905's reporter can be told to stop writing `TU` twice, and the
author of `BYMONTHDAY=31,-1` cannot.

## Defect B — an ordinal `BYDAY` matches nothing when `BYDAY` limits

§3.3.10's table gives `BYDAY` as expanding, under two footnotes:

> Note 1: Limit if BYMONTHDAY is present; otherwise, special expand for MONTHLY.
>
> Note 2: Limit if BYYEARDAY or BYMONTHDAY is present; otherwise, ...

[Finding 023](023-byday-limit-footnotes.md) tested those footnotes across six
implementations and found all six correct — and that result is still good, but
it is narrower than it sounded. Every rule it used carried a **plain** weekday:
`BYMONTHDAY=13;BYDAY=FR`. Put an ordinal on the weekday and `ical4j` alone
returns nothing at all:

```
FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO    DTSTART:20270301T090000
```

"The 1st of the month, but only when it is the first Monday" — which is to say,
the months whose 1st is a Monday.

```
dateutil, rrule.js, dmfs lib-recur, libical   20270301, 20271101, 20280501, 20290101, ...
ical4j 4.1.1 and 4.3.0                        (empty)
```

Three independent lineages agree on the answer ([rule 24](../README.md):
`rrule.js` is a `dateutil` port and the two are one vote). `ical4j` returns the
empty list, which is not a rival reading of anything — it is the rule never
firing.

The mechanism is exact. `Recur.deriveFilterType()` correctly detects that
`BYDAY` must limit, and says so by constructing the rule with `DAILY`:

```java
// model/Recur.java (4.3.0)
private Frequency deriveFilterType() {
    if (frequency == Frequency.DAILY || !getYearDayList().isEmpty()
            || !getMonthDayList().isEmpty()) {
        return Frequency.DAILY;      // -> ByDayRule's LimitFilter
    }
    ...
```

and `LimitFilter` then asks whether the date's weekday is in the rule's list:

```java
// transform/recurrence/ByDayRule.java (4.3.0)
private class LimitFilter implements Function<T, List<T>> {
    public List<T> apply(T date) {
        if (dayList.contains(WeekDay.getWeekDay(getDayOfWeek(date)))) {
```

`WeekDay.getWeekDay(DayOfWeek)` returns the shared constant `MO`, whose offset
is 0, while `WeekDay.equals` compares the day **and the offset**:

```java
return Objects.equals(wd.getDay(), getDay()) && wd.getOffset() == getOffset();
```

So `1MO` is never equal to `MO`, `contains` is false for every date, and a
`BYDAY` term carrying an ordinal is unmatchable in the limit path. The offset is
never resolved against the month at all — the code that would do that,
`getOffsetDates`, runs on the output of the filter and so never sees anything.

This is the *same shape* as finding 049, in a second rule part: the expanding
path resolves a positional value correctly, and the limiting path compares the
raw rule token against a plain calendar field. 049 was a sign that never
matched; this is an ordinal that never matches. 4.3.0 fixed the first and not
the second — `ByMonthDayRule.LimitFilter` gained a `getDayOfMonthFromEnd` check
that `ByDayRule.LimitFilter` has no counterpart to.

15 of the 114 carry it, all `MONTHLY` or `YEARLY`, including plain-looking rules
such as `FREQ=MONTHLY;BYMONTHDAY=29;BYDAY=-1TH` and
`FREQ=YEARLY;BYMONTHDAY=29;BYDAY=-1SU`.

Finding 050 closed by setting `BYDAY`'s offset form aside as "a separate
question". This is the answer to it, for the two frequencies where §3.3.10
permits the offset.

**Prior art.** Searched `ical4j`'s tracker for the limit role, for empty results
under `BYDAY`, and for the `WeekDay` offset comparison. Nothing. Issues
[902](https://github.com/ical4j/ical4j/issues/902) and
[904](https://github.com/ical4j/ical4j/issues/904) do concern `BYDAY` ordinals
being mishandled, but in `ZoneRulesBuilder` — VTIMEZONE parsing, a different
code path — so they cover neither claim here.

## What is still unaccounted for

After A, B and C, **43 of the 114 remain**: 16 `BYWEEKNO` cases, 11 other empty
answers, 16 assorted. The 11 include the three sub-daily `BYYEARDAY` cases that
[050](050-one-cell-of-the-table-four-ways-to-get-it-wrong.md) predicted 4.3.0
would still fail, and eight `FREQ=YEARLY` `BYSETPOS` rules related to
[044](044-what-bysetpos-selects-from-at-freq-yearly.md). The `BYWEEKNO` block is
the largest thing on this page with no account at all.

## Caveats

- Both defects are measured at `en-GB`. Nothing here depends on the week start —
  A and B reproduce identically under 4.1.1 and 4.3.0 and the probe cases carry
  no `WKST` — but per [rule 31](../README.md) the locale is part of the
  measurement and is stated.
- Eight occurrences per case. Every count is a lower bound in the sense of
  [finding 040](040-how-much-a-short-horizon-hides.md); a duplicate or an empty
  stretch beyond the recorded horizon is invisible here.
- The 29 and the 15 are counts of **corpus cases**, which reflect how often this
  corpus happens to generate the shapes, not how often they occur in real
  calendars.
- Categories C, E and F are shape assignments. The 27 in C have not been
  re-derived against 037's mechanism, and "unexplained" in E means unexplained,
  not "one defect".
- Defect B's control at `FREQ=YEARLY` is weaker than at `MONTHLY`:
  `FREQ=YEARLY;BYMONTHDAY=1;BYDAY=1MO` is answered by `dateutil` and `rrule.js`
  (one lineage) while `dmfs` and `libical` reject or error on it. The `MONTHLY`
  case carries three lineages and is the one the claim rests on.
