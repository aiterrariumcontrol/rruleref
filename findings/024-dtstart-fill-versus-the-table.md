# 024 — The lineage split is one rewrite rule, and §3.3.10 contains both readings

**Status:** Measured, and the model is exact. **Date:** 2026-09-11.
**Nothing here is a defect claim against any implementation or against RFC 5545.**
It is an account of *why* three independent lineages disagree with this corpus,
and of the two sentences in §3.3.10 that each side is following.

## What was open

[Finding 016](016-independent-lineage-results.md) found `ical4j` and
`dmfs lib-recur` agreeing with each other and against the `python-dateutil`
lineage on `FREQ=YEARLY` with `BYMONTHDAY`. [Finding 017](017-libical-third-lineage.md)
added `libical` as a third, older, independent origin, found it on the same
side, and stopped there: *"This does not adjudicate the split."* The cluster was
described but not explained, and the count was the only thing known about it.

## The explanation

Two sentences of RFC 5545 §3.3.10 both apply to `FREQ=YEARLY;BYMONTHDAY=15`,
and they give different answers.

**The table** (p. 44) says `BYMONTHDAY` under `YEARLY` is `Expand`. One year
becomes twelve candidate days — the 15th of every month. The surrounding prose
says the same thing in general terms: *"BYxxx rule parts for a period of time
less than the frequency generally increase or expand the number of
occurrences."*

**The DTSTART-fill sentence**, on the page after it, says:

> Similarly, if the BYMINUTE, BYHOUR, BYDAY, BYMONTHDAY, or BYMONTH rule part
> were missing, the appropriate minute, hour, day, or month would have been
> retrieved from the "DTSTART" property.

`FREQ=YEARLY;BYMONTHDAY=15` has no `BYMONTH`. Read literally, the month is
retrieved from `DTSTART` — and the rule means 15 March every year, not the 15th
of every month. That is precisely what `libical`, `ical4j` and `dmfs lib-recur`
return.

So the split is not a misreading on either side. It is an unresolved precedence
question between two sentences of the same section, and §3.3.10 never says which
one wins.

## This is one rewrite rule, and it is exact

If that is really the mechanism, then filling the missing field from `DTSTART`
*as an explicit BYxxx part* should turn the expanding implementations into the
limiting ones. The model is `python-dateutil` expanding a rewritten rule, with
nothing else changed:

| shape | rewrite |
|---|---|
| `FREQ=YEARLY` + `BYMONTHDAY`, no `BYMONTH` | add `BYMONTH=month(DTSTART)` |
| `FREQ=YEARLY` + `BYWEEKNO`, no `BYDAY` | add `BYDAY=weekday(DTSTART)` |

Selecting, before any model is applied, every corpus case where all three
independent lineages disagree with the corpus **and return the identical
answer**:

| cluster | cases | model reproduces | model disagrees |
|---|---:|---:|---:|
| `FREQ=YEARLY` + `BYMONTHDAY`, no `BYMONTH` | 41 | **41** | 0 |
| `FREQ=YEARLY` + `BYWEEKNO`, no `BYDAY` | 15 | **15** | 0 |
| total | 56 | **56** | 0 |

Exact list equality, not a summary statistic. Two one-line rewrites reproduce
every instant of three independent implementations' answers on every case where
those three agree against the corpus, and there is nothing left over: every
three-way-identical disagreement in the corpus is one of these two shapes.

**The superset test.** The cluster was selected by disagreement, so the model
was only asked about cases it was built to explain. Re-asking it about *all* 110
corpus cases of either shape: on 49 the three lineages do not agree with each
other, so there is no single answer to predict — 33 because at least one of the
three refuses the rule outright, 16 because the three return different sets. On
the remaining **61 the model is right 61 times, 0 wrong**. Those
61 include 5 where the three lineages agree *with* the corpus — every one
carries `BYSETPOS`, which collapses the expanded set to a single instance per
year, so both readings coincide. The model gets those right too, which it would
not if it were merely a restatement of "these cases fail".

`python-dateutil` and `rrule.js` match the corpus on all 56. Their failures here
are zero, so the split is clean: two lineages on the table, three on DTSTART-fill.

## Why exactly two cells, and why `BYDAY` is not split

The `YEARLY` column has four `Expand` cells whose part is coarser than a single
instant. Ask of each whether the table leaves a *coarser* date field for the
DTSTART-fill sentence to claim:

| part | leaves unspecified | prose override in §3.3.10? | split? |
|---|---|---|---|
| `BYMONTH` | nothing coarser | — | no |
| `BYYEARDAY` | nothing — it fixes the date | — | no |
| `BYMONTHDAY` | the month | **none** | **yes, 41 cases** |
| `BYWEEKNO` | the day within the week | **none** | **yes, 15 cases** |
| `BYDAY` | the month | yes — Note 2: *"special expand for YEARLY"* | no |

`BYDAY` under `YEARLY` with no `BYMONTH` is logically the *same* collision: the
month is missing, so DTSTART-fill would claim it. Nobody does that. Ten probes
([`repro/024-probe-cases.ndjson`](repro/024-probe-cases.ndjson)) run through all
six implementations confirm the asymmetry directly:

```
FREQ=YEARLY;BYMONTHDAY=15  DTSTART:20260315T090000
  dateutil, rrule.js            20260315 20260415 20260515 ...   (expand)
  libical, ical4j, lib-recur    20260315 20270315 20280315 ...   (DTSTART month)

FREQ=YEARLY;BYDAY=TU       DTSTART:20260303T090000
  all six                       20260303 20260310 20260317 ...   (expand, whole year)
```

The same probe set shows the limiting camp takes the month from **`DTSTART`, not
January** (so it is genuinely the fill sentence, not a "default to the first
month" shortcut); that `BYMONTHDAY=15,20` still expands *within* the fixed month;
and that signed `BYDAY` under `YEARLY` is a year offset for all six, which is
the reading RFC 5545 errata [1913](https://www.rfc-editor.org/errata/eid1913)
and [3779](https://www.rfc-editor.org/errata/eid3779) established.

So the pattern across all six implementations is consistent and narrow: **the
table is followed wherever §3.3.10 also spells the expansion out in prose, and
loses to the DTSTART-fill sentence in exactly the two cells where the table is
the only authority.** The limiting camp is not ignoring the table. It is
resolving a precedence question the table does not address.

## RFC 2445 had no table

The three implementations on the DTSTART-fill side are the three oldest:
`libical` (`icalrecur.c`, *CREATOR: eric 16 May 2000*), `ical4j` (2004), and
`dmfs lib-recur` (2013). The first two predate RFC 5545 and so were written
against [RFC 2445](https://www.rfc-editor.org/rfc/rfc2445) — and **RFC 2445
contains no expand/limit table at all.** In the whole document the word
*expand* occurs exactly once, lowercase, in the general prose sentence — checked
against [`vendor/rfc2445.txt`](../vendor/rfc2445.txt), whose sha256 the test
suite pins. §4.3.10 carries the
evaluation-order list and the DTSTART-fill sentence, and nothing else. The table
that makes `BYMONTHDAY` `Expand` under `YEARLY` first appears in RFC 5545
(2009), nine years after `icalrecur.c` was started.

**When the table did arrive is now known exactly.**
[Finding 034](034-when-the-table-arrived.md) traces both texts through all
thirteen documents in the line: the table was added in a single edit,
`draft-ietf-calsify-rfc2445bis-07` of July 2007, as a summary of the section,
and the fill sentence was not touched then or afterwards.

That is not proof of descent — `python-dateutil`'s `rrule` also predates RFC
5545 and chose expand. But it removes the need to explain the limiting reading
as a shared mistake. For a decade it was the only reading with an explicit
sentence behind it, and RFC 5545 added a table without saying that the table
overrides the sentence.

It also fits what libical's own maintainers say. [libical#1276](https://github.com/libical/libical/issues/1276),
still open, is a maintainer writing that expansive handling is *"as would seem to
be required by the table on page 44 of RFC 5545"* and choosing limiting anyway.
That issue is about *combinations* of parts and does not cover the single-part
cluster here, but it is the same precedence judgement.

## What no erratum says

All six RFC 5545 errata filed against §3.3.10 were read. Five are Verified
(1913, 3779, 4271 technical; 3747, 4414 editorial) and one is Rejected (3405). Two
correct the signed-`BYDAY` paragraph, one corrects Note 2's applicability, one
moves nonexistent-local-time handling to §3.3.5, one removes a stale sentence
from the `UNTIL` text. **None of them addresses whether the table or the
DTSTART-fill sentence controls**, and none touches the `BYMONTHDAY` or `BYWEEKNO`
rows. Seventeen years on, the ambiguity that splits the five real
implementations in this corpus has never been reported.

## The minimal fix, and what I am not doing with it

The smallest change that would resolve both cells is prose already present for a
neighbouring row: a note on `BYMONTHDAY` and `BYWEEKNO` under `YEARLY` of the
same form as Note 2 for `BYDAY`, saying which of the two sentences wins. One
sentence, no change to the table.

That is an observation about a published Standards Track RFC, not something this
repository acts on. Filing it anywhere is out of scope for this finding and
needs its own authorisation; the finding exists so that the evidence is complete
and checkable if it is ever wanted.

## What the corpus should do about it

**Done, 2026-09-11.** [Finding 018](018-reading-dependence-of-the-corpus.md)
had added a single `reading_alternative` field for one rival reading. That slot
could not hold this one as well — 15 corroborated cases carry *both* questions —
so the field is now `reading_alternatives`, a map from the name of a rival
reading to the answer it gives. Two are named: `first_period_truncated` (018)
and `dtstart_fill` (this finding). `score.py` reports a match as
`fail_other_reading` and says which reading. See
[`../corpus/SCHEMA.md`](../corpus/SCHEMA.md) and
[`../conformance/PROTOCOL.md`](../conformance/PROTOCOL.md).

Three things about how it was applied are worth stating, because each of them
could have made the result circular or too generous:

* **Shape-selected, not failure-selected.** Every corroborated case of the two
  shapes was expanded under the rewrite, not only the cases observed to fail.
  201 of 3813 carry the reading; 28 more have it coincide with `expect`.
* **The rewritten rule has to clear the same bar as everything else.** Both
  expanders must agree on it, or nothing is recorded.
* **And it has to yield a full `len(expect)` occurrences.** The `dtstart_fill`
  reading fires strictly less often, so it can run out inside the builder's
  ~30-year horizon where `expect` did not, and a list cut short by a cap I chose
  is not the same answer read differently. 175 shape-matching cases are left
  unannotated by that rule alone.

The corpus reading of every case is unchanged; `expect` did not move and no pass
count moved. What moved is how many of the *remaining* cases are called defects:
`ical4j` 253 → 195, `libical` master `4edd39a3` 79 → 22, `dmfs lib-recur`
76 → 13. The three lineages do not land on the annotation identically (58, 57
and 60 respectively), and the set where all three do is exactly **56** — this
finding's count, re-derived through the scorer rather than through the model
script below. Released `libical` 3.0.20 scores only 41, because it rejects 9 of
the `BYWEEKNO` rules as `MALFORMEDDATA` and answers 7 more in a third way.
[`../conformance/RESULTS.md`](../conformance/RESULTS.md) has the full table.

## Reproduce

```sh
# capture each adapter's raw output over cases.ndjson (id/rrule/dtstart/limit)
python3 findings/repro/024-dtstart-fill-model.py --out findings/data/024-dtstart-fill.json
```

> **Corrected 2026-09-25 by [finding 092](092-a-reproduce-command-expires.md).**
> This command used to default `--outdir` to `/tmp` and exit 0 when what it found
> there had nothing to do with the corpus. On 2026-09-25 it scored all 1727 cases
> against 29-line leftovers written by an unrelated probe eight days earlier,
> reproduced **0**, and reported success — its exit test was `disagreed == 0`, and
> nothing disagreed for the same reason nothing agreed. It now defaults `--outdir`
> into the repository, exits 2 naming the per-lineage coverage shortfall when the
> adapter output is missing or partial, and exits 3 if it reproduces nothing.
> **The figures below are not re-verified by that fix**: the command needs
> `libical`, and `libical.so.4.0` does not build in this environment. Nothing
> found contradicts them; nothing here confirms them either.

Exits non-zero if the model mispredicts a single case, and now also if it
reproduces none. The header of
[`repro/024-dtstart-fill-model.py`](repro/024-dtstart-fill-model.py) gives the
adapter commands. Results: [`data/024-dtstart-fill.json`](data/024-dtstart-fill.json).

Versions: `python-dateutil` 2.9.0.post0, `rrule.js` 2.8.1, `ical4j` 4.1.1,
`dmfs lib-recur` 0.17.1, `libical` master. The 56-case cluster is **byte-identical
under both libical builds** (`48d52b4b` and `4edd39a3`), so none of it is
affected by the `BYSETPOS` fix of [finding 019](019-libical-weekly-bymonth-bysetpos.md).
