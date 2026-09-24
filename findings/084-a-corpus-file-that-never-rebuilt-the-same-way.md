# 084 — a corpus file that never rebuilt the same way

**Date:** 2026-09-24
**Files:** `corpus/date-value-type.json`, `corpus/rfc5545-examples.json`,
`src/datevalue_cases.py`, `src/rfc_worked_examples.py`, `src/builds.py`,
`corpus/SCHEMA.md`, `corpus/VERSION.json`,
`tests/test_corpus_reproducible.py`

Finding 083 ended with an item left deliberately undone: the twelve scorable
DATE-value-type rules had nine to thirteen independent witnesses where the
corpus file recorded two, and adding them was the obvious next pass. This is
that pass. It took about ten minutes. The rest of this finding is what the
rebuild exposed on the way.

## The plan was wrong before it started

The note I left said "add them to `corroborated_by`". That field is
**provenance** — it names the two expanders that produced `expect`. The
thirteen builds are the **subjects**: they are what `conformance/RESULTS.md`
grades. Putting a subject into the provenance field would have made the corpus
look as though it had been built from the implementations it scores, and a
reader could no longer have told an expectation derived from the specification
from one derived from a majority vote of the field. Circular, and quietly so:
every individual entry would have been a true statement about agreement.

So the witnesses went into a new field, `reproduced_by`, in both files, and
`corpus/SCHEMA.md` now states the separation and why it is load-bearing.
`tests/test_corpus_reproducible.py` checks the two sets stay disjoint rather
than leaving it to care.

`null` rather than a list means the rule cannot be posed on the conformance
wire at all — two DATE-valued `UNTIL`s here, eight floating or `UNTIL=...Z`
forms in the RFC set. That is a property of `conformance/PROTOCOL.md`, not of
the case. It is the same gap findings 082 and 083 are about.

## The file was not reproducible, and had never been

Both generators write their file from scratch, so the way to attach witnesses
is to have the generator read the finding's measurement file. I ran
`src/datevalue_cases.py`, diffed against the committed file expecting one new
field, and got two:

```
case fields changed: {'reproduced_by', 'observed'}
```

`observed["rrule.js-2.8.1;VALUE=DATE"]` had moved in sixteen of eighteen cases:

```
before  20260906T174049, 20260907T094049, 20260907T174049, ...
after   20260925T095426, 20260925T175426, 20260926T095426, ...
```

The minutes and seconds — `54:26` — are the wall clock of the run, to the
second. rrule.js 2.8.1 accepts `DTSTART;VALUE=DATE:20260105` without parsing
the value, substitutes the current instant, and expands from there. The
recorded sample was a photograph of the moment the file was last built.

So `corpus/date-value-type.json` produced a different `corpus_id` on every
rebuild, for no change in meaning, since the day it was created. Anyone
re-running the generator to verify the id — which is the entire point of
`corpus/VERSION.json` — would have got a mismatch and had no way to tell a real
change from the clock.

## The test that said it checked this

`tests/test_date_value_type.py` opens:

> 2. that `corpus/date-value-type.json` reproduces exactly from the generator,
>    so the file is a record and not a hand-edited artifact;

It never runs the generator. It re-derives `expect` from `datevalue.expand` and
compares. That is a real check and it passes, and it is silent on `observed`,
which is the half that was moving. **The claim was true of the half that was
checked and false of the half that was not** — and the docstring is what a
reader would rely on, because re-reading a hundred lines of assertions to find
out what a test does not do is exactly what nobody does.

Eleven findings in this project now turn on the instrument rather than the
subject. This is the first where the instrument was a *test's description of
itself*.

`tests/test_corpus_reproducible.py` does the only thing that settles it: run
the generator, run it again, compare the bytes, and compare both against what
is committed. Both generated corpus files are now in it.

## Recording the property instead of a sample of it

The fix is not to freeze the sample — freezing it would preserve a false
record, a set of occurrence dates that never meant anything. The clock-seeding
is a genuine and reportable property of rrule.js, so it is recorded as one:

```json
"rrule.js-2.8.1;VALUE=DATE": {
  "clock_seeded": true,
  "note": "rrule.js 2.8.1 accepts `DTSTART;VALUE=DATE:` without parsing the
           value and expands from the instant of the run instead. ..."
}
```

Detected, not assumed: `is_clock_seeded` fires only when the first occurrence
is dated on or after the run itself, which no honest expansion of a `BASE` or
`LEAP` start can be. `assert_clock_is_ahead` refuses to run at all if that
inequality could invert.

**The first version of this fix destroyed a measurement.** I dropped the sample
inside the observation function, before scoring, and the summary moved from
"wrong days 16/18" to "18/18". Cases 13 and 14 are `FREQ=YEARLY;BYYEARDAY=1,-1`
and `FREQ=YEARLY;BYWEEKNO=1,53;BYDAY=MO`: those rules determine their own dates
without reference to the start, so rrule.js gets the **days** right even from a
substituted instant and only the times are junk. Scoring now happens on the raw
output and the property is published in its place, so
`observed_same_days` and `observed_midnight_only` are bit-for-bit what they
were. That two-case gap is pinned by name in the new test, because it is the
part a future simplification would delete first.

It was caught by watching a summary line move, not by rereading the diff.

## Result

Both files rebuild byte-identically, twice in a row and against what is
committed. `corpus_id` moves once, deliberately:

| | before | after |
|---|---|---|
| `corpus_id` | `767afd18df89` | `7d959ef1a533` |
| `cases_id`  | `7bd9731d3a48` | `7bd9731d3a48` |
| `scorer_id` | `434342bbd198` | `434342bbd198` |

`cases.ndjson` is untouched and **no score on `RESULTS.md` moves.**
`corpus/VERSION.json` is at 1.0.1.

Witnesses attached: 16 DATE-value-type cases (9–13 builds each, 2 not posable)
and 34 RFC example rules (11–13 builds each, 8 not posable).

`src/builds.py` is new and holds the one mapping from the audit tools' short
build ids to the names `RESULTS.md` prints. It raises on an unknown id instead
of passing it through, because a silent rename is how a witness list starts
crediting the wrong version.

## Standing rules

**Rule 89 — a generated file is not reproducible until something has rebuilt
it twice and compared the bytes.** Re-deriving the *expectations* and finding
them stable is a different, weaker claim, and it is the one that is easy to
write and easy to mistake for this one.

**Rule 90 — when a value drifts between runs, record the property, not a
sample of it; and score the sample before you throw it away.** The drift is
usually the interesting result. Dropping it early is tidy and loses real
measurements — it lost two here, in the first version of this fix, and the only
reason I noticed is that a summary count moved by two.
