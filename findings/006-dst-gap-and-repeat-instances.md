# 006 — Recurrence instances that land in a DST gap or repeat

**Status:** Done and passing. **Not a defect report.** Both expanders match the
specification on all 15 constructed cases, in four time zones.
**Date:** 2026-09-06. **Affects:** `rruleref`; `python-dateutil` 2.9.0.post0 is
checked and conformant.
**Test:** `tests/test_dst_recurrence.py` (30 assertions, run it directly).

## The gap this closes

Finding 005 added the project's first timezone coverage by running RFC 5545
§3.8.5.3's own 39 worked examples. Every occurrence they print sits at an
unambiguous local time. So after 005 the two localization rules of §3.3.5 were
pinned only by §3.3.5's two direct examples, and their *interaction with
recurrence expansion* — what happens when the rule computes an instance at a
local time that occurs twice, or not at all — was untested.

## I was wrong about how hard this was going to be

My standing note said this work "has no spec-printed answers and must be argued
from §3.3.5's text case by case", i.e. that the RFC does not say whether §3.3.5
even applies to a *generated* instance as opposed to a literal `DATE-TIME`
property value. That was wrong, and I found it out by reading rather than
arguing. RFC 5545 §3.3.10, the definition of the `RECUR` value type, answers it
in one sentence:

> If the computed local start time of a recurrence instance does not exist, or
> occurs more than once, for the specified time zone, the time of the
> recurrence instance is interpreted in the same manner as an explicit
> DATE-TIME value describing that date and time, as specified in Section 3.3.5.

That is the applicability condition my own evidence bar demands I check first,
stated by the spec, and it settles the question completely: a computed instance
is localized by exactly the same two rules as a literal value. §3.3.5:

> If, based on the definition of the referenced time zone, the local time
> described occurs more than once (when changing from daylight to standard
> time), the DATE-TIME value refers to the first occurrence of the referenced
> time.

> If the local time described does not occur (when changing from standard to
> daylight time), the DATE-TIME value is interpreted using the UTC offset
> before the gap in local times.

So the honest description of this finding is narrower than "argued from the
text": the *rule* is quoted, not argued. What the RFC does not supply is worked
values, and that is the only thing this finding derives.

## How the expected column is produced

Each case states its own derivation in the test table. There are only three
patterns:

* an **ambiguous** instance takes the offset in effect immediately *before* the
  transition instant — that is what "the first occurrence" means;
* a **nonexistent** instance takes the offset in effect immediately *before the
  gap*;
* every other instance takes the zone's unique offset for that local time.

The transition instants are not asserted from memory. `_transitions()` scans
the installed tz database at 15-minute resolution and bisects to the second, and
the test prints what it found before running anything:

```
America/New_York     2026-03-08 01:59:59 EST -> 2026-03-08 03:00:00 EDT
America/New_York     2026-11-01 01:59:59 EDT -> 2026-11-01 01:00:00 EST
Australia/Sydney     2026-04-05 02:59:59 AEDT -> 2026-04-05 02:00:00 AEST
Australia/Sydney     2026-10-04 01:59:59 AEST -> 2026-10-04 03:00:00 AEDT
Australia/Lord_Howe  2026-04-05 01:59:59 +11 -> 2026-04-05 01:30:00 +1030
Australia/Lord_Howe  2026-10-04 01:59:59 +1030 -> 2026-10-04 02:30:00 +11
Europe/Dublin        2026-03-29 00:59:59 GMT -> 2026-03-29 02:00:00 IST
Europe/Dublin        2026-10-25 01:59:59 IST -> 2026-10-25 01:00:00 GMT
```

If a future tzdata release moves one of these, the banner changes and the case
descriptions stop matching it, instead of the suite silently passing for a
different reason than it claims.

**This is the part of the method that matters, and it is the opposite of what
produced finding 001.** There I chose the inputs and also decided the right
answer. Here the answer comes from a quoted rule plus a machine-read tz
database; the only thing I chose is which cases to point at.

## Why these four zones

* **America/New_York** — one hour, northern hemisphere, and the zone every
  §3.8.5.3 example already uses.
* **Australia/Sydney** — one hour, *southern* hemisphere, so the gap is in
  October and the repeat in April. Catches anything that hardcodes the northern
  calendar.
* **Australia/Lord_Howe** — a **30-minute** shift. The gap is 02:00–02:29 and
  the repeat 01:30–01:59, so a test at 02:15 is in the gap and one at 02:45 is
  not. Catches the assumption that a DST discontinuity is an hour wide; the
  suite includes 02:45 as an explicit control that stays outside it.
* **Europe/Dublin** — transitions at 01:00 local rather than 02:00.

The 15 cases also vary *how the instance is reached*: inherited from `DTSTART`
under `FREQ=DAILY`/`WEEKLY`/`MONTHLY;BYMONTHDAY`, produced by `BYHOUR`
expansion (a different code path in most implementations), and walked into at
`FREQ=HOURLY` and `FREQ=MINUTELY` resolution.

## Result

**30/30 assertions pass, for `rruleref` and for `python-dateutil`
2.9.0.post0.** Including: `dateutil` discards a `fold=1` on `DTSTART` rather
than propagating it, which is correct — RFC 5545 cannot express "the second
occurrence" at all, because §3.3.5 says the value refers to the first.

Note what this agreement is and is not. Finding 003 established that agreement
between two RRULE implementations is weak evidence about the spec, because most
of them share a `dateutil` lineage. That objection does not apply here, because
neither implementation is the source of the expected values: both are checked
against a column derived from quoted spec text and the tz database. Two
implementations agreeing *with the spec* is a different claim from two
implementations agreeing *with each other*.

## Two consequences that are easy to disbelieve

Both follow from the quoted rules. Neither is a defect in anything, and I am
recording them because they are the practical content of this finding for
anyone scheduling real work.

**1. `FREQ=HOURLY` skips an hour of real time at the autumn transition.**
`DTSTART;TZID=America/New_York:20261101T000000` with `FREQ=HOURLY` produces
04:00Z, 05:00Z, **07:00Z**, 08:00Z, 09:00Z. There is no 06:00Z instance: the
only local time that could denote it, 01:00, is ambiguous, and §3.3.5 already
resolved it to its first occurrence at 05:00Z. An "every hour" rule therefore
has one two-hour real-time hole per year.

**2. `FREQ=HOURLY` produces two instances at the same instant at the spring
transition.** From `20260308T000000`, local 02:00 does not exist and takes the
pre-gap offset, which is the same instant as local 03:00: both are 07:00Z. The
sequence of instants is non-decreasing but **not strictly increasing**. A
consumer that assumes strict monotonicity — a dedupe keyed on the UTC instant,
a `>` cursor in a scheduler poll loop, a unique index on an instant column — is
what breaks, and it breaks once a year on a rule that looks entirely ordinary.

Whether those two instances are "duplicate instances" in the sense of §3.8.5
("When duplicate instances are generated by the RRULE and RDATE properties,
only one recurrence is considered") is **not** settled by anything I have read.
That sentence is about instances generated by different properties, and the two
here have distinct local start values and therefore distinct `RECURRENCE-ID`s,
which argues they are distinct instances that merely coincide in real time. I
am flagging the question, not answering it. It is the natural next thing to
look for a decisive quote on.

## Appendix, same day — the "duplicate instances" question, as far as the RFC takes it

I said above that this was the natural next thing to look for a decisive quote
on, so I looked. **The answer is that RFC 5545 does not settle it**, and I would
rather record that than manufacture a reading.

The sentence appears three times, in §3.8.5.1 (`EXDATE`), §3.8.5.2 (`RDATE`) and
§3.8.5.3 (`RRULE`), and all three are the same boilerplate paragraph:

> Where duplicate instances are generated by the "RRULE" and "RDATE"
> properties, only one recurrence is considered. Duplicate instances are
> ignored.

Two things about it. First, its scope is instances generated by `RRULE` **and**
`RDATE` — it is about the same instance arriving from two inclusion properties,
not about two instances of one rule coinciding. Second, and decisively for my
purpose, **the RFC nowhere defines when two `DATE-TIME` values are duplicates**.
It does not say whether the comparison is on the value as written (wall clock
plus `TZID`) or on the instant it denotes. That is exactly the distinction the
spring-transition pair turns on: local 02:00 and local 03:00 are different
values and the same instant.

The nearest thing to a lever is §3.8.4.4, on `RECURRENCE-ID`:

> The DATE-TIME value is set to the time when the original recurrence instance
> would occur

> Subsequent instances are determined by their "RECURRENCE-ID" value and not
> their current scheduled start time.

So the identity of an instance is carried by its *original local start value*,
explicitly in preference to when it is currently scheduled, and the two
instances here have different ones. That is a genuine argument that they are two
instances that merely coincide in real time — but it is an argument about how
`RANGE=THISANDFUTURE` picks out subsequent instances, not a definition of
"duplicate", and I am not going to stretch it into one. Note also that it cuts
the way that *matters* for a scheduler: it says do not identify instances by
their scheduled instant.

**Conclusion recorded, not asserted:** an implementation that emits both
instances and one that collapses them are both defensible under RFC 5545 as
written, so a portable consumer must not assume either. The concrete advice from
the body of this finding is unchanged and does not depend on the answer: do not
key on the UTC instant, and do not assume strictly increasing instants.
