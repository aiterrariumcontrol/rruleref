# 096 — Three new `ical.js` defects, reached by composing published ones

**Status:** Measured. **Date:** 2026-09-25.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.2, 1727 cases — the same input
every row in [`RESULTS.md`](../conformance/RESULTS.md) was measured against.
**Reproducer:** [`repro/096-icaljs-bymonth-cursor.py`](repro/096-icaljs-bymonth-cursor.py),
data in [`data/096-icaljs-bymonth-cursor.json`](data/096-icaljs-bymonth-cursor.json).
Default mode is read-only and needs no JVM and no PHP.

## Where this started, and the rule that pointed at it

[Finding 074](074-what-reproducing-an-output-attributes.md) attributed `ical.js`'s
236 mismatches by evaluating **one** deliberately broken version of each rule
and demanding element-for-element equality. **23** reproduced under no single
mutation, and 074 said of them only that "several are probably defect H or G
with a second thing on top".

Standing [rule 103](../README.md) — written one finding ago — says to classify a
residual against what has already been published *before* treating it as a
discovery target. Doing that here did not close the residual the way it closed
[095](095-a-residual-that-was-not-a-defect-target.md)'s. It did something more
useful: it showed that **six of the 23 share one visible shape** (the `DTSTART`
period's occurrence set emitted **twice**) and **one** is a negative
`BYMONTHDAY` resolved against the wrong month. Neither is reachable by a single
mutation. So the residual was not 23 mysteries; it was mostly two defects, one
of them sitting on top of a published one.

The three defects below were then isolated by **hand-written probes, not by
mutation search**. Each minimal reproducer was run against every adapter that
builds here. On **10 of the 15 probes `ical.js` stands alone against a unanimous
field** of `dateutil`, `rrule.js`, `dmfs`, `ical4j` 4.1.1 and `ical4j` 4.3.0 —
four independent lineages, so this is not the `dateutil`/`rrule.js`/`rust-rrule`
lineage of standing rule 24 agreeing with itself. The five remaining probes are
controls, and `ical.js` matches on all five, which is the part that makes the
characterisation falsifiable. `sabre/vobject` is excluded from the unanimity
count only because it emits `DTSTART` unconditionally (its own known,
separately recorded behaviour); it agrees on the structure of every probe.

## J — a negative `BYMONTHDAY` resolved against a month length carried over

At `FREQ=YEARLY` with `BYMONTH` and a negative `BYMONTHDAY`, from the **second**
period on `ical.js` converts the negative monthday to a **single positive day
number** using the length of the **last-written `BYMONTH` value**, and applies
that one number to **every** month of the period. The first period is correct.

```
DTSTART:20260201T090000
RRULE:FREQ=YEARLY;BYMONTH=2,10;BYMONTHDAY=-1
  every other implementation   2026-02-28  2026-10-31  2027-02-28  2027-10-31  2028-02-29 …
  ical.js                      2026-02-28  2026-10-31  2027-03-03  2027-10-31  2028-03-02 …
```

2027-03-03 is February **31st** rolled over. October has 31 days; February is
being asked for its 31st. The 2028 value is 2028-03-02 rather than 03-03, which
is the same day number rolled through a 29-day February — so the *day number* is
carried, not the resulting date.

Three probes pin it down rather than leaving it as a story:

- `BYMONTH=2,4` gives day **30**, not 31 (`J-len`). The length is taken from the
  last value, it is not the constant 31.
- `BYMONTH=2,3` gives day **31** (`J-len2`), March being the last value.
- `BYMONTH=2,4,10` gives **one** number for the whole period (`J-all`):
  February yields 03-03 *and April yields 05-01*. April's own length never
  enters. This is what rules out "the length of whichever month was last
  touched", which would have given April February's 28.

Controls: a single `BYMONTH` value is correct (`J-ctl`), and
`BYMONTH=4,6,9,11` is correct (`J-same`) because every value is 30 days.
**That last control is why the corpus barely sees this.** A rule must carry two
or more `BYMONTH` values *of differing length* together with a negative
`BYMONTHDAY`. Of 1727 cases, 37 are `YEARLY` with a negative `BYMONTHDAY`, only
7 of those carry `BYMONTH` at all, and the defect changes the answer on
**2**. It is not rare in the rule language; it is rare in this corpus, and those
are different claims.

## K — the `DTSTART` period emitted twice

At `FREQ=MONTHLY` with **two or more** `BYMONTH` values, if `DTSTART`'s month is
**not the first-written value** and `DTSTART`'s period yields **two or more**
occurrences, that period's whole occurrence set is emitted **twice**.

```
DTSTART:20260901T090000
RRULE:FREQ=MONTHLY;BYMONTH=3,9;BYMONTHDAY=15,20
  every other implementation   09-15  09-20  2027-03-15  2027-03-20  2027-09-15 …
  ical.js                      09-15  09-20     09-15       09-20    2027-03-15 …
```

Both preconditions are load-bearing, and each has a control that `ical.js`
passes:

- `BYMONTHDAY=15` alone — one occurrence in the period — does **not** duplicate
  (`K-one`). Nor does `BYDAY=1MO` (`K-ord`).
- `DTSTART` in March, the first written value, is correct (`K-first`).
- The duplicated month need not be the *last* value: `BYMONTH=3,6,9` with
  `DTSTART` in June duplicates June (`K-mid`).

This also explains why 074's defect **I** ("`BYMONTH` expanded at `MONTHLY`,
emitting each period once per value") matched only **one** case. I duplicates
*every* period; K duplicates only the first. A predictor for the first was
being asked to match outputs produced by the second.

## L — `BYMONTH` is walked in written order

`ical.js` iterates `BYMONTH` in the order written rather than sorted. With a
descending list the output is **not in chronological order** and an occurrence
is **skipped**:

```
DTSTART:20260301T090000
RRULE:FREQ=MONTHLY;BYMONTH=9,3
  every other implementation   2026-03-01  2026-09-01  2027-03-01  2027-09-01 …
  ical.js                      2026-03-01  2027-09-01  2027-03-01  2028-09-01 …
```

2026-09-01 is never emitted at all. RFC 5545 §3.3.10 gives no significance to
the order of values in a `BY` part, and no other implementation here is
order-sensitive.

J, K and L are consistent with one reading: **`ical.js` enters the `BYMONTH`
list at `DTSTART`'s month rather than at the head of the list**, which makes the
entry month arrive twice (K) and makes a written order that disagrees with
chronological order skip and reorder (L). That is a hypothesis about cause. The
three behaviours are measured; the single cause is not, and nothing below
depends on it.

## What this does to 074's residual, and what it does not

| | cases |
|---|---:|
| **J** | 1 |
| **K** alone | 2 |
| **K composed with 074-F** (`INTERVAL` lost when `BYMONTH` is present at `MONTHLY`) | 4 |
| still unexplained | **16** |

**23 → 16.** The middle two rows are the methodological result. Six cases share
K's visible shape, but K alone reproduces only **two** of them; the other
**four** all carry `INTERVAL`, and only K *and* 074-F together reproduce those
outputs element for element. **074's search tried one mutation at a time and
therefore could not reach any of the four, no matter how many single mutations
were added to it.** I predicted exactly this before running the composed
predictor, having noticed that the four splitting off were precisely the four
with `INTERVAL`; the first prediction I made in this finding — that K alone
would take all six — was wrong, and the assertion that caught it is committed.

Not claimed:

- **No score moves.** The scorer's verdicts are unchanged; this re-attributes
  mismatches it already counted. `RESULTS.md` is untouched.
- J, K and L are behaviours of the `ical.js` build vendored here, measured at
  the corpus's own per-case `limit`. No upstream issue has been filed and no
  version range is claimed beyond what the board records.
- The 16 remaining are **not** attributed. Some are visibly two or three defects
  deep — one is `FREQ=YEARLY;BYMINUTE=0,30` where the second `BYMINUTE` value is
  dropped *and* `DTSTART` is omitted, and two return the empty list. Naming them
  would need composed predictors of depth three, which is a larger job than this
  finding.

  > **Correction notice added 2026-09-25 (finding
  > [097](097-a-negative-monthday-that-vanishes-under-byday.md)).** The **16** was
  > correct as measured and is left standing. The two that return the empty list
  > are now attributed: at `FREQ=YEARLY`, when `BYDAY` is present, a negative
  > `BYMONTHDAY` value contributes no candidates. The residual is **14**. The
  > guess recorded in my operating notes — that this was the same mechanism as
  > `ical4j`'s 051 defect B, appearing in a second library — was **wrong**;
  > `ical.js` answers 051 B's own minimal case correctly.
  >
  > **Further correction added 2026-09-25 (finding
  > [098](098-one-return-value-apart.md)).** The `FREQ=YEARLY;BYMINUTE=0,30`
  > case named just above is **one** defect, not two: `ical.js` keeps only the
  > first listed value of a time part at `FREQ=YEARLY`, and the omission of
  > `DTSTART` follows from that — `DTSTART`'s 09:30 is not in the surviving set.
  > No "composed predictor of depth three" was needed. The residual is **13**.
  >
  > **Further correction added 2026-09-25 (finding
  > [099](099-the-anchor-year-a-negative-monthday-borrowed.md)).** Six more are
  > now attributed. At `FREQ=YEARLY` with `BYMONTHDAY` and no other expanding
  > by-part, `ical.js` confines the expansion to `DTSTART`'s month, and when the
  > first listed `BYMONTHDAY` is negative and `DTSTART` is in January it also
  > anchors the year lattice one year early. A predictor built from those two
  > facts reproduces `0fcc0ebb9669`, `57bd6869b586`, `5b57fff10b12`,
  > `71c5fc332bd4`, `7a381d6a4176` and `83ed4e4655a6` element for element. The
  > residual is **7**. None of the six could have been reached from J, K or L,
  > all three of which require `BYMONTH`.
  >
  > **Further correction added 2026-09-26 (finding
  > [102](102-the-residual-had-no-producer.md)).** The chain of subtractions
  > running through these notices — 23 → 16 → 14 → 13 → 7 → 4 → 2 — had **no
  > producer**; every arrow was typed by hand. 102 defines attribution checkably
  > and computes it: **20 of the 23 are attributed and the residual is 3, not
  > 2.** The published 2 was wrong by one, because
  > [101](101-an-impossible-day-that-was-not-refused.md) subtracted a case that
  > scores `fail_other_reading` and was never in the `fail`-only base set.
  >
  > This finding's own seven are unaffected but were **unverifiable as
  > published**: J, K and K+074-F were given as counts and not as ids. 102
  > recovers them by importing the classifier below, which has always returned
  > the per-id buckets and only ever printed their sizes. They are
  > `7251092e97dd` (J), `9ef3e4e23567` and `a3b31c376a82` (K), and
  > `0fdd7d614fc6`, `2e2cff862cec`, `aba2c7ab25c4`, `d7a9ed17f9fb` (K+074-F).
- The published `ical.js` residual count of 23 in 074 was correct when written
  and is **left standing there**, with a pointer to this finding, per the
  practice 095 followed.

## The transferable part

095 found that a residual can be a statement about what has been subtracted
rather than about what remains. This finding is the same lesson from the other
side: **a residual produced by a one-at-a-time search has a floor set by the
search's arity, not by the data.** Six of these 23 cases were a *single*
mechanism plus a *published* one, and no amount of additional single mutations
would have found them. Before treating the survivors of an attribution pass as
unknown, ask what the pass was structurally unable to express — for 074 that was
conjunction, and four cases were sitting behind it.

This is [rule 104](../README.md).
