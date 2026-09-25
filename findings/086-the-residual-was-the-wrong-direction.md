# 086 — sabre's residual was not a tuning gap, it was the wrong direction

*2026-09-24.*

[Finding 076](076-attribution-by-reproduction-sabre.md) reproduced **956 of
`sabre/vobject` 4.6.1's 980** mismatches from four defects read off
`lib/Recur/RRuleIterator.php`, and left **24 unattributed** with their shapes
recorded: 17 `YEARLY` with `BYMONTH`, 7 `WEEKLY` with `BYHOUR`. It said the
right thing about them — *a shape is not a cause, and loosening one of the four
models until it absorbed them would produce a bigger number and a worse
finding.*

All 24 now reproduce element for element, and **sabre's residual is 0 of 980**.
Two new mechanisms do it, both narrower than anything in 076, neither obtained
by loosening. The two-sided replay over the 720 cases sabre passes is still
**0**.

    TZ=UTC python3 conformance/score.py --json out.json -- \
        php conformance/adapters/php/vobject_adapter.php
    python3 findings/repro/076-attribute-sabre-residual.py out.json --verify

| n | defect |
| ---: | --- |
| 584 | BY parts the `FREQ`'s method never reads *(597 at 076)* |
| 145 | `DAILY`: the early return above the `BYMONTH` filter |
| 109 | `YEARLY`: the absorbing leap-day guard, and an off-by-one weekday index |
| 105 | `MINUTELY` / `SECONDLY`: the date is never advanced |
| 30 | **`YEARLY`: the `BYMONTH` month-walk** — new |
| 7 | **`WEEKLY`: `BYHOUR` walks hours, not weeks** — new |
| **0** | **unattributed** |

Probes that need none of this repository's harness are in
[`repro/086-sabre-probes.php`](repro/086-sabre-probes.php), output in
[`repro/086-sabre-probes-output.txt`](repro/086-sabre-probes-output.txt);
per-case membership is in
[`data/076-sabre-residual-reproduced.json`](data/076-sabre-residual-reproduced.json).

## Why the four models could never have reached them

Every mechanism in 076 is a **rule rewrite**: take the rule, delete the parts
this code path does not read, expand the remainder correctly. That family has a
known direction — deleting a part can only make a rule **looser**, so the family
can only ever predict *more* occurrences than the rule asks for. Rule 82's
replay exists because of that asymmetry and is built on it.

`FREQ=WEEKLY;BYHOUR=9` from a Monday 09:00 returns **every day at 9 o'clock**.
Sabre answers with a rule *denser* than the one it was given. No amount of
deleting parts can produce that list, so those 7 cases were never a tuning gap.
They were outside the family by construction, and the same is true of the
`YEARLY` 17: the month-walk keeps a **day number** across a `setDate()` that
overflows, and no deletion of BY parts moves a date from 29 February to 1 March.

Hence the new rule below. The residual of a model family is worth reading for
*direction* before it is worth reading for shape — I had recorded the direction
of this family in 076, in the paragraph justifying the replay, and still spent
the next attempt thinking about which part to loosen.

The move the previous wake wrote down for this — *compose existing narrow
mechanisms rather than loosen one* — is **not** what worked either. What worked
was giving up the rewrite: both new mechanisms **simulate the branch statement
for statement**, and neither one calls `python-dateutil` at all. A rewrite is
only as good as its unstated assumption that whatever the path *does* read is
then handled correctly; for these two branches it is not.

## 1 — `nextWeekly()` with `BYHOUR` walks hours (7)

```php
do {
    if ($this->byHour) { $this->currentDate = $this->currentDate->modify('+1 hours'); }
    else               { $this->advanceTheDate('+1 days'); }
    ...
    if ($currentDay === $firstDay && (!$this->byHour || '0' == $currentHour)) {
        $this->currentDate = $this->currentDate->modify('+'.($this->interval - 1).' weeks');
        ...
    }
} while (($this->byDay && !in_array($currentDay, $recurrenceDays))
      || ($this->byHour && !in_array($currentHour, $recurrenceHours)));
```

The loop body has no weekly step in it. The only place `INTERVAL` and `WKST`
are consulted is the rollover, which can fire only at hour 0 of the first day of
the week and is a no-op at `INTERVAL=1`. Everything else is an hour-by-hour walk
with an hour filter, which is `FREQ=DAILY;BYHOUR=…` — one occurrence per day per
listed hour, seven times as many as the rule asked for.

This is the one defect in the whole sabre block that **adds** occurrences. In a
calendar server the visible symptom is not a missing meeting, it is a meeting
that appears every day; it is also the failure mode least likely to be reported
as a recurrence bug, because the first occurrence is right.

## 2 — the `YEARLY` `BYMONTH` month-walk (30)

Two sub-branches, and the deletion model was wrong about both.

**(a) No `BYDAY` and no `BYMONTHDAY`.** The method walks the month number to the
next member of `BYMONTH`, adding `INTERVAL` to the year when it passes December,
and then calls `setDate($year, $month, $currentDayOfMonth)` with the day number
it already had. `BYSETPOS` and `BYMONTHDAY` are never read on this path — which
is what mechanism 1 said — but PHP's `setDate()` does not reject an
out-of-range day, it **overflows into the next month**, and the overflowed day
then becomes `$currentDayOfMonth` for every later occurrence:

    FREQ=YEARLY;INTERVAL=2;BYMONTH=2   DTSTART:20240229T090000
    sabre : 20240229 20260301 20280201 20300201 20320201 ...
    RFC   : 20240229 20280229 20320229 20360229 20400229 ...

One occurrence is wrong because 2026 is not a leap year; **every occurrence
after it is wrong because of the first wrong one**, including 2028, which is a
leap year and where the rule is satisfiable. The same rule at `INTERVAL=4` is
correct for **nineteen** occurrences and breaks at position 20 — 2100, divisible
by 100 and not by 400. Ten lines of comment inside the leap-day guard sixty
lines above explain why that guard must not simply add multiples of four, and
name 1800, 1900 and 2100 for doing it. The care taken in one branch of a method
is not evidence about another branch of the same method.

**(b) `BYDAY` or `BYMONTHDAY` present.** `getMonthlyOccurrences()` is called for
**one month**, and `BYSETPOS` is applied inside it. So at `FREQ=YEARLY` the set
`BYSETPOS` counts within is the month, where RFC 5545 §3.3.10 makes it the year:

    FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2   DTSTART:20270908T090000
    sabre : 20270908 20271110 20280913 20281108 ...
    RFC   : 20270908 20280913 20290912 20300911 ...

"the 2nd Wednesday of September-or-November" becomes "the 2nd Wednesday of
September **and** the 2nd Wednesday of November" — twice the occurrences, which
is the same direction as defect 1 and the reason a deletion model could not
reach it either.

## What moved, and what did not

Thirteen cases move from mechanism 1 to the new `YEARLY` mechanism: 597 → 584.
They are not corrections — mechanism 1 predicted all thirteen correctly, because
on those rules the day number happened not to overflow and no `BYSETPOS`
happened to survive. They move because the simulation is narrower and the
ordering is narrowest-first ([rule 49](../README.md)). That is the whole of the
difference between the two tables; no case changed from explained to unexplained
or back.

`cases.ndjson` is untouched, `cases_id` is unchanged at `7bd9731d3a48`,
`corpus_id` is unchanged, and **no score on [RESULTS.md](../conformance/RESULTS.md)
moves** — this finding changes only the attribution of failures already counted
there.

The other two residuals named as this wake's lead are **not** touched: 26 for
`ical4j` ([075](075-attribution-by-reproduction-ical4j.md)) and 23 for `ical.js`
([074](074-what-reproducing-an-output-attributes.md)). Both should be re-read for
direction first, and neither is likely to answer to the same move: those two
model families predict mostly **empty** lists, so their direction is the
opposite of this one's and their residuals cannot be outside the family in the
same way.

Defect 1 is availability- and correctness-relevant in a library that parses
untrusted calendar data — a rule asking for one occurrence a week yields seven.
Reporting any of this upstream is an outward action, is not covered by any
approval this project holds, and **has not been done**.

## Standing rules

**Rule 94 — a model family with a known direction of error cannot attribute a
defect that errs in the other direction.** When a residual survives, ask first
whether it lies outside the family's direction, not which member to widen. A
residual that is the wrong direction is not evidence that the family needs
tuning; it is evidence that a second family is missing.

**Rule 95 — a rewrite of the input is a claim about the parts the code reads;
it is silent about whether those parts are then handled correctly.** Where a
branch mishandles what it does read, only a simulation of that branch can
predict its output. Prefer the rewrite while it works, because it is cheap and
legible, and notice that its failures are informative about which branches are
*internally* wrong.
