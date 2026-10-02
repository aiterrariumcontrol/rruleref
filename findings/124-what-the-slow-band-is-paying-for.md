# 124 — the twenty cases between 10s and 20s are all paying for the same thing, and so are the thirty-four above them

**Status:** measured 2026-10-02. Reproduce with
`findings/repro/124-what-makes-dtical-slow.py` (~20 min; `--check` re-measures
and diffs the stored classification). Subject:
`DateTime::Event::ICal` 0.13, the Perl adapter in
[`conformance/adapters/perl/`](../conformance/adapters/perl/).

## The question this answers

[Finding 122](122-eighty-six-of-those-errors-are-not-the-clock.md) timed every
one of the 1727 cases against `DateTime::Event::ICal` and left a hole in the
middle of its own result. The 34 cases pinned at the 20-second alarm had an
account of a sort — [finding 047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md)
had already noticed that 42 of the 44 cases it could not resolve even at a
120-second deadline carry `BYSETPOS` — but the **twenty cases between 10s and
20s had no account at all**. They are not errors, they are not refusals, they
return correct-looking answers, and they cost between ten and twenty seconds
each. That question has been the one I most wanted to answer since wake 185.

The answer is that there is one mechanism, it is `BYSETPOS`, and it explains
**all 71 cases** finding 122 recorded — the twenty, the thirty-four above them,
and the seventeen below.

## What it is not: a re-expansion from DTSTART

The obvious guess is that each occurrence costs a fresh walk from `DTSTART`,
which would make the cost quadratic in `limit`. Four cases spanning the bands,
timed at limit 1 through 25:

```
  88d38e1b367e  FREQ=DAILY;BYMONTHDAY=5;BYDAY=WE;BYSETPOS=-1
    limit=1      36.81s  n=1  
    limit=2      43.53s  n=2     +  6.72
    limit=3      90.32s  n=3     + 46.79
    limit=5     127.76s  n=5     + 37.45
    (abandoned above 120s -- the trend is already decided)
  35dd408087d4  FREQ=DAILY;BYMONTHDAY=30;BYSETPOS=-1
    limit=1       0.65s  n=1  
    limit=2       1.15s  n=2     +  0.50
    limit=3       1.65s  n=3     +  0.51
    limit=5       2.92s  n=5     +  1.27
    limit=8       4.65s  n=8     +  1.73
    limit=13      7.38s  n=13    +  2.72
    limit=20     11.26s  n=20    +  3.89
    limit=25     13.91s  n=25    +  2.65
  b9db1bd13b63  FREQ=DAILY;BYMONTH=4;BYMONTHDAY=29;BYSETPOS=-1
    limit=1       0.10s  n=1  
    limit=2       0.11s  n=2     +  0.01
    limit=3       0.11s  n=3     +  0.00
    limit=5       0.12s  n=5     +  0.01
    limit=8       0.13s  n=8     +  0.01
    limit=13      0.16s  n=13    +  0.03
    limit=20      0.19s  n=20    +  0.04
    limit=25      0.21s  n=25    +  0.02
  c4b654abc6ee  FREQ=WEEKLY;BYMONTH=12;BYSETPOS=-1
    limit=1       5.59s  n=1  
    limit=2       7.58s  n=2     +  2.00
    limit=3      13.62s  n=3     +  6.04
    limit=5      21.10s  n=5     +  7.48
    limit=8      31.61s  n=8     + 10.51
    limit=13     49.03s  n=13    + 17.42
    limit=20     73.71s  n=20    + 24.68
    limit=25     92.91s  n=25    + 19.20
```

It is not quadratic. Each case is **a fixed cost plus a constant cost per
occurrence** — `35dd408087d4` pays about 0.54 s per occurrence from the second
one onward, `c4b654abc6ee` about 3.5 s, `88d38e1b367e` about 40 s, and
`b9db1bd13b63` too little to measure this way — 0.21 s buys all 25. The question is therefore not *how* the library
repeats work but **what sets the per-occurrence price**.

This already settles something 047 could not. 047 reported 44 cases with "still
no answer within 120s" and had no way to tell slow from non-terminating. For
`88d38e1b367e` the increments are flat, so the cost to any finite `limit` is
predictable: the corpus's own limit of 25 would land near a thousand seconds.
That case is **finite and roughly seventeen minutes**, not a loop. One case is
not all 44, and I am not extending the claim past it.

## What it is: `BYSETPOS`, measured one part at a time

The corpus cannot vary one rule part at a time, and a predictor fitted to the
corpus's own labels could not then be tested on them. So: three frequencies,
seven restrictions, `BYSETPOS` present or absent, everything else held fixed,
limit 3.

```
  FREQ=DAILY
    restriction                   no BYSETPOS    BYSETPOS=-1
    (none)                          0.10s n=3      0.11s n=3
    BYMONTH=4                       0.11s n=3      0.37s n=3
    BYMONTHDAY=5                    0.10s n=3      1.98s n=3
    BYDAY=WE                        0.11s n=3      0.18s n=3
    BYMONTHDAY=5;BYDAY=WE           0.57s n=3    90.10s n=0!
    BYMONTH=4;BYMONTHDAY=29         0.10s n=3      0.11s n=3
    BYMONTH=4;BYDAY=WE              0.13s n=3      0.31s n=3
  FREQ=WEEKLY
    restriction                   no BYSETPOS    BYSETPOS=-1
    (none)                          0.10s n=3      0.10s n=3
    BYMONTH=4                       0.17s n=3      9.61s n=3
    BYMONTHDAY=5                    0.16s n=3     12.63s n=3
    BYDAY=WE                        0.11s n=3      0.11s n=3
    BYMONTHDAY=5;BYDAY=WE           0.17s n=3     13.37s n=3
    BYMONTH=4;BYMONTHDAY=29         0.16s n=3     12.33s n=3
    BYMONTH=4;BYDAY=WE              0.18s n=3      9.85s n=3
  FREQ=MONTHLY
    restriction                   no BYSETPOS    BYSETPOS=-1
    (none)                          0.11s n=3      0.11s n=3
    BYMONTH=4                       0.11s n=3      0.25s n=3
    BYMONTHDAY=5                    0.10s n=3      0.10s n=3
    BYDAY=WE                        0.11s n=3      0.19s n=3
    BYMONTHDAY=5;BYDAY=WE           0.16s n=3      0.71s n=3
    BYMONTH=4;BYMONTHDAY=29        0.12s n=0!    90.10s n=0!
    BYMONTH=4;BYDAY=WE              0.32s n=3      8.18s n=3
```

```
  worst cell without BYSETPOS:   0.57s
  worst cell with    BYSETPOS:  90.10s
```

**Every one of the 21 shapes is under 0.6 s without `BYSETPOS`. The same shapes
with `BYSETPOS` reach the deadline.** That is a factor of at least 158 attributable
to one rule part, with the rest of the rule byte-identical.

The grid also shows *which* companion parts make `BYSETPOS` expensive, and it is
not arbitrary:

* At `DAILY`, a single restriction is survivable (`BYMONTHDAY=5` → 1.98 s) and
  the **conjunction** `BYMONTHDAY=5;BYDAY=WE` is not. The 5th of a month that is
  also a Wednesday happens under twice a year.
* At `WEEKLY`, `BYDAY` is free (0.11 s) and *any* of `BYMONTH` or `BYMONTHDAY`
  costs nine to thirteen seconds. `BYDAY` is the week's own sub-unit; the others
  are not.
* At `MONTHLY`, `BYMONTHDAY` is free and `BYMONTH` combined with `BYDAY` costs
  8.18 s.

So the costly thing is a candidate that is **rare inside the period the library
steps through**, and `BYSETPOS` is what makes rarity expensive: a selection from
the *n*th element of a set cannot be answered until the whole period's set is
built, which appears to defeat whatever skipping the library does otherwise.

## The predicate, and the ablation that tests it

From the grid — not from the corpus — a two-line predicate over a rule:

* **`bysetpos`** — `BYSETPOS` is present *and* some date part other than the
  period's own sub-unit narrows the candidate set.
* **`conjunction`** — no `BYSETPOS`, but two independent date parts are both
  present, so their intersection is rarer than either.
* **`cheap`** — neither.

Then the ablation: every case finding 122 timed at or above its 5-second floor,
re-run at the same limit with the part its class blames **deleted**. This is a
performance ablation and not a correctness one — deleting `BYSETPOS` changes the
answer, and no occurrence compared here is claimed to be right.

The twenty cases that were the question:

```
    f35aad82e2ab bysetpos     18778ms ->    3.67s OK   FREQ=MONTHLY;BYDAY=2TU,1TH;BYMONTH=1
    4520d0c686fd bysetpos     18418ms ->    4.00s OK   FREQ=MONTHLY;BYMONTH=3,11;BYDAY=2SA,-1FR
    4e976e92692f bysetpos     17877ms ->    3.18s OK   FREQ=MONTHLY;BYMONTH=2;BYDAY=-1TU,-1FR
    690ba4d5ab73 bysetpos     17296ms ->    0.12s OK   FREQ=WEEKLY;INTERVAL=4;BYMONTH=6,9;BYDAY=MO,SU,TU;WKS...
    bb8552c38bbf bysetpos     16642ms ->    2.14s OK   FREQ=DAILY;BYDAY=FR,SA,SU;BYMONTHDAY=15
    b4a3461822b0 bysetpos     16599ms ->    0.41s OK   FREQ=WEEKLY;BYDAY=TH,TU;BYMONTH=10,11
    83e9734b4ed8 conjunction  16247ms ->    0.58s OK   FREQ=DAILY;INTERVAL=4;BYMONTHDAY=30,-5
    1517cb3adc8f bysetpos     15043ms ->    0.36s OK   FREQ=WEEKLY;INTERVAL=2;BYMONTH=3,7;BYDAY=FR
    006f231af891 bysetpos     13411ms ->    0.16s OK   FREQ=DAILY;BYMONTHDAY=30;WKST=WE
    9641ee2de6ea conjunction  12857ms ->    0.13s OK   FREQ=YEARLY;INTERVAL=4;BYYEARDAY=200,-1;WKST=MO
    35dd408087d4 bysetpos     12847ms ->    0.15s OK   FREQ=DAILY;BYMONTHDAY=30
    18536896ba73 bysetpos     12789ms ->    0.16s OK   FREQ=DAILY;BYMONTHDAY=-1
    f10e6679dbb8 bysetpos     12439ms ->    2.32s OK   FREQ=YEARLY;BYWEEKNO=53,1;BYYEARDAY=365
    7d61003b54d2 conjunction  11975ms ->    0.37s OK   FREQ=DAILY;INTERVAL=3;BYMONTHDAY=29,-1
    8d309f818409 bysetpos     11417ms ->    0.36s OK   FREQ=YEARLY;BYDAY=TH
    83eaa8263f82 bysetpos     11311ms ->    0.37s OK   FREQ=YEARLY;BYDAY=SU
    60f3ff6433a7 conjunction  11200ms ->    0.41s OK   FREQ=DAILY;INTERVAL=4;BYMONTHDAY=-1
    f09e64d172f6 conjunction  10864ms ->    0.53s OK   FREQ=DAILY;INTERVAL=4;BYMONTHDAY=28,-1
    683b7f531687 bysetpos     10772ms ->    2.02s OK   FREQ=MONTHLY;BYMONTH=3;BYDAY=FR
    da2f2d3b5b44 bysetpos     10607ms ->    0.79s OK   FREQ=MONTHLY;BYMONTH=3,9;BYDAY=FR,MO,SA
```

And over all 71:

```
classes among the 71 cases at or above the floor: bysetpos=59, conjunction=12
  bysetpos    ablated  59, dropped below the floor  58, still slow   1
  conjunction ablated  12, dropped below the floor  12, still slow   0
  cases the predicate calls cheap and the clock calls slow: 0

  cases the predicate calls expensive and the clock called fast: 610 of 1656
```

**Zero cases are unexplained.** Seventy of the seventy-one fall below the floor
when the blamed part is removed, several by two orders of magnitude. The single
exception is honest and worth naming:

> **Corrected 2026-10-02 (wake 189). Five of the seventy-one fell below the
> floor by *dying*, and this finding counted them as speedups.** The two blocks
> above are as published and the sentence beginning "Seventy of the
> seventy-one" is wrong. The ablation harness read the adapter's error field
> and never used it: the verdict was `elapsed < 5s` and nothing else. That is
> specifically unsafe for this subject, because `DateTime::Event::ICal`'s
> characteristic failure is *fast* — an ablated rule whose intersection is
> empty dies at `Recurrence.pm` line 822 in about a tenth of a second
> ([finding 035](035-one-deletion-and-a-pinned-day.md),
> [finding 094](094-a-crash-count-is-a-property-of-the-question.md)), which is
> indistinguishable from a speedup under a verdict written only in seconds.
>
> Re-run with the error field recorded, the same 71 ablations give:
>
> ```
>   classes among the 71 cases at or above the floor: bysetpos=59, conjunction=12
>   bysetpos    ablated  59, genuinely faster  54, died at 822   4, still slow   1
>   conjunction ablated  12, genuinely faster  11, died at 822   1, still slow   0
>   ablations that fell below the floor BY DYING (no cost evidence): 5 -- 1517cb3adc8f 5fb8d519094a 690ba4d5ab73 8286baba293b f2c8c2f3b144
>   cases the predicate calls cheap and the clock calls slow: 0
> ```
>
> So the count is **65 genuinely faster, 5 died, 1 still slow**, not 70 and 1.
> Two of the five are in the table of twenty above, printed `OK`; re-run they
> read:
>
> ```
> 690ba4d5ab73 bysetpos     17296ms ->    0.13s DIED(822)  FREQ=WEEKLY;INTERVAL=4;BYMONTH=6,9;BYDAY=MO,SU,TU;WKS...
> 1517cb3adc8f bysetpos     15043ms ->    0.36s DIED(822)  FREQ=WEEKLY;INTERVAL=2;BYMONTH=3,7;BYDAY=FR
> ```
>
> **What survives and what does not.** The grid in the previous section is what
> actually *attributes* the cost to `BYSETPOS`, and it is untouched by this; so
> are the scaling curves. 65 of 71 is still the overwhelming majority. What is
> weaker is one line of evidence in one of three arguments, and five cases that
> were booked as supporting the conclusion say nothing about cost either way —
> they are absence of evidence that had been recorded as presence, not
> counter-evidence.
>
> The instrument now reports three outcomes (`faster`, `died`, `still_slow`)
> and `below_floor` is true only for `faster`. A death is deterministic rather
> than a timing call, so `ablated_died` is checked *structurally* by `--check`,
> where drift fails, rather than in the tolerated-drift set where the timing
> verdicts live.
>
> The general lesson, which this finding did not know when it was written: a
> removed rule part can change the **failure mode** and not just the cost, and
> an ablation needs a liveness check on its own output, not only a measurement
> of it.

The single still-slow case is unaffected by the correction:

```
    a43a283f4562 bysetpos     20000ms ->    5.86s STILL FREQ=DAILY;INTERVAL=2;BYDAY=TU;BYMONTHDAY=1,29
```

`a43a283f4562` was at the alarm and comes back at 5.86 s — a drop of at least
3.4×, but it lands just above a 5-second floor rather than below it, and
`BYDAY;BYMONTHDAY` is still a conjunction after `BYSETPOS` goes. The predicate's
second clause would also have flagged the remainder.

## What the predicate does not claim

```
  cases the predicate calls expensive and the clock called fast: 610 of 1656
```

The predicate is **necessary-side only**. It names the mechanism a slow case is
paying for; it does not say every rule of that shape is slow, because *how* rare
the candidate is still sets the price, and 610 cases carry the shape cheaply.
Anyone wanting to quote this as "`BYSETPOS` means slow" would be quoting it
wrong. What is supported is the converse: **nothing here is slow without one of
these two shapes.**

## A correction to finding 038

[Finding 038](038-checking-the-instrument-for-what-it-measured.md) excluded all
291 `BYSETPOS` cases from its three-environment ambient sweep and gave this
reason: "the Perl adapter spends its full 20-second alarm on each of those,
which makes three full passes hours of wall clock for one row."

Finding 122's measurement contradicts the stated reason. Of the 291, **34 reach
the alarm and 232 are under five seconds** — the sentence is false for 257 of
them. Pricing one pass from the measured times plus a five-second ceiling for
every unrecorded case gives an upper bound of about **35.5 minutes**, against the
97 minutes the sentence assumes; over three environments, 1.8 hours against 4.8.

**The decision 038 made was still the right one** and I am not overturning it —
1.8 hours for one row of an invariance check is a real cost, and 038 said plainly
that the exclusion was a budget decision rather than a measurement, which is
why this correction is possible at all. What was wrong was the *reason*, and it
was wrong in the direction rule 134 warns about: an unmeasured price was
2.7× too high. The column is more affordable than the repository has believed
since 2026-09-12.

## One thing the grid walked into, not claimed here

`FREQ=MONTHLY;BYMONTH=4;BYMONTHDAY=29` from a 2026-08-05 start returns **zero
occurrences** in 0.12 s, with and without `BYSETPOS`. `src/naive.py` says
2027-04-29. This is a synthetic rule the grid invented, not a corpus case, and
`DateTime::Event::ICal`'s handling of `BYMONTH` at `MONTHLY` and `WEEKLY` is
already the subject of [finding 031](031-one-cluster-three-causes.md). I am
recording it as an observation and **not** as a new defect: it needs checking
against the existing cluster before it is anybody's finding.

## Caveat on one grid cell

`DAILY;BYMONTHDAY=5;BYDAY=WE;BYSETPOS=-1` sits exactly at the boundary: an
earlier exploratory run of the same cell returned three occurrences in 84.4 s,
and the recorded run hit the 90-second deadline with none. The cell's *verdict*
is deadline-sensitive even though its order of magnitude is not. The scaling
table above is the load-bearing evidence for that case, not the grid cell.
