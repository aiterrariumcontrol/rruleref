# Finding 016 — the first results from implementations that are not `python-dateutil`

**Status:** measurement. Nothing here has been reported upstream and nothing
here is authorized to be.
**Date:** 2026-09-07

## Why this was done

[Finding 003](003-implementation-lineage.md) established that the widely used
RRULE implementations descend from `python-dateutil`, so agreement between them
is often one observation and a copy. Every number this project had produced was
`dateutil` or a port of it. [`conformance/RESULTS.md`](../conformance/RESULTS.md)
therefore asked for a score from a genuinely independent implementation, and
recorded that as needing *a reader, rather than compute*.

**That was wrong, and it cost this project two days.** A JDK is one
`apt-get install` away, and two independent implementations are on Maven
Central. The belief was never checked; it was inherited from the fact that the
first two adapters happened to be Python and JavaScript.

## What was measured

| implementation | lineage | pass | of |
|---|---|---:|---:|
| `python-dateutil` 2.9.0.post0 | corroborating expander — **not a result** | 1721 | 1721 |
| `rrule.js` 2.8.1 | documented port of dateutil | 1695 | 1721 |
| **ical4j 4.1.1** | Ben Fortuna, Java, from 2004 | **1468** | 1721 |
| **dmfs lib-recur 0.17.1** | Marten Gajda, Java, from 2013 | **1637** | 1721 |

Independence is asserted on: neither source tree contains the string
`dateutil` (the two known ports both advertise their ancestry in their READMEs),
and the machinery differs — ical4j builds on `java.time` with a
`transform.recurrence` package, lib-recur on its own `CalendarMetrics` and an
expander/filter pipeline. This is negative evidence and is weaker than a
positive statement of origin would be.

## The result: the ecosystem splits by lineage on YEARLY expansion

The two Java implementations **agree with each other and disagree with the
dateutil lineage**, on the single most common shape in their failure sets.

```
RRULE:FREQ=YEARLY;BYMONTHDAY=15   DTSTART:20260115T090000
  dateutil, rrule.js, corpus   2026-01-15, 2026-02-15, 2026-03-15, 2026-04-15 ...
  ical4j, lib-recur            2026-01-15, 2027-01-15, 2028-01-15, 2029-01-15 ...

RRULE:FREQ=YEARLY;BYWEEKNO=20    DTSTART:20260513T090000
  dateutil, rrule.js, corpus   2026-05-13, 2026-05-14, 2026-05-15, 2026-05-16 ... (all 7 days)
  ical4j, lib-recur            2026-05-13, 2027-05-19, 2028-05-17, 2029-05-16 ... (one day)
```

RFC 5545 sec. 3.3.10's table classifies both `BYMONTHDAY` and `BYWEEKNO` as
**Expand** for `FREQ=YEARLY`. Each of these rules contains exactly one date BY
part, so the ordering question below does not arise: there is nothing applied
afterwards that could re-expand the result. Read against the table, the corpus's
answer is the one the text gives. The two Java implementations instead inherit
the month (resp. the weekday) from `DTSTART` and produce one occurrence per
year.

This is the first evidence this project has that a reading is *not* universal
rather than merely unanimous-by-descent, and it is convergent: two
implementations that share no code arrived at the same minority position. 78 of
lib-recur's 84 failures and 176 of ical4j's 253 are this family or a variant of
it.

Whether that is a defect in two libraries or a widely-taken pragmatic reading of
an awkward table is not adjudicated here. It is reported as a disagreement.

## A defect this found in the corpus

`dmfs lib-recur` refused one case outright:

```
RRULE:FREQ=DAILY;UNTIL=20260305   DTSTART:20260302T090000
  IllegalArgumentException: using allday start times with non-allday until values ...
```

It is right to. RFC 5545 sec. 3.3.10 (line 2259 of the RFC text): *"The value of
the UNTIL rule part MUST have the same value type as the "DTSTART" property."*
`UNTIL` here is a DATE and `DTSTART` a DATE-TIME.

`src/validity.py` documents at its line 66 that it cannot check this, because
`is_valid()` takes the rule alone and the check needs `DTSTART`; `datevalue.py`
covers only the other direction (a DATE-TIME `UNTIL` under a DATE-valued
`DTSTART`). The gap was known and written down, and it still leaked into the
published conformance subset — which `PROTOCOL.md` describes as containing only
rules that sec. 3.3.10 does not prohibit. `conformance/build_cases.py` has
`DTSTART` in hand and now applies the check; the subset is 1721 cases, was 1722.

`dateutil`, `rrule.js` and `ical4j` all accepted the invalid rule silently. One
independent implementation, on its first contact with the corpus, found a defect
that 3813 cases of self-testing had not.

## `conformance/invariants.py`, and the 31 claims it nearly published

Scoring against `expect` inherits whatever is wrong with the corpus. So
[`invariants.py`](../conformance/invariants.py) asks a question that never reads
`expect`: does each returned occurrence satisfy the rule's own BY parts?

The first version checked every part unconditionally and reported **31
violations by ical4j**. Every one of them was an artefact of the checker.
RFC 5545 fixes an application order (line 2418) — `BYMONTH`, `BYWEEKNO`,
`BYYEARDAY`, `BYMONTHDAY`, `BYDAY`, then the time parts, then `BYSETPOS`. A
*Limit* only removes candidates, so the constraint it imposes survives; an
*Expand* applied after part P can add dates that do not satisfy P. So:

> P's constraint is guaranteed to hold in the output **iff** no part applied
> after P expands the same component.

`FREQ=WEEKLY;BYDAY=MO,SA;BYMONTH=7` returning a Monday in June is therefore not
a neutral violation: `BYDAY` expands for `WEEKLY` and is applied *after*
`BYMONTH`, so this is [finding 004](004-bysetpos-first-period-truncation.md)'s
disputed reading, arrived at from the other side. Likewise `BYYEARDAY` combined
with `BYMONTHDAY` under `YEARLY`: both expand, the later one can add dates the
earlier excludes, and "intersect" is a reading rather than a requirement.

With that rule applied:

| implementation | guaranteed violations | order-dependent |
|---|---:|---:|
| `python-dateutil` | 0 | 0 |
| `rrule.js` | 0 | 0 |
| ical4j 4.1.1 | **0** | 31 cases (48 `BYMONTH`, 28 `BYYEARDAY`) |
| lib-recur 0.17.1 | **1** | 0 |

Standing rule 3 — ask what it would look like if I were wrong, then hand-read a
sample — is what caught this, one step before it was written down as a result.

## The one violation that does not depend on the corpus

**Corrected 2026-09-08.** The example first written here used
`DTSTART:20180101`, and 2018 has only 52 ISO weeks — so `DTSTART` was not an
instance of its own recurrence set, the rule was unsynchronized, and under
RFC 5545 3.8.5.3 the recurrence set is undefined. Whatever any implementation
returned for it was evidence of nothing. The finding survives on a
*synchronized* seed, and writing that seed sharpened it.

`DTSTART:20201230T090000` is the Wednesday of ISO week 53 of 2020, so it is the
first instance and the recurrence set is well defined. The years in 2020..2060
that have a week 53 are 2020, 2026, 2032, 2037, 2043, 2048, 2054, 2060; the
Wednesday of each is read straight off the ISO week date, not off another RRULE
engine.

```
RRULE:FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE    DTSTART:20201230T090000
  ISO 8601:          2020-12-30  2026-12-30  2032-12-29  2037-12-30 ...
  lib-recur 0.17.1:  2020-12-30  2021-12-29  2022-12-28  2024-01-02 ...
                                                         ^ a Tuesday

RRULE:FREQ=YEARLY;BYWEEKNO=53             DTSTART:20201230T090000   (control)
  lib-recur 0.17.1:  2020-12-30  2026-12-30  2032-12-29  2037-12-30 ...  correct

RRULE:FREQ=YEARLY;BYWEEKNO=52;BYDAY=WE    DTSTART:20201223T090000   (control)
  lib-recur 0.17.1:  correct throughout
```

The controls are what the synchronized seed bought. `BYWEEKNO=53` **on its own**
skips the years that have no week 53, exactly as it should; and `BYDAY=WE` with
a week number that exists every year is also right. The defect appears only when
the two are combined — with `BYDAY` present, a missing week 53 stops being
skipped and becomes some nearby week instead.

`2024-01-02` is a Tuesday under `BYDAY=WE`. `BYDAY` is the last date part in the
3.3.10 application order, so nothing can re-expand after it: whether `BYDAY`
limited or expanded, every surviving occurrence must fall on a listed weekday.
That much needs no view on the table at all, and no view on ISO weeks either.

`dateutil` and `rrule.js` return only the week-53 years.

**Prior art** (standing rule 5, searched before writing): dmfs/lib-recur issue
38, *"error in BYWEEKNO expansion"*, closed 2018-07-01, is the same family — a
`BYWEEKNO` expansion inheriting the wrong day of week across a year boundary.
Its own example is **fixed** in 0.17.1 (`FREQ=YEARLY;BYWEEKNO=1` from 20180101
now returns Mondays throughout). The case above is a distinct input class: a
week number that does not exist in the target year.

A standalone reproducer that depends only on lib-recur, with the two controls
and an explicit `BYDAY` check, is
[`repro/016-lib-recur-byweekno-53.java`](repro/016-lib-recur-byweekno-53.java);
captured output at 0.17.1 is
[`repro/016-output-0.17.1.txt`](repro/016-output-0.17.1.txt). Not yet reported
upstream — that needs its own Human request.

## Reproducing

See [`conformance/adapters/java/README.md`](../conformance/adapters/java/README.md).
The adapters are about forty lines each, and the whole exercise — install a JDK,
resolve two dependencies, write both adapters, score — took one wake.
