# 050 — one cell of the table, four ways to get it wrong

*2026-09-17.*

## Why this was asked

[Finding 049](049-a-negative-day-that-only-counts-when-it-expands.md) found that
`ical4j` resolves a negative `BYMONTHDAY` correctly when the rule part **expands**
and compares it raw when the same rule part **limits**. Writing that up exposed a
gap in the instrument rather than in the library: of the 1721 scored cases, 164
use a sub-daily `FREQ`, only 6 of those carry a `BYMONTHDAY` or `BYYEARDAY` part
at all, and **not one carries a negative value**. Every negative-`BYYEARDAY` case
in the corpus is `FREQ=YEARLY` — the expansion cell, the half that works.

So the question was not "does `ical4j` get this wrong" but "who else does, and
has anyone been looking?"

## The cell

RFC 5545 §3.3.10 gives `BYYEARDAY` and `BYMONTHDAY` a role per frequency:

| | `SECONDLY` | `MINUTELY` | `HOURLY` | `DAILY` | `WEEKLY` | `MONTHLY` | `YEARLY` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BYYEARDAY` | Limit | Limit | Limit | N/A | N/A | N/A | Expand |
| `BYMONTHDAY` | Limit | Limit | Limit | Limit | N/A | Expand | Expand |

Negative values are legal throughout: `-1` is the last day of the month or year.
The **Limit** cells with a negative value are the subject here. Note that there
is no valid `FREQ=DAILY;BYYEARDAY=-1` rule — that pairing is N/A, so the
`BYYEARDAY` limit path is reachable *only* through `SECONDLY`, `MINUTELY` and
`HOURLY`. Getting that wrong is easy; finding 049's first draft did.

Seven rules cover every Limit cell of the two parts, at one sign:

| id | rule | `DTSTART` |
| --- | --- | --- |
| `18a92a27f558` | `FREQ=DAILY;BYMONTHDAY=-1` | `20260331T090000` |
| `62c703f07862` | `FREQ=HOURLY;BYMONTHDAY=-1` | `20260331T090000` |
| `cc1dcffc4bbb` | `FREQ=MINUTELY;BYMONTHDAY=-1` | `20260331T090000` |
| `c76d3879a009` | `FREQ=SECONDLY;BYMONTHDAY=-1` | `20260331T090000` |
| `801c98adc80a` | `FREQ=HOURLY;BYYEARDAY=-1` | `20261231T090000` |
| `3ada1d7ed4be` | `FREQ=MINUTELY;BYYEARDAY=-1` | `20261231T090000` |
| `3fcd47799486` | `FREQ=SECONDLY;BYYEARDAY=-1` | `20261231T090000` |

All seven are valid under `src/validity.py`, all seven have a synchronized
`DTSTART`, and all seven are corroborated in the sense the corpus uses — the
brute-force expander in `src/naive.py` and `python-dateutil` agree on all eight
recorded occurrences of each, independently.

## Result

Eight implementations, first eight occurrences, `en`-`GB` JVM locale for the two
Java rows:

| implementation | lineage | passes | notes |
| --- | --- | ---: | --- |
| `python-dateutil` 2.9.0.post0 | corroborating expander | 7 / 7 | |
| `rrule.js` 2.8.1 | port of dateutil | 7 / 7 | |
| `rrule-go` 1.8.2 | port of dateutil | 7 / 7 | |
| `rust-rrule` 0.14.0 | port of dateutil | 7 / 7 | |
| `libical` master `4edd39a3` | independent (C, 2000) | 7 / 7 | master `48d52b4b` also 7 / 7 |
| `ical4j` 4.1.1 | independent (Java, 2004) | **0 / 7** | returns nothing |
| `ical4j` 4.3.0 | independent (Java, 2004) | **4 / 7** | the three `BYYEARDAY` cells still return nothing |
| `dmfs lib-recur` 0.17.1 | independent (Java, 2013) | **4 / 7** | the three `BYYEARDAY` cells throw |
| `sabre/vobject` 4.6.1 | independent (PHP, 2011) | **2 / 7** | drops the constraint; stalls |
| `DateTime::Event::ICal` 0.13 | independent (Perl, 2003) | **3 / 7** | steps at the wrong granularity |

Every case, its corroborated expectation and every subject's raw reply are in
[`data/050-limit-cell-negative-day.json`](data/050-limit-cell-negative-day.json).

**Counting lineages rather than libraries** — the four dateutil-family rows are
one vote, per this repository's standing rule — two independent lineages get
this cell right and four get it wrong. The four dateutil descendants agreeing
says nothing beyond "the port did not drift"; `libical` is the only independent
corroboration that the cell is implementable.

## Four different ways

The failures are not one bug seen four times. Each lineage fails its own way.

**`ical4j` — silence.** The limit filter compares the rule's raw value against a
calendar field that is never negative, so it rejects every date it is shown and
the recurrence set is empty. 4.3.0 added a `getDayOfMonthFromEnd` disjunct to
`ByMonthDayRule`, which repairs all four `BYMONTHDAY` cells including the three
sub-daily ones; `ByYearDayRule` still has the original shape. Full account in
[finding 049](049-a-negative-day-that-only-counts-when-it-expands.md).

**`dmfs lib-recur` — a declared give-up.** All three `BYYEARDAY` cells raise
`IllegalArgumentException: too many empty recurrence sets`. This is the same
root cause reached by a library that notices: the filter matches nothing, the
iterator keeps producing empty periods, and a guard fires. It is the most
honest of the four failures — it says it failed — but the answer is still not
the recurrence set.

**`sabre/vobject` — the constraint vanishes.** For `FREQ=DAILY;BYMONTHDAY=-1` it
returns 31 March, then **1 April**, then 2 April: the negative day is dropped
and the rule degenerates to plain `FREQ=DAILY`. Worse, for the `MINUTELY` and
`SECONDLY` cells it returns the same instant eight times over
(`20260331T090000` repeated), which is not a recurrence set at all — a caller
iterating it sees time stop.

**`DateTime::Event::ICal` — the wrong granularity.** For
`FREQ=DAILY;BYMONTHDAY=-1` it returns 2026-03-31 and then **2027-03-31**: not
the next month-end but the next *year's*. For `FREQ=HOURLY;BYYEARDAY=-1` it
returns 2026-12-31 09:00 then 2027-12-31 09:00, skipping the remaining fourteen
hours of 31 December. It treats the limiting rule part as though it set the
frequency, so the limit silently promotes the period.

Three of the four produce a plausible-looking non-empty list. Only `dmfs` raises
anything. A caller checking "did I get dates back?" is told yes by
`sabre/vobject` and by `DateTime::Event::ICal`, and told yes by `ical4j` for
`BYMONTHDAY` on 4.3.0 while `BYYEARDAY` stays empty.

## Prior art, per claim

Searched per claim rather than per finding, because the hits cover different
parts of it.

**`ical4j`'s negative offsets — covered, and the fix is narrower than its own
description.** [ical4j#241](https://github.com/ical4j/ical4j/issues/241) reports
that `Recur.getNextDate()` throws `ArrayIndexOutOfBoundsException` for legal
negative offsets in `BYYEARDAY`, `BYMONTHDAY` and `BYWEEKNO`, and
[ical4j#243](https://github.com/ical4j/ical4j/pull/243) is the PR that fixed it:
*"The biggest fix is for negative offsets. These now work properly."* That is the
change carrying `getDayOfMonthFromEnd` into 4.3.0.

Two things are left over. The issue is about a **different API** — `getNextDate()`
rather than iterating the recurrence set — and about a different symptom, an
exception rather than an empty list; my probes call the iteration path and get
silence. And the PR's claim is broader than what shipped: in 4.3.0's own sources,
`ByYearDayRule`'s limit filter is still

```java
if (yearDayList.contains(getDayOfYear(date))) {
```

with no from-end disjunct, which is why the three `BYYEARDAY` cells above still
return nothing in the current release. I found no issue reporting the limit path
specifically. This is an instance of the standing caution that a library's answer
can depend on which of its own documented APIs you call.

**`dmfs`'s exception — the symptom is well known, the cause here is not.**
[dmfs/lib-recur#108](https://github.com/dmfs/lib-recur/issues/108),
[#121](https://github.com/dmfs/lib-recur/issues/121),
[#137](https://github.com/dmfs/lib-recur/issues/137) and
[#138](https://github.com/dmfs/lib-recur/issues/138) all report
`too many empty recurrence sets`, and #137/#138 are open and ask the right general
question — whether an iterator that can never yield should throw or simply be
empty. But every one of them reaches it through `BySetPosFilter` with a
`BYSETPOS` rule. My three cases contain no `BYSETPOS`; they reach the same guard
through the `BYYEARDAY` limit. The generic behaviour is reported; this route to
it is not.

**`sabre/vobject` and `DateTime::Event::ICal` — nothing found.** No issue matched
for either on negative `BYMONTHDAY`/`BYYEARDAY` in a limiting role. Absence of a
search hit is weak evidence, and for `DateTime::Event::ICal` it is weaker still:
its tracker is unreachable, as recorded in
[finding 045](045-sub-daily-expansion-is-confined-to-one-larger-unit.md).

## What this says about the corpus

The systematic generator in [`src/enumerate_cells.py`](../src/enumerate_cells.py)
guarantees at least one case per permitted cell of the §3.3.10 table, and
[`tests/test_coverage.py`](../tests/test_coverage.py) enforces that guarantee on
every build. It held. It was simply being read as more than it says: the
generator drew each cell's value from a single all-positive table, so "57 of 57
cells covered" meant every cell had been **visited**, never that both signs had
been tried. **Cell coverage is not value coverage.** A coverage model is a
statement about the axes it names and is silent about every axis it does not,
and the sign of a day number was such an axis — running the length of the two
rule parts where the spec explicitly defines a negative meaning.

That is the general lesson, and it is the one worth keeping: this repository's
whole argument is that a corpus built to a printed coverage model beats a corpus
grown from seeds. That argument survives — but a coverage model earns only the
coverage it states, and mine stated one dimension of a cell that has two.

## Status of the remedy

The generator change is written and verified but **not landed**, and the reason
is worth stating plainly rather than leaving as a silence. Adding the negative
variants makes the rebuild produce exactly 7 new corroborated cases, with every
existing case byte-identical and no cell or grammar branch lost — the rule 12
check passes cleanly. But those 7 join the scored set, moving it from 1721 to
1728, and that restates the denominator under all eleven rows of
[`conformance/RESULTS.md`](../conformance/RESULTS.md). Rescoring eleven rows is
dominated by `DateTime::Event::ICal`, whose adapter spends a full 20-second alarm
on each of 291 `BYSETPOS` cases — roughly 97 minutes for that row alone. Landing
the cases without rescoring would leave published numbers at two different
denominators, which is a worse state than either end.

So the measurement above is made directly against the adapters, which needs no
change to the scored corpus and is no weaker as evidence: the seven cases are
corroborated by the same two independent expanders as every other case here. The prepared
patch is [`repro/050-negative-value-cells.patch`](repro/050-negative-value-cells.patch);
it applies to `src/enumerate_cells.py` alone.

## Caveats

- Eight occurrences per case, which is this corpus's recording depth. Every
  count here is a lower bound in the sense of
  [finding 040](040-how-much-a-short-horizon-hides.md): a library that agrees on
  eight occurrences may still diverge later.
- `libical` 3.0.20 (the Debian row in `RESULTS.md`) was **not** run here; it
  needs a separately compiled binary. Both master builds were.
- The two Java rows were run with `-Duser.language=en -Duser.country=GB`.
  [Finding 036](036-a-score-that-depends-on-the-host-locale.md) is why that has
  to be said.
- One sign, one value. `-1` is the only negative tested; `-2` and `-31` are not,
  and a library that special-cases `-1` would pass this set.
- `sabre/vobject`'s repeated-instant behaviour was read off eight occurrences at
  the adapter's own limit. It is a stall within that window; I have not shown it
  never advances.
- The seven cases exercise the Limit role of two rule parts. `BYDAY`'s offset
  form is excluded on purpose: §3.3.10 forbids the offset under `DAILY` and
  `WEEKLY`, and under the sub-daily frequencies it is a separate question.
