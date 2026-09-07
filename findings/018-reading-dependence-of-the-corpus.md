# 018 — 54 corroborated cases are committed to a contested reading, unmarked

**Status:** Open. A defect in *my* corpus's labelling, not in any
implementation. It also retracts the closing section of
[finding 017](017-libical-third-lineage.md).

**Date:** 2026-09-07. **Affects:** `corpus/corroborated.json`,
`corpus/disputed.json`, and the closing claim of finding 017.

## The confusion

`corpus/disputed.json` collects the cases where `src/naive.py` and the pinned
`python-dateutil` return different occurrence lists. I have been reading that
file as "the cases where the right answer is contested". It is not. It is the
cases where *two particular implementations disagree*, which is a different
predicate, and the difference is not academic: two implementations can agree
with each other and still both be making the choice
[finding 004](004-bysetpos-first-period-truncation.md) calls disputed.

## Measuring it

`src/reading_dependence.py` expands every corroborated case carrying
`BYSETPOS` under both readings of the first period — BYSETPOS selecting from
the whole period with pre-DTSTART instances dropped afterwards, and the period
cut at DTSTART before BYSETPOS selects — and reports the cases whose first
`len(expect)` occurrences differ.

```
corroborated cases      : 3813
carrying BYSETPOS       : 677
reading-dependent       :  54
corpus records          : {'whole_period': 54}
by FREQ                 : {'FREQ=YEARLY': 32, 'FREQ=MONTHLY': 16,
                           'FREQ=DAILY': 2, 'FREQ=HOURLY': 2,
                           'FREQ=MINUTELY': 2}
```

Full list: [`data/018-reading-dependence.json`](data/018-reading-dependence.json).

**54 corroborated cases would change answer under the other reading, and every
one of them silently records the whole-period reading as corroborated fact.**
A reader taking `corroborated.json` as ground truth inherits a position on
finding 004 without being told.

The smallest instance needs no `BYDAY` at all:

```
DTSTART:20260302T090000
RRULE:FREQ=DAILY;BYHOUR=9,8;BYSETPOS=1
  whole period      : 20260303T080000, ...   <- what the corpus records
  first period cut  : 20260302T090000, ...
```

The first day's set is `{08:00, 09:00}`; position 1 is 08:00, which is before
DTSTART and is dropped, so the whole first day is lost. Cut the day at DTSTART
and position 1 is DTSTART itself. This is finding 004's question exactly, one
`FREQ` over, and `dateutil` agrees with the expander here, so it never reached
`disputed.json`.

## Why the gap has the shape it has

Not one of the 54 is `FREQ=WEEKLY`, although the corpus holds 132 corroborated
`WEEKLY`+`BYSETPOS` cases. That is not because `WEEKLY` is exempt: it is
because `WEEKLY` is where `dateutil` takes the *other* reading, so the
`WEEKLY` instances of this question all landed in `disputed.json` (10 of its 26
cases are `WEEKLY`+`BYSETPOS`). The disputed set is complete with respect to
its own predicate and under-inclusive with respect to the question, and the
boundary between the two follows a quirk of one implementation rather than
anything in RFC 5545.

## What this retracts in finding 017

Finding 017 ended with eight cases that survive in libical master, all
`FREQ=WEEKLY`+`BYDAY`+`BYMONTH`+`BYSETPOS`, and dismissed them:

> That is finding 004's disputed reading, so it is not a defect claim.

That was reached with a probe that dropped `BYMONTH` to "narrow the shape".
Dropping `BYMONTH` is what created the reading-dependence:

```
FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1  DTSTART:20260705T090000 (Sun)
  whole period     : 20260705, 20260706, ...
  first period cut : 20260705, 20260706, ...     <- readings AGREE

FREQ=WEEKLY;BYDAY=MO,SU,TU;BYSETPOS=1            DTSTART:20260705T090000
  whole period     : 20260706, ...
  first period cut : 20260705, ...               <- readings DIFFER
```

With `BYMONTH=7` present, the pre-DTSTART candidates in the straddling week
(Mon 2026-06-29 and Tue 2026-06-30) are limited away before `BYSETPOS` ever
sees them, so both readings select Sunday 2026-07-05. The eight cases are
reading-independent, they are not finding 004, and the dismissal had no basis.
`src/reading_dependence.py` finds no `WEEKLY` case among the 54, which is the
same fact stated corpus-wide.

What libical is actually doing there is
[finding 019](019-libical-weekly-bymonth-bysetpos.md).

## What I have not done

I have **not** added a `reading_dependent` flag to the corpus schema. That is
the obvious fix and it is a schema change; it wants its own pass with the
full rebuild comparison, and the derivation is reproducible from the published
corpus in the meantime. The 54 cases are not withdrawn: the whole-period
reading is the one I argue for in finding 004 and the expected values are what
that reading gives. What was wrong was presenting them as uncontested.

## The general lesson

Agreement between implementations is evidence about implementations. This
corpus's whole premise is that it is evidence about the specification, and for
677 cases it is only that if you already know the two witnesses cannot both be
wrong in the same direction. Finding 003 established that `dateutil`'s lineage
dominates the field; agreement inside a lineage is close to no evidence at
all. Reading-dependence is checkable without a second implementation, and
should be checked wherever a spec question has a mechanical alternative
reading.
