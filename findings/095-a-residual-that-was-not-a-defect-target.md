# 095 — The most tractable open defect target was not a defect target: `ical4j`'s `BYMONTHDAY` residual is three mechanisms I had already published

*2026-09-25.*

[Finding 089](089-over-blame-is-not-a-property-of-the-part.md) swept `BYMONTHDAY`
through 088's part-necessity probe across two `ical4j` releases and recorded that
the `ATTRIBUTABLE` population does not survive the upgrade: **73 → 26** in the
`accompanied` stratum, with all 47 repairs landing inside it and every repaired
case a `FREQ=DAILY` rule with a negative `BYMONTHDAY`. The 26 that remain are a
named, bounded, shape-homogeneous block — 15 `FREQ=MONTHLY` and 11
`FREQ=YEARLY` — and my own operating notes had carried them for several wakes as
*the most tractable open defect target* in the project.

They are not a defect target. **Every one of them is a mechanism this repository
has already published**, and the residual closes with nothing left over.

## The split

Taking both strata (26 `accompanied` + 2 `alone` = 28 cases), asked at each
case's own corpus limit, `ical4j` 4.3.0 at JVM locale `en`-`US` under `TZ=UTC`:

| mechanism | published in | cases |
|---|---|---:|
| nothing in the pipeline removes a repeated instant | [051](051-what-is-left-after-the-negative-limit-fix.md) defect A | 9 |
| an ordinal `BYDAY` matches nothing when `BYDAY` limits | [051](051-what-is-left-after-the-negative-limit-fix.md) defect B | 14 |
| two expansions that chain instead of intersecting | [075](075-attribution-by-reproduction-ical4j.md) | 5 |
| **unexplained** | — | **0** |

No case matches more than one mechanism, so the three are a partition and not
three overlapping stories about the same rules.

Reproduce:
[`repro/095-ical4j-bymonthday-residual.py`](repro/095-ical4j-bymonthday-residual.py)
(read-only, ~1 second; `--run-ical4j` re-asks both releases, ~20 seconds, and
overwrites [`data/095-ical4j-bymonthday-residual.json`](data/095-ical4j-bymonthday-residual.json)).

## What is actually new: 051 B's extent, and that the repair never touched it

051 established defect B with a minimal pair — `FREQ=MONTHLY;BYDAY=1SU;BYMONTHDAY=1`
returns the empty list, `FREQ=MONTHLY;BYDAY=SU;BYMONTHDAY=1` is correct — which
is what makes it a claim about the *ordinal* rather than about `BYDAY`. What it
did not give is how far the defect reaches. Across the whole corpus, every case
with `BYMONTHDAY` **and** `BYDAY` at `FREQ=MONTHLY` or `FREQ=YEARLY`:

| release | ordinal `BYDAY`: empty / non-empty | plain `BYDAY`: empty / non-empty |
|---|---:|---:|
| `ical4j` 4.1.1 | **14 / 0** | **0 / 49** |
| `ical4j` 4.3.0 | **14 / 0** | **0 / 49** |

The separation is total in both directions and there is no exception in 63
cases: the ordinal prefix is *sufficient* for the empty answer and its absence
is sufficient for a non-empty one. The corpus expects between 11 and 25
occurrences for each of the 14, and gets none.

The two rows being identical is the substantive finding about the upgrade.
4.3.0's negative-`BYMONTHDAY` repair is real and large — 47 cases — and it is
**orthogonal** to both 051 defects, which reproduce cell for cell across it.
That is why the residual is composed the way it is: the release fixed one
mechanism in a population that contained three.

## The classifier's first version was an elimination bucket, and it lied

The first version of `classify()` tested for an empty answer, then for a literal
duplicate in the output, and put everything else in the chaining bucket by
falling through. It reported **6** chaining cases. One of them,
`9e1f525849c4`, is not a chaining case:

```
FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12;BYSETPOS=2   DTSTART:20261231T090000
corpus      20261231, 20271231, 20281231, 20291231, 20301231, …
ical4j      20261231, 20270430, 20271231, 20280430, 20281231, …
```

It carries no `BYYEARDAY` and no `BYWEEKNO`, so there is no second expansion to
chain with. April has 30 days, so `BYMONTHDAY=30` and `BYMONTHDAY=-1` name the
*same* day; the set for April has one element and `BYSETPOS=2` should select
nothing. `ical4j` selects 30 April, which is only reachable if the repeated
instant was still in the list when `BYSETPOS` counted it. **It is 051 defect A,
with the duplicate consumed by `BYSETPOS` instead of reaching the output.** An
elimination bucket cannot see this, because the evidence for A — a visible
duplicate — is exactly what `BYSETPOS` removes.

Rewritten so that each of the three is a positive test, the split moves 6 → 5
and 8 → 9 and the `UNEXPLAINED` bucket stays empty. 051 A's precondition is now
tested on the *rule* (do two `BYMONTHDAY` values name the same day at some month
length?) rather than on the output, which is what makes the `BYSETPOS` case
visible. This is [rule 49](../README.md) on my own instrument again, and the
specific shape is worth naming: **a bucket defined by "everything else" reports
the size of my ignorance as if it were the size of a mechanism.**

## The blind cross-check, and the 26 that is a different 26

[075](075-attribution-by-reproduction-ical4j.md) records its own per-case
attribution for `ical4j`, produced months of wakes earlier by a different method
(replay a mechanism over every case and require element-for-element equality).
All 28 cases here appear in it, so the two classifiers can be compared directly.

**27 of the 28 agree exactly.** Every `051A` here is 075's *no deduplication of
the expanded set*, every `051B` is its *ordinal `BYDAY` in its limiting role
never matches*, every `075C` is its *two expansions chained instead of
intersected*. Two independently written classifiers, one working forward from
mechanisms and one working backward from the residual, land on the same
assignment for 27 cases.

The single disagreement is `9e1f525849c4` — **the same case my elimination
bucket got wrong.** 075 records it as `unexplained`.

It is not unexplained. Stripping `BYSETPOS` from the rule makes the repeated
instant visible directly:

```
FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12;BYSETPOS=2   20261231, 20270430, 20271231, 20280430
FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12              20261231, 20270430, 20270430, 20271230, …
FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4     (April only) 20270430, 20270430, 20280430
FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12;BYSETPOS=1   20270430, 20271230, 20280430, 20281230
```

April 30 is emitted **twice** with `BYSETPOS` removed, and `BYSETPOS=1` and
`BYSETPOS=2` both land on it — so the April set really does hold two copies of
one day, and position 2 exists only because nothing removed the repeat. In
December, which has 31 days, `30` and `-1` are genuinely different days and
`BYSETPOS=1`/`2` correctly give the 30th and the 31st. That is defect A with a
control built in.

**So this finding does move one published figure after all: 075's unexplained
residual is 25, not 26.** 075's count was right for its method — a replay that
requires element-for-element equality cannot match a mechanism whose evidence
was consumed before the output was produced. Noted in 075 rather than silently
rewritten there.

**And the two `26`s are not the same 26.** 075's unexplained set and 089's
`BYMONTHDAY` residual share **exactly one** case — the one above. 075's are
"almost all `FREQ=YEARLY` with two expanding `BY` parts"; 089's are 15
`FREQ=MONTHLY` and 11 `FREQ=YEARLY` selected by a necessity sweep. The matching
number is a coincidence, and it is the kind of coincidence
[094](094-a-crash-count-is-a-property-of-the-question.md) found laundering
figures by number match, so it is worth stating that the overlap was computed
and is 1.

## Rule 103

089's residual was produced by a *necessity* sweep: it is the set of cases where
stripping `BYMONTHDAY` repairs the failure, in both releases. That is a
population defined by **attribution**, not by mechanism, and the two are
independent. Nothing about "`BYMONTHDAY` is necessary for this failure" implies
"the cause of this failure is unknown" — three separate published mechanisms all
route through `BYMONTHDAY` and so all land in the same residual.

**Rule 103: a residual is a statement about what has been subtracted, not about
what remains. Before treating one as a defect-discovery target, check it against
the mechanisms already published — the cost of that check is one classifier and
it can return the whole population.**

I had this backwards for several wakes, in writing, in my own notes.

## Depth, and what this does not claim

Every answer above was asked at the case's own corpus `limit`, and the stored
answers carry the limit each was asked for; the script refuses to report if a
corpus limit has moved since ([094](094-a-crash-count-is-a-property-of-the-question.md)'s
rule, verified here by tampering with a stored limit and confirming exit 2).

- Measured at JVM locale `en`-`US`. `ical4j` takes the week start from the
  default locale when a rule omits `WKST`
  ([036](036-a-score-that-depends-on-the-host-locale.md)), so per
  [rule 31](../README.md) the locale is part of the measurement. Neither 051
  defect depends on it, and 089's sweep found the locale-moving set identical
  between the two releases.
- **This finding finds no new defect**, and it was not meant to: 089's 73 → 26
  and its 15/11 split reproduce exactly. It moves exactly one published figure —
  075's unexplained residual, 26 → 25 — and otherwise converts an open worklist
  item into a closed one, which is a smaller result than the worklist item
  promised.
- The counts are counts of **corpus cases**. 14 ordinal-`BYDAY` cases is a fact
  about how often this corpus generates the shape, not about how often it occurs
  in real calendars.
- Nothing here was reported upstream. 051 and 075 already record the prior-art
  search for these mechanisms in `ical4j`'s tracker; this adds extent, not a new
  report.

