# 067 — an empty list nobody had proved

**Status:** measured, 2026-09-20. **No corpus file has changed yet.**
**Subject:** the corpus itself.
**Answers the question left standing by** [065](065-choosing-both-numbers-at-once.md),
which called these 285 cases "an irreducible floor".
**Uses the horizon applied in** [066](066-the-ports-were-not-identical.md).

285 of the corpus's 3818 corroborated cases assert `expect: []` — the rule
produces nothing. They are the most expensive cases in the build: each one
costs a full brute-force walk of the horizon and buys an empty list at the end
of it. 065 raised the horizon from 30 years to 300 and found these same 285
unmoved in every one of its five builds, and called them an irreducible floor.

They are not a floor. They are the one part of the corpus that was never
measured at all, because `expect: []` at `expect_bound: "horizon"` is not a
statement about the rule. It is a statement about the window. It says *no
occurrence was seen in 300 years*, which is a much weaker claim than the corpus
appears to be making, and no amount of extra horizon would have turned one into
the other.

## The calendar has a period, and it is longer than the horizon was

The proleptic Gregorian calendar repeats exactly every

```
C = 146097 days = 400 years = 4800 months = 20871 weeks
```

146097 is divisible by 7, so weekday and ISO-week structure repeat with it, not
merely month lengths and leap years. Every RFC 5545 `BY*` part is a predicate
on a date's position inside that structure — `BYMONTH`, `BYMONTHDAY`,
`BYYEARDAY`, `BYDAY`, `BYWEEKNO` — and not one of them consults the absolute
year. `BYSETPOS` and `WKST` act on the set a period yields, so they inherit the
periodicity rather than breaking it.

What does *not* repeat with C is the sequence of periods the rule looks at.
`INTERVAL=k` examines every k-th period counted from `DTSTART`, and that
sequence only realigns with the calendar after `lcm(periods_per_cycle, k)`
periods. So for a rule carrying neither `UNTIL` nor `COUNT`, the whole
recurrence set is periodic with period

| `FREQ` | period |
|---|---|
| `YEARLY` | `lcm(400, k)` years |
| `MONTHLY` | `lcm(4800, k)` months |
| `WEEKLY` | `lcm(20871, k)` weeks |
| `DAILY` | `lcm(146097, k)` days |

from which the decision procedure follows immediately: **if no occurrence falls
in `[DTSTART, DTSTART + P)`, none ever will.** One period is enough, and one
period is finite.

The corpus's horizon is 109500 days — 300 years. **Every one of the 285 needs
at least 400.** Twenty of them need more:

| period | cases |
|---:|---:|
| 400 years | 265 |
| 800 years | 6 |
| 1200 years | 9 |
| 1600 years | 5 |

`FREQ=YEARLY;INTERVAL=3;BYMONTH=6` from a 31st needs 1200 years to decide,
because 3 does not divide 400. `FREQ=DAILY;INTERVAL=4;...` needs 1600, because
146097 is odd. Not one of the 285 empty lists in the published corpus was
inside its own decision bound.

## The check, and what it found

`tools/prove_empty.py` implements the argument. Run over the corpus:

```
horizon-bounded empty cases: 285
  proven empty:      285  (61 structural, 224 by period search)
  DISPROVED:         0
  undecided here:    0
```

**All 285 are genuinely empty**, and now provably so rather than merely
unobserved. The whole scan takes about 90 seconds.

The 61 "structural" cases need no search at all, and state their reason in
words, which a search cannot:

* **38** are `FREQ=DAILY` with `BYSETPOS` whose every position has magnitude 2
  or more. A `DAILY` period is one day, so the set `BYSETPOS` selects from holds
  at most one element no matter what the other parts do to it.
* **23** are `FREQ=WEEKLY` with every `BYSETPOS` position exceeding the number
  of weekdays `BYDAY` admits (or exceeding 1, when `BYDAY` is absent and the
  weekday comes from `DTSTART`).

These two lines are exactly the shapes the corpus notes had guessed at. The
other 224 have no such shortcut and are decided by search — `FREQ=YEARLY;
BYMONTHDAY=+15;BYYEARDAY=+60` is empty because year-day 60 is 1 March or 29
February and neither is a 15th, which is true but is not a rule about the
grammar.

## Why the result is "no change" and that is the point

Nothing in the corpus is wrong. 285 assertions that were resting on an
observation now rest on a proof, and the two agree. That is the ordinary and
expected outcome, and it is worth recording precisely because the alternative
was never checked: had any one of the 285 had a first occurrence in year 2400,
the corpus would have been publishing a false `expect` under a bound that could
not have caught it, and raising the horizon from 30 years to 300 would have
moved it no closer to catching it.

The general claim was corroborated separately rather than assumed. Taking 112
corpus rules that *do* produce occurrences and shifting `DTSTART` forward by
exactly their own period P, every occurrence moved by exactly P — 112 of 112,
no exceptions. That is the periodicity the proof rests on, tested where it can
produce witnesses instead of only silences.

## How much risk was actually retired

The proof says the horizon *could* not decide these cases. It does not say the
horizon was likely to get them wrong, and it is worth separating the two.

I went looking for a counterexample: a rule whose first occurrence falls past
109500 days but inside its own period, which is the shape that would have made
the corpus publish a false `expect`. The search covered 7296 rules in the
sparsest families I could construct — `BYWEEKNO=53` and `-53`, 29 February,
year-day 366 and -366, each crossed with a single `BYDAY`, `INTERVAL` 1 to 4,
and six `DTSTART`s chosen to be awkward. 4062 of them fire.

**The latest first occurrence any of them has is 96 years out**
(`FREQ=YEARLY;INTERVAL=3;BYYEARDAY=-366;BYDAY=MO` from 2024-02-29, first firing
2120-01-01). **Zero of 4062 exceed the horizon.**

So the practical gap is wide: the worst case I can construct is about a third of
the horizon, and the sound bound is four to sixteen times it. The 300-year
horizon was probably never going to be caught out by anything the builder
generates. What it could not do — and what no horizon can do — is *say so*. A
search that finds nothing has no way to distinguish "there is nothing" from "I
did not look far enough", and the whole value of the period argument is that it
replaces a quantity I chose with one the calendar chose.

That is also why this result is recorded rather than used to argue the horizon
could be shortened again. 96 years is the worst case of the rules I thought to
write down, which is exactly the kind of bound standing rule 58 exists to
distrust.

## What this changes about the corpus

`expect_bound: "horizon"` means "the set may still continue after the horizon".
For these 285 it demonstrably does not, which is the definition `"complete"`
already carries: `expect` is the *entire* recurrence set and a consumer may
assert there is nothing after it. An empty set that never continues is a
complete one.

Moving them would take the corpus's weakest bound from **296 cases to 11** —
the 11 horizon-bounded cases that are genuinely truncated rather than empty.
That is the largest single improvement available to the corpus's honesty, and
it costs 90 seconds of build time rather than centuries of horizon.

It was deliberately **not applied in this finding**, on the same rhythm 065 and
066 used: measure and decide first, change the corpus second, so that if a
number moves it is clear which change moved it.

### Applied, 2026-09-20

`src/build_corpus.py`'s `expect_bound()` now calls `prove_empty.prove()` when
`occ` is empty and nothing else has already bounded the case, and upgrades the
bound to `complete` only when the proof returns `empty is True`. A full rebuild
gives exactly the predicted result:

| | before | after |
|---|---|---|
| `count` | 3424 | 3424 |
| `horizon` | 296 | **11** |
| `complete` | 98 | **383** |
| corroborated / disputed | 3818 / 28 | 3818 / 28 |

Compared field by field against the committed build, **`expect_bound` is the
only field that differs anywhere in the corpus**, in exactly 285 cases, every
one of them `horizon` → `complete`. No `expect` list moved, no case was gained
or lost, no dispute changed. That was the prediction and separating it from the
measurement is what made it checkable.

The 11 that stay `horizon` are the genuinely sparse rules — nine `FREQ=YEARLY`
with `INTERVAL` 2–4 and a `MONTHLY;INTERVAL=2;BYSETPOS` pair — which do fire,
but fewer than 25 times in 300 years. For those the bound is still an honest
statement about the window, because for those the window is genuinely what
stopped the list.

A second consequence is smaller and sharper. The horizon is no longer the only
tool for the job, so it no longer has to be chosen with emptiness in mind. 064
and 065 costed the horizon partly as the thing that decides whether a case runs
out; for the 285, it never could.

## Standing rule

**Rule 72 — a bound that cannot see one period of the calendar cannot decide
emptiness.** An absence observed inside a window is not an absence. The
Gregorian calendar's period is 400 years, `lcm`-extended by `INTERVAL`, and
every horizon the corpus has ever used has been shorter than that.
