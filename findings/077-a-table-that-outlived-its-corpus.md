# 077 — A published table outlived the corpus it measured, and the check that catches it costs nothing

*2026-09-21.*

[RESULTS.md](../conformance/RESULTS.md) opens with a rule I wrote for myself at
[finding 069](069-a-number-with-no-provenance.md):
**if `cases_id` has moved, every row below is from a different experiment and
has to be re-run before it may be cited.** This finding is the discovery that
the page was already violating that rule, in a table that sat 90 lines under the
banner announcing it, and had been since `5d6745e` raised the corpus on
2026-09-20.

Three separate defects, all on the same page, all found by arithmetic:

## A. The JVM-locale table was a measurement of a corpus that no longer exists

`ical4j` takes the first day of the week from the JVM default locale when a rule
omits `WKST` ([finding 036](036-a-score-that-depends-on-the-host-locale.md)), so
the page carries a second table giving the same build at three locales. It was
last touched at `53e823c` — *before* `5d6745e` — and published:

| JVM locale | pass | fail | prefix | sum |
|---|---:|---:|---:|---:|
| `ar`-`EG` | 1456 | 196 | 7 | **1659** |
| `en`-`US` | 1468 | 183 | 7 | **1658** |
| `en`-`GB` | 1487 | 164 | 7 | **1658** |

Against a corpus of 1727 cases. Two rows are short by 69 and one by 68, and the
one-case disagreement *between* the rows cannot be a corpus difference at all,
because the table's own sentence says "the same build, same corpus".

Re-measured 2026-09-21, after `javac` (rule 42), against `cases_id`
`7bd9731d3a48`:

| JVM locale | pass | fail | other reading | short | sum |
|---|---:|---:|---:|---:|---:|
| `ar`-`EG` | 1408 | 243 | 75 | 1 | 1727 |
| `en`-`US` | 1420 | 230 | 76 | 1 | 1727 |
| `en`-`GB` | 1435 | 215 | 76 | 1 | 1727 |

Every published cell was wrong. The table had also been printed with three
columns where the scorer has five, which is the whole of the 68-69 shortfall:
`fail_other_reading` was never given a column, so the ~76 cases in it simply
vanished from the arithmetic.

The `en`-`US` row now reproduces the main table's `ical4j` row cell for cell
(1420 / 230 / 76 / 1), which is the cross-check that was never possible before.

Two downstream claims moved with it. "19 net of the 183 are the locale" is now
**15** of 230 — and the move is not a clean subset: 16 cases leave the
plain-failure column between Sunday and Monday and 1 enters. "The prefix column
does not move with the locale at all — the same 7 cases in all three rows" keeps
its *shape* and loses its number: it is the same **1** case, `c5175bbb94b8`, in
all three. The qualitative claim finding 057 rests on survives; the quantity
attached to it did not.

## B. The main table has no column for one of the scorer's six buckets

`score.py` reports six buckets. The table publishes five, and the missing one is
`fail_prefix` — a proper prefix of the corpus's *own* `expect`.

    pass  fail  fail_other_reading  fail_prefix  fail_other_reading_prefix  error
                                    ^^^^^^^^^^^  no column

This was harmless while `fail_prefix` was empty, and finding 057 measured it
empty and said so on the page. Raising the horizon on 2026-09-20 ended that, and
nothing revisited the sentence. The consequence is two errors that point in
opposite directions and therefore never looked like one error:

- **`rrule-go`'s row summed to 1724.** Its 3 `fail_prefix` cases — the
  `math.MaxInt64` truncation of [finding 066](066-the-ports-were-not-identical.md)
  — were in no column. The footnote said so in words (*"they are not in any
  column above"*) and left the row not adding up, as though a footnote could
  discharge an arithmetic obligation.
- **`ical4j`'s 1 was printed under the wrong heading.** The column is labelled
  *prefix of other reading*, i.e. `fail_other_reading_prefix`; the entry in it is
  `fail_prefix`, finding 050's sub-daily `BYYEARDAY` case. Its row summed
  correctly, by a coincidence of two adjacent buckets, and so looked fine.

Eight rows were re-measured to settle this — `dateutil`, `rrule.js`, `rrule-go`,
`rust-rrule`, `sabre`, `dmfs`, `ical4j` at all three locales. Every
pass/fail/other/error cell reproduced. `fail_other_reading_prefix` is **zero on
all eight**, so the column the page has been publishing is empty everywhere and
the bucket with entries in it had no column. The two are now merged into one
column, `short`, with the split stated in its footnote.

All nine rows' bucket counts are saved in
[`data/077-rows-remeasured.json`](data/077-rows-remeasured.json) (rule 79), so
the claim *`fail_other_reading_prefix` is zero on all eight* is checkable rather
than remembered.

The three `libical` rows were **not** re-measured: each needs its own rebuild and
the build has to be left on `4edd39a3`. Their rows sum correctly with a 0 in this
column; that is consistent with `fail_prefix` being 0 for them but does not
establish it.

## C. No 4.3.0 number on the page can be reproduced from this tree

The page cites `ical4j` 4.3.0 in five places, including a four-cell row
(1556 / 99 / 66 / 7) that **sums to 1728** — one more than the corpus it was
taken against held. There is no `ical4j-4.3.0` jar anywhere in the repository.
Those numbers are not merely stale, they are unreproducible from the committed
files, and the page now says so where they appear. Restoring them means
vendoring the jar; that is a decision, not an oversight to be quietly patched,
and it is left open.

## The check

Each of these is a row of numbers that should have summed to the case count and
did not. That is a weaker invariant than `cases_id` — a row can sum perfectly
and still be a year stale — but it is free, it needs no adapter, and it is the
one that has now caught published errors **three** times: `ical4j`'s main row
summed to 1726 ([finding 075](075-attribution-by-reproduction-ical4j.md)),
`rrule-go`'s to 1724, and the locale table's three to 1659/1658/1658. In all
three cases the error had been sitting in front of me on a page I had reread
many times.

    python3 tools/check_results_rows.py

Tables opt in with an HTML comment above them:

    <!-- rowsum: total=cases cols=pass:4,fail:5,other:6,short:7,error:8 -->
    <!-- rowsum: skip reason="one case, answers not counts" -->

`total=cases` is the live line count of `cases.ndjson`, so the check tightens by
itself when the corpus moves rather than freezing today's number — which is
precisely the failure mode A was. Columns are named with explicit 1-based
indices because other cells carry integers too (a lineage cell reading
*independent (Java, 2004)* would otherwise contribute a release year to the sum).
Every table must be either marked or explicitly skipped, and an unmarked table
**fails** — so a new table cannot quietly escape the check the way the locale
table did. Both guards were tested by breaking the page on purpose: removing one
directive gives `1 tables unmarked`, exit 1, and changing one cell by one gives
`sum to 1726, not 1727`, exit 1. It otherwise reports **15 rows checked against
1727 cases, 0 bad, 0 tables unmarked**.

It runs in the suite as `tests/test_results_rows.py`, for the reason
`tests/test_links.py` gives about itself: the failure mode is an author
rereading a page many times without adding the cells up, and a note telling me
to remember is the thing that already failed.

## What this says about the instrument

Finding 069 gave the corpus an identifier so that a row could be told from a
row of a different experiment. It worked, and it did not help here, for a
reason worth writing down: **the identifier was attached to the page, not to the
table.** One banner at the top said "every row on this page", and a table 90
lines down inherited that claim without ever having earned it. A guarantee that
is asserted once at the top of a document and then relied on throughout is not a
guarantee, it is a habit.

The rule I am taking from this is narrower than "re-measure everything", which I
cannot afford:

> **Rule 83.** A published table of numbers must carry, beside it, the means to
> falsify it — either the `cases_id` it ran under, or an arithmetic invariant a
> tool checks. A table with neither is to be treated as undated, whatever the
> page around it says.

The locale table had neither for nine days. It now has both.
