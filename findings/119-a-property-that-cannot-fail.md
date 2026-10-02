# 119 — a property that cannot fail, and the two reasons a column was zero

*2026-10-02.* Evidence: `findings/repro/119-why-ical4j-passes-p6.py` (~25 s;
`--no-adapters` runs section B alone, pure Python, no build needed). Data:
`findings/data/properties-adapters.json`, unchanged — nothing here re-measures
the sweep, it explains one of its columns.

[Finding 118](118-the-properties-against-the-other-builds.md) ran the eight
metamorphic properties of
[finding 014](014-metamorphic-properties.md) against eight builds and closed
with one thing left open. P6 — *dropping a part the RFC's table marks Limit
cannot lose occurrences* — failed 13 times on `python-dateutil`, `dmfs
lib-recur`, `libical` master and `rust-rrule`, 17 on `rrule.js`, 18 on
`ical.js`, and **zero** times on `ical4j` and `sabre/vobject`. Rule 131 says a
property is passed by an implementation that ignores the part the property
varies, so the obvious reading of a zero is vacuity. 118 could not take that
reading for `ical4j`, because `ical4j` plainly does respond to `WKST`
(it reproduces P5's 23 and adds 57 of its own), and left the question as a lead.

The lead was mis-aimed. P6 does not vary `WKST`; it varies a Limit part. The
right question was never asked, and when it is asked the answer is not
vacuity, not for `ical4j`.

## The shape of all 13

All 13 of P6's failures are one shape: `FREQ=WEEKLY` with `BYMONTH`, `BYDAY`
and `BYSETPOS`, the dropped part being `BYMONTH`. That is exactly the territory
of [finding 022](022-weekly-bymonth-ordering.md), which names two readings of
RFC 5545 §3.3.10 for it:

* **filter-instances** — `BYMONTH` restricts the instants the week finally
  yields.
* **seed-limit** — `BYMONTH` is applied to the week's single `DTSTART`-derived
  seed, and `BYDAY` then expands the whole week, *including into months
  `BYMONTH` does not select*.

## A. the zeros have two different causes

```
== A. is the P6 witness's BYSETPOS inert?  (limit 12)
   FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU[;BYSETPOS=-1]  DTSTART:20270101T090000
   dateutil   with BYSETPOS 20270101 20270108 20270115 20270122 20270129
              without       20270101 20270104 20270108 20270111 20270115  -> not inert
   ical4j     with BYSETPOS 20270101 20270108 20270115 20270122 20270129
              without       20270101 20270104 20270108 20270111 20270115  -> not inert
   sabre      with BYSETPOS 20270101 20270104 20270108 20270111 20270115
              without       20270101 20270104 20270108 20270111 20270115  -> INERT, BYSETPOS changes nothing
```

`sabre` is inert: it returns the same list with and without `BYSETPOS`, so its
zero is rule 131's vacuity and carries no information. `ical4j` is **not**
inert — it returns `dateutil`'s answer on both members of the pair. So its zero
needs a different explanation, and it has one.

## B. P6 cannot fail under the seed-limit reading

Both readings of 022, generalised here to arbitrary `WKST` and `INTERVAL`, run
against P6's own relation on all 13 witnesses under 118's own bounds:

```
== B. P6's relation under 022's two readings, on all 13 witnesses
   horizon 1095 days, cap 3000 -- finding 118's bounds
   RRULE                                                      DTSTART          filter-i.  seed-limit
   FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU;BYSETPOS=-1    20270101T090000  LOSES 20270628 pass
   FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1            20260102T090000  LOSES 20260102 pass
   FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1            20260705T090000  LOSES 20260705 pass
   FREQ=WEEKLY;BYDAY=MO,TH;BYMONTH=4,11;WKST=SU;BYSETPOS=1    20260402T090000  LOSES 20260402 pass
   FREQ=WEEKLY;BYDAY=MO,TU;BYMONTH=8;BYSETPOS=-1              20260804T090000  LOSES 20260831 pass
   FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=9;BYSETPOS=1               20260902T090000  LOSES 20260902 pass
   FREQ=WEEKLY;BYDAY=TH,TU;BYMONTH=10,11;BYSETPOS=-1          20261001T090000  LOSES 20271130 pass
   FREQ=WEEKLY;BYMONTH=10;BYDAY=SA,SU;BYSETPOS=-1             20261004T090000  LOSES 20261031 pass
   FREQ=WEEKLY;BYMONTH=6,7;BYDAY=FR,SA,TH;BYSETPOS=-2         20240607T090000  LOSES 20260730 pass
   FREQ=WEEKLY;BYMONTH=8;BYDAY=FR,MO,TH;BYSETPOS=1            20260803T090000  LOSES 20280803 pass
   FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU;BYSETPOS=-1              20260802T090000  LOSES 20270831 pass
   FREQ=WEEKLY;BYMONTH=9,11;BYDAY=SA,SU,TU;WKST=WE;BYSETPOS=1 20270904T090000  LOSES 20271102 pass
   FREQ=WEEKLY;INTERVAL=3;BYMONTH=3;BYDAY=SA,SU,TH;BYSETPOS=-1 20270307T090000  LOSES 20290331 pass
   ---
   filter-instances: 13 of 13 fail P6     seed-limit: 0 of 13 fail P6
```

**13 of 13 against 0 of 13.** The mechanism is not statistical. Under
seed-limit, `BYMONTH` never touches the within-week candidate set — it only
decides *which weeks participate*. Deleting it therefore adds weeks and changes
nothing inside a week, so the wider rule's output is a superset by
construction and P6's antecedent can never be violated. Under
filter-instances, deleting `BYMONTH` enlarges the set `BYSETPOS` indexes into,
so `BYSETPOS` can select a different member of it and an occurrence can be
lost.

**So P6's column does not rank these implementations.** Its three kinds of
entry mean three unrelated things:

| entry | what it means |
| --- | --- |
| `sabre` 0 | `BYSETPOS`-inert; the property was never exercised (rule 131) |
| `ical4j` 0 | holds the seed-limit reading, under which P6 is a tautology here |
| `dateutil` 13 | holds filter-instances — the reading this repository uses |

The last row is the uncomfortable one and it is the point: **on this shape, P6's
failures are not defects, and the builds that fail it most are the ones this
project considers right.** P6 is marked `hedged` in 014 precisely because the
set-inclusion reading of the table is mine, and this is what that hedge was
reserving. It should not be read as 13 defects anywhere, and finding 118's
table now says so.

What P6 *is*, on this shape, is a **reading detector**: it separates
filter-instances from seed-limit implementations with no expected values and no
appeal to my corpus. That is a use, just not the one its column looked like.

## C. a predictor for `ical4j`, assembled from two published defects

```
== C. what ical4j actually returns on the 13, against both readings
   `ical4j+036` is seed-limit with WKST defaulting to SU rather than
   RFC 5545's MO -- finding 036's locale-dependent default, which the
   adapter pins to en-US.
   FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU;BYSETPOS=-1    seed-limit + ical4j+036
   FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1            seed-limit + ical4j+036
   FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1            ical4j+036
   FREQ=WEEKLY;BYDAY=MO,TH;BYMONTH=4,11;WKST=SU;BYSETPOS=1    seed-limit + ical4j+036
   FREQ=WEEKLY;BYDAY=MO,TU;BYMONTH=8;BYSETPOS=-1              seed-limit + ical4j+036
   FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=9;BYSETPOS=1               seed-limit + ical4j+036
   FREQ=WEEKLY;BYDAY=TH,TU;BYMONTH=10,11;BYSETPOS=-1          seed-limit + ical4j+036
   FREQ=WEEKLY;BYMONTH=10;BYDAY=SA,SU;BYSETPOS=-1             ical4j+036
   FREQ=WEEKLY;BYMONTH=6,7;BYDAY=FR,SA,TH;BYSETPOS=-2         seed-limit + ical4j+036
   FREQ=WEEKLY;BYMONTH=8;BYDAY=FR,MO,TH;BYSETPOS=1            seed-limit + ical4j+036
   FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU;BYSETPOS=-1              ical4j+036
   FREQ=WEEKLY;BYMONTH=9,11;BYDAY=SA,SU,TU;WKST=WE;BYSETPOS=1 seed-limit + ical4j+036
   FREQ=WEEKLY;INTERVAL=3;BYMONTH=3;BYDAY=SA,SU,TH;BYSETPOS=-1 ical4j+036
   ---
   of 13: filter-instances 0, seed-limit 9, ical4j+036 13, neither 0
```

`ical4j` equals seed-limit on 9 of 13 and **seed-limit with `WKST` defaulting to
`SU` on all 13**. The second half of that is
[finding 036](036-a-score-that-depends-on-the-host-locale.md): when a rule omits
`WKST`, `ical4j` does not apply RFC 5545's stated default of `MO` but takes the
first day of the week from the host locale, and the adapter pins `en-US`, whose
first day is Sunday. The four rules where plain seed-limit misses are exactly
the four whose `BYDAY` contains `SU` with no explicit `WKST` — the only rules on
which the two week partitions differ.

So the whole of `ical4j`'s P6 column is **two already-published behaviours
composed**, 022's reading and 036's locale default, and the composite is exact
on 13 of 13 rather than approximately right. Nothing new is wrong with `ical4j`.
This is the eighth time the habit of grepping `findings/` for the subject before
attributing anything has turned a drafted defect into a citation.

## D. the new code is checked against the published reference

`repro/022-seed-limit-reading.py` implements both readings for `WKST=MO` only.
This script's generalisation must agree with it wherever both are defined:

```
== D. this script's two readings against finding 022's reference
   repro/022-seed-limit-reading.py is WKST=MO only, so only the
   witnesses that omit WKST or say MO can be cross-checked.
   14 rules x 2 readings: identical to the reference
```

## E. the same two readings over 120 generated rules of this shape

```
== E. the two readings over 120 generated rules of this shape (seed 11)
   dateutil   == filter-instances               117 of 120
      FREQ=WEEKLY;BYMONTH=4,11;BYDAY=WE,FR;BYSETPOS=2;WKST=SU  20261113T090000  mine 20261113T090000  dateutil 20261120T090000
      FREQ=WEEKLY;INTERVAL=2;BYMONTH=1,6;BYDAY=FR,MO;BYSETPOS=2;WKST=SU 20270618T090000  mine 20270618T090000  dateutil 20280114T090000
      FREQ=WEEKLY;BYMONTH=1,6;BYDAY=MO,FR;BYSETPOS=2;WKST=SU   20270120T090000  mine 20270122T090000  dateutil 20270129T090000
   ical4j     == seed-limit + WKST default SU   120 of 120
```

`ical4j` is **120 of 120** against the composite predictor, which is what moves
it from a pattern match to a predictor. The filter-instances arm is 117 of 120
against `dateutil`, and the three are not a third reading: all three carry
`BYSETPOS=2`, all three differ **only in the first period**, and they are
[finding 004](004-bysetpos-first-period-truncation.md) — `dateutil` truncates the
first period at `DTSTART` *before* `BYSETPOS` selects, so a two-member week
becomes a one-member week and `BYSETPOS=2` finds nothing; 022's reference, which
this script matches, applies the `DTSTART` cut after the selection. None of the
13 witnesses is affected, and 004 is orthogonal to the reading question.

Running this over generated rules is how the `SU` default was found at all:
plain seed-limit was exact everywhere except on rules containing `SU`, which is
rule 122's signature of an unmodelled stage rather than of a wrong model.

## Not claimed

* **No defect claim against `ical4j` is made or repeated here**, and nothing was
  filed upstream (rule 27). 036 is already written; this page only shows that it
  and 022 together account for a column.
* **Nothing is settled about §3.3.10.** 022 declines to settle the reading
  question and so does this page. The measurement is conditional on each
  reading, which is the only form available.
* **P5 is untouched.** The P5/P6 asymmetry 118 worried about is not a puzzle
  about `WKST` at all: P5 varies `WKST` and P6 varies a Limit part, and 118's
  argument that `ical4j`'s `WKST` sensitivity bears on its P6 column was simply
  a non-sequitur. It is withdrawn.
* **No score moved.** `conformance/RESULTS.md` is untouched, `cases_id`
  unchanged, and `findings/data/properties-adapters.json` was not regenerated.
* **The 13 are the `dateutil` row.** `rrule.js`'s 17 and `ical.js`'s 18 include
  the same 13 plus extras already attributed to
  [110](110-three-constructs-that-do-not-survive-translation.md)'s defect C;
  those extras are not analysed here.

## Reproducing

```sh
python3 findings/repro/119-why-ical4j-passes-p6.py                # ~25 s
python3 findings/repro/119-why-ical4j-passes-p6.py --no-adapters  # section B only
```
