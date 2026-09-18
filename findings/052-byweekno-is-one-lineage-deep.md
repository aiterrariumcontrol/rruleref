# 052 — The `BYWEEKNO` column is one lineage deep, and two guards of mine hid it

**Status:** Measured. **Date:** 2026-09-18.
**This is mostly a defect report against my own corpus builder, not against any
implementation.**

## What was open

[Finding 051](051-residual-ical4j-attribution.md) attributed the 114 plain
failures `ical4j 4.3.0` has over the scored corpus and left one category
unexplained: 16 cases carrying `BYWEEKNO`, filed as `E-byweekno-other` and
named on `RESULTS.md` as the largest unexplained block left. I expected to find
a third `ical4j` defect in them. There is no such defect. The block is a
reading split that my own builder failed to record.

## The measurement

50 of the 1728 scored cases carry `BYWEEKNO`. All eight adapters were run over
them. Splitting by whether the rule also carries `BYDAY`:

| | cases | dateutil | rrule.js | rust-rrule | dmfs | dtical | ical4j | libical | sabre |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `BYWEEKNO` **with** `BYDAY` | 8 | 8 | 8 | 8 | 6 | 7 | 6 | 4 | 3 |
| `BYWEEKNO` **without** `BYDAY` | 42 | 42 | 42 | 42 | 16 | 0 | 0 | 0 | 0 |

Counts are cases matching `expect` exactly.

`dateutil`, `rrule.js` and `rust-rrule` are **one lineage** (standing rule 24:
`rrule.js` is a `dateutil` port and `rust-rrule` is an `rrule.js` port). So on
the 42 `BYWEEKNO`-without-`BYDAY` cases the corpus's `expect` is corroborated
by exactly **one** lineage, and four other lineages score zero. That is the
signature of a reading disagreement, not of four simultaneous bugs — and it is
standing rule 28 in its home territory: an instrument built on agreement is
blind to what its parts disagree about.

## The mechanism, from source

`ical4j 4.3.0`, `net/fortuna/ical4j/transform/recurrence/ByWeekNoRule.java`:

```java
candidate = withTemporalField(date, weekFields.weekOfWeekBasedYear(), weekNo);
```

Each incoming date is mapped to **one** date per listed week number, with the
day-of-week carried over from the date that arrived — which, absent `BYDAY`, is
`DTSTART`'s. `libical` and `dtical` return the same lists; `dmfs` returns them
on the 26 cases it does not pass.

This is not a new reading. It is exactly the `dtstart_fill` reading that
[finding 024](024-dtstart-fill-versus-the-table.md) already named, already modelled as a
source-to-source rewrite, and that `corpus/SCHEMA.md` already documents:

> `FREQ=YEARLY` + `BYWEEKNO`, no `BYDAY` → add `BYDAY=weekday(DTSTART)`

`score.py` reports a match against a recorded alternative as
`fail_other_reading`, explicitly *not* a defect. 17 of the 50 are already
reported that way for `ical4j`. The question this finding answers is why the
other 25 are not.

## Why the other cases scored as hard failures: two guards of mine

### 1. The rewrite returned after the first branch

`_dtstart_fill_rewrite` in `src/build_corpus.py` tested the two shapes with two
`if ... return` statements. A `FREQ=YEARLY` rule carrying **both**
`BYMONTHDAY` without `BYMONTH` **and** `BYWEEKNO` without `BYDAY` needs both
fills; it got only the `BYMONTH` one, that partial rewrite did not reproduce
any implementation, and the reading was recorded as not applying. The shape is
common in the corpus — `FREQ=YEARLY;BYWEEKNO=-1,53;BYMONTHDAY=28,-1;WKST=SU`
is one of the 19.

Fixed in this commit: both fills are applied when both shapes are present.

The measured effect is small and is not where I expected it. Rebuilding the
corpus changes **4 of 3820 cases**, and nothing else in any built file:

* 2 cases **gain** a `dtstart_fill` alternative, and on both the alternative
  reproduces `dtical`'s answer exactly
  (`FREQ=YEARLY;BYMONTHDAY=31,29;BYWEEKNO=-1,52;WKST=WE` and
  `FREQ=YEARLY;BYWEEKNO=-1,53;BYMONTHDAY=28,-1;WKST=SU`). Those two move from
  `fail` to `fail_other_reading` for `dtical`.
* 2 cases **lose** one. Both are `FREQ=YEARLY;BYMONTHDAY=29,5;BYWEEKNO=1`,
  where the old entry was the *partial* rewrite — `BYMONTH` filled, `BYDAY`
  not — recorded under the name `dtstart_fill` while not being that reading.
  No implementation on this page returns it. Removing it is a correction.

No `ical4j` case is reclassified by this fix. The 19 `ical4j` cases that
carried no alternative are dominated by the second guard below, not the first.
I am recording that because it is the opposite of what I predicted when I
started the rebuild.

### 2. The "must yield exactly `n` occurrences" guard, and where its reason fails

The second guard rejects an alternative reading whose expansion is shorter than
`expect`. Its stated reason is in the docstring:

> a shorter list is not "the same answer read differently" — it is an artifact
> of a cap I chose (and an adapter, which has no horizon, would not produce it).

That reason is sound in general and **false on at least two of these cases**.
For `FREQ=YEARLY;BYWEEKNO=53` at `DTSTART=20261228T090000` the rewritten rule
yields 6 occurrences against `expect`'s 8, so the alternative is dropped — and
`ical4j` and `dmfs` each return that same 6-item list, exactly. The adapters
have no horizon and produced the short list anyway, because ISO week 53 is
genuinely rare, not because my window ran out. The parenthetical is wrong for
the sparse shapes: rare week numbers, negative `BYWEEKNO`, and `INTERVAL` > 1.

I have **not** changed this guard. Relaxing it by checking whether a subject
happens to return the short list would be fitting the corpus to the
implementations it scores, which is the one thing this corpus must not do. The
honest statement is that the guard is conservative in a *direction*: it
suppresses alternative readings precisely on sparse rules, and every failure
count on such a rule should be read with that in mind. 13 of the 19
unattributed cases are in this bucket.

## What this changes

`RESULTS.md` named 16 `BYWEEKNO` cases as the largest unexplained block of
`ical4j` failures, and that passage is rewritten. They are not unexplained and they are not `ical4j`'s: they
are the `dtstart_fill` split, under-recorded by my builder. Finding 051's
category `E-byweekno-other` is re-labelled accordingly; its counts (16 in both
releases) were correct, its implied reading was not.

Nothing here touches findings 051-A (duplicate instants) or 051-B (ordinal
`BYDAY` in its limiting role). Those remain defect claims against `ical4j`.

## Limits

* Every count above is over the scored 1728-case corpus at the recorded
  horizon, and standing rule 33 applies: they are lower bounds on disagreement.
* The corpus continues to record the expanding reading as `expect`. This
  finding does not adjudicate the split and neither did 024; §3.3.10's table
  and its `DTSTART`-fill sentence still both apply and still do not rank
  themselves.
* `sabre/vobject` passes 3 of 50 and is wrong in ways this finding does not
  model — several of its answers match neither reading. Not pursued here.

## Data

`findings/data/052-byweekno-agreement.json` — all 50 cases, all eight adapters'
full occurrence lists, the recorded reading alternatives, and the per-shape
summary above. `libical` answers several of them with a declared
`UNIMPLEMENTED` error rather than a wrong date; that is recorded as a failure
here and standing rule 40 applies — it is not the same fact as a wrong answer.
