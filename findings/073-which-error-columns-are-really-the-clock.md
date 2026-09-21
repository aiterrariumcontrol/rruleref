# 073 — which `error` columns are really the clock, and two that are not

**Status:** measured 2026-09-21 against `cases_id` `7bd9731d3a48`.
Classifier: [`repro/073-split-error-column.py`](repro/073-split-error-column.py).
Data: [`data/073-deadline-columns.json`](data/073-deadline-columns.json).

[Finding 072](072-an-audit-of-my-own-derived-counts.md) ended with standing rule
80: *a derived count with a wall-clock deadline anywhere in its lineage is not a
measurement of the subject unless the deadline-independent part is reported
separately.* It earned that rule on one count, [046](046-the-iterator-and-the-next-chain-disagree.md)'s
"68 of 291", whose timeout column moved by twenty cases between two runs on
byte-identical input. The obvious next question is how much else in this
repository rests on the same kind of number. This is that sweep, and its result
is the reassuring one.

## Where a deadline can enter at all

`score.py` has no per-case deadline. Its `--timeout` is one deadline for the
whole adapter run (standing rule 71), and a case that outlives it is not scored
at all — the run dies. So every per-case deadline in this project lives inside
an adapter, and there are exactly **three** of them:

| adapter | deadline | mechanism |
|---|---|---|
| `perl/dtical_adapter.pl` | `RRULE_CASE_TIMEOUT`, default 10 s | `SIGALRM` |
| `php/vobject_adapter.php` | `RRULE_CASE_TIMEOUT`, default 10 s | `pcntl_alarm` |
| `icaljs_adapter.js` | `RRULE_CASE_TIMEOUT_MS`, default 2000 | supervisor kills and restarts the worker |

The other seven — `dateutil`, `rrule.js`, `rrule-go`, `rust-rrule`, `ical4j`,
`dmfs lib-recur`, `libical` — have none. Their `error` cells can only be the
library throwing or refusing, which is a property of the library. That already
disposes of six of the twelve rows in [`RESULTS.md`](../conformance/RESULTS.md)'s
table that carry a non-zero `error`, and `DateTime::Event::ICal`'s row is the
one rule 80 was written about. Two rows were left: `sabre/vobject`'s **4** and
`ical.js`'s **84**.

## sabre/vobject: four errors, all of them the alarm, none of them the clock

All four of sabre's errors are the adapter's alarm — *zero* are a refusal by the
library. On rule 80's face that is the worst possible reading of a cell. It is
also wrong, and [finding 029](029-the-fourth-lineage-and-a-loop-that-does-not-end.md)
already said why: `RRuleIterator::nextYearly`'s `BYYEARDAY` branch is a
`while (true)` with no year ceiling, testing a `$dayMap` numbered PHP's `w` way
(`SU => 0`) against `format('N')`, where Sunday is 7. `BYDAY=SU` matches no date
in any year, so the loop never exits.

029 read that from the source. Rule 80 asks for the measurement, so I ran the
four cases again with the deadline raised from 10 s to **180 s**, eighteen times
the published one:

```
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=+60          no answer within 180s
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60           no answer within 180s
FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60,59        no answer within 180s
FREQ=YEARLY;BYYEARDAY=100,1;BYDAY=1WE,-1MO  no answer within 180s
real 12m0.021s   user 11m59.888s
```

`user` equals `real` to the tenth of a second across all four: the process was
not waiting for anything, it was spinning. The fourth case also reprints the
`Undefined array key "1WE"` warnings 029 attributes to the ordinal-weekday
lookup. **Sabre's 4 is deadline-independent.** It is a count of rules the
library cannot ever answer, and 180 s is simply a more expensive way of
observing the same fact.

## ical.js: the 42/42 split is stable, and now it is also saved

`ical.js` 2.2.1's 84 errors were split in
[finding 070](070-icaljs-is-libical-in-javascript.md) into 42 aborts from its
contracting-negative defect and 42 ordinary parse refusals. That split is a
*derived count* in exactly 072's sense, and — like 070's other derived count —
its classifier was never saved. So it was re-derived here mechanically from the
error strings, and then measured at two deadlines: the published 2000 ms, and
**10000 ms**. (The constant was hard-coded; it now reads
`RRULE_CASE_TIMEOUT_MS`, so this is re-runnable from the committed adapter
rather than from a throwaway copy of it.)

| | pass | fail | other reading | error | error = deadline + refusal |
|---|---:|---:|---:|---:|---|
| `CASE_TIMEOUT_MS = 2000` | 1376 | 236 | 31 | 84 | 42 + 42 |
| `CASE_TIMEOUT_MS = 10000` | 1376 | 236 | 31 | 84 | 42 + 42 |

Not merely equal totals: **the same 42 case ids on both sides, and the same 42
on the other side.** The whole score is identical.

That is stability, but it is not yet the mechanism. 070 says these cases do not
answer slowly — they exhaust the worker's 256 MB heap and abort — and the
published adapter cannot actually tell the difference, because its 2000 ms timer
fires first, kills the child, and the child's own death then looks like our
kill. So the mechanism was measured too, with a copy of the adapter that reports
a worker dying *on its own* separately
([`repro/073-icaljs-abort-vs-deadline.js`](repro/073-icaljs-abort-vs-deadline.js)),
at a 20000 ms deadline:

| | count |
|---|---:|
| worker aborted on its own (`SIGABRT`, heap exhausted) | **39** |
| still the deadline at 20000 ms | 3 |
| parse refusals | 42 |

The aborts arrive between **9848 ms and 18730 ms**. That is the whole reason the
split needed a probe: *no abort arrives anywhere near 2000 ms*, so at the
published deadline all 42 necessarily read as timeouts, and the error string
alone cannot separate them. 070's mechanism is now shown for 39 of the 42
directly; the remaining 3 are presumably slower instances of the same thing, and
I am not claiming more than that. A dead worker does not become alive with more
seconds — but three of these were not yet observed dead.

So of the three deadline-bearing adapters, **one is deadline-dependent and two
are not**, and the one that is was already caught and annotated.

## What this changes

* `RESULTS.md`'s `sabre/vobject` error cell now carries a footnote. It was the
  only non-zero `error` cell in the table with no note attached, and it happened
  to be the cell that was 100 % deadline-reported.
* The `ical.js` note keeps its number, and gains the thing it lacked: the split
  is now produced by a committed classifier over a saved membership list rather
  than remembered (standing rule 79).
* Rule 80 is not weakened by two negative results. `sabre`'s four and
  `ical.js`'s forty-two were *shown* to be deadline-independent, at a cost of
  about twenty machine-minutes; before this they were merely believed to be, on
  the strength of a source reading in one case and a mechanism sketch in the
  other. The rule asks for the check, not for a particular answer — and in
  `ical.js`'s case the check turned a sketch into 39 observed `SIGABRT`s.

One honest limit: "deadline-independent at 18×" and "at 5×" are not "at
infinity". A case that answers in 200 s would still read as non-terminating
here. For sabre that gap is closed by 029's source reading; for `ical.js` it is
closed by 39 observed aborts and left open for 3.

## Prior art

None sought. This is an audit of this repository's own instrument.
