# 056 — two scopes for one word: Category F, and the last of 051's six blocks

*2026-09-18.*

## Why this was asked

[Finding 051](051-what-is-left-after-the-negative-limit-fix.md) sorted
`ical4j` 4.3.0's residual corpus failures into six categories, and said plainly
which of them were guesses:

> Categories C, E and F are shape assignments.

Category F was the worst of the three, because its shape was *no shape*: 16
cases labelled "everything else", the residue after every other clustering had
taken what it could. [054](054-one-mechanism-twenty-seven-failures.md) closed C
and [052](052-byweekno-is-one-lineage-deep.md) accounted for E. F was the last
block on the page with no account at all. It is not assorted. Ten of the 16 are
one mechanism, five are not a defect of any kind, and one is a defect already
published, arriving by a route it had not been seen to take.

## Method

`ical4j`'s `Recur.getCandidates` is a pipeline: one seed date per period, then
`BYMONTH`, `BYWEEKNO`, `BYYEARDAY`, `BYMONTHDAY`, `BYDAY`, `BYHOUR`, `BYMINUTE`,
`BYSECOND`, `BYSETPOS`, each rule transforming the list the previous one
returned. That is the order §3.3.10 gives, and the RFC's table is quoted
verbatim in `AbstractDateExpansionRule.java`.

So the whole pipeline is reimplemented here for `FREQ=YEARLY`, from the 4.3.0
sources and nothing else:
[`repro/056-predict-yearly-pipeline.py`](repro/056-predict-yearly-pipeline.py).
It covers rules whose parts are drawn from `{FREQ, INTERVAL, WKST, BYMONTH,
BYYEARDAY, BYMONTHDAY, BYDAY, BYSETPOS}` — 305 of the corpus's 374 `FREQ=YEARLY`
cases; the other 69 carry `BYWEEKNO` (50), `BYHOUR` (9), `COUNT` (4), `UNTIL`
(4), `BYMINUTE` (1) or `BYSECOND` (1).

**It reproduces `ical4j` byte-for-byte on all 305, in 4.1.1 and in 4.3.0** — the
228 it gets right as well as the 77 it gets wrong. As in
[054](054-one-mechanism-twenty-seven-failures.md), that is the claim that makes
the rest of this page more than a story about four-line excerpts: the account
below is not a plausible reading of the source, it is the source's behaviour.

One detail of the predictor is worth naming because it is somebody else's
finding and not a new one. Its `BYDAY`-limits branch matches only a *plain*
weekday, because `ByDayRule.LimitFilter` compares whole `WeekDay` values —
ordinal included — against a plain one. That is
[051](051-what-is-left-after-the-negative-limit-fix.md)'s defect B, reproduced
rather than re-derived. Without it the predictor missed exactly 6 of the 305,
all of them 051's defect-B cases: a free independent check on a finding written
before this pipeline model existed.

Every case, sub-block and lineage:
[`data/056-category-f-attribution.json`](data/056-category-f-attribution.json).

## The mechanism: `expand` has two different scopes in the same pipeline

Two of the pipeline's expansion rules disagree about what an already-selected
date constrains.

`ByMonthDayRule`, at `YEARLY`, expands within the **enclosing month** of the
date it is given:

```java
final var yearMonth = YearMonth.of(getYear(date), getMonth(date).getMonthOfYear());
...
candidate = withTemporalField(date, DAY_OF_MONTH, monthDay);
```

`ByYearDayRule`, at `YEARLY`, expands within the **enclosing year**:

```java
final int numDaysInYear = Year.of(getYear(date)).length();
...
candidate = withTemporalField(date, DAY_OF_YEAR, yearDay);
```

Both are labelled `Expand` for `YEARLY` in the table the RFC gives and the
source quotes. Only one of them can be reading that word the same way. If
`expand` means "over the period of the `FREQ`" — the year — then
`ByMonthDayRule` is too narrow. If it means "over the unit one step above the
one the part names" — the month — then `ByYearDayRule` is too wide. There is no
reading of §3.3.10 under which both are right, and that is a statement about
`ical4j`'s internal consistency rather than about the specification, which is
why it does not depend on settling what §3.3.10 means.

One case shows both halves at once. `FREQ=YEARLY;BYYEARDAY=365,100;BYMONTHDAY=5,30`,
`DTSTART` 20241230T090000, second period:

| stage | dates |
| --- | --- |
| seed | 2025-12-30 |
| `BYYEARDAY=365,100` | 2025-12-31, 2025-04-10 |
| `BYMONTHDAY=5,30` | 2025-12-05, 2025-12-30, 2025-04-05, 2025-04-30 |

`BYYEARDAY` threw away the month December that the seed carried. `BYMONTHDAY`
then treated the months that `BYYEARDAY` had landed on as binding and expanded
inside them. Neither part's own restriction survives: nothing in the answer is
the 365th or 100th day of 2025, and the rule's author asked for dates that are
both. The corpus's control returns `20281230`, `20321230`, `20361230` … — the
intersection, day-of-year 365 in the leap years where it is also the 30th.

The same overwrite is what makes `BYMONTH` disappear.
`FREQ=YEARLY;BYYEARDAY=60;BYMONTH=3` — "the 60th day of the year, when it falls
in March" — returns `20280229` in leap years, because `BYMONTH` ran first,
selected March, and `ByYearDayRule` then replaced the day of the year without
asking whether the result was still in March.

## What Category F actually is

| sub-block | cases | what it is |
| --- | ---: | --- |
| `BYYEARDAY` discards the month | 10 | the mechanism above; every one carries `BYYEARDAY` |
| a truncated `dtstart_fill` reading | 5 | **not a defect** — see below |
| [051](051-what-is-left-after-the-negative-limit-fix.md)'s defect A through `BYSETPOS` | 1 | `FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12;BYSETPOS=2` |

The single `MONTHLY` case is the only member of F that is not `FREQ=YEARLY`, and
it is 051's duplicate-instant defect taking a route 051 did not record. In
April, `BYMONTHDAY=30` and `BYMONTHDAY=-1` name the same day; nothing
deduplicates; so the set handed to `BYSETPOS` has two members where the correct
set has one, and `BYSETPOS=2` selects the duplicate instead of selecting
nothing. This is the same shape as
[054](054-one-mechanism-twenty-seven-failures.md)'s third consequence of 037 —
`BYSETPOS` indexing into a set that should never have contained what it contains
— arrived at from the other defect.

## The five that are not a defect

The remaining five are `FREQ=YEARLY` with `BYMONTHDAY` and a plain `BYDAY`, and
they are an artifact of my own instrument. On
`FREQ=YEARLY;BYDAY=SU;BYMONTHDAY=28`, `DTSTART` 20270228T090000:

```
expect            20270228 20270328 20271128 20280528 20290128 20291028 20300428 20300728
alt dtstart_fill  20270228 20380228 20440228 20490228 20550228 20660228 20720228 20770228
ical4j 4.3.0      20270228 20380228 20440228 20490228 20550228
libical master    20270228 20380228 20440228 20490228 20550228 20660228 20720228 20770228
dmfs              20270228 20380228 20440228 20490228 20550228
```

`ical4j` and `dmfs` return a **proper prefix** of the rival `dtstart_fill`
reading of [finding 024](024-dtstart-fill-versus-the-table.md) — the reading
`libical` returns in full. They stop at five because my Java adapter's window is
`DTSTART` + 10958 days and the sixth occurrence is 39 years out. `score.py`
recognises a rival reading only by exact equality, so a prefix of one is
reported as `mismatch`, which is precisely the confusion
[rule 35](../README.md) exists to prevent: *stopped expanding* and *emitted a
date the control did not* are two different facts.

This is [rule 49](../README.md) for the second time — a residual I could not
attribute turning out to be a property of the instrument — so the scale is worth
measuring rather than asserting. Over all 1721 scored cases, counting plain
failures that are a proper non-empty prefix of `expect` or of a recorded
alternative reading:

| adapter | plain `fail` | prefix of `expect` | prefix of an alternative |
| --- | ---: | ---: | ---: |
| `dateutil` | 0 | 0 | 0 |
| `rrule.js` | 26 | 0 | 0 |
| `rust-rrule` | 0 | 0 | 0 |
| `libical` master | 8 | 0 | 0 |
| `ical4j` 4.3.0 | 106 | 0 | **7** |
| `dmfs` | 13 | 0 | **7** |
| `sabre` | 782 | 0 | 0 |

It is confined to the two JVM adapters and to seven cases each — the two
implementations that [rule 35](../README.md) already records as quitting around
thirty years after `DTSTART`. Five of `ical4j`'s seven are the F cases here; the
other two are `FREQ=YEARLY;BYWEEKNO=53` shapes inside Category E, so E is 14
rather than 16 for the same reason. For `dmfs` the seven are more than half of
its entire residual.

I have **not** changed `score.py` here. A third bucket for "a prefix of a rival
reading" is the right fix and it is small, but it moves published counts for two
adapters, and doing that properly means the tables in `RESULTS.md`, the README
and the live diagnostic all move with it ([rule 3d](../README.md)). Recorded,
measured, and deliberately left for a separate change; the numbers above are the
whole of it.

## Other implementations

On the ten `BYYEARDAY` cases: `dateutil`, `rrule.js` and `rust-rrule` — one
lineage, [rule 24](../README.md) — all return the intersection, and so does
`dmfs`, which is a second lineage. `libical` master answers
`UNIMPLEMENTED: This feature has not been implemented` on all ten, a limitation
it declares by name rather than a crash ([rule 40](../README.md)). `sabre` fails
all ten, and separately fails 782 cases overall, so that is not evidence of
much.

Two lineages agreeing is two lineages, not a proof ([rule 9](../README.md)), and
on this block the disagreement is not really about the answer — `ical4j`'s answer
contains dates that satisfy neither `BYYEARDAY` nor `BYMONTHDAY`, which no
reading asks for.

On the five truncated cases the picture is the opposite and is the reason they
are filed as a reading and not a defect: `dmfs` returns the identical prefix and
`libical` returns the same list in full. Three implementations, two of them
independent lineages, take the `dtstart_fill` reading here.

## Prior art

Searched `ical4j`'s tracker for each claim separately
([rule 38](../README.md)): `BYYEARDAY`, `BYYEARDAY`+`BYMONTH`,
`BYMONTHDAY`+`YEARLY`, `ByMonthDayRule`, `ByYearDayRule`, `BYMONTH`+expand, and
across all of GitHub for `ical4j BYYEARDAY BYMONTH`. Nothing covers either half.

The closest is [issue 39](https://github.com/ical4j/ical4j/issues/39) (2015,
closed), where `FREQ=MONTHLY;BYMONTH=2,3,9,10;BYMONTHDAY=28,29,30,31;BYSETPOS=-1`
selects across a candidate list spanning several months — the same family of
complaint, about `BYSETPOS` over a set assembled more widely than the reporter
expected, but at `MONTHLY` and about the size of the set rather than about two
expansion scopes. [Issue 23](https://github.com/ical4j/ical4j/issues/23) (2012)
is the observation that `getCandidates` did no expansion at all, which is the
history the current pipeline came out of. Neither states what is here.

Nothing was reported upstream. [Rule 27](../README.md) is in force; a finding
that stays in this repository is an accepted outcome.

## What this closes

With F accounted for, **every one of `ical4j` 4.3.0's residual plain failures in
this corpus now has a named account.** Rescored today at `en-GB`, they are 106,
not the 114 that 051 published:

| block | cases | account |
| --- | ---: | --- |
| A | 29 | [051](051-what-is-left-after-the-negative-limit-fix.md) — nothing deduplicates |
| B | 15 | [051](051-what-is-left-after-the-negative-limit-fix.md) — ordinal `BYDAY` in its limiting role |
| C | 27 | [054](054-one-mechanism-twenty-seven-failures.md) — one mechanism, derived |
| D | 3 | [050](050-one-cell-of-the-table-four-ways-to-get-it-wrong.md) — the sub-daily `BYYEARDAY` cases it predicted would survive |
| E | 16 | [052](052-byweekno-is-one-lineage-deep.md) — finding 024's split, one lineage deep; 2 of the 16 are prefixes, as above |
| F | 16 | this finding |

The eight cases between 114 and 106 are all of D, they all now score as the
`dtstart_fill` alternative reading rather than as a plain failure, and the cause
is [finding 053](053-a-short-list-is-not-always-my-horizon.md) removing the
length guard that had suppressed that reading on sparse `FREQ=YEARLY` shapes.
051 predicted the shape of what would remain in D — "the three sub-daily
`BYYEARDAY` cases that 050 predicted" plus "eight `FREQ=YEARLY` `BYSETPOS`
rules" — and it is exactly those eight that moved. A count published four days
ago is already the wrong count, for a reason that is itself published.

## Caveats

- Measured at `en-GB` ([rule 31](../README.md)). `ical4j` 4.1.1 and 4.3.0 agree
  case for case on all 305 in-scope `YEARLY` cases, and the predictor matches
  both.
- Eight occurrences per case, and a 10958-day adapter window. Every count here
  is a lower bound in the sense of [finding 040](040-how-much-a-short-horizon-hides.md)
  — except the two marked **7** in the prefix table, which are the first counts
  in this project that are an *upper* bound on a defect count rather than a
  lower one.
- 16 is a count of corpus cases, not of real calendars. `BYYEARDAY` with
  `BYMONTH` or `BYMONTHDAY` is rare in the wild; the corpus generates it because
  §3.3.10 permits it.
- The predictor is a model of one frequency. It says nothing about `MONTHLY`
  `BYYEARDAY` (`N/A` in the table) or about the `BYWEEKNO` branch, which is
  where E lives.
- The ten `BYYEARDAY` cases were not re-checked against a long horizon
  truncated to a common endpoint ([rule 33](../README.md)); they do not need it,
  because the disagreement is dates present in one answer and absent from the
  other inside a window both filled.
