# 009 — What the corpus covers, said out loud

**Status:** Not a defect in RFC 5545, and not a defect in `python-dateutil`.
This is a finding about **this project's own corpus** — what it was actually
testing, which was much less than its size suggested — and about one defect in
this project's own reference expander that the gap had been hiding.

**Date:** 2026-09-06.

## The problem with "2541 corroborated cases"

Every case in `corpus/corroborated.json` was produced by the random rule
generator in `src/differ.py` at one of five fixed seeds. That number therefore
answers "how many cases exist", and nothing at all about *what they exercise*.
A reader deciding whether to trust the corpus has no way to tell a thorough
suite from a large pile of near-duplicates.

RFC 5545 §3.3.10 supplies a coverage model, so I did not have to invent one.
It prints a table of how each `BYxxx` rule part behaves for each `FREQ` value —
`Limit`, `Expand`, or `N/A` — with two notes splitting `BYDAY` further:

> Note 1: Limit if BYMONTHDAY is present; otherwise, special expand for MONTHLY.
>
> Note 2: Limit if BYYEARDAY or BYMONTHDAY is present; otherwise, special
> expand for WEEKLY if BYWEEKNO present; otherwise, special expand for MONTHLY
> if BYMONTH present; otherwise, special expand for YEARLY.

`src/coverage.py` extracts that table **from the pinned RFC text by program**
rather than transcribing it, for the reason `src/vtimezone.py` extracts its
examples the same way: a retyped table can quietly disagree with the spec.
9 parts × 7 frequencies = 63 cells; 6 are `N/A`; the two notes expand `BYDAY`
under `MONTHLY` and `YEARLY` into 2 and 4 branches. **57 cells the spec
permits.**

The `N/A` cells are excluded from the denominator on purpose. The spec says
those combinations MUST NOT be used, so an empty `N/A` cell is conformance,
not a gap. `src/validity.py` already rejects them at generation time.

## The measurement

**21 of 57.** The corpus of 2,541 corroborated and 20 disputed cases covered
**37%** of the table.

The 36 empty cells were not a subtle sampling shortfall. They were the shape of
the generator:

- `differ.gen` chose `FREQ` from `YEARLY, MONTHLY, WEEKLY, DAILY` only. **All
  three sub-daily frequencies were absent entirely** — 15 cells.
- It never emitted `BYHOUR`, `BYMINUTE` or `BYSECOND` at all, at any frequency.
  Those three rows of the table — 18 permitted cells — were **completely
  empty**, including all eleven `Expand` cells, which is where the interesting
  behaviour is.

None of this was written down anywhere. It was not a decision; it was the
default of a generator someone (me) wrote to explore, and then kept.

## The fix

`src/enumerate_cells.py` emits one deterministic case per cell — 57 rules,
each chosen for the cell it occupies and each carrying a `DTSTART` anchored
near its own matching region. `src/build_corpus.py` now runs those first, then
the random seeds, and records on **every** case which cells it exercises, so
coverage is measurable from the corpus files alone. `corpus/coverage.json`
reports it.

All 57 systematic cases were adjudicated the same way as every other case: by
agreement between the spec-derived brute force and `python-dateutil`. **All 57
agreed.** No new dispute; the disputed set stays at 20. Corpus:
**2,598 corroborated, 57/57 cells covered.**

`tests/test_coverage.py` (47 checks) pins the parse, the note branches, and
the claim that no permitted cell is empty, so a future generator change cannot
silently shrink coverage again.

## What this does *not* claim

**One case per cell is a presence statement, not exhaustiveness.** 57/57 means
every combination the table permits is exercised at least once by two
independent expanders that agree. It does not mean any cell is tested
thoroughly, and it says nothing about interactions between three or more parts,
about `INTERVAL`, `WKST`, `COUNT`/`UNTIL`, or about unsynchronized `DTSTART` —
all of which the random cases still carry the weight for. The honest summary is
that the corpus went from *unstated* coverage to *stated, thin* coverage.

The old number is also not wrong, just uninformative: those 2,541 cases still
test what they always tested.

## The defect the gap was hiding

`src/naive.py`'s `BYSETPOS` path collected matches for **every period out to
the 30-year horizon** before selecting from any of them, because `BYSETPOS`
needs a complete period before it can pick from it. For `FREQ=DAILY` and
coarser that is merely wasteful. Below `DAILY` it is unusable:
`FREQ=SECONDLY;BYSETPOS=-1;BYSECOND=0,15,30` enumerates on the order of 10⁹
candidate instants before returning its first occurrence. Under a 20-second
timeout it returned nothing at all.

Three cells — `BYSETPOS` under `SECONDLY`, `MINUTELY` and `HOURLY` — were
therefore not merely uncovered but **unreachable**, and the random generator's
blind spot is exactly why that had never surfaced.

The buffer is now flushed as soon as the candidate stream leaves a period.
Candidates are produced in increasing time order, so a period that has been
left is complete, and `COUNT`/`limit` can terminate the walk. Same rule now
returns in 0.003 s.

**The rewrite changes no answer.** All 2,541 pre-existing corroborated cases
were re-expanded under the new code and reproduced exactly, zero regressions,
before the corpus was rebuilt. The full test suite (`test_byweekno`,
`test_differ`, `test_dst_recurrence`, `test_tz`, `test_validity`,
`test_vtimezone`) passes unchanged.

This defect is mine, in this repository. Nothing about it concerns
`python-dateutil`, which handled every one of these rules correctly and
promptly.

## Files

- `src/coverage.py` — the table, extracted from the RFC; `classify()` maps a
  rule to the cells it exercises.
- `src/enumerate_cells.py` — one case per cell.
- `corpus/coverage.json` — the report.
- `tests/test_coverage.py` — 47 checks.
