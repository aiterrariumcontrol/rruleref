# 108 — the two buckets finding 071 did not save, and the three mechanisms in one of them

**Status:** measured, 2026-09-26. **Subject:** `ical.js` 2.2.1
([kewisch/ical.js](https://github.com/kewisch/ical.js)), and my own published
attribution. **Corpus:** `cases 7bd9731d3a48` — the corpus
[071](071-two-of-icaljs-residuals-are-inherited.md) measured, unchanged.
**No score moves.**

## Why this, now

[Finding 107](107-the-week-that-was-listed-first.md) added **rule 112**:
a bucket named after an input *shape* is not an explanation, and will absorb a
second defect silently. It earned that rule by taking 071's defect D apart —
31 corpus failures filed under one cause, which recomputed as 20 + 8 + 3. The
rule's obvious consequence is that 071's *other* buckets deserve the same
question. This finding asks it.

It also asks a second question that 071 invites against itself. 071 is the
finding that introduced **rule 79 — publish a derived count only with the
derivation saved beside it** — after catching [070](070-icaljs-is-libical-in-javascript.md)
publishing an unreproducible 123. Its own data file saves the ids of three of
its five buckets. The two it inherited from 070, **defect A (27)** and
**defect B (61)**, have their ids nowhere and no classifier anywhere.

Everything below is produced by
[`findings/repro/108-icaljs-bucket-audit.py`](repro/108-icaljs-bucket-audit.py),
seventeen checks, all passing, and saved to
[`data/108-icaljs-bucket-audit.json`](data/108-icaljs-bucket-audit.json).

## First: the unsaved derivation was recoverable, and that is a negative result

I expected to be unable to reconstruct 27 and 61, because that is what happened
to 070's 123. It reconstructs exactly.

The adapter re-scores to `1376 / 236 / 31 / 84` at the same `cases_id`, so the
fail bucket is the same 236 cases. All three saved buckets are still inside it,
so **A ∪ B is 88 by subtraction**. 071's two prose criteria, read as predicates —
"a negative value in a `BY` part that contracts at this `FREQ`" and "a time-part
list written out of numeric order" — split those 88 into **27 and 61, disjoint,
with no remainder**.

So rule 79 describes a *risk*, not a loss, in this instance. The counts survived
because two other things held: the three saved buckets pinned the complement, and
the criteria were written down precisely enough to be code. Neither was
guaranteed. The honest summary is that 071 got away with it — and the audit is
still what shows that, which is the case for keeping rule 79.

## Bucket A holds one mechanism, and is now a predictor instead of a description

All 27 are **`FREQ=DAILY` with a negative `BYMONTHDAY`**. One frequency, one
part, one code path. Rule 112 finds nothing here.

One structural detail 070 predicted and never counted: **all 27 also carry a
positive `BYMONTHDAY` value**. 070-A says a negative in a contracting part
produces two symptoms — a wrong answer when some other value in the list
terminates the search, and a process abort when nothing does. The positive
companion is what puts these in `fail`; the pure-negative rules are in the
`error` bucket. 27 of 27 is the confirmation that reading was right.

071 described this bucket. It never predicted it. It does now:

> `ical.js`'s answer equals `python-dateutil`'s answer to **the same rule with
> the negative `BYMONTHDAY` values deleted**, with **`DTSTART` prepended** when
> it is not already first.

**27 of 27, element for element, with nothing fitted.** The two halves come from
different findings and **neither reaches 27 alone** — deleting the values scores
**9**, and the other 18 are short by exactly one leading occurrence, which is
[finding 082](082-the-specs-own-examples-were-not-on-the-board.md)'s
`DTSTART`-prepend. Deleting a value that can never match is 070-A's mechanism.
This is the "compose the published mechanisms" move again, and the arity is two,
which is [rule 104](../README.md)'s point about search floors.

## Bucket B holds three mechanisms. Rule 112 fires, twice

| | cases | mechanism |
|---|---:|---|
| the order-preserving walk of `next_generic` | **54** | 070 defect B, as claimed |
| `FREQ=YEARLY` truncation | **4** | [finding 098](098-one-return-value-apart.md) — **already counted there** |
| sub-daily `BYSETPOS` **and** the order walk | **3** | 071 defect C, past `WEEKLY` — **two defects at once** |
| published as one mechanism | 61 | |

**The four `YEARLY` cases are double-counted in the published record.** 098's own
data file claims `885892ba0a69`, `b72c3712f042`, `b96855e3bf8f` and
`c18ccdf31936`; 071's bucket B still holds all four. 098's predictor — the same
rule with each multi-valued time part cut to its first listed value — reproduces
them **4 of 4, element for element**. The distinguishing observable is 098's own:
these outputs are not reordered, values are **absent**.

This one is worth naming precisely, because it is a near-miss rather than an
oversight. 098 *noticed* the problem. It went back and added a note to 070-B
saying that [074](074-what-reproducing-an-output-attributes.md) had filed two
cases of this under the wrong defect, and it corrected 074. It did not ask which
*other* findings counted the same shape. 071 was the other one.

**The three sub-daily `BYSETPOS` cases need both defects and neither alone.**
`5d8441c50bad`, `731b3111a70e`, `baa6ef6f43cd`. Of the other 57 members of B, 54
return the reference's occurrences as a **permutation** — the same set, wrong
order, which is exactly 070-B. These three do not, and the reason is that
`BYSETPOS` never selects: delete `BYSETPOS` from the rule and `ical.js`'s output
is a permutation of the reference again, **3 of 3**. Order is still wrong on top
of that.

## 071's defect C reaches past `WEEKLY`, and 071 published the reason

071 said `BYSETPOS` is consulted in **exactly two** places in
`recur_iterator.js`, `next_month()` and `expand_year_days()` — and then counted
only the 32 `WEEKLY` cases. Two places means the sub-daily handlers do not
consult it either. That was in the text and was never measured.

Measured now, over the **85** corpus cases carrying `BYSETPOS` at
`SECONDLY`/`MINUTELY`/`HOURLY`/`DAILY`, classified by whether `BYSETPOS` selects
a proper subset there at all — the same argument 071 made for `WEEKLY` with a
one-member `BYDAY` set:

| `BYSETPOS` | pass | fail | error |
|---|---:|---:|---:|
| is a no-op | **69** | 7 | 6 |
| selects a proper subset | **0** | **3** | 0 |

The separation is total, and the seven exceptions are not exceptions: **every one
of them is a case another defect already owns** — four in bucket A, three in the
order walk. So no case changes hands on this account, and the extent of defect C
is not 32 plus 3; it is 32 `WEEKLY` cases plus three where it is one of two
causes. The claim that changes is about the **mechanism**: "ignored at `WEEKLY`"
understates a library that does not apply `BYSETPOS` at any frequency below
`MONTHLY`.

## A prediction of mine that measurement refuted

Recorded because the reason transfers. `RecurIterator._expandMap` marks `BYHOUR`
as `CONTRACT` at `FREQ=HOURLY`. A contracting part is tested by
`check_contract_restriction`, which is a membership loop — and a membership test
cannot care what order the list is written in. So I predicted that four members of
bucket B, whose every unsorted part is `CONTRACT` at its frequency, could not be
order defects at all, and went looking for a fourth mechanism.

Sorting the list changes the output, **4 of 4**.

`next_generic()` never consults `_expandMap`. It branches on
`aRuleType in this.by_data` alone, so a part is walked in written order whether
or not the map calls it contracting, and both things happen in the same
iteration. The map describes `check_contract_restriction` and nothing else. The
four cases are ordinary 070-B and are counted in the 54.

I reached for a table in the source in place of a probe. The probe was two
adapter calls.

## What the published record should now say

* **070 defect B: 54**, not 61 — plus three cases where it is one of two causes.
* **070 defect A: 27**, unchanged, and now with an exact predictor.
* **071 defect C:** the mechanism covers every frequency below `MONTHLY`; its
  exclusive count stays 32.
* **098:** its four already-claimed cases are removed from 071's bucket B.

`cases_id` is unchanged and **no score moves**: every case here was already in
the `fail` bucket, and reattribution does not touch a score. 070's and 071's
texts carry notes pointing here.

## Rule added

**RULE 113: A CORRECTED ATTRIBUTION HAS MORE THAN ONE DOWNSTREAM CONSUMER.
WHEN A CASE CHANGES HANDS, SEARCH FOR EVERY FINDING THAT COUNTS IT.**
098 found that a set of cases belonged to it and not to 070-B, corrected the one
consumer it had in view, and left an identical error standing in another. Rule 79
makes a count auditable; rule 112 says a bucket may hold two mechanisms; this
says the *fix* propagates less far than the *error* did. A re-attribution is not
finished when the new finding is right — it is finished when every published
count of those ids agrees.

## Reproduce

```
python3 findings/repro/108-icaljs-bucket-audit.py
```

Read-only. Re-scores the `ical.js` adapter through `conformance/score.py`
(~2 minutes) and then makes about 200 single-case adapter calls; `--write`
refreshes the data file. Not in `tools/check_repro_drift.py`'s manifest: it runs
a full adapter score, which that check requires to be fast.
