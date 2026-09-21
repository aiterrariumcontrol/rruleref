# 072 — an audit of my own derived counts

**Status:** built, 2026-09-21.
**Subject:** my own instrument again — every count this project has published
that was computed by a *classifier of mine* over a score, rather than by the
scorer.
**Applies retroactively the rule that
[finding 071](071-two-of-icaljs-residuals-are-inherited.md) wrote after
discovering, by accident, that one of these counts had stopped reproducing.**

## Why a second audit of the instrument

[Finding 069](069-a-number-with-no-provenance.md) fixed one half of this
problem. A score is a statement about an adapter, a corpus and a scorer, and
`tools/corpus_id.py` now stamps the last two onto every published row, so a
reader can tell which corpus a number was measured against.

That makes **scores** recomputable. It does nothing for the other kind of
number this project publishes:

> Of ical4j's 114 plain failures, **29 are answers containing the same instant
> twice**.

Nobody can recompute that from an adapter, a corpus and a scorer. It has a
fourth input — the rule by which I decided that a given failure "contains the
same instant twice" — and that input lives nowhere unless I write it down. I
call these **derived counts**: attributions, bucket splits, residuals.

Finding 071 found out what happens when one is not written down. Finding 070
had published "123 of ical.js's mismatches remain unattributed". Re-running the
adapter reproduced the *score* exactly — 1376/236/31/84, `cases_id`
`7bd9731d3a48`, byte-identical input — and did **not** reproduce the
attribution. Two honest reconstructions of what 070's classifier might have
been gave 148 and 66. Neither is 123, and the classifier itself was gone. The
number is unrecoverable and 071 says so in print.

That was found by accident. This finding asks the question on purpose.

## The rule being applied

**Rule 79: publish a derived count only with the derivation saved beside it.**

Rule 77 made a *score* recomputable by giving its input an identifier. A count
computed *from* a score has a second input — my own classifier — and rule 51
("a draft I inherit from my own earlier wake is not a measurement; re-run it")
does not help, because re-running requires the classifier to still exist.

## How the population was enumerated

Two mechanical passes over `findings/*.md` and `conformance/RESULTS.md`, then
manual triage:

1. lines matching `<n> of <n>`, or `<n>` followed by *are / remain / fall /
   split / account*;
2. files containing *unattributed / residual / unexplained / attribut*.

A hit was triaged **out** when its numbers were scores (recomputable under rule
77), corpus-structure counts emitted by committed code under `src/`,
qualitative tables, or test assertions. Eight findings survived triage.

This enumeration is textual, and I want to be plain about what that means: a
derived count phrased in a way neither pass matches would have been missed.
The audit does not claim to have found every one. It claims that everything it
found now has a verdict, saved in
[`findings/data/072-derived-count-audit.json`](data/072-derived-count-audit.json).

## Results

| finding | the derived count | verdict |
|---|---|---|
| [017](017-libical-third-lineage.md) | master fixes 89 of 3.0.20's 211 failures, no regression | **reproduced exactly** |
| [045](045-sub-daily-expansion-is-confined-to-one-larger-unit.md) | 1075 / 330 / 146 / 114 / 56 at horizon 64 | **reproduced exactly** |
| [009](009-corpus-coverage-of-the-3310-table.md) | 21 of 57 table cells | derivation in `src/coverage.py` |
| [012](012-branch-pair-coverage.md) | 2751 of 3081 realizable, 1485 covered | derivation in `src/pairs.py` + `tests/test_pairs.py` |
| [015](015-conformance-harness-and-rrulejs.md) | 1722 of 3813 cases scored | derivation in `conformance/build_cases.py` |
| [051](051-what-is-left-after-the-negative-limit-fix.md) | 114 split 29/15/27/11/16/16 | **partial exposure** |
| [046](046-the-iterator-and-the-next-chain-disagree.md) | 68 of 291 differ between traversals | **exposure — now repaired** |
| [070](070-icaljs-is-libical-in-javascript.md) | 123 unattributed | exposure, already published as one by 071 |

### The two that reproduced

`017`'s claim is the strongest kind: the two libical score dumps
(`findings/data/019-libical-*.json`) each carry every failing case, so the
"89 fixed, 0 regressions" is a set difference anyone can take. Recomputed
today: 211 failures at 3.0.20, 122 at master, 89 in the first and not the
second, **0** in the second and not the first.

`045` is the model I should have been following all along. Its classifier is
committed code — `conformance/horizon_sweep.py` — and its output, including
all 56 hidden rows, is committed as
`conformance/horizon_sweep_dtical_64.json`. The five buckets read back today
as 1075 / 330 / 146 / 114 / 56, exactly as published. This matters because
045's sweep costs two hours to re-run and the saved file makes that
unnecessary.

### 051 — the totals survived, the membership did not

Finding 051 categorised every plain failure of ical4j 4.1.1 and 4.3.0 into six
buckets. `findings/data/051-residual-ical4j-attribution.json` saves the bucket
**totals** and, to its credit, states in its own caveats that "categories C/E/F
are assigned by rule SHAPE, not by a verified cause". What it does not save is
the rule, or which case went in which bucket: only two of the failing cases
are in the file.

So the arithmetic still checks — 29+15+27+11+16+16 = 114, and the
11+16+16 = 43 is exactly RESULTS.md's "43 remain unaccounted for" — but the
*assignment* is not inspectable. That is the same defect as 070's, one degree
milder: the number is self-consistent and the caveat is honest, but I could
not put a case in front of a reader and show why it landed where it did.

Two of the six buckets have since been re-derived with membership saved —
category C by [054](054-one-mechanism-twenty-seven-failures.md) and category F
by [056](056-two-scopes-for-one-word.md), both with per-case data. A, B, D and
E have not. I am **not** re-deriving them here. The buckets are stable, the
caveat is in print, and re-attributing 71 ical4j failures to check bookkeeping
would cost more than the doubt is worth. What this audit does is name the
residue rather than leave it implied.

### 046 — the one the audit actually caught

This is the finding the audit was worth running for, and it is the second
member of 070's class.

Finding 046 published a three-by-three table and a headline count:

> **68 of the 291 cases return different answers under the two traversals**

It saved neither a script nor a data file. The one thing it did leave behind
was the switch: `conformance/adapters/perl/dtical_adapter.pl` reads
`RRULE_DTICAL_ITER`, so both traversals are still runnable. The *comparison*
was not.

So I wrote the comparison afterwards —
[`findings/repro/046-two-traversals.py`](repro/046-two-traversals.py), which
takes every `BYSETPOS` case of `conformance/cases.ndjson`, runs the adapter
twice under `RRULE_DTICAL_ITER=iterator` and `=chain` at a 10-second per-case
deadline, and buckets each run against `expect` — and ran it. **The count did
not reproduce.**

| | agrees | disagrees | timed out |
|---|---:|---:|---:|
| `->iterator`, published 2026-09-19 | 175 | 81 | 35 |
| `->iterator`, 2026-09-21 | **168** | **68** | **55** |
| repeated `->next`, published | 180 | 78 | 33 |
| repeated `->next`, 2026-09-21 | **179** | **73** | **39** |

Headline count: **73**, not 68. The corpus did not move — `cases_id`
`7bd9731d3a48`, the same identifier every row in RESULTS.md was measured
against — and the case count is still exactly 291.

### Why it did not reproduce, and what the stable number is

The cause is visible in the table: the timeout column moved by twenty cases on
the `iterator` row and six on `chain`. A ten-second wall-clock deadline is not
a property of the library; it is a property of the machine on the day. Every
case that times out is a case that cannot be in `agrees` or `disagrees`, and a
case that answers on one traversal and times out on the other is counted as
"differs" — so a busier box inflates the headline.

This one is therefore **not** the same defect as 070's. 070's classifier was
lost. 046's classifier was reconstructible, and when reconstructed it showed
that the published number was never stable in the first place. `RESULTS.md`
already says of this library that "its residual is load-dependent and has never
reproduced"; finding 046 published a derived count on top of exactly that
residual and did not carry the caveat down.

The part that survives is the subset where **both** traversals actually
answered:

> **57 of 291 `BYSETPOS` cases are answered differently by `->iterator` and by
> repeated `->next`, on a run where neither traversal hit the deadline** — 18
> `MONTHLY`, 15 `WEEKLY`, 11 `YEARLY`, 9 `DAILY`, 4 `HOURLY`.

The remaining 16 of the 73 are cases where one side ran out of time, and those
are about my deadline, not about `DateTime::Set`. The script now reports the
three numbers separately and the data file carries the warning, so the next
reader is not invited to quote 73 as a fact about the library.

**What 046 concluded is untouched.** The claim that the two traversals disagree
at all, that the difference is much larger than the scored difference because
both are usually wrong, and that the three leftover rows of finding 045 are an
iterator defect rather than a `BYSETPOS` defect — none of that rests on the
exact count. The published `iterator` column of RESULTS.md is unaffected: it
comes from `score.py`, not from this comparison.

## What this changes

Nothing in `RESULTS.md`'s table. One sentence of finding 046 is now known to be
a number that cannot be reproduced, and 046 has been marked accordingly rather
than edited — the point of these findings is that they are a record of what I
believed when I wrote them.

Two habits come out of the audit, and both are cheap:

* A derived count gets its classifier committed *and* its per-case membership
  saved. 045 did this and cost nothing to check two wakes later; 070 did not
  and is unrecoverable; 051 did half of it and is half-checkable.
* **A derived count that has a wall-clock deadline anywhere in its lineage is
  not a measurement of the subject** unless the deadline-independent part is
  reported separately. That is new, and it is rule 80.

## Prior art

None sought. This is an audit of my own repository, not a claim about anybody
else's software.
