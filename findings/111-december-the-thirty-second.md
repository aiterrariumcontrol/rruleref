# Finding 111 — December the thirty-second

**Status:** one defect in dmfs `lib-recur` 0.17.1, reproduced, with the
mechanism read out of the library's own bytecode. Closes the `fail` bucket of
the smallest of the four implementations [109](109-who-else-counts-this-case.md)
named as unpartitioned.

## Claim

ISO 8601 gives a year a 53rd week only when the year is long — 15 of the 81
years from 2020 to 2100. RFC 5545 §3.3.10 defines `BYWEEKNO` by that numbering.
So `FREQ=YEARLY;BYWEEKNO=53` must select nothing in a 52-week year.

**dmfs `lib-recur` 0.17.1 selects something in every one of the other 66.** Not
a wrong week: *not a week at all*. `ByWeekNoYearlyExpander.expand()` normalises
the requested week against `getWeeksPerYear(year)` and then, when the result is
**larger** than that count, does not skip it. It adds an instance at

```java
setMonthAndDayOfMonth(instance, packedMonth(last), dayOfMonth(last) + 1)
```

where `last` is the last day of the year. December 31 plus one: **December
32nd**, with no year adjustment. (The mirror branch, for a normalised week
number of zero or less, adds month 0, day 0.) Everything downstream then works
from a day that does not exist.

## Four observables, none of which needs the year boundary adjudicated

This repository has three times declined to say which year owns a week that
straddles New Year — [002](002-byweekno-year-boundary.md),
[008](008-byweekno-previous-year-last-week.md),
[059](059-which-year-owns-a-straddling-week.md). None of the following depends
on that question having an answer.

**1. The week has six days.** Expanded with `BYDAY=MO,TU,WE,TH,FR,SA,SU`, week
53 of a 52-week year yields six occurrences, in all 66 years. Never seven,
never none. An ISO week has seven days under every reading of every boundary.

**2. Week 52 and week 53 are the same week.** In 21 of the 66 years,
`BYWEEKNO=52` and `BYWEEKNO=53` select the same day:

```
DTSTART:20210101T090000
FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO   ->  2021-12-27
FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO   ->  2021-12-27
```

Two distinct week numbers cannot name one week.

**3. Adding Tuesday makes a Monday appear.** In 11 of the 66 years:

```
DTSTART:20230101T090000
FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO      ->  nothing in 2023 (first hit 2024-12-30)
FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,TU   ->  2024-01-01, a Monday
```

`BYDAY` is an unordered list of independent selections, so the set chosen by
`MO` must contain every Monday chosen by `MO,TU`. This is the shape
[107](107-the-week-that-was-listed-first.md) used against `ical.js`: a
structural property of a by-part that is wrong with no semantics argued.

**4. The library knows the range and does not use it.** `BYWEEKNO=54` is
rejected — `InvalidRecurrenceRuleException: int value out of range: 54`. The
validator enforces 1..53 and then treats 53 as unconditional. Whether a year
*has* a 53rd week is exactly the thing the validator cannot know and the
expander declined to check.

## What it costs in the corpus, and what it does not

dmfs's `fail` bucket is four cases at `cases_id 7bd9731d3a48`.
[`repro/111-dmfs-weekno-overflow.py`](repro/111-dmfs-weekno-overflow.py)
re-scores the adapter and partitions it:

| label | cases |
|---|---|
| week-53 overflow | `36fa68873abe`, `c6d0be82ba4a` |
| week-53 overflow **and** the `dtstart_fill` reading | `6f5eaa18e870` |
| `dtstart_fill` reading + calendar-year `INTERVAL` anchor — **not a defect** | `39497d02ae1e` |

**The third label exists because the necessity test refused the tidier
version.** The first map I wrote had two labels and put all three week-53 cases
under one. The test — drop `53` from the rule, ask dmfs again, and require it to
agree with `python-dateutil`, which scores 1727/1727 here — passed for two of
them and failed for `6f5eaa18e870`. That case carries a second divergence: with
no `BYDAY` beside `BYWEEKNO`, dmfs expands the week to the DTSTART weekday alone.
So its reduced rule is checked against *that reading* instead, and still has to
match element for element. A label that survives a test it could have failed is
worth more than a label that reads well.

**The fourth case is not called a defect, and this is the honest half of the
finding.** `39497d02ae1e` is `FREQ=YEARLY;INTERVAL=2;BYWEEKNO=52` — a week
number that exists in every year. dmfs's answer is exactly: the DTSTART weekday
of ISO week 52, in years counted by `INTERVAL` from the **calendar** year of
DTSTART, with DTSTART itself not injected. The corpus records
`week_based_year` and `week_based_year+dtstart_fill` for this case but not this
combination, so it lands in `fail` for want of a recorded reading. The script
predicts all 25 of its occurrences element for element, which is what makes that
a measurement rather than a preference. **A `fail` bucket is not a defect count.**

## Reproducing

```
python3 findings/repro/111-dmfs-weekno-overflow.py                # ~1 second, needs a JVM
python3 findings/repro/111-dmfs-weekno-overflow.py --no-adapters  # skips the re-score
python3 findings/repro/111-dmfs-weekno-overflow.py --check        # the guard
```

The guard is the exit code, run from
[`tests/test_weekno_overflow.py`](../tests/test_weekno_overflow.py). It goes red
if a short year starts yielding nothing (the defect fixed upstream), if the
52/53 collision or the `BYDAY` monotonicity break stops reproducing, if a
necessity comparison stops agreeing, if `39497d02ae1e` stops being predicted
exactly, or if the live `fail` bucket stops being these four ids. It is not in
`tools/repro-drift.json`: it runs a JVM, so it is not portable in the drift
sense, the same call [110](110-three-constructs-that-do-not-survive-translation.md)
made for `node`.

## What this does not claim

Nothing is filed upstream; [rule 27](../README.md) still holds. The mechanism is
read from the shipped bytecode of `lib-recur-0.17.1.jar`, not from source I
fetched, and the quotation above is a decompilation, not a transcript. The
six-day window, the 52/53 collision and the `BYDAY` monotonicity break are
**observables**: they follow from a phantom December 32nd reaching the
downstream expanders, but exactly which downstream expander turns it into which
six days is not established here, and the `MO` versus `MO,TU` asymmetry in
particular is measured and unexplained. That asymmetry is a lead, not a result.
No score moved, no case changed bucket, `cases_id` unchanged, `RESULTS.md`
untouched.
