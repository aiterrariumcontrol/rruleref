# 043 — `FREQ=HOURLY` ignores every `BY*` part, by a 2012 decision

[Finding 042](042-what-the-fourth-lineage-hides-past-occurrence-eight.md) left
14 `HOURLY` rows of `sabre/vobject`'s hidden divergences unattributed, and said
so rather than guess. This is the cause, and it turns out to be larger and
older than the 14 rows suggested.

## The 14 rows have one shape

All 14 agree with the control for exactly 15 occurrences — 09:00 through 23:00
on the start day — and then diverge at the first midnight rollover:

```
FREQ=HOURLY;BYDAY=MO   DTSTART=20260302T090000   (2026-03-02 is a Monday)

control  ... 20260302T230000, 20260309T000000, 20260309T010000 ...
sabre    ... 20260302T230000, 20260303T000000, 20260303T010000 ...
```

The control skips to the next Monday. sabre walks straight into Tuesday. The
day-level limit rule selected the first day only because `DTSTART` already
satisfied it; it was never applied again.

## It is not a `BYDAY` bug

`Recur/RRuleIterator.php` (sabre/vobject 4.6.1) advances hourly recurrences in
four lines:

```php
protected function nextHourly()
{
    $previousEventDateTime = clone $this->currentDate;
    $this->currentDate = $this->currentDate->modify('+'.$this->interval.' hours');
    $this->adjustForTimeJumpsOfHourlyEvent($previousEventDateTime);
}
```

There is no filter in it at all. `adjustForTimeJumpsOfHourlyEvent` handles DST
and nothing else. So the omission is every `BY*` part at once. Seven rules,
same `DTSTART`, limit 5 — sabre's output is byte-identical in all seven:

| rule | sabre | control (`python-dateutil`) |
|---|---|---|
| `FREQ=HOURLY;BYMONTH=1` | 09,10,11,12,13 on 01-01 | same |
| `FREQ=HOURLY;BYMONTHDAY=1` | 09,10,11,12,13 on 01-01 | same |
| `FREQ=HOURLY;BYYEARDAY=1` | 09,10,11,12,13 on 01-01 | same |
| `FREQ=HOURLY;BYSETPOS=1` | 09,10,11,12,13 on 01-01 | same |
| `FREQ=HOURLY;BYDAY=MO` | 09,10,11,12,13 on 01-01 | 00..04 on **01-05** |
| `FREQ=HOURLY;BYMINUTE=0,30` | 09,10,11,12,13 | 09:00, **09:30**, 10:00, **10:30**, 11:00 |
| `FREQ=HOURLY;BYHOUR=9,10` | 09,10,11,12,13 | 09,10 on 01-01, then 09,10 on **01-02** |

The first four agree only because `DTSTART` (2026-01-01, 09:00) happens to
satisfy them. RFC 5545 §3.3.10's table gives the `HOURLY` column as `Limit` for
`BYMONTH`, `BYYEARDAY`, `BYMONTHDAY`, `BYDAY`, `BYHOUR` and `BYSETPOS`, and
`Expand` for `BYMINUTE` and `BYSECOND`. None of the eight is honoured.

Repro: [`repro/043-hourly-byparts.sh`](repro/043-hourly-byparts.sh).

## How much of the corpus this reaches

Of the 1721 scored cases, 63 are `FREQ=HOURLY` and 58 carry at least one `BY*`
part that sabre structurally cannot honour. Re-run at a 64-occurrence horizon
against the two-lineage control of finding 040:

| | count |
|---|---:|
| diverge from the control | **40** |
| agree — `DTSTART` coincidentally satisfies the limit rule, no expand rule present | 18 |
| control cannot adjudicate | 0 |

14 of the 40 are the hidden rows of finding 042; the rest already diverge
inside the corpus horizon and are inside the published score. The
`HOURLY`/`YEARLY` remainder of 042 is now attributed except for its 2 `YEARLY`
rows, which stay unattributed.

## The part worth recording

This is not an oversight. In October 2012 a contributor opened
[sabre-io/vobject#11](https://github.com/sabre-io/vobject/issues/11), *"Add
support for FREQ=HOURLY;BYHOUR=8,9,10,11;BYDAY=SA,SU"*, with a patch ready. The
maintainer redirected it:

> Also, for this one.. I think I rather see BYHOUR implemented in FREQ=DAILY,
> as this will give you the BYDAY logic for free..
>
> I've read on the calconnect mailing lists before as well that they recommended
> to avoid BYx rules for FREQ=x.
>
> — BYMONTH is weird in combination with FREQ=MONTHLY, BYDAY is weird in
> combination with FREQ=DAILY, and so on..

The contributor agreed and moved the work to `nextDaily()`, which landed as
[#12](https://github.com/sabre-io/vobject/issues/12). `nextHourly()` has stayed
four lines ever since.

The advice being cited is about *redundant* combinations — `BYMONTH` under
`FREQ=MONTHLY` restates the frequency. For issue #11's own rule the redirect was
sound: `FREQ=DAILY;BYHOUR=8,9,10,11;BYDAY=SA,SU` and the `FREQ=HOURLY` spelling
of it produce identical output under the control, at `DTSTART` times both in and
out of the `BYHOUR` set. I expected them to differ and checked; they do not.

What the redirect gave up is the rest of the column. `FREQ=HOURLY;BYDAY=MO` has
no `DAILY` rewriting that is not a 24-value `BYHOUR` list, and once `INTERVAL`
is not 1 there is no rewriting at all, because the hourly walk carries its phase
across the skipped days:

```
FREQ=HOURLY;INTERVAL=5;BYDAY=MO   DTSTART=20260105T090000

control  20260105T090000, 20260105T140000, 20260105T190000,
         20260112T010000, 20260112T060000, 20260112T110000
```

The Monday after resumes at 01:00, five hours on from 20:00 — a position no
`FREQ=DAILY` rule states. So a style heuristic about one redundant pairing,
correct for the rule in front of it, was applied to a whole column of §3.3.10,
and fourteen years later that is still the behaviour.

This is the third omission of the same kind found in this implementation —
see [031](031-one-cluster-three-causes.md) for `BYMONTH` under
`WEEKLY` and `MONTHLY`, and 042 for `FREQ=DAILY`. In all three the part parses
without complaint and is then silently dropped.
