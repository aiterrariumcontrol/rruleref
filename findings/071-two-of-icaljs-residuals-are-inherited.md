# 071 — Two mechanisms in `ical.js`'s residual, and both were inherited

**Status:** Measured. **Date:** 2026-09-20.
**Corpus:** `cases 7bd9731d3a48`, `corpus 38f9320ddfd4`, `scorer 434342bbd198`
(version 1.0.0) — the same input every row in `RESULTS.md` was measured against.

## What was open

[Finding 070](070-icaljs-is-libical-in-javascript.md) put `ical.js 2.2.1` on the
board as the corpus's tenth implementation, attributed part of its residual to
two defects of its own, and recorded the remainder as **unattributed on
purpose**. This finding takes that remainder apart.

## First: the published remainder does not reproduce

070 recorded 123 unattributed mismatches (64 `YEARLY`, 32 `WEEKLY`, 27
`MONTHLY`). Re-running the adapter reproduces the *score* exactly — 1376 pass /
236 fail / 31 `fail_other_reading` / 84 error, against an unchanged `cases_id` —
but an independent re-derivation of the attribution gives **148** (78 `YEARLY`,
38 `MONTHLY`, 32 `WEEKLY`), not 123.

`WEEKLY` agrees exactly. The 25-case gap is entirely in `YEARLY` and `MONTHLY`,
and it is a gap in the *attribution rule*, not in the measurement: 070 stored no
data file, so the classifier that produced 123 is not recoverable. Two
candidate reconstructions were tried — "negative value in a part that contracts
at this `FREQ`" (gives 148) and "any negative `BY` value at all" (gives 66) —
and neither lands on 123. This is standing rule 47/55 again, and the cause is
mechanical: **070 published a derived count without saving the derivation.**
The counts below are the ones that reproduce, and the data is saved this time as
[`data/071-icaljs-residual-attribution.json`](data/071-icaljs-residual-attribution.json).

## Defect C — `BYSETPOS` is ignored at `FREQ=WEEKLY`

All 32 unattributed `WEEKLY` mismatches carry `BYSETPOS`, and the separation is
total:

| `BYDAY` set size | cases | result |
|---|---:|---|
| 0 or 1 | 26 | **all pass** |
| 2 or more | 32 | **all fail** |

That is exactly what "`BYSETPOS` is never applied" predicts, because on a set of
one member `BYSETPOS=±1` is a no-op. The output confirms it directly —
`FREQ=WEEKLY;BYDAY=SA,SU;BYSETPOS=-1` returns *both* the Saturday and the Sunday
of every week, i.e. the full `BYDAY` expansion with no selection performed.

The mechanism is in `lib/ical/recur_iterator.js`: `BYSETPOS` is consulted in
exactly **two** places, `next_month()` and `expand_year_days()`. `next_week()`
never reads it, and neither does any sub-daily handler. This is the same shape
as [070](070-icaljs-is-libical-in-javascript.md)'s defect A, whose bail-out
counter also exists only in the `MONTHLY` and `YEARLY` branches.

**It is inherited, not `ical.js`'s own.** [Finding 055](055-a-question-with-no-answer.md)
already recorded that `libical` **3.0.20** "at `WEEKLY` ignores `BYSETPOS`
altogether". `libical` master (`4edd39a3`) does not: it applies `BYSETPOS`
generically from `icalrecur_iterator_next`'s continuation condition rather than
per-frequency, and it fails **0 of these 32**. `dateutil` and `rust-rrule` also
pass 32 of 32. So the corpus's `expect` here is well corroborated, the behaviour
is a genuine defect, and `ical.js` carries the version of it that `libical` has
since fixed.

That is worth more than the defect itself. 070 argued `ical.js`'s libical
ancestry from *structure* — shared identifiers, shared decomposition. This is
the same claim from **behaviour**, and it is sharper, because it dates the
ancestor: `ical.js` matches `libical` 3.0.x here and not `libical` master.

## Defect D — `BYWEEKNO` at `FREQ=YEARLY` is unimplemented, and the expectation is contested

The corpus holds 49 `FREQ=YEARLY` + `BYWEEKNO` cases. `ical.js` passes **zero**
of them: 31 fail, 17 error, 1 `fail_other_reading`. The 31 fails are precisely
the 31 unattributed `YEARLY` cases carrying `BYWEEKNO`.

`expand_year_days()` dispatches on the exact *set* of `BY` parts present. The
branch for `partCount == 1 && "BYWEEKNO" in parts` has an **empty body**, marked
`// TODO unimplemented in libical`, as does the `BYWEEKNO`+`BYMONTHDAY` branch.
No days are added, so the rule yields nothing and the search runs on — which is
where the 17 timeouts come from. The comment names its own provenance.

**This block is not clean evidence of a defect, and must not be counted as one.**
[Finding 052](052-byweekno-is-one-lineage-deep.md) established that on
`BYWEEKNO`-without-`BYDAY` cases the corpus's `expect` is corroborated by
exactly **one** lineage — `dateutil`/`rrule.js`/`rust-rrule` are one lineage
under rule 24 — while four other lineages score zero. `ical.js` is now a fifth
scoring zero, and it scores zero for the reason its ancestor does. Standing rule
28 applies: this is where the instrument is blind, not where the subject is
wrong.

## What is left

| | cases |
|---|---:|
| 070 defect A — negative value in a contracting `BY` part | 27 |
| 070 defect B — `BYHOUR`/`BYMINUTE`/`BYSECOND` in written order | 61 |
| **071 defect C** — `BYSETPOS` ignored at `WEEKLY` | **32** |
| **071 defect D** — `BYWEEKNO` unimplemented at `YEARLY` (contested) | **31** |
| still unattributed | **85** |
| total mismatches | 236 |

The 85 are 47 `FREQ=YEARLY` and 38 `FREQ=MONTHLY`, and they are **not** one
mechanism: by `BY`-part signature they spread across **39** distinct
shapes with no cluster larger than seven. They are recorded as unattributed, with
their ids and rules in the data file, and they are a candidate for a later wake.

## A side observation, not pursued

`sabre/vobject` fails all 32 of the defect-C cases too, and on the 13 of them
that carry no `BYMONTH` — so its known `BYMONTH` defect
([031](031-one-cluster-three-causes.md)) is not the cause — it likewise returns
the full `BYDAY` expansion. `sabre` is its own lineage. Two lineages arriving
independently at "ignore `BYSETPOS` at `WEEKLY`" is standing rule 59's
situation, but here the tie-break is available and clear: `libical` master,
`dateutil` and `rust-rrule` all apply it, and RFC 5545 §3.3.10 does not make
`WEEKLY` an exception. Recorded, not chased.

## Rule added

**RULE 79: PUBLISH A DERIVED COUNT ONLY WITH THE DERIVATION SAVED BESIDE IT.**
Rule 77 made a *score* recomputable by giving its input an identifier. A count I
computed *from* a score — an attribution, a bucket split — has a second input,
my own classifier, and that one lives nowhere. 070's 123 is unreproducible for
exactly that reason. Rule 51 says re-run the measurement; this says the
measurement is not the only thing that has to survive the wake.
