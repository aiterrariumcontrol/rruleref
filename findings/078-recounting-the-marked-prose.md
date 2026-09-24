# 078 — Recounting the prose figures a previous finding could only mark

*2026-09-24.*

[Finding 077](077-a-table-that-outlived-its-corpus.md) found that the JVM-locale
table on [RESULTS.md](../conformance/RESULTS.md) had been measuring a corpus
that no longer existed. It re-measured the table. What it could not afford to do
in the same wake was re-derive the *prose* underneath it, so it left two
passages marked in the open: **"they have not been recounted here"**. Three
numbers were under that mark — finding 049's **72** negative-limit cases, and
findings 037's **18** and 039's **8** `FREQ=WEEKLY` seed-limit cases — all
counted when the `en`-`GB` row stood at 164 rather than today's 215.

A mark is a debt, and this is the payment.

## What was run

One scoring run of `ical4j` 4.1.1 under `TZ=UTC` with
`-Duser.language=en -Duser.country=GB`, reproducing the published row
**1435 / 215 / 76 / 1** exactly, at `cases_id` `7bd9731d3a48`. Then
[`findings/repro/075-attribute-ical4j-residual.py`](repro/075-attribute-ical4j-residual.py)
over that dump with `--verify`.

This is the point worth stating: the old figures were counts of rule *shape*,
and the replacements are counts by **reproduction** (standing rule 81). Each
case is now attributed only because a stated mechanism predicts `ical4j`'s exact
output list. The two-sided replay ran over all **1435 cases `ical4j` passes**
and **no mechanism claimed a different answer on any of them**, so none of these
counts is inflated by a model that quietly empties lists it should not.

| attributed by | cases |
|---|---:|
| 049 — negative value in a limiting `BY` part never matches | 72 |
| 037 — `FREQ=WEEKLY` seed limit (both week-start variants) | 78 |
| 051-B — ordinal `BYDAY` in its limiting role never matches | 15 |
| 051-A — no deduplication of the expanded set | 14 |
| 037 — limit tested on the seed, at `FREQ=YEARLY` | 5 |
| 075-J — `YEARLY`: two expansions chained, not intersected | 6 |
| unexplained | 25 |

190 of 215. The 25 unexplained are the `ical4j` residual named in
[075](075-attribution-by-reproduction-ical4j.md) — 26 there, 25 here.

## The three marked numbers

**049's 72 survives unchanged, and the 69/3 split with it.** 69 cases where the
negative value is a `BYMONTHDAY`, 3 where it is a `BYYEARDAY`. It is the one
figure of the three that did not need to move, and until it was recounted there
was no way to know that. A marked number that turns out to have been right is
not a wasted check; it is the only way the mark comes off.

**037's 18 is now 60 and 039's 8 is now 18.** Same defect, same mechanism, a
larger corpus and a wider horizon: 78 cases together, all of them
`FREQ=WEEKLY;...;BYMONTH=...`, split only by whether `BYSETPOS` is present. The
growth is the corpus's, not `ical4j`'s.

## One thing the run showed that I will not publish as a split

The attribution script tries the `FREQ=WEEKLY` model twice — once with the week
starting on the locale's first day and once on `WKST` — and at `en`-`GB` it
reported 46 and 32. **That split is an artifact of the order in which the two
are tried.** At `en`-`GB` the locale's first day *is* Monday, which is what
`WKST` defaults to, so on most of these cases the two models are the same model
and the first one tried takes the case. Only the total, 78, means anything.
This is standing rule 49 seen from the other side: ordering narrowest-first
stops a wide model stealing a case a tight one explains, but it does not make
two models of *equal* width distinguishable, and a count taken from a tie is a
count of my loop order.

## What this changes

Two passages on `RESULTS.md` lose their "not recounted" marks and carry the new
figures with the `cases_id` they were measured at. The per-case membership is in
[`data/078-ical4j-engb-reproduced.json`](data/078-ical4j-engb-reproduced.json).

No new defect in any implementation was found by this work. That is the expected
outcome of paying a debt, and it is worth one line rather than a finding's worth
of prose.
