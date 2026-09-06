# 010 — The corpus had never terminated a rule

*2026-09-06*

Finding 009 measured the corpus against the coverage model RFC 5545 §3.3.10
prints: the `BYxxx`/`FREQ` table. It reached 57/57 permitted cells and the
README said, in as many words, that this was *presence*, not exhaustiveness,
and that nothing measured `INTERVAL`, `WKST`, `COUNT`/`UNTIL` or list arity.

That was true but toothless — a limitation you write down is not a limitation
you have measured. §3.3.10 prints a **second** model right above the table:
the ABNF for the `recur` value. This finding takes branch coverage of that
grammar as the second axis, and it is orthogonal to the first by construction:
the table has no column for any of the dimensions above.

## What the grammar says, extracted rather than transcribed

`src/grammar.py` pulls the `recur` .. `setposday` productions out of the pinned
RFC text, parses the ABNF subset they use, and enumerates branches by three
general rules applied to the parse tree:

* each alternative of an alternation is one branch;
* each optional element `[x]` is two — present and absent;
* each repetition `*(x)` is two — zero repeats and at least one.

Branches are named by the path from `recur`, so a production reached two ways
counts twice: `WKST=MO` and `BYDAY=MO` are not the same exercise. Productions
whose whole right-hand side is a `DIGIT` repetition (`seconds = 1*2DIGIT`) are
leaves — the 1-vs-2-digit distinction is lexical padding, not something the
spec draws a line at anywhere.

**79 branches.**

## The corpus took 61 of them

Measuring the 2,598-case corpus produced the list, and it is not a list of near
misses:

| never exercised | |
|---|---|
| `UNTIL`, in both value types | the corpus had never *bounded* a rule |
| `COUNT` | nor counted one |
| every `plus` — `BYDAY=+2SU`, `BYMONTHDAY=+15`, `BYYEARDAY=+60`, `BYWEEKNO=+2`, `BYSETPOS=+1` | the ABNF makes `+` explicit; nothing had ever written one |
| `WKST=TU`, `TH`, `FR`, `SA` | the generator drew from `MO`/`SU`/`WE` |
| single-element `BYSECOND` / `BYMINUTE` / `BYHOUR` lists | finding 009's cell cases all used two |
| multi-element `BYSETPOS` | |
| a rule that is `FREQ=DAILY` and nothing else | every case had at least two parts |

`UNTIL` and `COUNT` are the ones that matter. A conformance corpus for a
recurrence grammar that has never terminated a recurrence is not measuring the
half of §3.3.10 that says when the answers stop.

## Cases synthesized from the grammar, not written out

`src/enumerate_branches.py` walks the parsed ABNF choosing, at each choice
point, the branch that can reach the target and otherwise the shortest one, so
the case for `BYMONTHDAY|monthdaynum/0/0|plus` is whatever the grammar says a
`BYMONTHDAY` with an explicit sign looks like. Adding a branch to the grammar
adds a case rather than leaving a silent hole — which is the failure mode
finding 009 was about.

Two things the grammar cannot supply are tables, and are marked as such:
concrete values for numeric leaves (the ranges live in ABNF *comments*, which
the extractor drops), and a host `FREQ` plus companions that make each
synthesized part into a rule §3.3.10 permits. That the hosts succeed is
checked, not assumed: `tests/test_grammar.py` runs `validity.violations` over
all 79.

79 branches → 54 distinct rules. **Coverage is now 79/79**, and every corpus
case records the branches it takes (`corpus/grammar-coverage.json`), so this is
measurable from the corpus alone.

## Result: nothing broke

52 new corroborated cases; **disputed unchanged at 20**. The explicit `+`
sign, `UNTIL` at both value types, `COUNT`, and `WKST` at all seven weekdays
all produce identical output from the spec-derived brute force and from
`python-dateutil`. All 2,598 pre-existing corroborated cases reproduce
byte-identically. Corpus: **2,650 corroborated / 20 disputed**, 57/57 cells,
79/79 branches.

That is a negative result and worth saying plainly. The value of this work is
that the gap is now closed and *stated*, not that it caught anything.

## Two things the grammar made me look up

**One branch cannot be taken conformantly here.** §3.3.10: "The value of the
UNTIL rule part MUST have the same value type as the 'DTSTART' property."
Every DTSTART in this corpus is a DATE-TIME, so `UNTIL|enddate|date` is
covered by a case that violates that MUST no matter what rule it is attached
to. It is reported separately (`covered_nonconformantly`) rather than counted
as clean, and it is the honest statement of a real limit: this corpus has no
DATE-valued DTSTARTs at all.

**RFC 5545 as printed contradicts itself about `UNTIL`, and it is a known
erratum.** With a floating DATE-TIME DTSTART, §3.3.10 says both

> if the "DTSTART" property is specified as a date with local time, then the
> UNTIL rule part MUST also be specified as a date with local time

and

> If specified as a DATE-TIME value, then it MUST be specified in a UTC time
> format.

No floating DATE-TIME `UNTIL` satisfies both. **Erratum 4414 (Verified,
Editorial)** deletes the second sentence — it should have gone when RFC 2445
became RFC 5545. `python-dateutil` rejects `UNTIL=…Z` against a naive
DTSTART, which is the corrected text's answer; only its error message
("…when DTSTART is timezone-aware") describes the opposite direction. Checked
before writing, not after: this is the third time in three days that grepping
the errata before recording a defect has changed what I recorded.

**The ABNF's constraints are in its comments.** "The FREQ rule part is
REQUIRED, but MUST NOT occur more than once", the `;1 to 12` ranges, `UNTIL`
vs `COUNT` — all comments, all dropped by the extractor. So
`grammar.classify("BYDAY=MO")` succeeds: the grammar measures branch coverage,
not conformance. `src/validity.py` is what rejects it, and
`tests/test_grammar.py` pins five strings the grammar accepts and validity
refuses, so the division of labour cannot drift silently.

## Honest limits, again

Branch coverage is still *presence*. Nothing here covers branch **pairs** —
`COUNT` with `BYSETPOS`, `UNTIL` under `INTERVAL`, a signed `BYDAY` inside a
multi-element list. `INTERVAL` appears only as 2 and 3, `COUNT` only as 3,
and the two coverage axes are measured independently rather than crossed. The
corpus has no DATE-valued DTSTART, so a whole value type of §3.3.10's
`UNTIL` rules is out of reach. Those are the next things to make checkable,
not things this finding has settled.

## Files

* `src/grammar.py` — ABNF extraction, parser, branch enumeration, classifier
* `src/enumerate_branches.py` — one synthesized case per branch
* `src/build_corpus.py` — records `branches` on every case; writes the coverage file
* `corpus/grammar-coverage.json` — 79 branches, per-branch case counts
* `tests/test_grammar.py` — 288 checks
