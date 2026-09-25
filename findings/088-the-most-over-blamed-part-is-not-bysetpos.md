# 088 — the most over-blamed part is not `BYSETPOS`, it is `BYDAY`; and both of my predictions were wrong

*2026-09-25.*

> **Headline narrowed on 2026-09-25 by [089](089-over-blame-is-not-a-property-of-the-part.md).**
> Sweeping three further parts shows the per-part profile does not transfer
> between implementations (cross-lineage Spearman +0.40 to −0.68). *The
> parenthesis first read "0.00 to −0.80; the only positive pair is `ical4j`

<!-- provenance: RETRACTED-QUOTE -0.80 -- a quotation of superseded wording, kept so
     the correction is legible. -->
> 4.1.1 vs 4.3.0, the same codebase". Both halves were wrong: the endpoints were
> the two values [090](090-the-grid-two-wrong-rhos-and-what-the-gate-throws-away.md)
> found unreproducible, and `ical4j` 4.1.1 vs `ical.js` is cross-lineage and
> **+0.40**. Corrected by [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md).* Removing `sabre`
> takes `BYDAY` from 63% to **33%**. "The field's most over-blamed part is
> `BYDAY`" is an artifact of pooling; the defensible claim is the narrow one,
> *`sabre` over-attributes `BYDAY` at 95%*. The `ical4j` version-delta check
> below is also **one-sided** — extended to `BYMONTHDAY` the same 42 repairs
> land in `ATTRIBUTABLE`, not `NOT-NECESSARY`. The method is sound; this finding
> read one side of it.

## Why this was asked

[087](087-bysetpos-is-over-blamed.md) ended by proposing rule 96 — *a failure on
a rule carrying part X is not evidence of a defect in X until the same rule has
been asked without X* — and the standing note recorded a prediction, stated so
it could be wrong:

> `BYWEEKNO` will come out almost entirely upstream-free (it is a single-lineage
> part, [052](052-byweekno-is-one-lineage-deep.md)) and `BYMONTH` will
> look like `BYSETPOS`.

Both halves are wrong, and the part that is actually most over-blamed was not on
the list.

## What had to change in the method first

087's decomposition was clean because `BYSETPOS` is a **selector**. Deleting it
leaves the candidate set untouched and removes only the selection step, so a
surviving disagreement localises: *the set was already wrong*. That is a genuine
decomposition into "the set" and "the selecting".

`BYMONTH`, `BYDAY` and `BYWEEKNO` are **set-construction** parts. Deleting one
does not leave the same set minus a step — it changes the set. So the same
counterfactual supports a weaker claim, and calling it by 087's name would have
overstated it. Here the verdicts are:

* **ATTRIBUTABLE** — fails the original, agrees with the reference once X is
  gone. X is *necessary* to provoke the disagreement.
* **NOT-NECESSARY** — fails the original and disagrees without X too. The
  implementation is already wrong on the remainder of the rule.

`NOT-NECESSARY` is **not** 087's `UPSTREAM`. It does not say where the defect
lives. It says only that X is not required to expose it, so reporting the
failure as an X defect is unsupported either way.

One control 087 did not need. Stripping X from a rule whose *only* `BY` part is
X leaves a bare `FREQ` rule, which nearly every implementation handles, so those
cases are near-guaranteed to come out `ATTRIBUTABLE` and pooling them would
manufacture the result. `BYSETPOS` never occurs alone — **291 of 291** corpus
cases carrying it carry something else — which is exactly why the question did
not arise. The other parts are not like that: `BYDAY` is alone in 314 of 808
cases, `BYMONTH` in 222 of 696, `BYWEEKNO` in 20 of 49. **The alone stratum is
reported separately and excluded from every headline number below.**

## The measurement

For each corpus case carrying X, build the same case with the X part deleted and
nothing else changed; run both through the same adapter. Reference is
`python-dateutil` on the stripped rule — a *reference, not an oracle*. Note one
honesty cost relative to 087: there, the reference structurally could not exhibit
its own known `BYSETPOS` defect ([004](004-bysetpos-first-period-truncation.md)),
because the stripped rules carried no `BYSETPOS`. Here a stripped rule may still
carry parts `dateutil` gets wrong, so that protection is gone. `dateutil` passes
all 1979 accompanied cases across the three parts, so it contributes no verdicts
and is excluded from field totals as the reference lineage.

Accompanied stratum, ATTRIBUTABLE / NOT-NECESSARY:

| adapter | `BYWEEKNO` | `BYMONTH` | `BYDAY` |
|---|---|---|---|
| `dateutil` (reference) | 0 / 0 | 0 / 0 | 0 / 0 |
| `rrule.js` | 0 / 0 | 5 / 2 | **0 / 8** |
| `ical.js` | 9 / 2 | 21 / 49 | 40 / 58 |
| `sabre/vobject` | 13 / 13 | 266 / 100 | **17 / 300** |
| `ical4j` 4.1.1 | 13 / 7 | 73 / 48 | 94 / 31 |
| `ical4j` 4.3.0 | 13 / 7 | 73 / 25 | 94 / 12 |
| `dmfs` | 2 / 1 | 0 / 1 | 0 / 1 |
| **field** | **50 / 30 — 38%** | **438 / 225 — 34%** | **245 / 410 — 63%** |

## What this says

**The prediction was wrong twice.** `BYWEEKNO` is not "almost entirely
upstream-free": 38% of its attributed failures do not need it, and `sabre` splits
exactly 13/13. `BYMONTH` does not "look like `BYSETPOS`": at 34% it is the *least*
over-blamed of the three, roughly half `BYSETPOS`'s 62%.

**`BYDAY` is the field's most over-blamed part, and it was not on the list.** At
**63%** it edges out `BYSETPOS`'s 62%, and it matters far more, because `BYDAY`
is the most-carried part in the corpus — **808 cases** against `BYSETPOS`'s 291.
`sabre` is the extreme: **300 of its 317 attributed `BYDAY` failures do not need
`BYDAY` at all** — 95%. `rrule.js` is a smaller but purer case, 8 of 8.

So the conclusion 087 drew for one part is not a `BYSETPOS` fact. It is worse
elsewhere, and it is worst on the part that the largest share of any
`BYDAY`-shaped test suite is nominally measuring.

## The check the method was not told to pass

`ical4j` shipped 4.1.1 → 4.3.0 without knowing this partition exists. Across all
three parts the `ATTRIBUTABLE` side is the **identical set of ids**, not merely
the same count — 13, 73 and 94 — while the repairs land **42 of 42 inside
`NOT-NECESSARY`** (23 on `BYMONTH`, 19 on `BYDAY`, 0 on `BYWEEKNO`). With 087's
ten, that is **52 of 52 real upstream repairs falling on one side of a partition
drawn without reference to them**, and zero regressions crossing the other way.

Stated against itself: `BYWEEKNO` contributes no evidence here, since it saw no
repairs; the weight is carried by `BYMONTH` and `BYDAY`.

## Hand checks

Two of the shapes driving `sabre`'s 300, run directly on rules carrying **no
`BYDAY` at all**:

```
FREQ=WEEKLY;BYMONTH=3      DTSTART 20260115T090000
  sabre     20260115, 20260122, 20260129, 20260205, ...   (BYMONTH ignored)
  reference 20260305, 20260312, 20260319, 20260326, ...

FREQ=DAILY;BYMONTHDAY=15   DTSTART 20270115T090000
  sabre     20270115, 20270116, 20270117, 20270118       (BYMONTHDAY ignored)
  reference 20270115, 20270215, 20270315, 20270415
```

Those two shapes are **166 of the 300** (`WEEKLY;BYDAY+BYMONTH` 129,
`DAILY;BYDAY+BYMONTHDAY` 37). `sabre` is already wrong on the remainder of the
rule with nothing for `BYDAY` to have caused.

## Limits

* Six lineages, not "the field": `libical` and `rust-rrule` adapters do not build
  in this environment today, so two lineages are absent.
* `NOT-NECESSARY` is a necessity verdict, not a localisation. It refutes an
  attribution; it does not supply the right one.
* The reference's own defects are not structurally excluded here, unlike in 087.
* `dmfs` and `rrule.js` produce too few attributed failures on these parts for
  their percentages to mean much; they are reported as counts for that reason.

No score moves. `cases.ndjson` is untouched, `cases_id` `7bd9731d3a48` and
`corpus_id` `48988e689fb2` unchanged.

## Standing rule

**Rule 97 — rule 96's counterfactual is not equally informative for every part.**
For a selector it decomposes; for a set-construction part it only establishes
necessity, and it degenerates entirely when the stripped part was the rule's only
`BY` part. Report the accompanied stratum separately or the control manufactures
the answer.

Probe: [`findings/repro/088-part-necessity.py`](repro/088-part-necessity.py).
Per-case verdicts for seven adapter configurations across three parts in
[`findings/data/`](data/).
