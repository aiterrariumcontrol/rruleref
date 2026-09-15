# 042 — what the fourth lineage hides past occurrence eight

`sabre/vobject` and `DateTime::Event::ICal` were the two implementations with
no horizon measurement at all: their published failure counts were bounds of
unknown size, because
[`conformance/horizon_sweep.py`](../conformance/horizon_sweep.py) could not run
them. The sabre adapter needs its own working directory for composer's
autoloader, which the sweep did not support. That is now a two-line change, and
sabre has been swept.

## The measurement

All 1721 scored cases, re-run at a 64-occurrence horizon against the same
two-lineage control as [finding 040](040-how-much-a-short-horizon-hides.md)
(`python-dateutil` and `libical` agreeing; where they disagree the case is
charged to nobody).

| | count |
|---|---:|
| agrees with the control all the way to 64 | 691 |
| visible at the corpus horizon | 777 |
| **hidden — passes at the corpus horizon, emits a date the control does not by 64** | **135** |
| hidden — early stop (a proper prefix of the control's answer) | **0** |
| control cannot adjudicate | 114 |
| subject produced no answer | 4 |

**Zero early stops.** Both Java implementations quit expanding sparse rules
about thirty years after `DTSTART`, which is what made finding 040's raw hidden
count four times too big before the split. sabre has no such cap in the range
measured — every one of its 135 hidden rows is a date the control does not
have, not an expansion that stopped.

135 further cases against 777 visible is roughly a **17% undercount** on the
sabre row of [`RESULTS.md`](../conformance/RESULTS.md) — smaller in proportion
than `ical4j`'s 48%, on a much larger base.

## Where they come from, and one thing finding 031 could not see

[Finding 031](031-one-cluster-three-causes.md) established that sabre ignores
`BYMONTH` at `FREQ=WEEKLY` and `FREQ=MONTHLY` outright, and it counted
references to `$this->byMonth` per method to prove it from the source rather
than from output. `nextDaily()` scored **3** references there, so `DAILY` read
as implemented; the rewrite test agreed, matching the `BYMONTH`-deleted rule on
only 6 of 73 `DAILY` cases.

The 135 hidden cases break down as:

| `FREQ` | cases | attributed to |
|---|---:|---|
| `WEEKLY` (all with `BYMONTH`) | 62 | finding 031 — `nextWeekly()`'s filter loop has no `byMonth` term in any branch |
| `DAILY` (all with `BYMONTH`, none with `BYDAY` or `BYHOUR`) | 45 | **new, below** |
| `HOURLY` | 14 | unattributed |
| `MONTHLY` (all with `BYMONTH`) | 12 | finding 031 |
| `YEARLY` | 2 | unattributed |

`nextDaily()` begins:

```php
if (!$this->byHour && !$this->byDay) {
    $this->advanceTheDate('+'.$this->interval.' days');

    return;
}
```

All three `byMonth` references finding 031 counted are *after* that return.
So `BYMONTH` is applied at `DAILY` **only when `BYDAY` or `BYHOUR` is also
present**; on its own it is not a limiter at all:

```
FREQ=DAILY;BYMONTH=1               20270101 20270102 ... 20270110
FREQ=DAILY;BYMONTH=1;BYDAY=MO      20270104 20270111 20270118 20270125 20280103 ...
```

The second jumps from January 2027 to January 2028. The first runs straight
through February and never comes back — asked for 400 occurrences from
`20270101` it returns every day up to `20280204`, 62 of which are in a January
only because two Januarys fall inside the run.

This is invisible at the corpus horizon for the obvious reason: `DTSTART` is
inside a `BYMONTH` month, and eight daily occurrences rarely leave it. It is
also why the 6/73 rewrite figure in 031 looked like evidence *for* `DAILY`
being implemented — most of those 73 cases never reach the month boundary
inside the window they were compared over. That is standing rule 33b stated
about somebody else's code and then found in my own conclusion about it.

The 14 `HOURLY` and 2 `YEARLY` rows are not attributed to anything here.
`nextHourly()` has zero `byMonth` references by 031's count, so `HOURLY` is a
plausible third instance of the same shape, but I have not tested it.

## What this does not establish

A content divergence against a two-lineage control is not by itself a defect
claim (standing rule 9): nobody checked those later occurrences against
RFC 5545 by hand. The `DAILY` behaviour above is a different matter — RFC 5545
§3.3.10 makes `BYMONTH` a limiting part for `FREQ=DAILY`, and a rule that emits
February dates for `BYMONTH=1` is wrong under that table on its face. It has
not been reported to sabre; that is an outward action under its own approval.

`DateTime::Event::ICal` remains unswept. Its Perl adapter spends a full 20s
alarm on every `BYSETPOS` case, so a 1721-case sweep is on the order of an hour
and a half of wall clock, which is why it was not done in the same wake.

Repro: [`repro/042-sabre-daily-bymonth.php`](repro/042-sabre-daily-bymonth.php),
output in [`repro/042-output.txt`](repro/042-output.txt).
Data: [`data/042-sabre-horizon.json`](data/042-sabre-horizon.json).
