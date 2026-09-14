# 036 — a conformance score that depends on the host machine's locale

*2026-09-13.*

## Why this was asked

The open item was narrower: `ical4j` 4.1.1 on
`FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52` emits dates **in May, with
duplicates**, while `BYMONTH=1,8` is set ([finding
033](033-the-last-five-disputes-are-two-questions.md)). It was the last
uncharacterised entry on the list.

Characterising it turned up something larger and much more ordinary, which is
what this finding is mostly about: for an entire class of common rules,
`ical4j` returns **different occurrences on different machines**, and nothing
in the rule, the `DTSTART`, or the library version selects which. The JVM's
default locale does.

## The claim

When an `RRULE` omits `WKST`, `ical4j` does not apply RFC 5545's stated default
of `MO`. It takes the first day of the week from `Locale.getDefault()`.

RFC 5545 §3.3.10:

> `wkst` … This is also significant when in a `YEARLY` "RRULE" when a `BYWEEKNO`
> rule part is specified. The default value is `MO`.

The library knows this in one place and not the other.
`ByWeekNoRule`'s constructor maps a null first-day-of-week to
`WeekFields.of(DayOfWeek.MONDAY, 4)` and cites the sentence above in a comment.
`ByDayRule`'s two constructors, for the same null, fall through to
`WeekFields.of(Locale.getDefault())`.

```java
// net/fortuna/ical4j/transform/recurrence/ByDayRule.java
public ByDayRule(List<WeekDay> dayList, Frequency frequency, DayOfWeek firstDayOfWeek) {
    super(frequency);
    this.dayList = dayList;
    if (firstDayOfWeek != null) {
        weekFields = WeekFields.of(firstDayOfWeek, 1);
    } else {
        weekFields = WeekFields.of(Locale.getDefault());   // <-- RFC 5545 says MO
    }
}
```

`Recur.getCandidates` passes `WeekDay.getDayOfWeek(weekStartDay)` into that
constructor, and `weekStartDay` is **null** whenever the rule carries no
`WKST` — so the fallback is not an edge case, it is the default path. The
`WeeklyExpansionFilter` then snaps each date to a weekday *within the week as
that locale draws it*, and a locale whose week starts on Sunday draws a
different week from one whose week starts on Monday.

## Measurement

The whole conformance subset — 1721 cases — run through the same `ical4j`
4.1.1 build three times, changing only `-Duser.language`/`-Duser.country`:

| JVM locale | first day of week | pass | fail | `fail_other_reading` |
| --- | --- | ---: | ---: | ---: |
| `ar`-`EG` | Saturday | 1456 | 207 | 58 |
| `en`-`US` | Sunday | **1468** | **195** | 58 |
| `en`-`GB` | Monday | **1487** | **176** | 58 |

The `en`-`US` row is the number published in
[`conformance/RESULTS.md`](../conformance/RESULTS.md). It is not a property of
`ical4j`. It is a property of this container.

**19 net (20 cases gained, 1 lost)** of `ical4j`'s 195 recorded mismatches
disappear when the host's week starts on Monday, which is what the RFC's
default asks for.

### The 20 cases

Every one of them has `FREQ=WEEKLY` or `BYWEEKNO`, has **no `WKST`**, and has
`SU` in `BYDAY` — Sunday being exactly the day that changes weeks when the week
boundary moves. Examples:

```
FREQ=WEEKLY;INTERVAL=2;BYDAY=SA,SU,TU        DTSTART:20240302T090000
FREQ=WEEKLY;INTERVAL=4;BYDAY=SU,TU           DTSTART:20260104T090000
FREQ=WEEKLY;BYDAY=SU,TH;BYMONTH=3            DTSTART:20270304T090000
FREQ=YEARLY;BYDAY=MO,SU;BYWEEKNO=-2          DTSTART:20261221T090000
```

Appending `;WKST=MO` — which changes nothing about the rule's meaning, since
`MO` is the stated default — fixes **20 of 20** on the `en`-`US` JVM. The
control, the same 20 cases left unchanged on the same JVM, is **0 of 20**.

### Three independent lineages agree with the Monday answer

For `FREQ=WEEKLY;INTERVAL=2;BYDAY=SU,TU`, `DTSTART:20260107T090000`:

| source | first six occurrences |
| --- | --- |
| `python-dateutil` | 20260111, 20260120, 20260125, 20260203, 20260208, 20260217 |
| `dmfs lib-recur` | 20260111, 20260120, 20260125, 20260203, 20260208, 20260217 |
| `libical` master | 20260111, 20260120, 20260125, 20260203, 20260208, 20260217 |
| `ical4j`, Monday-first host | 20260111, 20260120, 20260125, 20260203, 20260208, 20260217 |
| `ical4j`, Sunday-first host | **20260118**, 20260120, **20260201**, 20260203, **20260215**, 20260217 |

Three lineages, one of them `ical4j`'s own answer under a Monday-first locale,
against `ical4j` under `en`-`US`. This is a biweekly Sunday-and-Tuesday
meeting. It is not an exotic rule.

### The locale bug also *hides* one

One case fails on the Monday-first host and passes on `en`-`US`:

```
FREQ=WEEKLY;BYDAY=MO,SU;BYMONTH=4   DTSTART:20270404T090000
expect          … 20270418, 20270419, 20270425, 20270426
Monday-first    … 20270418, 20270419, 20270425, 20280327
Sunday-first    … 20270418, 20270419, 20270425, 20270426   (matches)
```

With the correct default the last April Monday is dropped and the expansion
jumps to the next year. That is a **second, separate defect** in the
`BYMONTH`-limited weekly expansion, and the Sunday-first week boundary happened
to mask it. Appending `;WKST=MO` on the `en`-`US` host reproduces the drop, so
the mask is the locale and not the host. This one is **not** characterised
here.

> **Update, 2026-09-14.** It is now, in
> [finding 037](037-a-limit-that-runs-before-the-thing-it-limits.md), and it is
> not one case. At `FREQ=WEEKLY`, `ical4j` applies the `BYMONTH` limit to the
> period seed and then expands `BYDAY` across the whole `WKST` week, so the
> result can contain dates in months `BYMONTH` excludes. 18 of the 176 failures
> on the Monday-first row are this defect, and it reaches a further 42
> corroborated cases whose `DTSTART` is unsynchronized — where, as here,
> §3.8.5.3 declines to define the answer.

## Back to the `BYMONTH`+`BYWEEKNO` case

The original question also has an answer, and it is a different defect again.
`Recur.getCandidates` at `FREQ=YEARLY` with `BYWEEKNO` present runs:

1. the period seed advances in **week-based years**, not calendar years
   (`Recur.validateFrequency`), so the seed for period *k* is `DTSTART` with its
   ISO week-based year incremented by *k* — for `DTSTART:20280101` (a Saturday
   in week 52 of week-based year 2027) the seeds are 20280101, 20281230,
   20291229, 20301228, …;
2. `ByMonthRule` **expands** the seed to one date per `BYMONTH` value by
   setting `MONTH_OF_YEAR` and keeping the day-of-month — which moves the date
   to a different weekday and often a different week-based year;
3. `ByWeekNoRule` sets `weekOfWeekBasedYear`, which in `java.time` is
   implemented as *add (n − current) weeks*. Nothing about the month survives
   this. `BYMONTH` has already done all the work it is going to do;
4. the implicit `ByDayRule(rootSeed, …)` — the one in the fallthrough branch —
   snaps each date to `DTSTART`'s weekday within its week, using the locale.

So `BYMONTH` at `FREQ=YEARLY;BYWEEKNO=…` is not a month filter and not really
an expansion either: it is a **perturbation of the seed's weekday and
day-of-month**, and the months in the output are decided entirely by the week
numbers. Hence May.

The duplicates follow from step 4. Two candidates that differ only in weekday —
because they came from different `BYMONTH` values — are snapped onto the *same*
weekday in the *same* week, and `getCandidates` sorts but never de-duplicates:

```
FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52   DTSTART:20280101T090000   limit 6

Saturday-first host  20280101, 20280513, 20280513, 20280520, 20281223, 20281223
Sunday-first host    20280101, 20280520, 20280520, 20280527, 20281230, 20281230
Monday-first host    20280101, 20280520, 20280520, 20280520, 20281230, 20281230
```

Three hosts, three calendars, one rule. The corpus records no expected value
for this shape — `dmfs` errors on it and `libical` reports `UNIMPLEMENTED` —
so it costs `ical4j` nothing in the score. It is here because it is the same
mechanism.

## Prior art

The locale dependence has been **seen before and closed without a library
change.** `ical4j` issues
[#727](https://github.com/ical4j/ical4j/issues/727) and
[#730](https://github.com/ical4j/ical4j/issues/730), both filed by `raboof` in
September 2024, report ical4j's *own tests* failing under `en_DK.UTF-8`. The
diagnosis in the thread is correct and names this exact line:

> when `firstDayOfWeek` is not specified, the current implementation takes the
> default from the Locale — but section 3.3.10 of RFC5545 (`The default value
> is MO.`) seems to suggest that should be `WeekFields.of(MONDAY, 4)`

\#727 was closed on the grounds that its test case, `FREQ=WEEKLY;INTERVAL=2;BYDAY=SU`
with `DTSTART:20110101` (a Saturday), is **not synchronized** with the rule, so
RFC 5545 §3.8.5.3 makes its recurrence set undefined:

> The recurrence set generated with a "DTSTART" property value not synchronized
> with the recurrence rule is undefined.

That reasoning is sound for that test. **It does not cover these 20 cases.** In
all 20, `DTSTART` *is* the first expected occurrence — the rule and the
`DTSTART` are synchronized, §3.8.5.3 does not apply, and the recurrence set is
defined. The escape used to close #727 is unavailable here.

The code is unchanged in **4.3.0**, the current release as of 2026-09-13:
`ByDayRule`'s constructors are byte-for-byte the same, and 4.3.0 reproduces the
`en`-`US` / `en`-`GB` split on the probe above.

## What this changes

- **For anyone using `ical4j`:** put `WKST=MO` in every `RRULE` that has
  `BYDAY` or `BYWEEKNO` and does not already set it, or set the JVM default
  locale explicitly. Without one of those, the recurrence set your server
  computes is a function of the machine it runs on.
- **For a maintainer:** the fix is the one #730 already names — in both
  `ByDayRule` constructors, replace `WeekFields.of(Locale.getDefault())` with
  `WeekFields.of(DayOfWeek.MONDAY, 1)`, matching what `ByWeekNoRule` already
  does for the same null. Measured effect on this corpus: 195 failures → 176.
- **For this corpus:** the published `ical4j` score was never a property of
  `ical4j` alone. [`conformance/RESULTS.md`](../conformance/RESULTS.md) now says
  which locale it was measured under. Any implementation that reads ambient
  machine state can do this, and nothing in the harness was watching for it.
- The general lesson, which is not about `ical4j`: **a conformance score is a
  measurement of an implementation *and its environment*.** Rule 4 of my own
  notes says a cap or timeout I set is not a property of what I am measuring.
  This is the same error from the other side — a default I did *not* set, and
  did not know I had inherited.

## Reproduce

`findings/repro/036-ical4j-locale-wkst.java` needs only `ical4j` and `slf4j-api`
on the classpath, nothing from this repository, and exits non-zero if any of its
claims stops holding:

```sh
java -cp "conformance/adapters/java/libs/*" findings/repro/036-ical4j-locale-wkst.java
```

The per-locale case lists are in
[`findings/data/036-locale-scores.json`](data/036-locale-scores.json). The score
table above:

```sh
CP='conformance/adapters/java/classes:conformance/adapters/java/libs/*'
for L in "en US" "en GB" "ar EG"; do set -- $L
  python3 conformance/score.py --json /tmp/ical4j-$1$2.json -- \
    java -Duser.language=$1 -Duser.country=$2 -cp "$CP" Ical4jAdapter
done
```

---

*2026-09-14.* [Finding 038](038-checking-the-instrument-for-what-it-measured.md)
swept all eight adapters for the general shape of this defect. `ical4j` is the
only implementation that moves, and it moves exactly as described above; the
sweep's other catch was in this repository's own `dmfs` adapter. The check is
now `conformance/ambient_sweep.py`.
