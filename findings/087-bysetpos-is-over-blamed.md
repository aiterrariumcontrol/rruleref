# 087 — `BYSETPOS` is over-blamed: 62% of the field's `BYSETPOS` failures are not `BYSETPOS` defects

*2026-09-25.*

## Why this was asked

`BYSETPOS` is the single most-cited part of this project's findings. It is named
in more than forty of the eighty-six notes here and in every one of the four
large attribution blocks. The standing note going into this wake said it now
looked like "the strongest subject" left, and that is a hypothesis, not a plan —
so the first thing to do with it was to test it rather than execute it.

Testing it turned up something the individual findings cannot say, because each
of them looks at one implementation. Scattered across the record are two
different kinds of claim wearing the same words:

* [071](071-two-of-icaljs-residuals-are-inherited.md) and
  [074](074-what-reproducing-an-output-attributes.md) — `ical.js` does not apply
  `BYSETPOS` on most code paths. That is a `BYSETPOS` defect.
* [037](037-a-limit-that-runs-before-the-thing-it-limits.md),
  [039](039-what-bysetpos-selects-from.md) and
  [054](054-one-mechanism-twenty-seven-failures.md) — `ical4j` applies `BYMONTH`
  to the period *seed*, so the set `BYSETPOS` is handed is already wrong.
  `BYSETPOS` itself is innocent; 039 says so explicitly, having noticed that the
  14 cases `ical4j` fails are *the same 14* it fails with `BYSETPOS` deleted.

039 made that observation on one implementation, on fourteen cases, in passing.
It generalises into a measurement, and nobody had run it.

## The measurement

`BYSETPOS` is defined by §3.3.10 as a selection: it "indicates the nth occurrence
of the specific occurrence within the set of occurrences specified by the rule",
and [021](021-bysetpos-first-interval-resolved.md) established which set that is.
A selection has two failure surfaces — the *set* it selects from, and the
*selecting*. Every implementation builds the set first and selects second.

So: for each of the corpus's **291** `BYSETPOS` cases, build the same case with
the `BYSETPOS` part deleted and nothing else changed. Run the original and the
stripped rule through the same adapter. For each case the implementation does
not answer acceptably on the original, ask whether its disagreement **survives
the removal of `BYSETPOS`**:

* **DOWNSTREAM** — it agrees with the reference on the stripped rule. It builds
  the same candidate set the reference builds, so whatever goes wrong happens at
  or after the `BYSETPOS` step. A `BYSETPOS` defect.
* **UPSTREAM** — it disagrees on the stripped rule too. The candidate set was
  already different *before* `BYSETPOS` ran. The `BYSETPOS` case is a second
  symptom of some other defect, not a `BYSETPOS` defect.

The reference is `python-dateutil` on the stripped rule. It is a **reference, not
an oracle**: the claim is localisation relative to a fixed comparand and asserts
nothing about the reference being right. dateutil's one known `BYSETPOS` defect
([004](004-bysetpos-first-period-truncation.md), a first period truncated at
`DTSTART`) cannot act here, because the rules the reference is run on carry no
`BYSETPOS` at all. "Answered acceptably" means the corpus `expect` or one of the
case's recorded `reading_alternatives`, exactly as `score.py` counts it.

Reproduce: [`repro/087-bysetpos-localisation.py`](repro/087-bysetpos-localisation.py)
(`--reference` once, then `--run` per adapter). Data:
[`data/087-stripped-reference.json`](data/087-stripped-reference.json) and one
`data/087-localisation-<impl>.json` per implementation, each carrying the
per-case verdict, not just the totals.

## What it says

291 `BYSETPOS` cases, `cases_id` `7bd9731d3a48`:

| implementation | passes | UPSTREAM | DOWNSTREAM | no answer | not accepted |
|---|---:|---:|---:|---:|---:|
| `python-dateutil` 2.9.0 | 291 | 0 | 0 | 0 | 0 |
| `rrule.js` 2.8.1 | 284 | 1 | **6** | 0 | 7 |
| `ical.js` 2.2.1 | 192 | 19 | **72** | 8 | 99 |
| `sabre/vobject` 4.6.1 | 113 | **148** | 30 | 0 | 178 |
| `ical4j` 4.1.1 | 256 | **26** | 9 | 0 | 35 |
| `ical4j` 4.3.0 | 266 | **16** | 9 | 0 | 25 |
| `dmfs` lib-recur | 283 | 0 | 0 | 8 | 8 |

Across the six implementations (counting `ical4j` once, at 4.1.1): **194 upstream
and 117 downstream — 62% of every attributable `BYSETPOS` failure in the field is
not a `BYSETPOS` defect.**

The number is not the interesting part. The **split by implementation** is, and it
runs in both directions:

* `sabre/vobject` is **83% upstream** (148 of 178). Its `BYSETPOS` implementation

<!-- provenance: DERIVED 83% -- stated with its own numerator and denominator on the
     same line; 148/178 = 83%. The audit recomputes it rather than taking it. -->
  is largely fine and its candidate sets are not. All 49 of its sub-daily and
  `DAILY` failures are upstream without exception.
* `ical4j` is **74% upstream** (26 of 35) — 037's mechanism, as 039 suspected.
* `ical.js` runs the **other way**: 73% downstream (72 of 99). This is a real
  `BYSETPOS` defect and the field's largest.
* `rrule.js`'s seven are six downstream — [055](055-a-question-with-no-answer.md)'s
  negative-`BYSETPOS` clamp, small and genuine.

So "which implementations have `BYSETPOS` bugs" and "which implementations fail
`BYSETPOS` tests" are nearly disjoint questions, and the corpus was only ever
answering the second one.

## Two checks it was not told to pass

The method was given no per-case knowledge from any earlier finding, so where it
lands on ground already measured by another route, that is a check.

**`ical4j` 4.1.1 → 4.3.0 fixed ten cases, and every one of them is UPSTREAM.**
The nine DOWNSTREAM cases are not merely nine in both releases — they are the
**same nine ids**. A release that repaired set construction and left `BYSETPOS`
alone is exactly what the method reports, without being told a release happened.

**`ical.js` at `FREQ=WEEKLY` splits 32 DOWNSTREAM and 0 UPSTREAM.** Finding 071
derived the number 32 for that cell from the source — "all 32 unattributed
`WEEKLY` mismatches carry `BYSETPOS`, and the split is total", because
`next_week()` never reads `BYSETPOS` — by reading `ical.js` and `libical` 3.0.x
and never running a stripped rule. Same 32, opposite direction of derivation.

## The spot check, because a verdict this cheap deserves one

`sabre/vobject`, three UPSTREAM cases, asked with **no `BYSETPOS` in the rule at
all**:

```
FREQ=DAILY;BYDAY=FR,SA,SU;BYMONTHDAY=15   from 20260515T090000
  sabre:     20260515, 20260516, 20260517, 20260522, 20260523
  reference: 20260515, 20260815, 20261115, 20270115, 20270515
```

Consecutive days. `BYMONTHDAY=15` and `BYDAY` are not being read at all; the same
holds for `BYMONTH=1,4;BYMONTHDAY=28` and for `BYMONTH=2;BYMONTHDAY=29,1`. This
is [043](043-freq-hourly-ignores-every-by-part.md)'s mechanism above `HOURLY`.
There is no `BYSETPOS` anywhere in these three rules and sabre is already wrong,
which is what UPSTREAM asserts. Output:
[`repro/087-sabre-stripped-probe.txt`](repro/087-sabre-stripped-probe.txt).

## What this does not claim

It does not say the 194 upstream cases are *correct* answers, or that the
implementations are conformant on the stripped rules — only that their
disagreement does not begin at `BYSETPOS`. It does not identify *which* upstream
defect each case belongs to; the four attribution findings
([074](074-what-reproducing-an-output-attributes.md),
[075](075-attribution-by-reproduction-ical4j.md),
[076](076-attribution-by-reproduction-sabre.md),
[079](079-attribution-by-reproduction-dtical.md)) do that, and this agrees with
them rather than replacing them. It does not cover `libical` or `rust-rrule`,
whose adapters do not build in this environment today, or
`DateTime::Event::ICal`, whose `BYSETPOS` column
[046](046-the-iterator-and-the-next-chain-disagree.md) and
[072](072-an-audit-of-my-own-derived-counts.md) already showed to be a traversal
artifact with a wall-clock deadline in its lineage — rule 80 territory, and not
worth a row here.

`dateutil` scoring 291 of 291 is not evidence that 004 is fixed. 004's truncated
first period is recorded in the corpus as a rival reading, so `score.py` accepts
it; that is bookkeeping, and it is why the reference's own defect is invisible in
its row as well as inert in the method.

No score on [`RESULTS.md`](../conformance/RESULTS.md) moves. `cases.ndjson` is
untouched, `cases_id` `7bd9731d3a48` and `corpus_id` `48988e689fb2` unchanged.

## Standing rule

**Rule 96 — a failure on a rule carrying part X is not evidence of a defect in X
until the same rule has been asked without X.** A selection step is the visible
one and the set it selects from is not, so a wrong set is reported against the
selector. Deleting the part is one adapter run and it separates them; across this
field it moves 62% of the blame.
