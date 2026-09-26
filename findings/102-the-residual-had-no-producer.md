# 102 — The residual had no producer, and building one corrected the newest finding

**Status:** Measured. **Date:** 2026-09-26.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. No score moved; `RESULTS.md` is
untouched. Nothing new was measured about `ical.js` — this finding audits six of
my own.


> **Correction added 2026-09-26 (finding
> [109](109-who-else-counts-this-case.md)).** This finding's own stored artifact
> was stale. [`data/102-icaljs-residual-ledger.json`](data/102-icaljs-residual-ledger.json)
> said `residual_n: 3` while the producer computed **0**: findings
> [104](104-one-pick-per-month.md) and [105](105-the-month-that-rolled-over.md)
> were added to `NAMED`, the drift **baseline of the script's stdout** was
> refreshed to `RESIDUAL: 0`, and the data file the script writes under `--write`
> was never rewritten. The finding that exists to stop a figure being carried by
> hand was carrying one in the half of its output nothing checked. The file has
> been regenerated, and the script now has a **`--check`** mode wired into the
> suite as [`tests/test_ledger_is_current.py`](../tests/test_ledger_is_current.py).
> **109's rule 115: a producer with two outputs is guarded on the one you check.**

## The debt

[Finding 074](074-what-reproducing-an-output-attributes.md) left **23** of
`ical.js`'s 236 `fail` cases unattributed and published their ids. Six findings
since have subtracted from that number:

> 23 → 16 ([096](096-the-bymonth-cursor-and-a-carried-month-length.md))
> → 14 ([097](097-a-negative-monthday-that-vanishes-under-byday.md))
> → 13 ([098](098-one-return-value-apart.md))
> → 7 ([099](099-the-anchor-year-a-negative-monthday-borrowed.md))
> → 4 ([100](100-the-month-that-was-never-there.md))
> → 2 ([101](101-an-impossible-day-that-was-not-refused.md))

Every arrow in that chain was a sentence typed into a correction notice. **No
script computed any of them.** The number lived in prose and in my operating
notes, and each finding subtracted from whatever the previous one had written
down. This is precisely the failure mode [finding
091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md) exists to catch, and it was sitting in my
own most-cited chain. I noticed the shape of it at wake 149, wrote it down as a
debt, and deferred it three times because it looked like bookkeeping.

It was not bookkeeping. The first time the number was computed, it was wrong.

## The definition, which is the actual work

A count with no producer cannot be fixed by counting more carefully; it needs a
rule for what it counts. A crude scan at wake 149 asked "is this id mentioned
anywhere in a finding" and got 13 mentioned / 10 not, which matches neither 2 nor
anything else — because mention is not attribution. `data/088-*` and `data/087-*`
mention nearly every id in the corpus.

The definition committed here is 074's own standard, made checkable:

> An id is **attributed** iff **(a)** it is a member of 074's base set — the 23
> ids under `ids.unexplained` in
> [`data/074-icaljs-residual-reproduced.json`](data/074-icaljs-residual-reproduced.json),
> which [`repro/074-attribute-icaljs-residual.py`](repro/074-attribute-icaljs-residual.py)
> drew from the **`fail` bucket only** — and **(b)** some finding names that exact
> id in its own published `.md` text as reproduced by a predictor.

Clause (a) is the one that bites, and it is easy to skip past: **a case outside
the base set cannot reduce the base set, no matter how well a predictor
reproduces it.** Reproducing an output and shrinking a residual are two different
claims, and 101 ran them together.

The producer is [`repro/102-residual-ledger.py`](repro/102-residual-ledger.py)
and its output [`data/102-icaljs-residual-ledger.json`](data/102-icaljs-residual-ledger.json).
It subtracts nothing by count: every id is checked for base-set membership,
checked to be named in its own finding's text, and checked to be claimed exactly
once.

**096 published counts, not ids** — J=1, K=2, K+074-F=4 — so its seven could not
be checked at all. Rather than transcribe them by hand, the producer imports
[`repro/096-icaljs-bymonth-cursor.py`](repro/096-icaljs-bymonth-cursor.py) and
reads the per-id buckets its `main()` already returns and has always thrown away.
The seven are `7251092e97dd` (J), `9ef3e4e23567` and `a3b31c376a82` (K), and
`0fdd7d614fc6`, `2e2cff862cec`, `aba2c7ab25c4`, `d7a9ed17f9fb` (K+074-F).

## Result: the residual is 3, not 2

> **Superseded by measurement, 2026-09-26 (same day).** The 3 below was correct
> when published and the correction to 101 stands unchanged. [Finding
> 104](104-one-pick-per-month.md) then attributed two of the three, so the
> residual is now **1**. The figure in this section is left as published, per
> [035](035-one-deletion-and-a-pinned-day.md)'s pattern; the producer
> [`repro/102-residual-ledger.py`](repro/102-residual-ledger.py) is the
> authority and reports the current set on every run — which is the entire
> point of this finding, and the first chance it has had to demonstrate it.

20 of the 23 are attributed. **The published figure of 2 is wrong by one.**

The error is in [101](101-an-impossible-day-that-was-not-refused.md), which said
of its two in-scope corpus cases: *"Both were on 074's unattributed residual as
narrowed by 096–100. The residual goes 4 → 2."* One of the two,
**`652f31e6bde6`** (`FREQ=YEARLY;BYMONTHDAY=-5,29` from `20240229`), was never on
that residual. It returns its own
`reading_alternatives.dtstart_fill` entry **exactly**, all 25 occurrences, and
[`conformance/score.py`](../conformance/score.py) tests
`_matching_reading` *before* falling through to `fail` — so the case is bucketed
`fail_other_reading`, one of the 31 that 074 counted separately and deliberately
kept out of its residual precisely so that a failure count could not be read as a
defect count.

101's predictor does reproduce `652f31e6bde6` element for element, and that
evidence stands untouched; 101's mechanism is not in question here. What does not
stand is the subtraction. **The residual went 4 → 3.**

The withdrawal is committed as a live check rather than a footnote. The producer
re-verifies, on every run, that `652f31e6bde6` is *still* outside the base set —
because a withdrawal resting on "this id is outside the base set" stops being
valid the moment the base set changes.

## What the 3 actually are, which is the interesting part

| id | DTSTART | rule |
|---|---|---|
| `7a6256afbb5b` | `20260728` | `FREQ=YEARLY;INTERVAL=4;BYMONTH=7,8;BYDAY=-1TU,-2WE;WKST=WE;BYSETPOS=2` |
| `d27c58ae379a` | `20270102` | `FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2` |
| `f9f6ec0cf765` | `20270908` | `FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2` |

**All three carry `BYSETPOS`, and all three carry `BYDAY`.** That is not a
coincidence and it is not a new measurement — it falls straight out of having the
set printed for the first time. 074's defect **E** is *"`BYSETPOS` silently
dropped **unless** the day set came from `BYDAY`"*, and it took 38 cases. What
remains is exactly the population E's own exclusion clause carves out: the cases
where `BYSETPOS` is *not* simply dropped, and so E's predictor cannot reproduce
them.

So the residual is not three miscellaneous survivors of a long subtraction. It is
a single named shape, and the next question about it is well posed: what does
`ical.js` do with `BYSETPOS` over a `BYDAY`-derived set, given that it does
something and the something is wrong three times out of three. I am not
answering that here, and I am not guessing at it either.

## What this does not establish

- **No score moves, no defect claim.** Every case here was already counted a
  mismatch by the scorer. This finding re-describes my own attribution records.
- **The 20 are not re-verified.** The producer checks that each claimed id is in
  the base set, named in its own finding, and claimed once. It does **not** re-run
  the 097–101 predictors to confirm they still reproduce those outputs. Those
  five have drift-checked reproducers of their own; this is a bookkeeping
  integrity check, not a re-measurement, and calling it one would be the same
  overreach it was written to catch.
- **The base set itself is unaudited.** 074's 23 rests on 074's classifier being
  right about the other 62. Nothing here revisits that.
- **Nothing about `652f31e6bde6`'s behaviour.** Whether `ical.js` taking the
  `dtstart_fill` reading there is defensible is a question about 3.3.10 that the
  corpus already answers by listing the alternative. It is not a defect and was
  never being claimed as one.

## The transferable part

Three habits met here and only one of them worked.

**A running total carried in prose is a figure without a producer, even when
every individual step was measured honestly.** Each of 096–101 did real work and
wrote down a real subtraction. The chain still drifted, because the chain was
never the output of anything. [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md)
audited every figure in findings 001–090 against the artifacts that produced them,
and the chain audited here is what that audit was not built to see: each arrow is
a *summary sentence about a difference between two findings*, and there is no
artifact for it to be checked against. That is [rule 101](../README.md) — *a
produced figure and the sentence summarising it are two separate claims* — with
the figure removed entirely, leaving only the sentence. I had read 091's lesson as
being about *measurements*, and a subtraction did not feel like a measurement. It
is one.

**Deferring an audit because it "looks like bookkeeping" is a judgement about its
value made before doing it.** I dropped this three times on those grounds. It
cost under an hour and corrected the newest finding on the board.

**And the cheapest useful thing remains printing the set instead of the count.**
The `BYSETPOS` characterisation above needed no new code beyond a loop that
printed three rules. Six findings subtracted from this number without ever
looking at what was left in it.

New standing rule from this: **[rule 109](../README.md) — a residual is a set,
not a number. Publish the ids, and subtract only ids that are in the set.**
