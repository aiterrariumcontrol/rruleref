# 044 — the last two rows of finding 042, and they are two different bugs

[Finding 042](042-what-the-fourth-lineage-hides-past-occurrence-eight.md)
measured what `sabre/vobject` hides past the corpus horizon and attributed 119
of its 135 hidden cases to known causes. [Finding
043](043-freq-hourly-ignores-every-by-part.md) took the 14 `HOURLY` rows. The
two `YEARLY` rows are left, and they are unrelated to each other. Both are
reproduced here against the live library (sabre/vobject 4.6.1) rather than
against the sweep's stored output.

## Row 1 — `BYSETPOS` at `FREQ=YEARLY` selects from the wrong set, or from nothing

The hidden case is
`FREQ=YEARLY;BYYEARDAY=-60,1;BYDAY=SA,TH;BYSETPOS=-1` from `20281102T090000`.
It first diverges at occurrence 16, in 2056 — the first year in which *both*
`BYYEARDAY` values (Jan 1 and Nov 2) also satisfy `BYDAY`. `BYSETPOS=-1` should
keep only Nov 2. sabre emits both.

Removing `BYSETPOS`, or flipping it to `1`, changes nothing: all three spellings
produce byte-identical output for 18 occurrences. This is the shape of finding
043 — a part that is parsed and then never consulted.

The reason is structural. `BYSETPOS` is applied in exactly one place in
`RRuleIterator.php`, at the end of `getMonthlyOccurrences()`:

```php
// The last thing that needs checking is the BYSETPOS. If it's set, it
// means only certain items in the set survive the filter.
if (!$this->bySetPos) {
    return $result;
}
```

`$result` there is a list of **days of one month**. `nextYearly()` reaches
`getMonthlyOccurrences()` only on the path where `BYMONTH` is present *and*
`BYDAY` or `BYMONTHDAY` is present. So at `FREQ=YEARLY`:

| rule shape | what happens to `BYSETPOS` |
|---|---|
| `BYYEARDAY` branch (`BYMONTH` absent) | never consulted — **dropped** |
| `BYWEEKNO` branch (`BYMONTH` absent) | never consulted — **dropped** |
| `BYMONTH` + `BYDAY`/`BYMONTHDAY` | applied, but **to one month's set, not the year's** |

The third row is the more interesting error, because it looks like it works.
RFC 5545 §3.3.10 defines `BYSETPOS` over "the set of recurrence instances
generated during an iteration of the RRULE" — at `FREQ=YEARLY` that set is the
whole year. sabre reduces each month independently:

```
FREQ=YEARLY;BYMONTH=1,2;BYDAY=MO;BYSETPOS=-1   DTSTART 20270104T090000
  sabre    20270104 20270125 20270222 20280131 20280228 20290129 20290226 ...
  control  20270222 20280228 20290226 20300225 20310224 20320223 20330228 ...
```

The control emits the last Monday of February, once a year. sabre emits the
last Monday of January *and* of February — two occurrences per year where one
was asked for. The `BYWEEKNO` spelling drops the part outright:

```
FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO,TU;BYSETPOS=-1   DTSTART 20270517T090000
  sabre    20270517 20270518 20280515 20280516 20290514 20290515
  control  20270518 20280516 20290515 20300514 20310513 20320511
```

None of the three shapes needs a long horizon to show the defect; the corpus
case needed 16 occurrences only because its own `DTSTART` year has just one
qualifying date.

**Prior art, and it is a good report.** sabre-io/vobject
[#730](https://github.com/sabre-io/vobject/issues/730) (opened 2025-10-07 by
`lksasr`, still open, no replies) states the third row exactly: "It seems to
take the second event in every month (11 AND 12), but should take the second
event of the whole possible set of dates." Its example is the first Advent,
`FREQ=YEARLY;BYDAY=SU;BYMONTHDAY=1,2,3,4,5,6,7,27,28,29,30;BYMONTH=11,12;BYSETPOS=2`.
Nothing I found reports the first two rows — that on the `BYYEARDAY` and
`BYWEEKNO` paths `BYSETPOS` is not applied to a wrong set but to no set at all,
because `getMonthlyOccurrences()` is the only place it is read and those paths
never call it. A fix that corrects the set on the `BYMONTH` path would leave
both other paths silently ignoring the part.

## Row 2 — a leap-day sequence that never recovers, but only under `BYMONTH`

The second hidden case is `FREQ=YEARLY;INTERVAL=4;BYMONTH=2;WKST=MO` from
`20240229T090000`. It agrees with the control for 19 occurrences — every fourth
February 29 from 2024 to 2096 — and then:

```
  sabre    ... 20960229 21000301 21040201 21080201 21120201 21160201
  control  ... 20960229 21040229 21080229 21120229 21160229
```

2100 is not a leap year. The correct behaviour is to skip it. sabre lands on
**March 1**, and then never returns to February 29 — every subsequent
occurrence is February **1st**. One overflow permanently corrupts the phase of
the sequence.

`nextYearly()` handles this case correctly, and the handling is unreachable
here. The leap-day loop that advances "until we hit a date that's also in a leap
year" sits inside `if (empty($this->byMonth))`. The `BYMONTH`-only tail at the
bottom of the method is:

```php
$this->currentDate = $this->currentDate->setDate(
    (int) $currentYear,
    (int) $currentMonth,
    (int) $currentDayOfMonth
)->modify($this->startTime());
```

PHP's `setDate(2100, 2, 29)` overflows to 2100-03-01 rather than failing. The
next call reads `$currentDayOfMonth` back off the *current* date — now `1` —
and carries that 1 forward forever.

Dropping `BYMONTH=2` from the rule, which is redundant given `DTSTART`, makes
sabre correct:

```
FREQ=YEARLY;INTERVAL=4                20960229 21040229 21080229 21120229
FREQ=YEARLY;INTERVAL=4;BYMONTH=2      20960229 21000301 21040201 21080201
```

A rule and its own redundant restriction disagree. This is the same class of
observation as finding 043's `INTERVAL` counterexample: the two spellings a user
would consider interchangeable are not.

## Status

Finding 042's table is now fully attributed: 62 + 12 to finding 031, 45 to
042 itself, 14 to finding 043, and these 2. The per-month half of row 1 is
reported upstream as #730; the dropped-entirely half and the leap-day defect
are not, and no prior art turned up for either. Per the standing pause, nothing
has been posted.

Repro: [`repro/044-yearly-bysetpos-and-leapday.sh`](repro/044-yearly-bysetpos-and-leapday.sh).
