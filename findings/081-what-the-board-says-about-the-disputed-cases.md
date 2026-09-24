# 081 — What the board says about the disputed cases

**Status:** the 28 cases in `corpus/disputed.json` measured against twelve
builds for the first time. Two verdicts amended from `naive` to `undecided`;
one stale figure on `RESULTS.md` corrected. No new defect claim is filed
against any implementation here.
**Date:** 2026-09-24. **Tool:** `tools/audit_disputed.py`.

## The blind spot

`conformance/build_cases.py` selects cases that are *corroborated* — the two
expanders agreed — and every row on
[`RESULTS.md`](../conformance/RESULTS.md) is a run over that selection. So the
28 cases in `corpus/disputed.json` have never appeared in any adapter run in
this repository. They are the only part of the corpus where the answer is a
judgement of mine rather than an agreement, and they were the only part no
implementation had ever been asked about.

That is backwards. A verdict on a disputed case is the most fragile thing the
corpus contains, and it was the one thing held furthest from evidence.

This finding closes the gap: all 28 cases, at the corpus's own bound of 25
occurrences, against **thirteen builds** — the twelve on `RESULTS.md` plus
`libical` 3.0.20, whose row is there but whose binary had to be rebuilt against
the system library. 364 answers, none of which existed before.

    python3 tools/audit_disputed.py --emit > disputed.ndjson
    TZ=UTC <adapter> < disputed.ndjson > out.<name>.ndjson
    python3 tools/audit_disputed.py --classify out.*.ndjson

Each answer is classified against the two recorded lists: **N** equals `naive`,
**D** equals `dateutil`, **X** is a third answer, **ERR** is a refusal. There is
no bucket for *close*.

## Two controls, because a recorded dispute can go stale

`disputed.json` records a disagreement as it stood when the case was admitted.
If the library no longer produces its side of it, the verdict is about a version
that no longer exists and the row below means nothing. Both controls are run by
`--classify` on every invocation and both are clean:

* `naive.expand` re-derives the recorded `naive` list on **28 of 28**;
* the `dateutil` adapter re-derives the recorded `dateutil` list on **28 of 28**.

Every disagreement in the file is live.

## The first result: dateutil's answer is dateutil's alone

| | builds | cases | answers equal to `dateutil`'s list |
| --- | --- | --- | --- |
| `python-dateutil` and its three ports | 4 | 28 | **112 of 112** |
| everything else on the board | 9 | 28 | **0 of 252** |

On every case where the corpus's two adjudicators split, the entire rest of the
board declines to join `dateutil` — nine builds, five independent families,
zero exceptions. And the three ports (`rrule.js`, `rrule-go`, `rust-rrule`)
reproduce `dateutil` exactly on all 28, which is worth stating because
[finding 066](066-the-ports-were-not-identical.md) admitted two of these very
cases after finding that the ports were *not* identical elsewhere. They are
identical here.

This is not evidence about what RFC 5545 requires — the whole project turns on
not making that mistake, and five families that disagree with one library are
still just implementations. It is evidence about where the corpus sits: it
does not adjudicate against the field.

## Finding 013: unanimous

Six cases, `BYDAY` mixing a signed weekdaynum with an unsigned one.
[Finding 013](013-byday-mixed-signed-and-unsigned.md) read §3.3.10 as making
the list a union and adjudicated against `dateutil`, which intersects and so
returns an empty set whenever the weekdays differ.

On the three cases with a synchronized `DTSTART`, **all nine non-`dateutil`
builds return `naive`'s 25-instant list exactly.** On the three unsynchronized
twins — where §3.8.5.3 declares the recurrence set undefined and nothing obliges
anyone to agree about anything — six of the nine still do.

That verdict rested on my reading of one sentence. It now has every other
family in this corpus behind it, and that makes the `dateutil` behaviour an
ordinary defect rather than a contested reading.

## Finding 032: corroborated, and `libical` is walking toward it

Ten cases, `FREQ=WEEKLY` with `BYSETPOS`.
[Finding 032](032-a-blind-spot-the-corpus-cannot-see.md) adjudicated to `naive`.

| build | agrees with `naive` (of 10) |
| --- | --- |
| `dmfs lib-recur` 0.17.1 | **10** |
| `libical` master `4edd39a3` | **10** |
| `libical` master `48d52b4b` | 7 |
| `ical4j` 4.1.1 and 4.3.0 | 6 each |
| `DateTime::Event::ICal` 0.13 | 5 |
| `libical` 3.0.20 | 0 |
| `ical.js` 2.2.1 | 0 |
| `sabre/vobject` 4.6.1 | 0 |
| any `dateutil` build | 0 |

Two independent families reproduce the adjudicated answer exactly and in full.
The more useful column is `libical`'s: **0, then 7, then 10** across three
builds of one library in commit order. The verdict is not a place where the
corpus and the field disagree; it is a place the field has been moving toward.

`ical.js` 2.2.1 scoring 0 while its own upstream master scores 10 is the same
observation as [finding 070](070-icaljs-is-libical-in-javascript.md) from the
other side: the port carries 3.0.x behaviour, and on this block that is the
behaviour `libical` has since left.

## Finding 008 and 033: no corroboration at all, and that is the honest part

Twelve cases are `FREQ=YEARLY` with `BYWEEKNO`. **Not one build agrees with
`naive` on any of them.** Most refuse the rule outright — `libical` master
answers `UNIMPLEMENTED`, `dmfs` throws *too many empty recurrence sets*,
`libical` 3.0.20 cannot even parse it — and the rest return third answers.

This does not refute [finding 008](008-byweekno-previous-year-last-week.md).
Its argument is about ISO week numbering and is checkable against the calendar
rather than against a population, and a library that declines to implement
`BYWEEKNO` is not a witness. But it is the shape of the evidence and it belongs
on the record: the corpus's `BYWEEKNO` verdicts stand on argument alone, where
013's and 032's now stand on argument *and* the field.

Four of the twelve do have a cross-family answer, and it is reproducible.
On `FREQ=YEARLY;BYWEEKNO=53` (two `DTSTART`s) and
`FREQ=YEARLY;INTERVAL=3;BYWEEKNO=52,-2;BYSETPOS=1` (two `DTSTART`s), six builds
across **four** independent families — `libical` master `48d52b4b` and
`4edd39a3`, `ical4j` 4.1.1 and 4.3.0, `dmfs lib-recur` 0.17.1 and
`DateTime::Event::ICal` 0.13 — return one list that is identical between them,
and that list is reproduced **instant for instant, all 25**, by rewriting the
rule as `BYDAY=weekday(DTSTART)` and expanding it with `naive`.

That is [finding 024](024-dtstart-fill-versus-the-table.md)'s rewrite,
appearing at `BYWEEKNO` exactly as [finding 033](033-the-last-five-disputes-are-two-questions.md)
said it does — now reproduced rather than observed, at 25 occurrences instead of
8, with a fifth and sixth build added to 033's three.

## What changed in the corpus

**Two verdicts are amended from `naive` to `undecided`.** The two
`FREQ=YEARLY;BYWEEKNO=53` cases were admitted by finding 066 on 2026-09-20 and
adjudicated `naive`. Their note is a sound argument about finding 033's *axis
(i)* — which week — and `dateutil` really does place occurrences in a week 53 of
a year that has 52 ISO weeks. But `BYWEEKNO` appears there with no `BYDAY`, so
the answer also has to say *which day of that week*, and recording `naive`'s
list as the verdict silently records `naive`'s answer to that second question
too. Finding 033 declined to adjudicate that question on five cases **using this
exact rule as its illustration**. Finding 066 came later and gave the same rule
a verdict 033 had already refused.

The note is kept in full and extended; only the verdict field changes. Both
cases were already excluded from `cases.ndjson`, so **no score on `RESULTS.md`
moves**: `cases_id` is unchanged at `7bd9731d3a48`. `corpus_id` does move, from
`38f9320ddfd4` to `767afd18df89`, because the corpus changed and the scored
subset did not — the same distinction the two identifiers were introduced to
make, and the second time it has done real work.

The split is now **21 `naive`, 7 `undecided`**.

**One stale figure is corrected.** `RESULTS.md` has said "21 `naive`, 5
`undecided`" since before finding 066 added two cases, so it has been
describing a 26-case file while the file held 28. The corrected count happens to
be 21 again, for a different reason, which is a good argument for not trusting a
number because it looks familiar. This is the same class of defect as
[finding 077](077-a-table-that-outlived-its-corpus.md) and it was found the same
way: by recomputing a figure instead of reading it.

## Standing rule 86

> **Every part of the corpus gets measured against the board, including the
> parts the board did not help produce.**

The disputed set was excluded from scoring for a good reason — a case where the
two expanders disagree is not conformance evidence — and that exclusion silently
became "never shown to anyone". The reason not to *score* a case is not a reason
not to *ask*. Two of the three things above came out of a set of 364 answers
that every adapter on the board could already have
produced at any time in the last three weeks, and that nothing in the repository
had ever asked for.
