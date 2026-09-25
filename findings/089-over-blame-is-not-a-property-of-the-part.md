# 089 — "the most over-blamed part" is not a property of the part; and 088's validation was one-sided

*2026-09-25.*

## Why this was asked

[088](088-the-most-over-blamed-part-is-not-bysetpos.md) measured three `BY` parts
and reported `BYDAY` as the field's most over-blamed, at 63% `NOT-NECESSARY`. It
named its own confound and did not resolve it:

> `sabre` dominates the `BYDAY` number (300 of 410 field-wide). Is `BYDAY`
> over-blamed, or is `sabre` simply broadly broken so that **every** part looks
> over-blamed on it?

The standing note also recorded a prediction, stated so it could be wrong:

> `BYMONTHDAY` will come out **low** not-necessary (like `BYMONTH`, ~30%),
> because [049](049-a-negative-day-that-only-counts-when-it-expands.md)'s 72 cases attribute to
> it directly.

That prediction is wrong: `BYMONTHDAY` is **42%**, mid-pack, between `BYMONTH`'s
34% and `BYDAY`'s 63%. But the number is the least interesting thing this wake
produced.

## What was run

The probe from 088 (`findings/repro/088-part-necessity.py`) is part-agnostic, so
three more parts were swept with no method change: `BYMONTHDAY` (407 cases),
`BYYEARDAY` (128), `BYHOUR` (97). Seven adapter configurations, six lineages.
Accompanied stratum only throughout — rule 97.

| adapter | `BYWEEKNO` | `BYMONTH` | `BYDAY` | `BYMONTHDAY` | `BYYEARDAY` | `BYHOUR` |
|---|---|---|---|---|---|---|
| `ical4j` 4.1.1 | 35% | 40% | 25% | **9%** | 56% | — |
| `ical4j` 4.3.0 | 35% | 26% | **11%** | 21% | 56% | — |
| `ical.js` | 18% | **70%** | 59% | 24% | 62% | 29% |
| `sabre` | 50% | **27%** | **95%** | 64% | 50% | 65% |
| field | 38% | 34% | 63% | 42% | 55% | 45% |

## The confound, resolved — and it goes the other way

**`sabre` is not uniformly broken.** Within `sabre` the per-part rate spans
**67 percentage points**, from `BYMONTH` at 27% to `BYDAY` at 95%. If breadth of
breakage were the explanation, every part would be high on `sabre`; `BYMONTH`,
its largest part at 366 accompanied cases, is its *lowest*. So the first half of
the confound is refuted.

The second half is not, and it is worse than the confound as posed. **The
per-part profile does not transfer between implementations.** `sabre` ranks
`BYDAY` **first** (95%) and `BYMONTH` last; `ical4j` 4.3.0 ranks `BYDAY`
**last** (11%). Pairwise Spearman correlation of the per-part rate, on parts
with ≥10 accompanied cases in both:

| pair | n | ρ |
|---|---|---|
| `ical4j` 4.1.1 vs `ical4j` 4.3.0 | 5 | **+0.80** |
| `ical4j` 4.1.1 vs `ical.js` | 4 | +0.40 |
| `ical.js` vs `sabre` | 5 | 0.00 |
| `ical4j` 4.3.0 vs `sabre` | 5 | **−0.70** |
| `ical4j` 4.1.1 vs `sabre` | 5 | **−0.80** |

The one strongly positive pair is **the same codebase at two versions** — which
is the control that says the measurement is not noise. Every genuinely
cross-lineage pair is zero or negative.

Leave-one-out makes the consequence concrete. Removing `sabre` alone:

| part | field | field without `sabre` |
|---|---|---|
| `BYDAY` | 63% | **33%** |
| `BYMONTHDAY` | 42% | **17%** |
| `BYHOUR` | 45% | **18%** |
| `BYMONTH` | 34% | 42% |

`sabre`'s share of the accompanied cases is roughly constant across parts
(32–58%), so this is not a weighting artifact: it is `sabre`'s own per-part rate
varying that moves the field number.

**So 088's headline does not survive.** "The most over-blamed part is `BYDAY`"
is an artifact of pooling implementations whose profiles disagree, in a corpus
where one implementation holds about half the cases. Over-blame is a property of
the **(implementation, part) pair**, not of the part. The correct statement of
088's own result is narrower and still true: *`sabre` over-attributes `BYDAY`
at 95%*.

## The check 088 got right for the wrong reason

088 reported, as a check it was not told to pass, that `ical4j` 4.1.1→4.3.0
leaves the `ATTRIBUTABLE` side an identical set of ids while all 42 repairs land
inside `NOT-NECESSARY` — 52 of 52 with 087's ten. Extending the same check to
the three new parts breaks it:

| part | `ATTRIBUTABLE` set identical? | repairs landing in `ATTRIBUTABLE` | in `NOT-NECESSARY` |
|---|---|---|---|
| `BYWEEKNO` | yes | 0 | 0 |
| `BYMONTH` | yes | 0 | 23 |
| `BYDAY` | yes | 0 | 19 |
| **`BYMONTHDAY`** | **no (73→26)** | **47** | **0** |
| `BYYEARDAY` | yes | 0 | 0 |

And the three repaired sets are not three populations. The 23 `BYMONTH` repairs
and the 19 `BYDAY` repairs are disjoint, and **both are subsets of the 47
`BYMONTHDAY` repairs**; the union of all three is exactly 47. It is **one**
population of 47 cases, seen through three different strippings, and the verdict
**flips** depending on which part is stripped.

That is not a failure of the method — it is the method working, and 088 reading
one side of it. Strip `BYMONTH` from a case whose defect is in `BYMONTHDAY` and
the disagreement survives: `NOT-NECESSARY`, correctly saying *not a `BYMONTH`
defect*. Strip `BYMONTHDAY` from the same case and the disagreement vanishes:
`ATTRIBUTABLE`, correctly saying *this one is*. A real repair lands in
`NOT-NECESSARY` for every part **except the one that actually holds the
defect**, where it lands in `ATTRIBUTABLE`. 088 never ran the part that held the
defect, so it saw only the negative side and mistook a one-sided view for a
validation.

Run as a sweep, the partition names the release's actual change. All **47**
repaired cases are `FREQ=DAILY` carrying a **negative** `BYMONTHDAY`; none
remain in 4.3.0. The 26 that stay `ATTRIBUTABLE` under 4.3.0 are a disjoint
shape — 15 `MONTHLY`, 11 `YEARLY`. The sweep localised a version delta to a
part *and a shape* without being told a release had happened.

## An independent check the sweep was not told about

[049](049-a-negative-day-that-only-counts-when-it-expands.md) characterised this
same `ical4j` defect in September by **reading the source** — `ByMonthDayRule`
resolves negative values only in the expansion branch, and the limit branch
compares against a never-negative day-of-month — and derived the mechanical
signature *"`FREQ` is `DAILY` and `BYMONTHDAY` contains a negative value"*,
selecting **65** cases fixed in 4.3.0.

The sweep is blind to all of that. Across both strata it isolates **69** repaired
cases, and **all 65 of 049's ids are inside them**, with none of 049's outside.
So a source-read mechanism and a black-box counterfactual partition, three weeks
and one method apart, pick out the same population.

The 4 extra are worth naming, because they sharpen 049 rather than contradict
it. All four are `BYMONTHDAY=-1` from `DTSTART=20260331T090000`, and three carry
`FREQ=HOURLY`, `MINUTELY` and `SECONDLY`. `BYMONTHDAY` is a *limit* at every
sub-daily frequency too, so the defect 049 read out of the limit branch applies
there as well — but 049's stated signature says `DAILY` and does not cover them.
The mechanism was right and the signature was narrower than the mechanism.

049 also predicted a **non**-repair: `ByYearDayRule` has the identical shape and
4.3.0 does not fix it. The sweep records `BYYEARDAY` repairs at **0**. It
reproduces both the fix and the absence of the fix.

## What this does not say

* Six lineages, not "the field": `libical` and `rust-rrule` adapters do not
  build here, `dtical` is excluded on rule 80 grounds.
* The ρ values rest on n=4–5 and have wide error bars; ρ=−0.80 at n=5 is not
  significant on its own. The argument rests on the *pattern* — the only
  positive pair is within-lineage, and the raw rankings are visibly opposed —
  not on any single coefficient.
* `dmfs` and `rrule.js` have no part with ≥10 accompanied cases and are excluded
  from the correlation entirely; their column in the big table is noise.
* `NOT-NECESSARY` still does not say where a defect lives (rule 97). Nothing
  here upgrades it.
* No score moves. `cases.ndjson` untouched, `cases_id` unchanged.

## Rules

**Rule 98 — a rate pooled across implementations is a statement about the
corpus's composition until the per-implementation profiles are shown to agree.**
Here they anti-correlate, and the pooled ranking inverts the ranking of the
implementation that holds half the cases.

**Rule 99 — a counterfactual partition must be swept over every part before its
verdicts are read as evidence.** A single part shows one side: repairs land in
`NOT-NECESSARY` everywhere except the part that holds the defect. Seeing only
the negative side looks like validation and is not.

## Reproducing

```
python3 findings/repro/088-part-necessity.py --part BYMONTHDAY --reference
python3 findings/repro/088-part-necessity.py --part BYMONTHDAY --name sabre \
    --run "php conformance/adapters/php/vobject_adapter.php"
```

Per-case verdicts for seven adapter configurations across six parts are in
`findings/data/088-necessity-<part>-<adapter>.json`.
