# 049 — a negative day that only counts when it expands

*2026-09-17.*

## Why this was asked

[Finding 036](036-a-score-that-depends-on-the-host-locale.md)
removed a confound: run `ical4j` 4.1.1 with the JVM week starting on Monday, as
RFC 5545's `WKST` default asks, and its 195 recorded mismatches fall to **176**.
That left 176 failures with no account of *what they are*. This finding
characterises the largest block of them.

## The claim

`BYMONTHDAY` and `BYYEARDAY` do two different jobs depending on `FREQ`. The
table in RFC 5545 §3.3.10 assigns each pairing a role, and forbids some
outright:

| | `SECONDLY` | `MINUTELY` | `HOURLY` | `DAILY` | `WEEKLY` | `MONTHLY` | `YEARLY` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BYYEARDAY` | Limit | Limit | Limit | N/A | N/A | N/A | Expand |
| `BYMONTHDAY` | Limit | Limit | Limit | Limit | N/A | Expand | Expand |

**Expand** means the rule part generates dates; **Limit** means it filters
dates already generated; **N/A** means the combination "MUST NOT be used".
Negative values are permitted in both live roles: `-1` means the last day of
the month (or year).

`ical4j` 4.1.1 resolves negative values correctly **only in the expansion
path**. The limit path compares the raw rule value against a calendar field
that is never negative:

```java
// net/fortuna/ical4j/transform/recurrence/ByMonthDayRule.java (4.1.1)
private class LimitFilter implements Function<T, Optional<T>> {
    public Optional<T> apply(T date) {
        if (monthDayList.contains(getDayOfMonth(date))) {   // 1..31, never negative
            return Optional.of(date);
        }
        return Optional.empty();
    }
}
```

`getDayOfMonth` returns 1–31. A `monthDayList` entry of `-1` cannot equal any
of them, so the filter rejects every date it is shown. The sibling
`ExpansionFilter`, a few lines below in the same class, does the arithmetic
properly (`yearMonth.lengthOfMonth() + 1 + monthDay`).

The consequence is not an error. It is silence:

| rule (`DTSTART=20240131T090000`) | `ical4j` 4.1.1 | control (`dateutil`) |
| --- | --- | --- |
| `FREQ=MONTHLY;BYMONTHDAY=-1` (expand) | Jan 31, Feb 29, Mar 31 | same |
| `FREQ=DAILY;BYMONTHDAY=-1` (limit) | *(nothing)* | Jan 31, Feb 29, Mar 31 |
| `FREQ=DAILY;BYMONTHDAY=31` (limit) | Jan 31, Mar 31, May 31 | same |

The same rule part, the same library, the same value: correct when it expands,
empty when it limits. Positive values are unaffected, which is why this hid.

When the list mixes signs, the failure is quieter still — the positive members
survive and the negative ones are dropped without a trace:

| rule (`DTSTART=20240101T090000`) | `ical4j` 4.1.1 | control |
| --- | --- | --- |
| `FREQ=DAILY;BYMONTHDAY=1,-1` | Jan 1, Feb 1, Mar 1, Apr 1 | Jan 1, **Jan 31**, Feb 1, **Feb 29** |

## Measurement

Over the 1721 scored cases in [`conformance/cases.ndjson`](../conformance/cases.ndjson),
JVM locale pinned to `en`-`GB`:

| | pass | fail | `fail_other_reading` |
| --- | ---: | ---: | ---: |
| `ical4j` 4.1.1 | 1487 | **176** | 58 |
| `ical4j` 4.3.0 | 1552 | **111** | 58 |

**65 of the 176 disappear.** The mechanical signature *"`FREQ` is `DAILY` and
`BYMONTHDAY` contains a negative value"* selects exactly those 65 cases — no false positives, no false negatives, and 4.3.0 introduces no new
failures. Every one of the 65 is `FREQ=DAILY`; after the fix, `ical4j` has **no
remaining `FREQ=DAILY` failure in this corpus at all**. Ids and per-case
occurrence lists are in
[`data/049-ical4j-negative-limit.json`](data/049-ical4j-negative-limit.json).

The fix is visible in the 4.3.0 source as one added disjunct:

```java
// 4.3.0
if (monthDayList.contains(getDayOfMonth(date))
        || monthDayList.contains(getDayOfMonthFromEnd(date))) {
```

## The half that is not fixed

`ByYearDayRule` has the identical shape and **4.3.0 does not fix it**:

```java
// net/fortuna/ical4j/transform/recurrence/ByYearDayRule.java (4.3.0, unchanged from 4.1.1)
if (yearDayList.contains(getDayOfYear(date))) {
```

`getDayOfYear` returns 1–366, so a `yearDayList` entry of `-1` matches nothing,
exactly as `getDayOfMonth` did before 4.3.0 gained its `getDayOfMonthFromEnd`
disjunct.

Reaching that path takes some care. `BYYEARDAY` limits **only** under the three
sub-daily frequencies — under `DAILY`, `WEEKLY` and `MONTHLY` the combination is
N/A, so there is no such thing as a valid `FREQ=DAILY;BYYEARDAY=-1` rule to test
it with. The probes therefore use `HOURLY` and `MINUTELY`, both of which the
table marks Limit, with `DTSTART=20241230T090000` and the control being
`dateutil`:

| rule | `ical4j` 4.1.1 | `ical4j` 4.3.0 | control |
| --- | --- | --- | --- |
| `FREQ=HOURLY;BYYEARDAY=-1` | *(nothing)* | *(nothing)* | Dec 31 00:00, 01:00, 02:00 … |
| `FREQ=MINUTELY;BYYEARDAY=-1` | *(nothing)* | *(nothing)* | Dec 31 00:00, 00:01, 00:02 … |
| `FREQ=HOURLY;BYYEARDAY=366` | Dec 31 00:00, 01:00 … | same | same |

The positive row is the control on the defect: same rule part, same frequency,
same limiting role, and it works. Only the sign fails, and it fails in the
current release.

Running the same three frequencies against `BYMONTHDAY` shows the 4.3.0 fix is
wider than the corpus could see. `FREQ=HOURLY;BYMONTHDAY=-1` from
`20240130T090000` returns nothing under 4.1.1 and the correct Jan 31 hours under
4.3.0: the added disjunct repairs the sub-daily Limit cells as well as the
`DAILY` one, even though every one of the 65 scored cases it fixes is `DAILY`.

## Why the corpus could not have caught this

None of the above is scored, and the reason is a defect in my own instrument
rather than a shortage of cases. Of the 1721 cases in `cases.ndjson`, 164 use a
sub-daily `FREQ`, but only **6** of those carry a `BYMONTHDAY` or `BYYEARDAY`
part at all, and **not one carries a negative value**. All 22 negative-`BYYEARDAY`
cases in the corpus are `FREQ=YEARLY` — the expansion cell, the half that works.

The systematic generator in [`src/enumerate_cells.py`](../src/enumerate_cells.py)
guarantees a case for every permitted cell of the §3.3.10 table, and
[`tests/test_coverage.py`](../tests/test_coverage.py) enforces it. That
guarantee was being read as more than it says. The generator drew each cell's
value from a single all-positive table, so "every cell is covered" meant every
cell had been *visited*, never that both signs had been tried — and this defect
is visible only in one sign of one role. **Cell coverage is not value
coverage.** A coverage model states what it measures along the axes it names,
and is silent about every axis it does not; the sign of a day number was such an
axis.

The remedy is small and has been built and verified but **not yet landed**: the
generator emits a second case per cell for the rule parts that accept a negative
value, filed under the same cell because it is not a new cell of the table but
the other sign of an existing one. A full rebuild adds exactly 7 corroborated
cases and changes nothing else — every existing case is byte-identical and no
cell or grammar branch is lost. It is held back because it moves the scored set
from 1721 to 1728, which restates the denominator under all eleven rows of
[`conformance/RESULTS.md`](../conformance/RESULTS.md), and rescoring every row is
a job dominated by the Perl adapter's per-case alarm. [Finding
050](050-one-cell-of-the-table-four-ways-to-get-it-wrong.md) measures the same
seven cases against all eight implementations directly, which needs no change to
the scored corpus.

## What is left

The 111 remaining 4.3.0 failures are not one thing. By rule shape: 27 involve
`BYWEEKNO`, 21 `BYSETPOS`, 13 `YEARLY`+`BYYEARDAY`, 13 `YEARLY`+`BYMONTHDAY`
expansion, and the rest are `BYDAY`/`BYMONTH` combinations. 63 are `YEARLY`, 27
`WEEKLY`, 21 `MONTHLY`, none `DAILY`. Uncharacterised.

## Caveats

- Every count here is a lower bound over a truncated window, as everywhere in
  [`conformance/RESULTS.md`](../conformance/RESULTS.md).
- 4.3.0 was scored with the 4.1.1-era adapter class against the 4.3.0 jar; the
  adapter does not use any API that changed between them, and 4.3.0 produced no
  failure that 4.1.1 did not.
- `ByDayRule`'s limit path rejects offset day values such as `-1FR` under
  `DAILY` the same way. That is **not** counted as a defect here: §3.3.10 says
  the offset "MUST NOT be specified when the BYDAY rule part is used with
  FREQ=DAILY or FREQ=WEEKLY".
- **Corrected after first publication, same day.** The first version of this
  finding described `BYMONTHDAY` as limiting under "`DAILY` and `WEEKLY`" and
  probed the `BYYEARDAY` twin with `FREQ=DAILY;BYYEARDAY=-1`. §3.3.10 marks both
  of those pairings N/A, so two of the published probe rules were not legal
  rules and proved nothing; `src/validity.py` rejects them, and I had not asked
  it. The defect claims survive on legal probes — the `BYYEARDAY` one is now
  demonstrated against the current release rather than only read out of the
  source — and the scored 65 is unchanged, because the corpus contains no
  `WEEKLY` case with a negative `BYMONTHDAY` for the discarded disjunct to have
  selected. What did change is the account of *why* the corpus was silent: not
  an accidental gap, but an all-positive value table behind a cell-coverage
  guarantee.
