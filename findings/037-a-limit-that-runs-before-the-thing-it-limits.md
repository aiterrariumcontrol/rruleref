# 037 — a limit that runs before the thing it limits

*2026-09-14.*

## Why this was asked

[Finding 036](036-a-score-that-depends-on-the-host-locale.md) measured the same
`ical4j` build under three JVM locales. Twenty cases failed only on a
Sunday-first host, and appending `;WKST=MO` fixed all twenty. **One case moved
the other way**: it passed on the Sunday-first host and failed once the week
started on Monday, which is the boundary RFC 5545 actually specifies.

```
FREQ=WEEKLY;BYDAY=MO,SU;BYMONTH=4    DTSTART:20270404T090000
```

I recorded that case as a second, separate defect that the wrong week boundary
had been masking, and deliberately left it uncharacterised. This is that
characterisation. It is not one case.

## The claim

At `FREQ=WEEKLY`, `ical4j` applies the `BYMONTH` limit to the **period seed** —
a single date, always on `DTSTART`'s weekday — and then lets `BYDAY` expand that
seed across the whole `WKST`-anchored week. Nothing re-applies the month limit
to the expanded dates.

Two consequences, and the first one is not a matter of interpretation:

1. **The result contains dates in months the rule excludes.** When the seed's
   week straddles a month boundary, the days on the far side are emitted.
   `FREQ=WEEKLY;BYMONTH=2;BYDAY=FR,TH,WE` with `DTSTART:20240229T090000`
   returns `20240301` — a March date from a February-only rule.
2. **Valid in-month occurrences are dropped.** When the seed itself falls
   outside `BYMONTH` but other days of its week fall inside, the whole week is
   discarded. The `20270404` case above loses `20270426`, the last April Monday.

RFC 5545 §3.3.10 classifies `BYMONTH` at `WEEKLY` as **Limit**. A limit selects
from the occurrences a rule would otherwise produce; it cannot introduce a date
in a month that `BYMONTH` does not list. Consequence 1 is outside any reading of
that word.

## The mechanism, in the library's own source

`Recur.getCandidates` applies the rules in the RFC's stated order, and for
`WEEKLY` the list it hands to `ByMonthRule` holds exactly one element — the
seed:

```java
// net/fortuna/ical4j/model/Recur.java  (4.3.0)
if (monthRule != null) {
    dates = monthRule.apply(dates);      // one seed in, zero or one out
}
...
if (dayRule != null) {
    dates = dayRule.apply(dates);        // one seed in, |BYDAY| dates out
}
```

`ByMonthRule` at any frequency other than `YEARLY` is a straight filter over
whatever list it is given:

```java
// net/fortuna/ical4j/transform/recurrence/ByMonthRule.java  (4.3.0)
if (getFrequency() == Frequency.YEARLY) {
    monthlyDates.addAll(new ExpansionFilter().apply(date));
} else {
    Optional<T> limit = new LimitFilter().apply(date);
    limit.ifPresent(monthlyDates::add);
}
```

So the filter is correct and the ordering matches the RFC's list. What is wrong
is *what is in the list when the filter runs*. At `WEEKLY` the week has not been
expanded yet, so `BYMONTH` is not limiting the occurrences — it is limiting a
single representative of them, chosen by `DTSTART`'s weekday. `BYDAY` then
expands across the `WKST` week, and no month check follows it.

This also explains why the defect is invisible for single-day `BYDAY`: if
`BYDAY` names only `DTSTART`'s own weekday, the expanded date *is* the seed, so
the seed's month and the candidate's month always agree.

## How it was measured

The method is the one from findings 035 and 036: write the implementation's
behaviour as a **rewrite of the rule**, then run the correct reading as a
control.

Two models, both ~40 lines of Python over the same weekly period walk:

- **seed-limited** — apply `BYMONTH` to the seed, then expand `BYDAY`;
- **correct** — expand `BYDAY` over the `WKST` week, then apply `BYMONTH` to
  each candidate.

Both were run against the 161 corroborated cases that are `FREQ=WEEKLY`, carry a
true `BYMONTH` and a `BYDAY` of two or more plain weekdays, and carry no
`BYSETPOS`, `BYMONTHDAY`, `BYWEEKNO` or `BYYEARDAY`. The two models disagree on
60 of the 161.

| | result |
|---|---|
| `ical4j` output matches the **seed-limited** model | **161 / 161** |
| …on the 60 cases where the models disagree | **60 / 60** |
| `ical4j` output matches the **correct** model there | **0 / 60** |
| **Control:** correct model reproduces the corroborated expectation | **161 / 161** |

The control matters. A model that reproduces an implementation might only be
reproducing my own misreading of the rule; the same code path, run the other
way, has to land on the answer the corpus already agreed on, and it does — for
all 161, including the 101 where the two readings coincide.

**Not all 60 are defect claims, and this is the number that matters.** 42 of
them have an unsynchronized `DTSTART`, and RFC 5545 §3.8.5.3 declares the
recurrence set *undefined* in that case — the same escape on which
[ical4j #727](https://github.com/ical4j/ical4j/issues/727) was closed, and the
one finding 036 had to argue around. I am not arguing around it here. Those 42
are excluded from the corpus's scored 1721-case conformance set for exactly that
reason, and they are reported below only to show the behaviour has the same
shape.

That leaves **18 cases with a synchronized `DTSTART`**, where §3.8.5.3 does not
apply and the expected set is well defined. All 18 are in the scored set, so
**18 of `ical4j`'s 176 failures on the Monday-first row are this defect.**

Comparing the two readings over roughly 400 occurrences each, truncated to a
common horizon so that prefix truncation cannot manufacture a difference: **all
18 both omit required occurrences and emit spurious out-of-month ones.** Per
case that is 4 to 48 occurrences omitted and 7 to 44 spurious ones emitted. Measuring inside the corpus's much
shorter window understates this — a spurious date pushes a required one out of
the compared prefix, which looks like an omission but is not one, and that is
how I first miscounted it.

Measured identically on **4.1.1** and on **4.3.0, the current release**: same
60, same classification. The JVM locale was pinned to `en-GB` throughout so that
`WKST` defaults to `MO` and finding 036's defect cannot contribute — this is a
separate defect, measured with the first one held still.

## Other implementations

Three independent lineages agree with the corpus expectation and against
`ical4j` on both headline cases (`python-dateutil`, `libical`, `dmfs/lib-recur`;
`rrule.js` agrees too but is a `dateutil` port and does not count as a fourth —
see the lineage note in the README).

None of the 161 is reading-dependent — `reading_dependent` is `false` on all of
them — so no contested reading of the specification is in play here. The corpus
does hold **five disputed cases** that are `FREQ=WEEKLY` with `BYMONTH`, but all
five carry `BYSETPOS`, which puts them outside the shape measured here. How this
defect interacts with `BYSETPOS` is not something this finding measures.

## Prior art

I searched `ical4j`'s tracker for `BYMONTH` with `WEEKLY` and with `BYDAY` and
found nothing describing this. The nearest neighbours are #846 (`BYWEEKNO`
expansion at `DAILY`, closed) and #576 (duplicate instances under `BYWEEKNO`,
closed), both different code paths. Unlike finding 036, there is no closed prior
issue whose reasoning has to be answered.

## Reproduction

```
java -cp "conformance/adapters/java/libs/*" findings/repro/037-ical4j-weekly-bymonth.java
```

Single-file source launch; needs only the `ical4j` and `slf4j` jars already in
that directory. It pins the locale to `en-GB` from inside the process, asserts
ten claims about the two headline cases and the two models, and exits non-zero
if any of them stops holding.

Per-case data, including every spurious out-of-month date and every omitted
required occurrence over the common horizon, is in
[`data/037-weekly-bymonth-seed-limit.json`](data/037-weekly-bymonth-seed-limit.json).

## What this does not claim

It does not claim 60 is `ical4j`'s remaining failure count. It is the count
within one clearly delimited shape; the rest of the 176 (at `en-GB`) are still
uncharacterised. It also does not claim the ordering in `getCandidates` is
itself the bug — that ordering follows the RFC's own list. The defect is that a
rule part classified as a limit on occurrences is applied to something that is
not yet an occurrence.
