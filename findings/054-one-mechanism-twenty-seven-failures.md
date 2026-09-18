# 054 — one mechanism, twenty-seven failures: Category C re-derived

*2026-09-18.*

## Why this was asked

[Finding 051](051-what-is-left-after-the-negative-limit-fix.md) sorted `ical4j`'s
114 residual failures into six categories and was explicit that three of them
were guesses:

> Categories C, E and F are assigned by rule **shape**, not by a verified cause.
> C is "looks like 037"; it has not been re-derived here.

Category C is 27 cases, every one of them `FREQ=WEEKLY` with `BYMONTH` and a
multi-day `BYDAY`. That is the shape of
[finding 037](037-a-limit-that-runs-before-the-thing-it-limits.md), which claims
`ical4j` applies the `BYMONTH` limit to a single period *seed* and then lets
`BYDAY` expand that seed across the whole week with no month check afterwards.
"Looks like 037" is not the same statement as "is 037". This finding closes the
gap, and it closes it further than intended: the mechanism turns out to account
for `ical4j`'s `WEEKLY` behaviour *entirely*, not just its failures.

## Method

037's mechanism, and nothing else, reimplemented in 40 lines of Python:
[`repro/054-predict-weekly-037.py`](repro/054-predict-weekly-037.py). The seed
is `DTSTART`'s date advanced by `INTERVAL` weeks; `BYMONTH` filters the seed;
`BYDAY` expands the survivor across the `WKST`-anchored week; `BYSETPOS` selects
from that expansion; dates before `DTSTART` are dropped last. There is no
occurrence-level month filter anywhere in it, because 037 says there is none in
the library.

**This mechanism was already implemented in this repository, and I should say so
plainly.** [Finding 022](022-weekly-bymonth-ordering.md) named these two
readings of §3.3.10 — `filter-instances` and `seed-limit` — before 037 attributed
the second one to `ical4j` as a defect, and
[`repro/022-seed-limit-reading.py`](repro/022-seed-limit-reading.py) implements
`seed-limit` directly. What is new here is not the reading. It is the scale: 022
ran it over a handful of hand-built probe cases, and its implementation asserts
`WKST=MO`. The predictor here is that same reading generalised to an arbitrary
`WKST`, run over the corpus.

It is not a recurrence engine. It handles six rule parts —
`FREQ`, `BYDAY`, `BYMONTH`, `INTERVAL`, `WKST`, `BYSETPOS` — and one frequency.
That vocabulary covers **362 of the corpus's 373 `FREQ=WEEKLY` cases**; the
other 11 carry `BYHOUR`/`BYMINUTE`/`BYSECOND`/`COUNT`/`UNTIL` and are out of
scope throughout. `ical4j` was run at JVM locale `en-GB`
([finding 036](036-a-score-that-depends-on-the-host-locale.md) is why the locale
is part of the measurement).

Raw data: [`data/054-category-c-rederived.json`](data/054-category-c-rederived.json).

## The result

| | count |
| --- | ---: |
| `FREQ=WEEKLY` cases in scope | 362 |
| predictor output **identical** to `ical4j` 4.3.0 | **362** |
| predictor output **identical** to `ical4j` 4.1.1 | **362** |
| `ical4j` 4.1.1 identical to 4.3.0 | 362 |
| predictor differs from the corpus's expected answer | 27 |
| `ical4j` differs from the corpus's expected answer | 27 |
| those two sets of 27 are the same cases | yes |

So the answer to the question 051 left open is stronger than "yes, C is 037".
A reimplementation of one mechanism reproduces `ical4j` **byte-for-byte on all
362 cases**, the 335 it gets right as well as the 27 it gets wrong, and the 27
it gets wrong are exactly Category C. The 27 failures are not 27 facts. They are
one mechanism, counted 27 times by a corpus that happens to generate that shape
27 times.

The same comparison is the negative control for the claim. If the predictor
merely reproduced the *correct* answer it would agree with the corpus and
disagree with `ical4j`; it does the opposite, on precisely the right cases.

It also says something 051 could not: **there is no second `WEEKLY` defect
hiding in this corpus.** Any residual not explained by 037 would have shown up
as a predictor/`ical4j` mismatch, and there are none.

### The predictor checked against a second implementation

Agreement between `ical4j` and a predictor I wrote today is worth less if the
predictor has a bug that happens to imitate the library. So it is also checked
against 022's independent implementation, written for a different purpose and
sharing no code with it.

022's version asserts `WKST=MO`, which leaves **314** of the 362 in-scope cases.
On all 314 the two implementations produce the same dates, and both produce the
same dates as `ical4j` 4.3.0. Two separately written implementations of the
seed-limit reading agree with each other and with the library everywhere they
can be compared. (022 emits dates without times; the comparison is on the date
part.)

The 48 cases carrying a non-`MO` `WKST` rest on the predictor alone.

## What the 27 actually look like

037 named two consequences and gave an example of each. Classifying all 27
against them — each case compared with the correct answer over a common
truncation endpoint, `min(max(ical4j), max(expect))`, per
[rule 33](../README.md) — gives an exhaustive split, but only after a third
consequence is added:

| consequence | cases |
| --- | ---: |
| 1. a date in a month `BYMONTH` excludes is emitted | 9 |
| 2. a valid in-month occurrence is dropped | 20 |
| 3. `BYSETPOS` selects a date the correct set does not contain | 1 |
| none of the three | **0** |

Counts are of cases, not dates, and a case can show more than one consequence.
Consequence 2 is the common one; consequence 1, the one that is outside any
reading of the word "limit", is a third of the block.

### The third consequence

One case fell outside 037's two named symptoms:

```
FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-2    DTSTART:20260601T090000
```

`ical4j` emits `20260629`, which the correct answer omits. June the 29th is a
Monday and it is in June, so neither consequence fits — and yet the predictor
reproduced the case exactly, which means the mechanism does explain it and my
classification was what fell short.

The week of Monday 29 June 2026 runs to Sunday 5 July. `BYDAY=MO,WE` selects
Mon the 29th and Wed 1 July; `BYMONTH=6` leaves a **one-element** set; and
`BYSETPOS=-2` has no second-from-last element to select. The correct answer for
that week is nothing. `ical4j` limits the seed, expands to two days, and applies
`BYSETPOS=-2` to the pair, which yields Monday the 29th.

So the third consequence is: **`BYSETPOS` at `WEEKLY` selects from a set that
still contains out-of-month dates.** It can therefore pick the wrong member, or
pick a member at all where the correct set is too small. A purpose-built probe
separates it from the other two:

```
DTSTART:20260701T090000   (Wednesday)

FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=7;BYSETPOS=2
  ical4j 4.1.1 / 4.3.0   20260701 20260708 20260715 20260722
  dateutil               20260708 20260715 20260722 20260729
  rrule.js               20260708 20260715 20260722 20260729
  libical                20260708 20260715 20260722 20260729
  dmfs                   20260708 20260715 20260722 20260729
```

The week 29 June – 5 July holds one July day, so `BYSETPOS=2` selects nothing
from it. `ical4j` selects `20260701` — an in-month date, a genuine `BYDAY`
occurrence, and still wrong, because the selection was made over a set that
included 29 June. Three independent lineages
([rule 24](../README.md): `dateutil` and `rrule.js` are one vote) agree against
it. Dropping the `BYSETPOS` from the same rule makes all five agree, which is
what isolates the interaction rather than the expansion.

## The other implementations on these 27 cases

| | failures of 27 |
| --- | ---: |
| `dateutil` (control) | 0 |
| `libical` master 4edd39a3 | 0 |
| `rust-rrule` | 0 |
| `dmfs` | 0 |
| `rrule.js` | 1 |
| `sabre/vobject` 4.6.1 | 23 |

Both non-zero rows need saying carefully, and neither is a new `WEEKLY` defect.

**sabre's 23 is already published.** [Finding 031](031-one-cluster-three-causes.md)
established from `RRuleIterator.php` that `nextWeekly()` references neither
`byMonth` nor `bySetPos` — the fields are absent from the code path, not
mishandled in it. These 23 corroborate that count on a set of cases chosen for
an unrelated reason; they are not evidence of anything 031 did not already say.

**`rrule.js`'s one is a different defect, in a library I had been treating as
one vote with `dateutil`.** It is the consequence-3 case, and `rrule.js` fails
it while `dateutil` — its upstream — passes, and while `rust-rrule` — its own
downstream port — also passes. [Finding 055](055-a-question-with-no-answer.md)
characterises it. Note for the instrument: rule 24 collapses `dateutil`,
`rrule.js` and `rust-rrule` into one lineage vote, and that is the right default,
but in this cell the three do not agree with each other. A lineage is a claim
about *provenance*, not a guarantee of identical behaviour.

## Caveats

- The predictor is scoped to one frequency and six rule parts. Agreement with
  `ical4j` across 362 cases is evidence that 037 describes the code path this
  corpus reaches at `WEEKLY`; it is silent about the 11 excluded cases and about
  any `WEEKLY` behaviour the corpus does not generate.
- Eight occurrences per case. Every count here is a lower bound in the sense of
  [finding 040](040-how-much-a-short-horizon-hides.md).
- The 27 is a count of **corpus cases**. It reflects how often this corpus
  generates `FREQ=WEEKLY` with `BYMONTH` and a multi-day `BYDAY`, not how often
  that combination occurs in real calendars.
- 051's Categories **E** (16 `BYWEEKNO`) and **F** (16 assorted) remain shape
  assignments. E was subsequently accounted for by
  [finding 052](052-byweekno-is-one-lineage-deep.md) as finding 024's
  `dtstart_fill` split rather than a defect; F has had no account at all.
