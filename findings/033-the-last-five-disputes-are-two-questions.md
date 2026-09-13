# 033 — The last five disputes are two questions, and finding 008 answered only one

**Status:** All five remaining cases in `corpus/disputed.json` adjudicated
**undecided**. This narrows a claim made in
[finding 008](008-byweekno-previous-year-last-week.md).
**Date:** 2026-09-13. **Nothing here is a new defect claim against any
implementation.**

## What was open

`corpus/disputed.json` held 26 cases, 21 adjudicated. The five left were all
`FREQ=YEARLY` with `BYWEEKNO`, and finding 008 had already looked at exactly
these five rules. Its table showed that stock `python-dateutil` 2.9.0.post0
differs from `src/naive.py` on all five, and that `dateutil` with
[PR #1537](https://github.com/dateutil/dateutil/pull/1537) applied **agrees**
with `naive` on all five. The obvious next step was to adjudicate them to
`naive` and close the list.

That step is not safe, and the reason is [standing rule 28](../README.md): the
corpus adjudicates by agreement between `naive` and `dateutil`, so an axis on
which those two never disagree is invisible to it.

## The two axes

Take the case that separates them most cleanly:

```
FREQ=YEARLY;INTERVAL=3;BYWEEKNO=52,-2;BYSETPOS=1
DTSTART = 20261231T090000   (a Thursday)
```

2029 has 52 ISO weeks, so `-2` denotes week 51 and `BYSETPOS=1` selects from
week 51. Every implementation measured agrees about that. They do not agree
about **which day of week 51**:

| source | first four occurrences | weekday |
| --- | --- | --- |
| `src/naive.py` | 20291217 20321220 20351217 20381220 | Mon |
| `python-dateutil` 2.9.0.post0 | 20291217 20321220 20351217 20381220 | Mon |
| `libical` master `4edd39a3` | 20291220 20321223 20351220 20381223 | Thu |
| `dmfs lib-recur` 0.17.1 | 20291220 20321223 20351220 20381223 | Thu |
| `ical4j` 4.1.1 | 20291220 20321223 20351220 20381223 | Thu |

The three independent lineages are **byte-identical to each other** across all
eight occurrences, and every date they emit is a Thursday — `DTSTART`'s weekday.
Both adjudicators emit Mondays — the week start.

So this case decomposes into two orthogonal questions:

* **Axis (i), which week.** `naive`'s eighth occurrence is `20500101`, which is
  in ISO week 52 of **2049**; `dateutil` and all three lineages place the eighth
  occurrence in 2050. This is finding 008's defect A, in `naive` rather than in
  `dateutil`, and finding 008 settles it against `naive`.
* **Axis (ii), which day of that week.** `BYWEEKNO` expands a year to weeks and
  no `BYDAY` is present, so something has to supply the day-of-week. Both
  adjudicators expand the week to all seven of its days and let `BYSETPOS=1`
  take the first. All three independent lineages fill the day from `DTSTART`.

Axis (ii) is [finding 024](024-dtstart-fill-versus-the-table.md)'s rewrite rule
— the table's `Expand` against §3.3.10's `DTSTART`-fill sentence — reappearing
at `BYWEEKNO` instead of at `BYMONTHDAY`. Finding 024 concluded that §3.3.10
contains both readings and did not adjudicate between them. **Finding 008
tested only axis (i).** "Patched `dateutil` agrees with `naive` on all five" is
true and is evidence about axis (i) only; on axis (ii) the patched library and
`naive` are the same reading, so their agreement is not independent.

The same split shows up on the bare rule, with nothing else in it.
`FREQ=YEARLY;BYWEEKNO=53`, `DTSTART=20380101T090000` (a Friday):

* `dateutil` emits all seven days of each matching week;
* `dmfs` and `ical4j` emit exactly one day per matching week, the Friday.

## The other three, and why they are worse

Two of the five combine `BYWEEKNO` with `BYYEARDAY`:

```
FREQ=YEARLY;BYWEEKNO=53;BYYEARDAY=1,200        DTSTART = 20260101T090000
FREQ=YEARLY;BYYEARDAY=60,1;BYWEEKNO=-2,53      DTSTART = 20260517T090000
```

Both parts are `Expand` under `YEARLY` and both determine day-of-year, and
§3.3.10 gives a special note for `BYDAY` in that situation (Note 2: *"Limit if
BYYEARDAY or BYMONTHDAY is present"*) but none for `BYYEARDAY` after
`BYWEEKNO`. Eight implementations give **five different answers**:

| source | behaviour on `BYWEEKNO=53;BYYEARDAY=1,200` |
| --- | --- |
| `naive` | intersection; "week 53" resolved against the calendar year the day sits in → 20270101, 20330101, 20380101, … |
| `dateutil`, `rrule.js`, `rust-rrule` (one lineage) | same, plus finding 008's defect A → also 20390101, 20500101 |
| `dmfs lib-recur` | intersection, week 53 strictly of year *Y* → **empty**, then `too many empty recurrence sets` |
| `ical4j` | literal sequential expand: `BYWEEKNO` survives only as a year filter, then `BYYEARDAY` re-expands → 20260101, 20260719, 20320101, … (exactly the 53-week years) |
| `libical` master | `UNIMPLEMENTED: This feature has not been implemented` |
| `sabre/vobject` 4.6.1 | ignores `BYYEARDAY` entirely (finding 031, cause 1) |
| `DateTime::Event::ICal` 0.13 | dies inside `Recurrence.pm` line 822 |

`ical4j`'s answer is the one the text most literally licenses — the BY parts are
*"applied to the current set of evaluated occurrences"* in the order `BYMONTH,
BYWEEKNO, BYYEARDAY, …`, and a later expand at the same granularity simply
overwrites the earlier one. It is also the answer nobody else gives. The
remaining case, `FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52`, is worse still:
`dmfs` errors, `libical` is `UNIMPLEMENTED`, and `ical4j` emits dates in May
with duplicates while `BYMONTH=1,8` is set.

## Verdict

All five: **undecided**, recorded in `corpus/adjudications.json` with per-case
reasons. `disputed.json` is 26 cases, 26 adjudicated, 21 `naive` and 5
`undecided`.

"Undecided" here is not a failure to look. For the two `BYYEARDAY` cases there
is no implementation majority to appeal to and the text supports at least two
constructions. For the other three the *week-numbering* question is settled —
finding 008 settles it — but the answer still depends on axis (ii), which
finding 024 explicitly left open. Adjudicating them to `naive` would have
imported an unadjudicated reading into the corpus's expected values under the
cover of a settled defect.

## What this changes

The five stay undecided, and
[finding 034](034-when-the-table-arrived.md) is why that is a position rather
than a deferral: §3.3.10 cannot settle finding 024's split, because the table
and the `DTSTART`-fill sentence were never brought into contact in the eleven
years of drafting that produced RFC 5545.

Finding 008's sentence *"all 13 synchronized disputes in the corpus are
accounted for … these 5 by defect A"* is narrowed: defect A accounts for the
*week numbering* in those five, not for their expected values. The five were
never actually adjudicated, so no published expected value moves.

## Reproduce

```sh
printf '%s\n' \
  '{"id":"C5","rrule":"FREQ=YEARLY;INTERVAL=3;BYWEEKNO=52,-2;BYSETPOS=1","dtstart":"20261231T090000","limit":8}' \
  > /tmp/p.ndjson
python3 conformance/adapters/dateutil_adapter.py < /tmp/p.ndjson
LD_LIBRARY_PATH=../../scratch/libical-install-4edd/lib conformance/adapters/c/libical_adapter < /tmp/p.ndjson
CP='conformance/adapters/java/classes:conformance/adapters/java/libs/*'
java -cp "$CP" DmfsAdapter  < /tmp/p.ndjson
java -cp "$CP" Ical4jAdapter < /tmp/p.ndjson
```

Versions: `python-dateutil` 2.9.0.post0, `rrule.js` 2.8.1, `rust-rrule` 0.14.0,
`ical4j` 4.1.1, `dmfs lib-recur` 0.17.1, `libical` master `4edd39a3`,
`sabre/vobject` 4.6.1, `DateTime::Event::ICal` 0.13.
