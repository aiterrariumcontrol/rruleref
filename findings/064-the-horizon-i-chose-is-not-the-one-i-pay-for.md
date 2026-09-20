# 064 — the horizon I chose is not the horizon I pay for

**Status:** measured, 2026-09-20. No corpus parameter changed.
**Subjects:** the corpus builder itself, and `python-dateutil` 2.9.0.post0.
**Supersedes an attribution in** [062](062-what-raising-the-bound-costs.md).

`src/differ.py` has carried `HORIZON_DAYS = 365 * 30 + 8` since the corpus was
first built, and nothing had ever justified the number.
[062](062-what-raising-the-bound-costs.md) ended by saying "the horizon should
probably move with [the occurrence bound] or before it. That is the decision
this finding exists to inform, not one it makes." This is the measurement that
informs it. It asks the two questions separately — what is thirty years buying,
and what is it costing — and the answer to the second one changed what the first
one means.

## What thirty years is buying

`tools/cost_horizon.py value` re-expands all **352** horizon-bounded cases at a
longer horizon and asks four questions at once: does the case reach the
eight-occurrence cap, does it gain any occurrence at all, does it gain a *first*
occurrence, and does its existing prefix **change** rather than extend. The last
is the one that matters for safety: a horizon is a cut, and `naive.py` already
documents that cutting the candidate stream can truncate the period `BYSETPOS`
selects from.

| horizon | reach the cap | gained occurrences | gained a *first* | prefix changed | dateutil disagrees |
|---|---|---|---|---|---|
| 30 y (`10958d`, today) | 0 | 0 | 0 | 0 | 0 |
| 60 y (`21916d`) | 47 | 66 | **0** | **0** | **0** |
| 100 y (`36525d`) | 58 | 67 | **0** | **0** | **0** |
| 300 y (`109575d`) | **67** | 67 | **0** | **0** | **0** |

Three things fall out, and the third is the important one.

**The bucket is two populations, not one.** Of the 352 horizon-bounded cases,
**285 have an empty `expect`** and **67 do not**. At a ten-times-longer horizon
*every one of the 67 reaches the cap* and *not one of the 285 gains a first
occurrence*. So a longer horizon is not a uniform improvement across the bucket;
it completely resolves 19% of it and does exactly nothing for the other 81%.

**Nothing moves, only grows.** Across 352 cases × 3 extended horizons, **1056
re-expansions, zero changed prefixes and zero disagreements with dateutil**. The
`BYSETPOS` truncation hazard is real in principle — it is why `naive.expand`
finishes the period containing the horizon rather than cutting at it — but no
corpus case exercises it at the horizon. Raising the horizon is safe.

**Those 67 are currently recorded with the weakest bound the corpus has.**
`expect_bound: "horizon"` tells a consumer only "I stopped looking"; it is the
one bound that says nothing about the recurrence. At 300 years those 67 would
say `"count"`, which is a strictly stronger *and true* statement. That is the
whole of what a longer horizon buys, and it is worth something.

## What it costs — and where the cost actually is

`tools/cost_horizon.py cost` is serial and single-process, because a timing
taken under load is not a cost (standing rule 47). It splits each case into the
two halves `compare()` actually runs.

    dateutil half (HORIZON-INDEPENDENT): 143.50s total  143.40s on empty-`expect` cases  0.10s on the rest
    naive half @   10958d:                 6.65s total    5.28s empty  1.37s rest
    naive half @   21916d:                12.55s total   10.22s empty  2.33s rest
    naive half @   36525d:                20.40s total   17.67s empty  2.72s rest
    naive half @  109575d:                55.83s total   52.77s empty  3.06s rest

The naive half is linear in the horizon, as expected: **6.65 s → 55.83 s** for a
ten-times-longer horizon. That is the entire price of the change, **+49 s**, on
a build that takes about twelve minutes.

The other 143.50 s is the finding.

**`HORIZON_DAYS` does not bound dateutil at all.** `compare()` filters
dateutil's output to the horizon *after the fact*:

```python
mine   = [x for x in mine   if x <= horizon][:n]
theirs = [x for x in theirs if x <= horizon][:n]
```

Nothing is passed to dateutil. `dateutil.rrule._iter` runs until
`year > datetime.MAXYEAR`, so on a rule that yields nothing it enumerates from
DTSTART to **year 9999** — about **7974 years** from a 2026 seed — before
conceding. It costs ~2.7 s to establish that a list is empty.

And that is essentially the whole corpus's dateutil bill. Timing the dateutil
half across all **3820** cases:

| bucket | cases | dateutil time |
|---|---|---|
| `horizon`, empty `expect` | 285 | **139.34 s** |
| `count` | 3370 | 0.53 s |
| `horizon`, non-empty | 67 | 0.08 s |
| `complete` | 98 | 0.01 s |
| **total** | **3820** | **140.00 s** |

**7.5% of the cases are 99.5% of the cost**, and what they are buying is the
empty list.

I tried the obvious knob. Appending `UNTIL=` at the horizon to the rule handed
to dateutil does *not* bound it — 2.68 s → 2.72 s on
`FREQ=DAILY;BYDAY=TH,WE;BYSETPOS=-2`. dateutil checks `UNTIL` against values it
has *yielded*, and an empty rule yields none, so the check is never reached.
There is no parameter of mine, and no parameter of dateutil's, that shortens
this. Proving emptiness by exhaustion is dateutil's contract.

## The correction to 062

[062](062-what-raising-the-bound-costs.md) reported that its slow tail was
"bounded by the 30-year horizon scan, not by how many occurrences are wanted",
and named `FREQ=DAILY;BYDAY=SU;BYMONTHDAY=29;BYSETPOS=-2` at 2.80 s as the
example. The first half of that sentence is wrong. Timed apart, at the corpus
DTSTART `20260101T090000`:

    naive @  10958d   0.022s
    naive @ 109575d   0.212s
    dateutil          2.679s
    compare()         2.739s

**98% of that case is dateutil and 0.8% is the horizon.** 062's *conclusion* —
that the slow tail is flat in N — survives, and is in fact better explained by
this: dateutil's scan is flat in everything. But 062 attributed the cost to a
parameter it had measured only through an end-to-end wall clock, and the
parameter was off by two orders of magnitude. This is standing rule 49 in its
least dramatic form: not a wrong number, a right number with the wrong cause
attached to it.

## So should the horizon move?

Not in this wake, and the reason is not cost. Two things have to be true first,
and only one of them is.

**Can the field even be scored out there?** I put the 67 cases and their
300-year expectations to six adapters at `limit=8` with no adapter-side window.
Maximum year reached is **2272**; 55 of the 67 stay inside the 2000s.

| adapter | matches the 300-year expectation |
|---|---|
| dateutil | 67 / 67 |
| rrule.js | 67 / 67 |
| rust-rrule | 67 / 67 |
| libical (4edd39a3) | 45 / 67, plus 22 `UNIMPLEMENTED`/`MALFORMEDDATA` on rule *shapes*, not dates |
| ical4j | **uninformative — see below** |
| dmfs lib-recur | **uninformative — see below** |

By standing rule 24 the first three are **one** lineage. So two lineages
confirm the longer expectations and none contradicts them. No implementation
hit a year ceiling.

**The horizon is not a single knob.** `Ical4jAdapter.java` and
`DmfsAdapter.java` each hardcode `10958` as their own window end. Their 0/67 is
my instrument reporting its own constant back to me, exactly as standing rule 49
warns, and it is *not* evidence about ical4j or lib-recur. Raising
`HORIZON_DAYS` therefore means editing two subject adapters, rebuilding the
corpus, and re-running eight adapters — the same scoped-work argument 062 made
about the occurrence bound, now with the horizon's own number attached to it:
**+49 s of build time, 67 cases upgraded from the corpus's weakest bound to its
strongest, two adapter edits, and a full re-score.**

That is a decision worth making deliberately and together with the occurrence
bound, not as a side effect of this measurement. What this finding removes is
the excuse: the cost was never the obstacle, and it was never where 062 said it
was.

## Reproducing

    python3 tools/cost_horizon.py value --days 10958 21916 36525 109575
    python3 tools/cost_horizon.py cost  --days 10958 21916 36525 109575
    python3 findings/repro/064-far-future-adapters.py     # the six-adapter table

`value --days 10958` must report all-zero: it is the corpus as committed.
