# 103 — The year the iterator gave up, and the year it was willing to wait for

**Status:** Measured. **Date:** 2026-09-26.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. **No score moved**; `RESULTS.md`
is untouched; 074's residual is unchanged at 3. This defect is **outside the
corpus**, and saying so is part of the finding.

## The claim

`ical.js` 2.2.1 abandons a `FREQ=YEARLY` expansion after **28 consecutive
iterations that produce no occurrence**, and reports the series as complete. No
error is raised. The same rule, evaluated from a `DTSTART` on the other side of
the same empty run, is answered correctly — because the search for the *first*
occurrence is not bounded at all.

```
FREQ=YEARLY;BYMONTH=2;BYDAY=5MO   from 2026-01-01
  ical.js    20440229 20720229
  reference  20440229 20720229 21120229 21400229 21680229 21960229 ...
```

A fifth Monday in February requires a leap year whose 1 February is a Monday.
Those years are 2044, 2072, **2112**, 2140, 2168, 2196, 2208 — gaps of 28, **40**,
28, 28, 28, 12. `ical.js` returns the first two and stops.

`dateutil`, `rrule.js`, `lib-recur` (dmfs) and `ical4j` 4.1.1 all return the full
series. `sabre/vobject` also reaches 2112 and beyond; it differs only by
prepending `DTSTART`, which is its own separate reading and not this defect.

## The mechanism, and it is two policies in one class

[`recur_iterator.js`](../js/node_modules/ical.js/lib/ical/recur_iterator.js) does
the same search twice, with different rules.

In `next()`, when `next_year()` returns 0 the iteration is retried, and:

```js
} else if (++invalid_count == 28) {
  // We've been through all 14 year variations and not found a recurrence. Stop.
  // (365-day and 366-day years × 7 starting days.)
  this.completed = true;
  return null;
}
```

The comment states its own premise, and the premise is false. There really are
only 14 (length, starting-weekday) year shapes — but **28 consecutive years do
not visit all 14.** The 28-year cycle that would make them do so is broken every
time the Gregorian calendar skips a leap year at a century boundary. Across 2100,
2200 and 2300 the gap between successive years of the same shape is **40**, not
28. The bound is short by twelve years, three times every four centuries.

The same class, in `init()`, searches for the first occurrence like this:

```js
const untilYear = this.rule.until ? this.rule.until.year : 20000;
while (this.last.year <= untilYear) {
  this.expand_year_days(this.last.year);
  if (this.days.length > 0) break;
  this.increment_year(this.rule.interval);
}
```

Nearly eighteen thousand years, against 28. The comment above it says `libical`
"will iterate until it finds a matching year", which is the behaviour it then
implements — once. So the iterator is willing to wait essentially forever for the
first occurrence and gives up after 28 tries on the second.

That asymmetry is what makes this a defect rather than a documented limit, and it
is directly demonstrable: the identical rule from `DTSTART=20800101` must cross
the identical 31 empty iterations to reach 2112, and does.

## What the reproducer establishes

[`repro/103-icaljs-yearly-gives-up.py`](repro/103-icaljs-yearly-gives-up.py),
read-only by default against
[`data/103-icaljs-yearly-gives-up.json`](data/103-icaljs-yearly-gives-up.json).

**The predictor**, exact on every probe: `ical.js`'s answer equals the reference
answer cut before the first occurrence that is 28 or more non-matching iterations
past *the previous occurrence*. The gap from `DTSTART` to the first occurrence is
exempt.

| | |
|---|---|
| `D-5mo` | the case above |
| `D-feb29mon` | `BYMONTH=2;BYMONTHDAY=29;BYDAY=MO` — different text, same conjunction, same stop. The BYDAY ordinal is not the mechanism |
| `D-count` | `COUNT=6` returns **2**. A caller who asked for a fixed count gets a short series and no error |
| `D-interval3` | `INTERVAL=3` keeps only 2044. **A larger interval truncates earlier in calendar terms** — the next reachable year is 96 years out, 32 iterations |
| `A-dtstart` | the asymmetry: the same rule from 2080 is correct |
| `C-interval2` | `INTERVAL=2` crosses the same 40 calendar years correctly, in 19 iterations. **The bound counts iterations, not years** |
| `C-leaponly` | `BYYEARDAY=366` — leap years alone gap by at most 8. (Deliberately not `BYMONTHDAY=29`, which [101](101-an-impossible-day-that-was-not-refused.md) already shows `ical.js` mishandles; a control has to be clean of other defects to control anything.) |
| `C-monthly` | the same conjunction at `FREQ=MONTHLY` is **correct**. Its own bound is 336, and `BYMONTH` is a contracting rule checked outside `next_month()`, so `invalid_count` is reset every month. `FREQ=YEARLY` is load-bearing |

Three of these controls failed on the first run, and each failure was
informative rather than cosmetic: `A-dtstart` is what exposed the unbounded
`init()` path, `C-monthly` showed the predictor had been applied to a frequency
whose bound is different, and `C-leaponly` replaced a control that was
contaminated by finding 101. **The first draft of the predictor was wrong about
where the bound applies, and the controls are what said so.**

## Scope, stated against the finding

**No corpus case can reach the bound.** Measured from each case's own stored
reference expansion: of the 373 `FREQ=YEARLY` cases, the longest run of
non-matching iterations any of them demands is **16**
(`54a5c8a07907`, `INTERVAL=3`, a 51-year gap). The bound is 28.

So this finding subtracts nothing from [074](074-what-reproducing-an-output-attributes.md)'s
residual, which stays at the 3 `BYSETPOS`+`BYDAY` cases
[102](102-the-residual-had-no-producer.md) published. It was found by reading
`next()` after finding 101 sent me into that file, not by measuring anything —
and the corpus scan here exists to say *how far outside* the corpus it is, not to
claim credit inside it.

**Rule 110: a defect the corpus cannot reach is still a defect, and the honest
way to publish it is to measure the distance.** A finding that quietly omits its
scope invites the reader to assume corpus coverage. Reporting "0 of 373, longest
run 16 against a bound of 28" costs one paragraph and tells a maintainer exactly
what a regression test would have to look like.

## What would fix it

Raising 28 to 40 would close the observed case and leave the same class of bug
for any rule whose satisfying years gap further — the bound would still be a
guess about the calendar. The premise the comment appeals to is sound at **400**
years, the full Gregorian cycle, which is also the point past which no yearly
rule can have a first occurrence without having a second. The narrower fix is to
use the bound `init()` already uses, since both are answering the same question.
