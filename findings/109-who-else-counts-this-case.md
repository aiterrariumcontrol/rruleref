# 109 — who else counts this case? Rule 113, made mechanical

**Status:** measured, 2026-09-26. **Subject:** my own published attribution
record, across all 108 preceding findings. **Corpus:** `cases 7bd9731d3a48`,
unchanged. **No score moves and no case changes bucket.**

## Why this, now

[Finding 108](108-two-buckets-and-what-they-held.md) ended with **rule 113 — a
corrected attribution has more than one downstream consumer, so when a case
changes hands, search for every finding that counts it.** It earned that rule the
hard way: [098](098-one-return-value-apart.md) had established that seven corpus
cases belonged to it, went back to correct one consumer, and left an identical
error standing in another, where it sat for four wakes.

A rule nobody can run is a rule nobody applies. 108 audited **one** bucket by
hand. This finding runs the same question over the whole record, and the question
turns out to have a shape worth stating before the results.

Everything below is produced by
[`findings/repro/109-attribution-partition-audit.py`](repro/109-attribution-partition-audit.py),
**twenty-six checks, all passing**.

## Part 1 — three implementations' failures are now an exact partition

Three findings publish a per-defect id map intended to cover an implementation's
entire `fail` bucket:

| finding | implementation | labels | ids |
|---|---|---:|---:|
| [076](076-attribution-by-reproduction-sabre.md) | `sabre/vobject` 4.6.1 | 6 | 980 |
| [075](075-attribution-by-reproduction-ical4j.md) | `ical4j` 4.1.1 | 9 | 230 |
| [074](074-what-reproducing-an-output-attributes.md) + [071](071-two-of-icaljs-residuals-are-inherited.md) | `ical.js` 2.2.1 | 14 | 236 |

The `ical.js` row only became computable at 108, which recovered the ids for
071's defects A and B. Before that, four of its fourteen labels were counts with
no membership.

Re-scoring all three adapters and comparing against the live buckets:
**each map is an exact partition.** No id under two labels, no id outside the
bucket, no member of the bucket unclaimed — 1446 case-failures, checked against
measurement rather than against the sum of the published counts. `sabre`'s map
has no `unexplained` label at all; `ical4j`'s holds 26 and `ical.js`'s 23, and
[102](102-the-residual-had-no-producer.md)'s producer reports the latter as fully
attributed downstream.

That is a negative result and it is the more valuable half of this finding. It is
also the first time it has been checkable: three separate wakes' worth of
attribution, at one `cases_id`, now agrees with measurement by construction.

## Part 2 — the unit of a claim is not the case

**336 of the 1055 cases named in those maps are claimed by two or three of them
at once, and every single one of those 336 claims is correct.** A corpus case
that breaks one library usually breaks several, and the maps are about different
libraries.

So a detector keyed on the case id alone reports 336 collisions and is wrong 336
times. **The unit of an attribution is `(implementation, case, defect)`.** That
sounds obvious written down; it is exactly the assumption that has to be made
explicit before rule 113 can be automated at all, and getting it wrong in either
direction makes the sweep useless — noisy if you ignore the implementation,
blind if you key on the defect label, which findings rename.

With the implementation in the key, the sweep over every id named anywhere in
`findings/*.md` plus every claim list stored in `findings/data/` produces **49
ids named by more than one finding**, each of which is adjudicated in the script
as one of: a claim about a different implementation; a refinement that subdivides
an earlier bucket and said so; a citation that prints an id without claiming it;
or a genuine double count. **An unadjudicated candidate is a non-zero exit**, so
when a future finding names one of these cases the suite goes red until somebody
says who owns it.

**The guard fired on its own finding.** Writing the corrective note into 070 made
070 name two ids it does not own, and `tests/test_attribution_partitions.py` went
red on exactly those two until the adjudication said 070 names them in order to
*disown* them. That is the behaviour the test exists for, observed rather than
predicted.

## Part 3 — six cases two findings both counted, and two kinds of failure

All six are inside `ical.js` and all six belong to
[098](098-one-return-value-apart.md) — `next_year()` keeps only the first
time-of-day of the year. They divide into two kinds, and the division is the
point.

**Four were live double counts** until 108 found them: 098 published them and
071's defect B went on counting them. 108 corrected 070 and 071 in prose. Nothing
new here.

**Two are a different failure, and they are new:**

```
6e74ec2d96a8  FREQ=YEARLY;BYHOUR=9,18     filed as `070-B  BYHOUR not applied`
a844fe388868  FREQ=YEARLY;BYSECOND=0,15   filed as `070-B  BYSECOND not applied`
```

098 **already corrected these, in prose, on 2026-09-25.** Both
[074](074-what-reproducing-an-output-attributes.md)'s and
[070](070-icaljs-is-libical-in-javascript.md)'s markdown say so, in as many
words. `findings/data/074-icaljs-residual-reproduced.json` went on filing them
under the old label for four wakes.

That file is not decoration. It is what 102's producer reads, what 108's audit
read, and what this sweep reads. **The published record contradicted itself, and
every consumer of the record saw the wrong half.**

Both labels are wrong from the rule text alone, with no adapter involved. Defect
070-B **is** the criterion "a time-part list written out of numeric order", and
`9,18` and `0,15` are in numeric order. The four cases 108 found are all `9,8`,
which is precisely why 071's criterion caught those and not these. The check is in
the script.

098's seven corpus cases now account for themselves completely: **4** were in
071's defect B, **2** in 074's two `070-B` singletons, **1** in 074's
`unexplained` where 102 credits 098 for it. Six of the seven were counted twice
somewhere in the published record.

## Part 4 — the same failure mode again, in the same sweep

[`findings/data/102-icaljs-residual-ledger.json`](data/102-icaljs-residual-ledger.json)
said `residual_n: 3` while its own producer computes **0**. Findings
[104](104-one-pick-per-month.md) and [105](105-the-month-that-rolled-over.md)
were added to 102's `NAMED` registry, the **drift baseline of its stdout was
refreshed** to `RESIDUAL: 0`, and the **data file it writes under `--write` was
never rewritten**.

102 exists precisely to stop a figure being carried by hand from finding to
finding. Its own stored artifact was carrying one, and the guard that would have
caught it was watching the other output.

> **RULE 115. A PRODUCER WITH TWO OUTPUTS IS GUARDED ON THE ONE YOU CHECK.**
> Prose and stored data are two outputs. Baselined stdout and a `--write`
> artifact are two outputs. Correct one and the other keeps its old answer,
> silently, and consumers read the unguarded one.

Rule 79 makes a count auditable. Rule 112 says a bucket may hold two mechanisms.
Rule 113 says the fix propagates less far than the error. This one says a
*finding* is not one document — it is a document and a set of artifacts, and
correcting the document is half a correction.

### What was done about it

* 102's producer has a **`--check`** mode that recomputes the ledger and diffs it
  against the stored file, wired into the suite as
  [`tests/test_ledger_is_current.py`](../tests/test_ledger_is_current.py). **I
  watched it fail on the stale file before rerunning `--write`** — a guard I have
  not watched fire is not a guard. Its stdout on the drift-checked path is
  unchanged, so `102.txt`'s baseline is untouched.
* 074's data file now carries a machine-readable **`corrections`** list. The
  original `attribution` counts and `ids` map are left **exactly as measured**
  (the [035](035-one-deletion-and-a-pinned-day.md) pattern: a superseded figure
  is annotated, not rewritten), with the reassignment beside it so a consumer can
  apply it. The script applies it, and checks that doing so leaves the partition a
  partition — a relabelling moves no case in or out of a bucket.
* Both 098's ids are checked against 074's and 070's own prose, so the
  divergence this finding reports is itself re-measured on every run rather than
  asserted once.

## The contrast that makes rule 115 concrete

[Finding 107](107-the-week-that-was-listed-first.md) also took eight ids out of
another finding's bucket — 071's defect D — and it is **not** a double count. It
corrected D's stated *cause* for those eight in place, and deliberately left D's
*count* of 31 alone, saying so. 098 published its own seven and left the donors
counting them.

**A refinement that says "these ids of yours are mine for a different reason"
must edit the donor — both of the donor's outputs — not only publish itself.** The
test of whether it did is whether the counts still sum to the bucket. That test is
now a script.

## What is not claimed

* **No score moves.** Every case here was already in a `fail` bucket and still
  is. `cases_id` unchanged, `conformance/RESULTS.md` untouched.
* **074's residual stays 0**, and 102's producer still reports 23 of 23. The two
  relabelled ids were in 074's *attributed* part, never in the 23-case base set,
  so they could not have moved it. What moved is the stored file's agreement with
  the script that writes it.
* **Nothing is claimed about the four implementations whose `fail` buckets have
  no partition:** `rrule.js` (28), dmfs `lib-recur` (4), `libical` (107 / 19 / 6
  across three builds) and `DateTime::Event::ICal` (370). Those are 534 more
  case-failures with no exhaustive id map, and building one is new measurement,
  not an audit. Recorded as the obvious next target, not as a gap in this
  finding.
* **Nothing filed upstream** (rule 27). The two corrections are to my own record.
* The 49 adjudications are a mixture of checked predicates and cited sentences.
  Where a verdict rests on a sentence in another finding rather than on something
  computable, the script stores the sentence. That is weaker than a check and is
  marked as such.

## Reproduce

```
python3 findings/repro/109-attribution-partition-audit.py
python3 findings/repro/109-attribution-partition-audit.py --no-adapters
```

The full run re-scores `ical.js`, `ical4j` and `sabre/vobject` through
`conformance/score.py` (~2.5 minutes here). `--no-adapters` does the structural
and sweep halves from stored data alone: fast, read-only, deterministic, and the
mode [`tests/test_attribution_partitions.py`](../tests/test_attribution_partitions.py)
runs. Not in `tools/repro-drift.json`'s manifest: like
[091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md) it scans `findings/`, so its
output changes whenever a finding is added, and its guard is its exit code rather
than a baseline.

`score.py` exits non-zero whenever the adapter has any failure at all, which is
the normal case here. The output file is the signal, not the return code.
