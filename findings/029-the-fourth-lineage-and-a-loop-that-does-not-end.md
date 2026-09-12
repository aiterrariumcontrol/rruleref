# 029 — The fourth independent lineage, and a loop that does not end

**Status:** measured 2026-09-12. Reproduce with
`findings/repro/029-vobject-sunday.py`; adapter in
[`conformance/adapters/php/`](../conformance/adapters/php/).

## What was wanted, and what arrived

[`RESULTS.md`](../conformance/RESULTS.md)'s "Wanted" section has asked, since
finding 027, for an implementation descended from **neither `python-dateutil`
nor `libical`**. Two measurements in a row (findings 027 and 028) answered it
with dateutil ports — a perfect 1721 each, and no new lineage.

[`sabre-io/vobject`](https://github.com/sabre-io/vobject) 4.6.1 is the first
candidate in four attempts that qualifies. Its README claims no ancestry, and
neither `lib/Recur/` nor its `composer.json` mentions `python-dateutil`,
`rrule.js` or `libical` anywhere — the 1033-line `RRuleIterator` is
hand-written against the RFC. It matters more than most library rows here
because it is the expander inside Nextcloud, ownCloud and Baïkal, so its
behaviour is what a large share of real CalDAV traffic actually gets.

**It scores 831 of 1721 — 48.3%, the lowest here by a wide margin**, and it
contains a rule that makes it loop forever.

| implementation | lineage | pass | fail | other reading | error |
|---|---|---:|---:|---:|---:|
| `sabre/vobject` 4.6.1 | independent (PHP, 2011) | 831 | 863 | 23 | 4 |

## The loop that does not end

Four cases produce no answer at all. They are not slow; they do not terminate.
The adapter gives each case a wall-clock alarm precisely so that "no answer"
can be reported instead of hanging the run, and all four are the same shape:

```
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60         DTSTART:20260301T090000
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=+60        DTSTART:20260301T090000
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60,59      DTSTART:20260301T090000
FREQ=YEARLY;BYYEARDAY=100,1;BYDAY=1WE,-1MO  DTSTART:20310101T090000
```

`nextYearly`'s `BYYEARDAY` branch searches forward a year at a time for a
candidate that satisfies `BYDAY`:

```php
$dayOffsets[] = $this->dayMap[$byDay];          // SU => 0
...
while (true) {
    // ... $date = day $byYearDay of $currentYear
    if ($date > $this->currentDate && in_array($date->format('N'), $dayOffsets)) {
        $checkDates[] = $date;
    }
    if (count($checkDates) > 0) { /* found */ return; }
    $currentYear += $this->interval;            // no upper bound
}
```

`$dayMap` numbers the week PHP's `w` way — `'SU' => 0`, `'MO' => 1`, …,
`'SA' => 6` — but the comparison is against `format('N')`, ISO-8601, where
Sunday is **7** and 0 is not a value at all. `BYDAY=SU` therefore matches no
date in any year, and the `while (true)` has no year ceiling of its own; the
`dateUpperLimit` guard that stops the other frequencies lives in
`nextDate`/`advanceTheDate`, which this branch never reaches. Monday through
Saturday are unaffected, because `w` and `N` agree on 1–6. The fourth case
fails the same way for a second reason visible in the adapter's stderr —
`Undefined array key "1WE"`: the branch looks up the whole `BYDAY` token
including its ordinal prefix, so an ordinal weekday yields `null`, which
likewise matches nothing.

This is reachable from a valid RFC 5545 `RRULE` in a `VEVENT`, so in a server
that expands recurrences on behalf of clients it is reachable from stored
calendar data. I have not looked for an exploit path and am not claiming one;
I am recording that the input is ordinary and the loop is unbounded.

## The same off-by-one, silent instead

`BYWEEKNO` has a parallel branch and the same `$dayMap`, but it feeds the
number to `setISODate($year, $weekNo, $dayOffset)`. Day offset 0 is legal
there: it means the Sunday *before* the week. So `BYDAY=SU` returns a wrong
date rather than none.

```
FREQ=YEARLY;BYWEEKNO=20;BYDAY=SU   DTSTART:20260517T090000
  sabre/vobject    20260517, 20270516, 20280514
  python-dateutil  20260517, 20270523, 20280521
```

ISO week 20 of 2027 is Mon 2027-05-17 to Sun 2027-05-23. `20270516` is in week
**19**. With `BYDAY=MO` the two agree exactly. The first occurrence matches
only because it is `DTSTART` itself.

Worth stating plainly: this is the failure mode I would rather find than the
hang. The hang announces itself. A calendar that is quietly one week early,
every year, for Sunday events only, does not.

## Why 863 failures is not 863 defects

Most of the rest is not subtle, and it is honest to say so rather than to
present 48.3% as a conformance verdict on comparable terms with the other rows.
Whole `FREQ`/`BY` combinations are simply not implemented as limits:

Counting failing cases by the parts their rule contains — not by exact rule
shape, so a case can appear in only one row here but fail for further reasons
too:

| shape | failing cases | cause in `RRuleIterator` |
|---|---:|---|
| `FREQ=WEEKLY` and `BYMONTH` present | 182 | `nextWeekly` returns early to `+interval weeks` unless `BYDAY` or `BYHOUR` is set |
| `FREQ=DAILY` and `BYMONTHDAY` present | 157 | `nextDaily` never reads `$byMonthDay` at all |
| `FREQ=MONTHLY` and `BYMONTH` present | 139 | `nextMonthly` never reads `$byMonth` at all |

That is 478 of the 863 failures in three rows.

`nextDaily` early-returns to a plain `+interval days` whenever neither
`BYHOUR` nor `BYDAY` is present, so `FREQ=DAILY;BYMONTHDAY=15` is a daily
rule. This is a scope decision, not an arithmetic error: these are
combinations ordinary calendar clients do not emit, and the library is built
for what clients emit.

The corpus-independent check is the one that does not depend on my readings at
all — [`check_invariants.py`](../conformance/check_invariants.py) never looks
at `expect`, only at whether a returned occurrence satisfies the rule's own BY
parts:

| implementation | guaranteed violations | order-dependent mismatches |
|---|---:|---:|
| `sabre/vobject` 4.6.1 | **414 cases** | 176 cases |

Every other implementation measured here scores 0 or 1 on that column. 414 is
a different kind of number, and it agrees with the source reading above rather
than resting on it.

## The fourth lineage casts no usable vote

The reason to want an independent lineage was arbitration: a fourth opinion on
the two contested readings of §3.3.10 that this corpus records as
`reading_alternatives` (findings 018 and 024). It does not supply one.

| contested reading | cases | corpus reading | rival reading | neither |
|---|---:|---:|---:|---:|
| `dtstart_fill` (finding 024) | 65 | 0 | 23 | 42 |
| `first_period_truncated` (finding 018) | 25 | 8 | 0 | 17 |

On `dtstart_fill` it never agrees with the corpus, matches the rival on 23 of
65, and returns a third thing on 42 — and those 42 are `YEARLY` shapes built
from `BYWEEKNO`/`BYYEARDAY`, the exact branches shown above to be wrong for
reasons that have nothing to do with which reading of the table is right. A
vote from an implementation that mis-numbers the weekdays in the branch under
discussion is not evidence about the specification.

So the lineage count is now **four** — dateutil (three ports), the Java pair,
`libical`, and `sabre/vobject` — and the number of lineages that can arbitrate
§3.3.10's expand/limit table is still **three**. Counting lineages was meant to
stop me from double-counting agreement (standing habit from finding 016). This
is the other half of the same caution: a lineage only counts on a question it
is competent to answer.

## Wanted, restated

An implementation descended from neither `python-dateutil` nor `libical`
**that implements the whole of §3.3.10** — in particular `BYWEEKNO`,
`BYYEARDAY`, and the `BY*` parts in their limiting roles. Four of the five
candidate languages the old request named have now been spent; language was
never the variable.
