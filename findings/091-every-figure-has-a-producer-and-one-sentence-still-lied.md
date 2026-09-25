# 091 — auditing every published figure: 31 have no producer, and the worst thing on the board was a sentence, not a number

*2026-09-25.*

[077](077-a-table-that-outlived-its-corpus.md) found a table copied forward
until it was nine days stale. [090](090-the-grid-two-wrong-rhos-and-what-the-gate-throws-away.md)
found two published ρ values computed by hand and simply wrong. Both were found
**by accident, one figure at a time**, and both named the same cause: a figure
with no script that would print it has nothing to contradict it.

Neither asked the obvious next question: **how many other figures on this board
are in that state?** This is the systematic version. It produced three things —
a worklist, one real retraction, and a lesson about the audit itself that I
nearly published a false headline over.

## The audit

`findings/repro/091-figure-provenance-audit.py` reads every `findings/*.md`,
extracts every published percentage, signed decimal and explicit fraction, and
asks whether that value exists in any stored artifact — the finding's own
`findings/data/*.json` and `findings/repro/*` first, then anywhere else in the
repository. Figures inside fenced code blocks are skipped: those are already
evidence. Three outcomes:

| status | meaning |
|---|---|
| `DIRECT` | the value is in **this** finding's own stored data or script output |
| `GLOBAL` | not here, but it exists in some other stored artifact |
| `NOWHERE` | it exists in no stored artifact anywhere — nothing on disk contradicts it |

The test is deliberately generous: a value counts as produced if it appears
*anywhere* in the artifact, so coincidences pass. A generous test that still
says `NOWHERE` is saying something.

## Result 1 — the worklist

**263 distinct figures across findings 001–090. 78 `DIRECT`, 154 `GLOBAL`, 31
`NOWHERE`.** The audit excludes itself, so these totals do not move when this
page is reworded.

Six of the 31 are `−0.80` and `−0.70` in 088, 089 and 090 — the values 090
already retracted, quoted only inside the notes that withdraw them. The other
25 are concentrated in fourteen findings and are mostly *ratios over stored
counts*: `237 / 244` in [031](031-one-cluster-three-causes.md), `155 / 158` in
[035](035-one-deletion-and-a-pinned-day.md), `629 / 800` in
[032](032-a-blind-spot-the-corpus-cannot-see.md), `1696 / 1722` in
[015](015-conformance-harness-and-rrulejs.md), and the four bare decimals in
[062](062-what-raising-the-bound-costs.md).

I spot-checked the single most 089-like case — [087](087-bysetpos-is-over-blamed.md)'s
lone "`sabre/vobject` is **83% upstream** (148 of 178)", a rate in a finding
with eleven artifacts. `087-localisation-sabre.json` stores
`UPSTREAM: 148, DOWNSTREAM: 30`. The denominator 178 is their sum and is not
stored, so the audit cannot see it; 148/178 = 83.1%, and **the published figure
is correct.**

So the honest characterisation is not "the board is rotten" and not "the board
is clean": **31 figures are arithmetic performed over stored data by hand, and
where I checked one, it was right.** That is precisely the category 089's two
wrong ρ values came from, which is why the list is worth having rather than
worth dismissing. It is a ranked worklist, not a verdict.

## Result 2 — the real defect is a sentence

The audit was built to find *figures with no producer*. What it actually caught,
by forcing me to read the pair table next to the prose, is worse and is not what
I was looking for: **a figure that is produced, stored and correct, with a
sentence beside it that contradicts it.**

089 published this table, and every row is right:

| pair | n | ρ |
|---|---|---|
| `ical4j` 4.1.1 vs `ical4j` 4.3.0 | 5 | **+0.80** |
| `ical4j` 4.1.1 vs `ical.js` | 4 | **+0.40** |
| `ical.js` vs `sabre` | 5 | 0.00 → −0.19 at n=7 |
| `ical4j` 4.3.0 vs `sabre` | 5 | −0.62 |
| `ical4j` 4.1.1 vs `sabre` | 5 | −0.68 |

Then it concluded — in its body, in its caveats, in 090's correction note, and
twice in the README index:

> Every genuinely cross-lineage pair is zero or negative.
> The only positive pair is one codebase at two versions.

**Both sentences are false, and the table above always showed it.** `ical4j`
4.1.1 vs `ical.js` is **+0.40**: Java against JavaScript, as cross-lineage as
anything here, `same_codebase: false` in the stored JSON since 090 wrote it. The
README went furthest, enumerating the cross-lineage values as "0.00, −0.62 or
−0.68" — a list of three drawn from a set of four, silently dropping the member
that breaks the claim.

This is not a rounding dispute. 090 verified that every *number* reproduced,
declared "089's conclusion is unaffected", and never checked whether the
*conclusion* followed from the numbers. It did not.

### Why it matters: the control was the argument

The lost sentence was load-bearing. 089's defence of a weak statistic was
exactly that the one positive correlation was within-lineage:

> The one strongly positive pair is the same codebase at two versions — which is
> the control that says the measurement is not noise.

Remove the exclusivity and the control is gone: with a cross-lineage pair at
+0.40, "positive ⇒ same codebase" no longer separates signal from noise.

And the data says noise. The producing script now prints:

```
sign stability across a version bump (n is small -- check it)
  icaljs    SIGN FLIPS: ical4j411 +0.40 (n=4)  ical4j430 -0.40 (n=4)
  sabre     stable:     ical4j411 -0.68 (n=5)  ical4j430 -0.62 (n=5)
```

**`ical.js` correlates +0.40 with `ical4j` 4.1.1 and −0.40 with `ical4j` 4.3.0 —
while those two versions correlate +0.80 with each other.** One minor-version
bump of the *other* library flips the sign at full magnitude, under both tie
conventions. At n=4 over four shared parts this coefficient has no resolution.
That is not a caveat about error bars; it is a measurement giving opposite
answers to the same question. `sabre`'s n=5 pairs, on a much larger case base,
are stable across that same bump.

So the correct reading is narrower than either the old claim or a blanket
dismissal: **the `sabre` anti-correlations are stable and carry the argument;
the n=4 `ical.js`–`ical4j` pairs carry nothing and should never have been read
as sign-bearing.**

### What survives

089's **headline survives**, because it never rested on ρ. Over-blame being a
property of the *(implementation, part)* pair rests on the leave-one-out —
`BYDAY` 63%→33% without `sabre`, `BYMONTHDAY` 42%→17%, `BYHOUR` 45%→18% — and on
directly opposed rankings: `sabre` ranks `BYDAY` first at 95%, `ical4j` 4.3.0
last at 11%. None of that moves.

Retracted is the **exclusivity claim and the control built on it**. The honest
statement of the correlation evidence:

> Of five cross-lineage pairs, three are negative, one is ≈0, and one is +0.40.
> The three `sabre` pairs are stable across an `ical4j` version bump; the two
> n=4 `ical.js`–`ical4j` pairs flip sign across it and are not evidence.

Corrected in place in 088, 089, 090 and both README entries.

## Rule 101

> **A produced figure and the sentence summarising it are two separate claims.
> Checking provenance validates only the first.**

090 built a script that prints every number and then wrote a false sentence
directly under its output. Reproducibility of the figures did not protect the
paragraph, because the paragraph was never compared to them.

The fix is applied, not merely stated: the summary statements are now **printed
by the script that holds the data**, so they are figures too.
`findings/repro/090-profile-grid.py` emits

```
claim check (rule 101 -- the summary sentence is a claim too)
  positive pairs:                        ical4j411 vs ical4j430, ical4j411 vs icaljs
  cross-lineage POSITIVE pairs:          ical4j411 vs icaljs
  'every cross-lineage pair is <= 0':    False
  'only positive pair is same codebase': False
```

Both sentences I published now print `False` from the data that always said so.

## Result 3 — the audit graded itself clean, and I nearly published it

This is the part worth keeping. Three instrument bugs, in the order they bit:

1. **A rounding boundary.** `−0.675` stored, `−0.68` published; an
   absolute-tolerance comparison misses exactly on the half-way boundary, which
   is where rounded figures land disproportionately. Comparison is now at the
   precision the figure was published at, under both rounding modes.

2. **U+2212.** These findings render negative numbers with MINUS SIGN, not the
   ASCII hyphen. My regex matched `[-+]?0\.\d+`, so it read `−0.68` as
   *positive* `0.68` and hunted for a number that was never published. Any grep,
   diff, or external script reading this board as ASCII **silently inverts the
   sign of every correlation on it** — a hazard well past this audit.

3. **The audit read its own output.** Its JSON records every figure it scanned,
   and that JSON sits in `findings/data/`, which is the global pool. On the
   second run every figure matched itself. `NOWHERE` fell from 28 to **0** and
   the board was pronounced perfect.

The third one is the dangerous one, because it failed in the flattering
direction and its output looked like success. I had already drafted this finding
around "**5 unbacked figures, all five already retracted — the board's
provenance is complete**". That headline was an artifact of the instrument
reading yesterday's copy of its own answer. The true count is 31, six times
larger, and it was *never* 5: even that run was contaminated by the run before
it.

The audit now excludes its own output from the pool and its own prose from the
scan, and is idempotent — two consecutive runs give identical totals, which is
the property whose absence hid the bug. [038](038-checking-the-instrument-for-what-it-measured.md)
said check the instrument for what it measured; the sharper form is **an
instrument that stores its results near its inputs will eventually read them,
and it will do so in the direction that looks like success.**

## What this does not say

* The audit proves **existence**, not **derivation**. A `GLOBAL` figure exists
  in some stored artifact but nothing ties that artifact to the claim; 154 of
  263 are `GLOBAL`. The strong guarantee — this finding's script prints this
  finding's number — holds for the 78 `DIRECT`.
* Matching is by value, so coincidences pass. The audit can say a figure is
  *unbacked*; it can never say one is *wrong*. 089's ρ values were wrong for
  nine hours while being perfectly well-formed numbers.
* 31 `NOWHERE` is **not** 31 errors. One was checked and was correct. The
  remaining 30 are unchecked.
* The one real defect here was found by reading, not by the tool. The tool's
  contribution was narrowing 90 findings to the three worth reading closely.
* No score moves. `cases_id` and `corpus_id` unchanged; no corpus case touched.

## Reproduce

```
python3 findings/repro/091-figure-provenance-audit.py --json findings/data/091-figure-provenance.json
python3 findings/repro/090-profile-grid.py            # claim check at the end
```
