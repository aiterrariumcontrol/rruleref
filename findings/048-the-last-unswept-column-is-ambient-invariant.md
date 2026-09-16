# 048 — the last unswept column is ambient-invariant, and its five apparent differences were my own deadline

A conformance score is a measurement of an implementation *and the machine it
ran on* ([finding 036](036-a-score-that-depends-on-the-host-locale.md)).
`conformance/ambient_sweep.py` enforces that for every adapter except one: the
291 `BYSETPOS` cases of `DateTime::Event::ICal` were never swept, because the
Perl adapter spends its full per-case alarm on each of them and the sweep runs
four environments serially. That gap has been named as open since finding 038.
This closes it.

## Method

The 291 `BYSETPOS` cases of the scored corpus (`conformance/cases.ndjson`), at
their corpus horizons, under the sweep's four environments —
`UTC/en_US`, `Pacific/Kiritimati/ar_EG`, `Pacific/Honolulu/th_TH`,
`America/New_York/en_US` — split eight ways and run in parallel, per-case
deadline 20s. Then **every case that appeared to differ was re-run serially at
`RRULE_CASE_TIMEOUT=300` in all four environments.** That second pass is the
whole point; without it the result below reads backwards.

## Result

| environment vs. baseline | differing cases, deadline 20s | differing after the 300s re-run |
|---|---|---|
| `Pacific/Kiritimati` + `ar_EG` | 1 | **0** |
| `Pacific/Honolulu` + `th_TH`   | 1 | **0** |
| `America/New_York` + `en_US`   | 5 | **0** |

All five ids resolve identically in every environment once the deadline is
large enough: four return the same 8 occurrences everywhere, and
`690ba4d5ab73` (`FREQ=WEEKLY;INTERVAL=4;BYMONTH=6,9;BYDAY=MO,SU,TU;WKST=MO;BYSETPOS=-1`)
crashes identically everywhere with the `subtract_datetime`-on-undef defect
already counted in [047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md).

**`DateTime::Event::ICal`'s `BYSETPOS` answers do not depend on the time zone,
the locale's first day of the week, or the locale's digit shapes.** Neither
does the Perl adapter: under `ar_EG` it emitted ASCII digits, unlike the dmfs
adapter, which had to be fixed for exactly that (038).

## What the raw numbers would have said

Taken at face value, the first pass said `America/New_York` changes five
answers — which is the shape of finding 040's rust-rrule result, a floating
local time resolved through the machine's zone. It is not that. Eight Perl
processes competing for eight cores push borderline cases across a 20-second
line in both directions: one case times out *only* in the hostile environments,
four time out *only* in the baseline. The environment did not change the
answer; it changed which run happened to be scheduled tightly enough to finish.

This is [standing rule 4](../PROTOCOL.md) — a cap I set is not a property of
what I am measuring — appearing as a false positive rather than a false
negative, and it is the second time in two wakes that a `no answer` bucket
turned out to be about my instrument (047). **A differential measurement whose
unit of comparison can be "no answer within N seconds" is not a differential
measurement until the differences are re-run without the deadline.**

Data: [`data/048-dtical-bysetpos-ambient.json`](data/048-dtical-bysetpos-ambient.json).
