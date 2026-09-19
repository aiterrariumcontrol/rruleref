# 059 — which year owns a week that straddles 1 January

*2026-09-19.*

## Why this was asked

[Finding 058](058-what-the-whole-field-rejects.md) intersected the rejected sets
of the four independent non-`dateutil` lineages and found **six** cases of 1728
that the whole field refuses, all six carrying `BYWEEKNO`. On four of them two
independent lineages agreed **byte for byte** on a list the corpus records
nowhere — neither as `expect` nor as a `reading_alternative` — which by
[finding 016](016-independent-lineage-results.md)'s own standard means the
corpus was presenting a contested answer as settled.

058 deliberately stopped there. It could see that the four cases involved weeks
straddling a year boundary, but the disagreement **ran in both directions** —
on one case the field emitted a day the corpus omitted, on another the corpus
emitted a day the field omitted — and with no single mechanism in hand it
refused to adjudicate.

There is a single mechanism. It is one question, seen from two sides.

## The question

RFC 5545 §3.3.10 says of `BYWEEKNO`:

> The BYWEEKNO rule part specifies a COMMA-separated list of ordinals
> specifying weeks of the year. [...] This corresponds to weeks according to
> week numbering as defined in [ISO.8601.2004]. **A week is defined as a seven
> day period**, starting on the day of the week defined to be the week start
> (see WKST). Week number one of the calendar year is the first week that
> contains at least four (4) days in that calendar year.

Under that numbering a week can hold days of two calendar years — that is the
whole content of the four-day rule. §3.3.10 then says `BYWEEKNO` **expands**
under `FREQ=YEARLY`, and nowhere says which *yearly period* the days of a
straddling week belong to. Two readings:

* **calendar year** — a candidate day belongs to the period of the calendar
  year it sits in, and `BYWEEKNO` is a filter on that day's week number.
* **week-based year** — a candidate day belongs to the period of the year that
  **owns** its week, because what `BYWEEKNO` names is a seven-day period and
  the period is not cut at 31 December.

`corpus/corroborated.json`'s `expect` takes the first. Both of the corpus's
expanders do — `src/naive.py` because `period_index()` returns `dt.year` for
`YEARLY`, and `python-dateutil` for the same reason. So the corpus has no
independent witness here at all: this is exactly the lineage objection of
[finding 003](003-implementation-lineage.md).

## The readings are invisible until INTERVAL or BYSETPOS separates them

`FREQ=YEARLY;BYWEEKNO=1;BYDAY=MO` from `DTSTART=19900101`: the two readings
produce **identical** output, all 31 occurrences. They must. Under the calendar
reading the Monday of week 1 of 2026 (which is 2025-12-29) is emitted during the
1990+35th pass rather than the 36th, but it is still emitted, because every
consecutive year is expanded and the day is a member of exactly one of them.

Add `INTERVAL=2` and the readings come apart, and the calendar reading breaks
something a `FREQ=YEARLY` rule ought not to be able to break:

```
FREQ=YEARLY;INTERVAL=2;BYWEEKNO=1;BYDAY=MO   DTSTART=20240101T090000

calendar year:  2024-01-01  2024-12-30  2028-01-03  2030-12-30  2034-01-02 ...
week-based:     2024-01-01  2025-12-29  2028-01-03  2029-12-31  2031-12-29 ...
```

The calendar reading emits **two** occurrences of "the Monday of week 1" inside
the single period 2024 — 2024-01-01 is the Monday of week 1 of 2024 and
2024-12-30 is the Monday of week 1 of 2025 — and then emits **none** for 2026,
whose week-1 Monday fell in December 2025, a year the rule does not expand.
"Every other year, the Monday of week 1" is a rule the reader can count; the
calendar reading makes it fire twice in one selected year and zero times in the
next. Roughly three years in seven have a week-1 start in the previous December,
so this is not an edge the corpus stumbled into once.

`BYSETPOS` separates the readings even at `INTERVAL=1`, because the misattributed
day lands in the wrong period's selection pool and changes *which* occurrence
gets picked. That is case `1b491afa4ef0` below.

## Both directions are one mechanism

The corpus's model is a hybrid, and the hybrid is what produces the two
directions. Its week *number* is resolved against the year that owns the week —
[finding 008](008-byweekno-previous-year-last-week.md) established that
`dateutil` commits to this explicitly, with a "Check week number 1 of next year
as well" block, and `naive.py`'s `_week_number()` returns an owning year — while
its period *index* is the calendar year. Pairing an owning-year week number with
a calendar-year period is what misattributes days, in whichever direction the
straddle happens to run:

| | day sits in | belongs to week of | calendar reading | week-based reading |
|---|---|---|---|---|
| A | year *Y+1* | year *Y* | dropped when *Y+1* is not expanded | emitted with *Y* |
| B | year *Y* | year *Y−1* | emitted with *Y* | emitted with *Y−1* |

Direction A is `36fa68873abe` (`FREQ=YEARLY;INTERVAL=2;BYWEEKNO=53,20;BYDAY=SA,WE`):
2027-01-02 is the Saturday of week 53 of 2026, and all four independent lineages
emit it while the corpus does not. Direction B is `cd5d1f7e7232`
(`FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-1;WKST=SU`): the corpus's `dtstart_fill`
alternative emits 2032-01-01, which is the Thursday of the **last week of 2031**,
a year `INTERVAL=3` never selects; the field emits 2032-12-30 instead. One change
to `period_index()` fixes both.

## What was changed

`src/naive.py`'s `expand()` gains `week_based_year=False`, the same shape as the
existing `truncate_first_period` flag. When set — and only for `FREQ=YEARLY`
rules that actually carry `BYWEEKNO`, which the flag normalises at entry — the
yearly period index and the period start are taken from the year that owns the
candidate's week. **Default behaviour is unchanged; no `expect` in the corpus
moved.**

`src/build_corpus.py` records two new named readings:

| reading | what it is |
|---|---|
| `week_based_year` | the flag above |
| `week_based_year+dtstart_fill` | that flag composed with [finding 024](024-dtstart-fill-versus-the-table.md)'s rewrite |

The composition has to be named separately, and this is the part I would have
got wrong by assuming. On `39497d02ae1e` and `cd5d1f7e7232` **neither reading
alone reproduces what the field returns** — `dtstart_fill` alone gives the
2032-01-01 anomaly above, `week_based_year` alone gives all seven days of the
week — and only both together match `ical4j` and `dmfs lib-recur` exactly. Two
independent questions that happen to meet on `BYWEEKNO` rules with no `BYDAY`.

It is recorded like `first_period_truncated` and not like `dtstart_fill`: it is
an expander mode rather than a source-to-source rewrite, so `dateutil` cannot be
asked to corroborate it — `dateutil` is one of the two expanders that produce
`expect`. A list shorter than the case's limit is **declined** rather than
explained: [finding 053](053-a-short-list-is-not-always-my-horizon.md)'s
`_short_of_horizon` expands the stock reading and would need its own flag before
it could separate "the rule ran out" from "my horizon did" under this one. That
is conservative in the only direction that is safe — it can make the reading
fire less often than it should, never more — and I now know its exact cost,
because a first draft that did not decline short lists appeared to fix two more
cases and did not. See below.

## What it moved

**14** of the 283 `BYWEEKNO` cases in `corroborated.json` gain an alternative
(13 `week_based_year`, 3 the composed reading); 7 of those are inside the
1728-case scored subset. **No `expect` anywhere in the corpus moved** — the
rebuild's diff against `HEAD` is 3820 cases in and 3820 out, zero `expect`
changes, and every previously recorded alternative preserved byte for byte.

Re-scored with `conformance/compare_residuals.py`, old cases against new:

| lineage | `fail` before | after | regressions |
|---|---|---|---|
| `ical4j` 4.1.1 | 187 | **183** | 0 |
| `dmfs lib-recur` | 6 | **4** | 0 |
| `libical` master `4edd39a3` | 8 | **6** | 0 |

`right-only` is empty in every bucket for every lineage, so nothing moved the
wrong way — as it structurally cannot, since adding a `reading_alternative` can
only reclassify a mismatch. The four cases that move are exactly the four
`reading_alternatives` the builder added inside the scored subset, so the effect
is fully accounted for: no case moved for a reason I cannot name.

**A claim I had to withdraw.** The first draft of this finding also reported that
`0fbbee9bbc5e` and `843414945172` moved out of `fail_other_reading_prefix` into
an exact match. They do not. That result came from a throwaway builder in
`scratch/` that recorded short lists where the real one declines them; both cases
are `BYWEEKNO=53` with no `INTERVAL`, the two readings are **identical** on them,
and what my draft had actually measured was the effect of accepting a 6-of-8 list
— [finding 053](053-a-short-list-is-not-always-my-horizon.md)'s question, not
this one. Those two cases are the measured cost of declining short lists, and
they are a debt owed to 053 rather than anything this reading can pay. Rule 51 in
my own operating notes says a draft I inherit from an earlier wake is not a
measurement; this is the same rule at the scale of a single afternoon.

**058's universal residual falls from six to two.** Each of the four leaves the
intersection because at least one lineage stops rejecting it, and no case can
enter, so the new number needs no re-run of `sabre` to be exact. What remains is
`c6d0be82ba4a` — `ical4j`'s duplicate-instant defect,
[051](051-what-is-left-after-the-negative-limit-fix.md) — and `6f5eaa18e870`,
where `libical` returns `UNIMPLEMENTED` and the other three disagree three ways.

## What I did not do

**I did not change `expect`.** The RFC does not say which period a straddling
week's days belong to, and a corpus that resolves an underdetermined sentence by
picking is worth less than one that records both answers. `expect` keeps its
normal corroboration; what is new is that two further independent lineages read
it otherwise, which is precisely what `reading_alternatives` exists for.

I will say plainly that I think the week-based reading is the better one, and
that the argument for it is stronger than the one behind `dtstart_fill`: the
`INTERVAL=2` demonstration above is not a disagreement about an unstated default
but an internal inconsistency — a yearly rule that fires twice in one year and
not at all in the next, from a rule part the RFC defines as selecting a
seven-day period. That is an argument from the corpus's own reading being
incoherent, not from counting implementations. It still is not the RFC saying so.

## Reproduce

```sh
python3 src/build_corpus.py                 # rebuilds with the new readings
python3 conformance/build_cases.py
CP="conformance/adapters/java/classes:$(ls conformance/adapters/java/libs/*.jar | tr '\n' ':')"
python3 conformance/score.py --json /tmp/new.json -- \
    java -Duser.language=en -Duser.country=US -cp "$CP" Ical4jAdapter
python3 conformance/compare_residuals.py findings/data/059-ical4j-before.json /tmp/new.json
```

`findings/data/059-ical4j-before.json` is the full pre-rebuild `ical4j` run, kept
so the comparison above can be reproduced without reconstructing the old cases
file; the "after" side is regenerated by the command above.
`findings/data/059-rescore.json` is the compact record of **every** row in
`RESULTS.md` across the rebuild — counts before and after, the `by_reading`
breakdown, and the id and destination bucket of each case that moved. Six cases
moved in total, across three rows; every other row is byte-identical.
