# 065 — choosing both numbers at once

**Status:** measured and decided, 2026-09-20. **No corpus parameter has moved yet.**
**Subject:** the corpus itself.
**Closes the question left open by** [062](062-what-raising-the-bound-costs.md)
**and** [064](064-the-horizon-i-chose-is-not-the-one-i-pay-for.md).
**Corrects a count in** [062](062-what-raising-the-bound-costs.md).

Two of the corpus's defining constants had been measured separately and neither
had been chosen. 062 costed raising the occurrence bound `N` from 8 and found
that it makes 143 cases *stop* being able to supply their own bound. 064 costed
lengthening the 30-year horizon and found that it makes 67 cases *start* being
able to. The two effects push in opposite directions on the same quantity, so
each measurement, taken alone, argued against the change it had just priced.
That is why neither finding moved anything.

This one builds the corners of the grid and compares them by *membership*
rather than by count, which is what standing rule 54 asks for and what neither
predecessor did.

## Method

`src/build_corpus.py` gained `--horizon-days D`, alongside 062's
`--occurrences N`, under the same guard: both refuse to run without `--out`, so
neither can overwrite the committed build by accident
(`tests/test_horizon_flag.py`, `tests/test_bound_flag.py`).

Making that flag work required a repair first. `HORIZON_DAYS` was declared in
**two** modules — `src/differ.py` and `src/naive.py` — and a caller reaching the
expander through `compare()` saw one of them while a caller relying on the
default saw the other. That is the defect 064 found and standing rule 66 names.
There is now a single definition, in `naive.py`, that every call site reads at
call time rather than binding by value at import. The refactor is a proven
no-op: `tools/verify_corpus.py` reports **all 5 derived files reproduce
byte-for-byte**.

Five builds, then, all from the same source at the same commit:

| | 10958 d (30 y) | 36525 d (100 y) | 109500 d (300 y) |
|---|---|---|---|
| **N = 8**  | **A** — the committed corpus | — | **C** |
| **N = 25** | **B** | **E** | **D** |

compared pairwise by `tools/compare_corpora.py`, which reports membership, the
`expect_bound` distribution *with the moves named*, whether every shared case's
`expect` in the second build extends the first as a **prefix**, and which cases
changed the set of rival readings they carry.

## The safety result, which is the same in every direction

**In all six pairwise comparisons, every shared case's `expect` is a prefix
extension of the other build's. Zero exceptions, out of 3818 or 3820 shared
cases each time.** No published expectation is *revised* by either change in
either combination; the corpus only ever gains occurrences it had not looked far
enough to see. That is the property that makes this change safe to make at all,
and it is not something 062 or 064 could establish on its own.

## What each parameter does, separately and together

Counting `expect_bound`, whose three values rank the strength of the reason a
case's `expect` ends where it does: `complete` (the rule itself ran out),
`count` (the bound stopped it), `horizon` (the clock ran out — the weakest).

| build | corroborated | disputed | `complete` | `count` | `horizon` |
|---|---|---|---|---|---|
| **A**  N=8, 30 y   | 3820 | 26 | 98 | 3370 | **352** |
| **B**  N=25, 30 y  | 3818 | 28 | 98 | 3227 | **493** |
| **C**  N=8, 300 y  | 3820 | 26 | 98 | 3437 | **285** |
| **E**  N=25, 100 y | 3818 | 28 | 98 | 3369 | **351** |
| **D**  N=25, 300 y | 3818 | 28 | 98 | 3424 | **296** |

The moves, among shared cases:

* **A → B** (bound alone): 141 cases `count` → `horizon`. The corpus gets three
  times the evidence per case and pays for it by resting 141 more cases on its
  weakest bound.
* **A → C** (horizon alone): 67 cases `horizon` → `count`, and **nothing else
  changes at all** — same membership, same reading sets, `reading_dependent`
  unchanged at 332.
* **B → E → D** (horizon, once the bound is raised): 142 cases `horizon` →
  `count` at a hundred years, and **55 more** at three hundred — **197** in all.

That last number is the finding. **The longer horizon rescues 67 cases at N=8
and 197 at N=25** — it is worth nearly three times as much once the bound is
raised, because raising the bound is what creates the demand for a longer look.
Measured separately, each parameter looks like a trade. Measured together they
compound: **D has fewer horizon-bounded cases than the corpus has today (296
against 352) while asserting 25 occurrences per case instead of 8.** Both axes
improve at once. There is no trade to make.

## A correction to 062

062 reported "143 cases stop being able to supply the bound" and, in the same
sentence, `count` 3370 → 3227 and `horizon` 352 → 493. Those are two different
numbers: 3370 − 3227 = 143, but 493 − 352 = 141. Compared by membership, the
`count` bucket loses 143 cases in two different ways — **141 move to `horizon`,
and 2 leave the corroborated set entirely.** The two that leave are
`FREQ=YEARLY;BYWEEKNO=53` at `20240229T090000` and at `20261228T090000`, both
`count`-bounded with eight occurrences at N=8 and both becoming disputes at 25.
062 already named that pair as its membership cost; what it did not notice is
that they are also inside its 143, so the 143 and the 141 describe overlapping
populations and only one of them is a count of *moves*. This is standing rule 54
catching its own author, and it is the first thing `compare_corpora.py` found.

## What the horizon stops being an excuse for

The 285 cases with an **empty** `expect` are **the same 285 in all five
builds** — neither parameter, at any setting tried, gives a single one of them a
first occurrence. They are therefore an irreducible floor under the `horizon`
bucket, and at N=8 with a 300-year horizon they are *the entire* bucket
(**C**: 285 of 285). The full breakdown is in the table in the next section.

So at 300 years `expect_bound == "horizon"` almost stops meaning "I stopped
early" and starts meaning "I looked for three hundred years and found nothing".
Those are very different claims to publish, and today's corpus conflates them in
one bucket. The 11 survivors at N=25 are genuinely sparse rules — nine to
twenty-four occurrences each, things like
`FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-1;BYYEARDAY=100,366;BYSETPOS=1` — and they
are an honest residual rather than an artefact.

## The argument against, and why it does not choose 100 years

At N=25 and 300 years the corpus asserts dates as far out as **2347**. Those are
expectations no user of any of these libraries will ever evaluate, and 064
showed that two of my own adapters cannot even reach them. A corpus that asserts
a Thursday in 2347 is making a claim about arithmetic, not about calendars, and
it invites the reply that it is testing something nobody needs.

That argument is real, and the obvious response to it is a hundred years rather
than three hundred — which is why **E** was built. It does not survive the
measurement:

| build | `horizon`-bounded | empty `expect` | genuinely truncated | max year | cases with a date ≥ 2100 |
|---|---|---|---|---|---|
| **A**  N=8, 30 y   | 352 | 285 | **67**  | 2080 | **0** |
| **B**  N=25, 30 y  | 493 | 285 | **208** | 2080 | **0** |
| **C**  N=8, 300 y  | 285 | 285 | **0**   | 2272 | 12 |
| **E**  N=25, 100 y | 351 | 285 | **66**  | 2149 | **107** |
| **D**  N=25, 300 y | 296 | 285 | **11**  | 2347 | **108** |

**A hundred years already costs the whole far-future price.** It puts 107 cases
past the year 2100; three hundred years puts 108 past it. The marginal cost of
300 over 100 is **one additional case crossing 2100**, and the marginal benefit
is **55 cases** lifted off the corpus's weakest bound — truncated 66 → 11. The
objection is to publishing dates beyond a human planning horizon at all, and
that decision is made at N=25 by any horizon long enough to be worth raising.
Once it is made, stopping at 100 years buys nothing back.

Note also which parameter drives the exposure: at N=8 a three-hundred-year
horizon reaches past 2100 in only **12** cases (**C**). It is the *bound*, not
the horizon, that marches the corpus into the next century — raising N asks for
more occurrences of rules that produce one every few years, and they have to
come from somewhere.

A hundred years is also the one option that improves nothing: **E**'s 351
horizon-bounded cases are, to within one case, exactly the 352 the corpus has
today. It pays the whole cost of the change and lands back where it started.

The counter-argument to the objection itself is that the alternative is not
silence. The cases in question already have an `expect`, and today it simply
stops for a reason that has nothing to do with the rule. A truncated list
carrying `expect_bound: "horizon"` is *also* a claim, and a weaker and less
honest one. 064 established that the far dates are not guesses — dateutil,
rrule.js and rust-rrule match all 67 of them, and no implementation hit a year
ceiling.

## A test that was passing for the wrong reason

The single-definition repair broke `tests/test_differ.py`, and how it broke is
worth recording. That test injects a constant output in place of `naive.expand`
to prove the comparator reports a difference when an implementation returns
fewer occurrences than the reference — the check the Human found missing on
2026-09-05. Its stub was written as `lambda rule, dtstart, limit=None`, and once
`compare()` began passing `horizon=` explicitly the stub raised `TypeError`.

`compare()` catches exceptions from the expander and returns
`("ERROR:TypeError", ...)`, which *is* a difference. So three of the five
injection checks — empty output, DTSTART-only output, truncated output — went on
**passing**, while testing nothing whatsoever: they asserted that a difference
was reported, and a difference was reported, by a code path that never looked at
the injected value. Only the two checks asserting that identical output is *not*
a difference failed, which is what made the breakage visible at all.

This is [063](063-a-check-that-only-ever-saw-one-branch.md)'s shape again: a
check whose passing carried no information. A fault-injection harness whose stub
can drift out of signature with the function it replaces will report the drift
as the very condition it is testing for. The stub now takes `**kw`, and
`injected()` refuses to return any result whose reference side is an `ERROR:`
marker, so a future signature change fails loudly instead of quietly passing.

## Decision

**N = 25, horizon = 109500 days (300 years),** applied as one change.

The reasons, in order: nothing is revised, only extended (3818/3818 prefix, in
every one of the six comparisons); both quality axes improve simultaneously,
which is not true of either parameter alone; a hundred years pays the same
far-future price for 55 fewer upgrades and leaves the bound distribution exactly
where it is today; the cost is the +49 s 064 measured, on a build that already
takes twelve minutes; and the membership cost is exactly two cases, named above,
caused by the bound and not by the horizon.

The horizon is quoted as the value actually built and compared here, 109500 d.
064's tables used 109575 d. The difference is 75 days and no result above sits
near that edge, but the constant that finally lands in `naive.py` should be one
of the two, and whichever is chosen is the one to re-verify against.

**This finding does not apply the change.** What remains is scoped and known:

1. `naive.HORIZON_DAYS` → 109500; `build_corpus.N` → 25.
2. `Ical4jAdapter.java` and `DmfsAdapter.java` each hardcode `10958` as their
   own window and must be raised with it — 064's standing rule 49 warning, and
   the reason those two scored 0/67 there.
3. Rebuild (~12 min), `tools/verify_corpus.py`, re-score **eight** adapters,
   and re-check every published count under standing rule 53. `dtical` alone
   needs ~25 min and a quiet machine.

That is a whole-window job and it is now a job with its target numbers already
decided, which is what 062 and 064 each said the next step had to be.

## Reproducing

    python3 src/build_corpus.py --occurrences 25                       --out /tmp/B
    python3 src/build_corpus.py                 --horizon-days 109500  --out /tmp/C
    python3 src/build_corpus.py --occurrences 25 --horizon-days 109500 --out /tmp/D
    python3 src/build_corpus.py --occurrences 25 --horizon-days 36525  --out /tmp/E

    python3 tools/compare_corpora.py corpus /tmp/B --label-a "N=8 h=30y"   --label-b "N=25 h=30y"
    python3 tools/compare_corpora.py corpus /tmp/C --label-a "N=8 h=30y"   --label-b "N=8 h=300y"
    python3 tools/compare_corpora.py /tmp/B /tmp/E --label-a "N=25 h=30y"  --label-b "N=25 h=100y"
    python3 tools/compare_corpora.py /tmp/E /tmp/D --label-a "N=25 h=100y" --label-b "N=25 h=300y"

    python3 tools/verify_corpus.py    # must still reproduce byte-for-byte

Each build takes roughly twelve minutes alone. The wall-clock times observed
here are **not** a cost measurement — four of the five were run concurrently and
contended for the machine. 064's `tools/cost_horizon.py` is the cost instrument;
standing rules 47 and 55 apply.
