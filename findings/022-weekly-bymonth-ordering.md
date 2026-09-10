# 022 — what "the current set of evaluated occurrences" is, for FREQ=WEEKLY with BYMONTH

**Status:** Measured. Written in response to the discussion on
[libical/libical#1374](https://github.com/libical/libical/issues/1374), which
is [finding 019](019-libical-weekly-bymonth-bysetpos.md) reported upstream.
**Date:** 2026-09-10.
**Nothing here is a defect claim against a specification.** It is a
measurement of six implementations plus a mechanical statement of two readings.

## The question that was raised

On #1374, `minichma` doubted one date in the expected set of case A, and gave
a reading of RFC 5545 §3.3.10 to justify the doubt. §3.3.10 says the BYxxx
parts are applied

> to the current set of evaluated occurrences in the following order: BYMONTH,
> BYWEEKNO, BYYEARDAY, BYMONTHDAY, BYDAY, BYHOUR, BYMINUTE, BYSECOND and
> BYSETPOS

For `FREQ=WEEKLY`, `BYMONTH` is a **limit** and `BYDAY` is an **expand**. So
`BYMONTH` runs *before* the week has been expanded into days. What set does it
limit? Two answers:

* **filter-instances** — `BYMONTH` restricts the instants the week finally
  yields, wherever in the pipeline that is arranged.
* **seed-limit** — the set entering the week is the single `DTSTART`-derived
  seed for that week. `BYMONTH` is applied to *that*. If the seed's month is
  not selected the week yields nothing; if it is, `BYDAY` then expands the
  whole week — **including into months `BYMONTH` does not select**.

`CMendia` then observed that this question is not about `BYSETPOS` at all and
proposed a test without it.

Both are implemented, dependency-free, in
[`repro/022-seed-limit-reading.py`](repro/022-seed-limit-reading.py). All rows
labelled *filter-instances* and *seed-limit* below are its output.

## Measured: `CMendia`'s test, with no BYSETPOS

```
DTSTART:20260705T090000
RRULE:FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7        (first 15)

rruleref, python-dateutil, rrule.js, ical4j, lib-recur, libical master
                 20260705 20260706 20260707 20260712 20260713 20260714
                 20260719 20260720 20260721 20260726 20260727 20260728
                 20270704 20270705 20270706
seed-limit       ... 20260726 20270628 20270629 20270704 20270705 20270706
```

Six implementations, including libical master, return an identical
list, and it is the *filter-instances* list. Every one of them returns
`20260727`, the date `minichma` doubted.

That is evidence about implementations, not about the specification
([finding 003](003-implementation-lineage.md) is why this project does not
treat a majority as an authority). What it does settle is narrower and
sufficient: **libical master already answers this rule the filter-instances
way when `BYSETPOS` is absent.**

The *seed-limit* row is the price of the other reading, stated so it can be
accepted deliberately rather than by accident: `BYMONTH=7` must then yield
**2027-06-28 and 2027-06-29**, two dates in June. No implementation measured
here does that.

## Measured: the same rule, with BYSETPOS

```
DTSTART:20260705T090000
RRULE:FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1     (first 8)

filter-instances 20260705 20260706 20260713 20260720 20260727 20270704 20270705 20270712
  = rruleref, python-dateutil, rrule.js, lib-recur
seed-limit       20260706 20260713 20260720 20270628 20270705 20270712 20270719 20280626
libical master   20260706 20260713 20260720 20260727 20270705 20270712 20270719 20270726
ical4j           20260705 20260712 20260719 20260726 20270704 20270711 20270718 20270725
```

libical's list is **neither**. It agrees with *seed-limit* in dropping
`20260705`, and with *filter-instances* in keeping `20260727` and in never
producing `20270628`. So the reading question, however it is settled, does not
by itself account for case A.

## Two rules that are easy to say out loud

`ksmurchison` asked whether there is a real-world use for such an RRULE. I have
no user who hit this; it came out of a corpus sweep, and I am not going to
invent one. What I can offer instead is the same defect stated in rules that
are describable in a sentence — and in both, the occurrence that goes missing
is `DTSTART` itself.

**"The first working day of each week, during July."**

```
DTSTART:20260701T090000                                   (Wednesday)
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=7;BYSETPOS=1    (first 6)

filter-instances 20260701 20260706 20260713 20260720 20260727 20270701
  = rruleref, python-dateutil, rrule.js, lib-recur
seed-limit       20260706 20260713 20260720 20260727 20270705 20270712
  = libical master, ical4j
```

**"The first working day of each week, during the September–December term."**

```
DTSTART:20260901T090000                                   (Tuesday)
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=9,10,11,12;BYSETPOS=1  (first 10)

filter-instances 20260901 20260907 20260914 20260921 20260928 20261005
                 20261012 20261019 20261026 20261102
  = rruleref, python-dateutil, rrule.js, lib-recur
seed-limit       20260907 20260914 20260921 20260928 20261005 20261012
                 20261019 20261026 20261102 20261109
  = libical master, ical4j
```

On these two, libical's output equals *seed-limit* exactly. On the rule in the
section above it does not. Matching on six or ten values is not proof of a
mechanism, and no claim about `icalrecur.c` is made here.

**ical4j drops `DTSTART` on both.** This is not libical-specific.

Under *filter-instances*, `DTSTART` is the first instance of both of these
recurrence sets, so §3.8.5.3 does not excuse omitting it:

> The "DTSTART" property defines the first instance in the recurrence set.

Under *seed-limit* it is not — the first instance is 2026-07-06 and
2026-09-07 respectively — and §3.8.5.3 then says the recurrence set generated
from an unsynchronized `DTSTART` is undefined. That is a defensible position to
take about these two rules, but it is a different claim from "libical is right
here", and it is not available for the no-`BYSETPOS` case in the first section:
there *seed-limit* does include `DTSTART`, and still disagrees with all six
implementations three months later.

## One case the reading question cannot reach at all

```
DTSTART:20260703T090000                                   (Friday)
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=7;BYSETPOS=-1   (first 6)

filter-instances 20260703 20260710 20260717 20260724 20260731 20270702
seed-limit       20260703 20260710 20260717 20260724 20260731 20270702
  = rruleref, python-dateutil, rrule.js, ical4j, lib-recur
libical master   20260703 20260710 20260717 20260724 20260731 20270709
```

"The last working day of each week, during July." Here the two readings
**coincide** — the 2027 week Mon 06-28 .. Sun 07-04 has its seed on 07-04, in
July under either account, and `BYSETPOS=-1` picks 07-02 either way — and
`DTSTART` is the first instance under both. libical alone returns neither
reading's answer: it skips 2027-07-02 and resumes a week later. This is case C
of #1374, the resumption-after-a-gap behaviour, and no settlement of the
ordering question makes it correct.

## Measured: case C's mechanism is absent without BYSETPOS

Case C of #1374 was a week skipped when iteration resumes after a long gap.
Removing `BYSETPOS` removes the divergence:

```
DTSTART:20260802T090000
RRULE:FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU                        (first 8)

all six           20260802 20260804 20260809 20260811 20260816 20260818
                  20260823 20260825
```

So `CMendia`'s suggestion that the issue is not about `BYSETPOS` is not borne
out for case C: without `BYSETPOS` there is nothing to see. Case A is
different — there the *reading* question is real, and the answer to it is
above.

## Not measured

**Ical.Net.** `minichma` reported that Ical.Net does not return `20260727`.
No .NET toolchain is available in this environment, so Ical.Net is not among
the six. Which rule that check was run against matters: if it included
`BYSETPOS` it is a datum about the same divergence class as libical's, and if
it did not, it is a second implementation of *seed-limit* and worth knowing.

## Reproducing

```sh
python3 findings/repro/022-seed-limit-reading.py         # both readings, no deps
```

The six-implementation rows come from the adapters in
[`../conformance/adapters/`](../conformance/adapters/) driven with the cases in
[`repro/022-probe-cases.ndjson`](repro/022-probe-cases.ndjson), which is in the
[adapter protocol](../conformance/PROTOCOL.md) format — one JSON object per
line on stdin, one per line on stdout:

```sh
LD_LIBRARY_PATH=/path/to/libical-install/lib \
  conformance/adapters/c/libical_adapter < findings/repro/022-probe-cases.ndjson
python3 conformance/adapters/dateutil_adapter.py < findings/repro/022-probe-cases.ndjson
```

Every row on this page, in one file, as produced on 2026-09-10:
[`repro/022-output.txt`](repro/022-output.txt).

libical master is `48d52b4b868d5adb05aa7b4ba3be95c848066552`; the other
versions are recorded in
[`../conformance/RESULTS.md`](../conformance/RESULTS.md).
