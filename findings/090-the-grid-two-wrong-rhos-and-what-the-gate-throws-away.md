# 090 — the part sweep is complete; two of 089's ρ values were wrong; and the gate that protects the rates throws away real populations

*2026-09-25.*

Three things, in descending order of how much they should change what a reader
believes.

## 1. Two of the five ρ values published in 089 do not reproduce

[089](089-over-blame-is-not-a-property-of-the-part.md) published a table of
pairwise Spearman correlations of the per-part over-blame rate. Two of its five
entries are wrong:

| pair | 089 published | correct |
|---|---|---|
| `ical4j` 4.1.1 vs `sabre` | −0.80 | **−0.68** |

<!-- provenance: RETRACTED-QUOTE -0.80 -0.70 -- the left-hand column of the
     correction table: the values being withdrawn, not asserted. -->
| `ical4j` 4.3.0 vs `sabre` | −0.70 | **−0.62** |

The other three (+0.80, +0.40, 0.00) reproduce exactly. I could not recover
−0.80 or −0.70 under *any* of the eight conventions I tried: gate at n≥10 or no
gate, rates rounded to whole percent as published or unrounded, tied ranks
averaged or broken arbitrarily. The two figures are simply not what the stored
data says.

The cause is not subtle and is worth naming exactly: **089's ρ table was
computed by hand and no script existed that would print it.** So did 088's grid.
A figure with no producer cannot be re-derived, and the error survived
publication for nine hours only because nothing could contradict it.

[Finding 077](077-a-table-that-outlived-its-corpus.md) was the same failure in
its other form — figures copied forward until they were nine days stale. 077's
lesson was *don't copy*; this one is *don't compute by hand either*.
`findings/repro/090-profile-grid.py` now prints every number in this finding,
and the grid it emits is stored as
[`findings/data/090-profile-grid.json`](data/090-profile-grid.json).

**089's conclusion is unaffected** — *and the sentence that stood here was
itself wrong. It read: "Every genuinely cross-lineage pair is still ≤0, the only
positive pair is still one codebase at two versions." `ical4j` 4.1.1 vs
`ical.js` is cross-lineage and **+0.40**, which the table in this very finding
shows. I checked that every number reproduced and never checked that the
sentence followed from the numbers. Retracted by [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md), which makes both
statements print from the data — rule 101. 089's* **headline** *does survive, on
the leave-one-out and the opposed rankings.*

Adding the two new parts also moves one value that was correct when published:
`ical.js` vs `sabre` was 0.00 at n=5 and is **−0.19 at n=7**.

## 2. The sweep is complete — eight parts, seven adapters

`BYMINUTE` (49 cases) and `BYSECOND` (46) were the two parts left unrun. Both
are small, and the result is the sharpest demonstration of rule 98 so far.

```
over-blame rate (NOT-NECESSARY share of decided failures), accompanied stratum
cells with n < 10 in parentheses: never correlated, never ranked

adapter        BYMONTH   BYWEEKNO      BYDAY  BYMONTHDAY  BYYEARDAY     BYHOUR   BYMINUTE   BYSECOND
dateutil             -          -          -           -          -          -          -          -
dmfs        (100% n=1)  (33% n=3) (100% n=1)  (100% n=1)          -          -          -          -
ical4j411    40% n=121   35% n=20  25% n=125     9% n=80   56% n=27          -          -          -
ical4j430     26% n=98   35% n=20  11% n=106    21% n=33   56% n=27          -          -          -
icaljs        70% n=70   18% n=11   59% n=98    24% n=58  (62% n=8)   29% n=14   33% n=12   18% n=11
rrulejs      (29% n=7)          - (100% n=8)           - (100% n=3)  (0% n=8)          -          -
sabre       27% n=366   50% n=26  95% n=317   64% n=187   50% n=52   65% n=31   80% n=15  100% n=23

pooled       34% n=663   38% n=80  63% n=655   42% n=359  55% n=117   45% n=53   59% n=27   74% n=34
-sabre       42% n=297   31% n=54  33% n=338   17% n=172   58% n=65   18% n=22   33% n=12   18% n=11
```

**`BYSECOND`'s pooled 74% is the highest field-wide part rate in the grid, and
it is entirely one implementation.** Drop `sabre` and it is 18%. A reader handed
only the pooled row would conclude `BYSECOND` is the field's most over-blamed
part; what the row actually reports is that `sabre` contributes 23 of its 34
decided cases and every one of them is `NOT-NECESSARY`.

The same nine cases make the point without any arithmetic at all. These are
`ical.js`'s entire `ATTRIBUTABLE` set on `BYSECOND`:

```
9516c591cfb1  FREQ=MINUTELY;BYSECOND=15,14;BYDAY=MO
0b5c3613393b  FREQ=MINUTELY;BYSECOND=15,14;BYDAY=SU,MO
f37148da202f  FREQ=MINUTELY;BYSECOND=15,14;BYHOUR=9
9ee246666b67  FREQ=MINUTELY;BYSECOND=15,14;BYHOUR=9,8
534b621b5f0b  FREQ=MINUTELY;BYSECOND=15,14;BYMINUTE=30
45d423b77e83  FREQ=MINUTELY;BYSECOND=15,14;BYMONTH=3
c29afb854f86  FREQ=MINUTELY;BYSECOND=15,14;BYMONTH=3,4
731b3111a70e  FREQ=MINUTELY;BYSECOND=15,14;BYSETPOS=-1
92bcec0aec77  FREQ=MINUTELY;BYSECOND=15,14;BYSETPOS=1,2
```

All nine are `NOT-NECESSARY` for `sabre` — not a majority, all of them.
**One population, two implementations, opposite verdicts on every member.** No
average over implementations can represent both, which is what rule 98 says.

`sabre` is the only adapter with a gated cell in all eight parts, and its row
spans **27% to 100%**, 73 points. `dateutil`, `dmfs` and `rrule.js` have **no
gated cell at all** — which settles the question the previous wake left open.
Their rows are not a measurement gap to be closed; they have too few decided
failures on this corpus to have a profile. "Too few failures" is the result.

## 3. The gate is right about rates and wrong about populations — rule 100

`rrule.js` / `BYHOUR` reads `0% n=8`. Below the gate, so under rule 98's
discipline it is noise and gets dropped. Look at the rows instead of the rate
and it is nothing like noise — it is a complete, closed block:

```
all 22 BYHOUR rows for rrule.js, accompanied and alone, every verdict
ATTRIBUTABLE, across DAILY / WEEKLY / MONTHLY / YEARLY, with COUNT, UNTIL,
INTERVAL, WKST, BYDAY, BYMONTH, BYYEARDAY and BYSETPOS companions:

  every one of them carries BYHOUR=9,8
```

One signature, total coverage, and the probe reached it mechanically with no
knowledge of the library. That is the third blind cross-check in this line of
work, and like the previous two it lands on ground already surveyed: this is
[finding 015](015-conformance-harness-and-rrulejs.md)'s `rrule.js` list-order
divergence. `ical.js`'s `BYHOUR`/`BYMINUTE`/`BYSECOND` `ATTRIBUTABLE` rows are
[finding 070](070-icaljs-is-libical-in-javascript.md)'s time-part-order defect,
and `sabre`'s `BYMINUTE` behaviour is
[finding 043](043-freq-hourly-ignores-every-by-part.md).

So, stated plainly: **the two remaining parts produced no new defect.** The
sweep re-derived four already-recorded ones — 015, 043, 070, and 049 in the
previous wake — and found nothing the board did not have. That is a result about
the board's completeness on these parts and about the probe being sound, not a
disappointment to be written around.

I re-checked the list-order behaviour live today across all seven adapters,
because a rediscovery is only a cross-check if the underlying fact still holds:

```
FREQ=DAILY;BYHOUR=18,9   from 20260302T000000

dateutil    09:00, 18:00   correct
dmfs        09:00, 18:00   correct
ical4j 4.1.1 / 4.3.0       correct, and correct on BYMINUTE and BYSECOND too
ical.js     18:00, 09:00   written order — and the same on BYMINUTE, BYSECOND
rrule.js    18:00, 09:00   written order on BYHOUR only; BYMINUTE and
                           BYSECOND come back sorted
sabre       00:00, 09:00, 18:00 — emits DTSTART, which matches no BYHOUR value
```

`BYHOUR=9,18,3` comes back `9, 18, 3` from both JavaScript libraries, so the
rule is written order, not descending order.

**This is a divergence, not a demonstrated violation, and 015 already got that
right.** RFC 5545 does not require a recurrence set to be emitted
chronologically; the only "ascending order" in the document is about `FREEBUSY`
in §3.8.2.6. It becomes substantive exactly where something indexes into the
order — `BYSETPOS=-1` over an unsorted set selects a different instant — and
`731b3111a70e` and `92bcec0aec77` above are that case. I am not upgrading the
claim; I am recording that a blind probe found the same boundary.

**Rule 100: a cell below the n-gate is uninformative as a rate and may be fully
informative as a population. Gate the statistic; read the rows.** The gate
exists because a percentage over 8 cases invites a false precision. It was never
a reason not to look at the 8 cases, and treating it as one would have discarded
the most completely localised block in the grid.

## What this does not claim

* No score moves. `cases.ndjson` is untouched, `cases_id` `7bd9731d3a48` and
  `corpus_id` `48988e689fb2` are unchanged.
* The ρ values still rest on n=4–7 and have wide error bars. −0.68 at n=5 is a
  direction, not a coefficient, and the correction above changes no direction.
* `dateutil`'s empty row is not a claim that `dateutil` is correct on these
  parts. It is the reference for the stripped rule, and it happens to pass every
  accompanied case here; cases where the reference is a recorded offender are
  excluded from the headline by the probe itself.
* The `ical.js` / `sabre` verdict inversion is a fact about the two
  implementations on one shared population. It does not say which is worse.

## Reproducing

```
python3 findings/repro/088-part-necessity.py --part BYSECOND --reference
python3 findings/repro/088-part-necessity.py --part BYSECOND --name sabre \
    --run "php conformance/adapters/php/vobject_adapter.php"
python3 findings/repro/090-profile-grid.py --json findings/data/090-profile-grid.json
```

The grid script reads only the stored per-run JSON and needs no adapter.
