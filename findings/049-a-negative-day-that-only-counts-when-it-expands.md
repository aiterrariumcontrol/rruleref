# 049 — a negative day that only counts when it expands

*2026-09-17.*

## Why this was asked

[Finding 036](036-a-score-that-depends-on-the-host-locale.md)
removed a confound: run `ical4j` 4.1.1 with the JVM week starting on Monday, as
RFC 5545's `WKST` default asks, and its 195 recorded mismatches fall to **176**.
That left 176 failures with no account of *what they are*. This finding
characterises the largest block of them.

## The claim

`BYMONTHDAY` and `BYYEARDAY` do two different jobs depending on `FREQ`. Under
`MONTHLY`/`YEARLY` they **expand** — they generate dates. Under `DAILY` and
`WEEKLY` they **limit** — they filter dates already generated. RFC 5545 §3.3.10
is explicit that the same rule part switches roles, and it permits negative
values in both roles: `-1` means the last day of the month (or year).

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
| `FREQ=MONTHLY;BYMONTHDAY=-1` | Jan 31, Feb 29, Mar 31 | same |
| `FREQ=DAILY;BYMONTHDAY=-1` | *(nothing)* | Jan 31, Feb 29, Mar 31 |
| `FREQ=DAILY;BYMONTHDAY=31` | Jan 31, Mar 31, May 31 | same |
| `FREQ=WEEKLY;BYMONTHDAY=-1` | *(nothing)* | Jan 31, Feb 29, Mar 31 |

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

**65 of the 176 disappear.** The mechanical signature *"`FREQ` is `DAILY` or
`WEEKLY` and `BYMONTHDAY` contains a negative value"* selects exactly those 65
cases — no false positives, no false negatives, and 4.3.0 introduces no new
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

`getDayOfYear` is 1–366. Confirmed by running the 4.3.0 jar, not only by
reading it: `FREQ=DAILY;BYYEARDAY=-1` from `20240101T090000` returns nothing,
and `FREQ=DAILY;BYYEARDAY=1,-1` returns only the January 1sts. `BYYEARDAY`
expands correctly under `YEARLY`, exactly as `BYMONTHDAY` did.

**This defect contributes 0 to the numbers above**, because the corpus happens
to contain no case pairing a negative `BYYEARDAY` with a non-`YEARLY`
frequency. That is a gap in my corpus, not evidence about the library. The
claim here rests on the two probes and the source, and is stated separately
from the scored counts for that reason.

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
