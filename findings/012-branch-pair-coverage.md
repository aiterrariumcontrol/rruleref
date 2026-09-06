# 012 — Two coverage models at 100%, and an interaction model at 54%

*2026-09-06*

Findings 009 and 010 built the corpus's two coverage models, both taken from
what RFC 5545 §3.3.10 itself prints: the `BYxxx`/`FREQ` table (57 permitted
cells) and the `recur` ABNF (79 branches). By the end of 2026-09-06 both read
100% with nothing covered non-conformantly.

That is the point at which a presence measure stops measuring. Both models ask
the same shape of question — *does some case in the corpus reach this thing* —
and they ask it of each thing independently. Neither can see an interaction,
and the disagreements this corpus has actually found were interactions:

* **[001](001-dateutil-weekly-bysetpos.md)** — `BYSETPOS` *under* `WEEKLY`.
  `BYSETPOS` alone is fine; `WEEKLY` alone is fine.
* **[004](004-bysetpos-first-period-truncation.md)** — `BYSETPOS` *with* a
  first period that `DTSTART` truncates.
* **[008](008-byweekno-previous-year-last-week.md)** — `BYWEEKNO` *with* a
  year boundary.

So the third model is the pair.

## The model

For the 79 branches there are C(79,2) = **3081** unordered pairs. A case covers
a pair when the branch set `src/grammar.py` classifies it into contains both
branches — the same classifier the single-branch measure uses, so the two
numbers are computed from one recorded fact per case.

Most pairs cannot be covered at all, and that is the part of this worth being
careful about. `FREQ=DAILY` and `FREQ=WEEKLY` are alternatives of one choice.
`BYWEEKNO` shares no rule with `FREQ=MONTHLY` — §3.3.10 marks the cell N/A.
`UNTIL` and `COUNT` "MUST NOT occur in the same 'recur'". Counting those as
gaps would make the denominator meaningless; *declaring* pairs unrealizable to
make the number look better would make it worse than meaningless. So
realizability is decided by construction and then checked:

> A pair is **realizable** when `src/pairs.py` emits a rule that the RFC's own
> ABNF parses, that `src/validity.py` accepts against the MUST sentences of
> §3.3.10, and that `classify` reports as taking both branches.

**2751 of the 3081 pairs are realizable.** The other 330 are refused, each with
a recorded reason:

| reason | pairs | what it means |
|---|---|---|
| `no-common-freq` | 91 | the two parts share no `FREQ` column outside N/A |
| `needs-date-dtstart` | 78 | involves `UNTIL` as a DATE; see finding 011 |
| `arity-conflict` | 69 | `recur` with no rule part after `FREQ` admits no second branch |
| `invalid:byday-numeric-byweekno` | 35 | signed `BYDAY` with `BYWEEKNO` at `YEARLY` |
| `same-choice-point` | 30 | two labels on one ABNF choice, e.g. a list repeated and not |
| `invalid:byday-numeric-freq` | 25 | signed `BYDAY` outside `MONTHLY`/`YEARLY` |
| `invalid:count-until-exclusive` | 2 | `UNTIL` and `COUNT` in one rule |

`tests/test_pairs.py` asserts that no pair is ever refused for the one reason
that would be *my* fault rather than the spec's — "the synthesizer could not
build it". That count is zero, and it is the check that keeps the denominator
honest.

### Two bugs the denominator flushed out

Both were found by looking at refusals rather than by trusting them.

**Greedy host frequency invented 70 false gaps.** The single-branch enumerator
gives each rule part one host `FREQ` — `BYDAY` is enumerated at `MONTHLY`,
`BYSECOND` at `MINUTELY`. Composing a pair by taking the first part's host
made `BYSECOND` + signed `BYDAY` land at `MINUTELY`, where a signed `BYDAY`
violates a MUST, and the pair was recorded as unrealizable. It is realizable
at `MONTHLY`. `build` now tries every frequency the table permits both parts
at, and only then gives up.

**`BYDAY=SU,MO` came out as `BYDAY=SU,TU`.** Reaching two branches inside one
rule part needed the synthesizer to take a set of targets rather than one, and
when a target is reached inside the *repeated* element of a list, the step that
moves a duplicated element off its neighbour was moving the branch away too.
All 21 two-weekday pairs were being reported as unrealizable. The fix — vary
the copy only when it is not itself carrying a target — leaves all 79
single-branch cases byte-identical, which is how it was checked.

## The corpus covered 1485 of 2751 — 54%

The 2,650-case corpus — systematic on both single-branch models, random
otherwise — covered **1485 of the 2751** realizable pairs. The 1266 it missed
are not exotic. Among them:

```
BYDAY|bywdaylist/1|repeat=0   + BYSETPOS|bysplist/1|repeat=1+
BYDAY|bywdaylist/1|repeat=0   + BYMONTHDAY|monthdaynum/0/0|plus
BYDAY|bywdaylist/1|repeat=0   + BYSECOND|byseclist/1|repeat=1+
recur|recur-rule-part|COUNT   + BYSETPOS|yeardaynum/0/0|minus
```

A single-element `BYDAY` with a multi-element `BYSETPOS`; `COUNT` with a
negative `BYSETPOS` — the shape of finding 001, one axis over. The random
generator had produced 2,000+ rules and never written one.

`src/pairs.py` now synthesizes a rule per realizable pair and the generator
records them, so the number is a target rather than an observation.

