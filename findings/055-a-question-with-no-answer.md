# 055 — a question with no answer: two ways to invent an occurrence

*2026-09-18.*

## Why this was asked

[Finding 054](054-one-mechanism-twenty-seven-failures.md) needed one probe case
where `BYSETPOS` selects from a set that is too small to satisfy it. Running
that probe across all eight adapters turned up two implementations that answer a
question with no answer, and they answer it in two different and unrelated ways.

`BYSETPOS` is a selection from a finite set. RFC 5545 §3.3.10:

> Each `BYSETPOS` value can include a positive (+n) or negative (-n) integer. If
> present, this indicates the nth occurrence of the specific occurrence within
> the set of occurrences specified by the rule.

When the set holds two members and the rule asks for the third, or the
third-from-last, there is no nth occurrence. The correct result for that period
is the empty set. Two implementations return a date instead.

Reproduce:
[`repro/055-rrulejs-setpos-clamp.js`](repro/055-rrulejs-setpos-clamp.js)
(output: [`055-rrulejs-output.txt`](repro/055-rrulejs-output.txt)),
[`repro/055-libical-setpos-budget.c`](repro/055-libical-setpos-budget.c) and
[`repro/055-libical-budget-scaling.c`](repro/055-libical-budget-scaling.c)
(output: [`055-libical-output.txt`](repro/055-libical-output.txt); data: [`data/055-unsatisfiable-bysetpos.json`](data/055-unsatisfiable-bysetpos.json)).

## Defect 1 — `rrule.js` clamps a negative `BYSETPOS` to the first element

```
DTSTART:20260601T090000
FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=<n>
```

Each week of June 2026 contributes two occurrences, a Monday and a Wednesday —
except the week of Monday 29 June, whose Wednesday is 1 July and is removed by
`BYMONTH=6`. That week's set has one member.

| `BYSETPOS` | `rrule.js` (first 6) | `dateutil` and `rust-rrule` |
| ---: | --- | --- |
| `-1` | 0603 0610 0617 0624 **0629** 20270602 | same |
| `-2` | 0601 0608 0615 0622 **0629** 20270602 | 0601 0608 0615 0622 20270607 20270614 |
| `-3` | 0601 0608 0615 0622 **0629** 20270602 | *(empty)* |
| `-5` | 0601 0608 0615 0622 **0629** 20270602 | *(empty)* |
| `3` | *(empty)* | *(empty)* |
| `5` | *(empty)* | *(empty)* |

Three things are visible at once.

`BYSETPOS=-1` is correct everywhere, including the one-element week, where it
selects 29 June and everyone agrees.

`BYSETPOS=-3` and `-5` should select nothing from *any* week, because no week
here has three members. `rrule.js` returns a full list — and it is the same list
`BYSETPOS=1` returns. The out-of-range negative index is being clamped to the
first element of the set.

**Positive out-of-range is handled correctly.** `3` and `5` are empty in every
implementation. The defect is asymmetric between the two signs, which is what
one would expect from a negative index resolved as `len + n` and then used
without a lower-bound check.

The `-2` row is the case that reaches this repository's corpus, as
`c29dd0b92b8f`, and it is the sharpest form of the defect because `-2` is
perfectly valid for eleven of June's twelve weeks and unanswerable only for the
last one.

**This breaks a rule of my own instrument.**
[Rule 24](../README.md) collapses `dateutil`, `rrule.js` and `rust-rrule` into a
single lineage vote, on the correct ground that `rrule.js` is a `dateutil` port
and `rust-rrule` is an `rrule.js` port. Here the middle member of that chain
disagrees with both ends. A lineage is a claim about provenance; it is not a
guarantee that behaviour survived the port. The rule stays — it is the right
default against over-counting agreement — but it is not evidence that the three
*do* agree, and finding 054's table now records this cell as an exception.

## Defect 2 — `libical` master returns its own search budget as an occurrence

The same question asked of `libical` master (4edd39a3) produces something
different in kind:

```
FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-3    DTSTART:20260601T090000
  libical master  29840908 39421221 49010330 58590711 ...
```

Those are the years 2984, 3942, 4901 and 5859. The rule's correct answer is the
empty set. `libical` 3.0.20 does not do this: at `WEEKLY` it ignores `BYSETPOS`
altogether ([finding 031](031-one-cluster-three-causes.md)'s neighbourhood), and
it rejects `FREQ=MONTHLY;BYDAY=MO;BYSETPOS=9` at iterator construction.

### The mechanism, in the library's own source

`icalrecur_iterator_next` in `src/libical/icalrecur.c` is a `do`/`while` whose
continuation condition includes the `BYSETPOS` check, and whose *budget* does
not:

```c
    size_t cntRecurrences = 0;
    const size_t max_recurrences = icallimit_get(ICAL_LIMIT_RECURRENCE_SEARCH);
    do {
        ...
    } while ((cntRecurrences++ < max_recurrences) &&
             ((lastTimeCompare == 0) ||
              icaltime_compare(impl->last, impl->istart) < 0 ||
              (!check_contracting_rules(impl)) ||
              (hasSetPos && !check_setpos(impl, 1))));

    impl->occurrence_no++;

    return impl->last;
```

There is exactly one path in this function that returns
`icaltime_null_time()`, and it is the guard for `MAX_TIME_T_YEAR`, `UNTIL` and
the explicit end time. Exhausting `max_recurrences` is not that path: the loop
simply stops and control falls through to `return impl->last`, handing back
whatever date the search had wandered to when it ran out of budget. The date is
never re-checked against `check_setpos`.

`_MAX_RECURRENCE_SEARCH` defaults to **100000** (`src/libical/icallimits.c`).
The arithmetic matches the observed output: at `FREQ=WEEKLY` with two `BYDAY`
values the loop consumes two iterations per week, so 100000 iterations is
roughly 50000 weeks, roughly 958 years — and the first returned date is 958
years after `DTSTART`, the second 958 years after that. At
`FREQ=MONTHLY;BYDAY=MO;BYSETPOS=9` the step is 1917 years, which is 100000
Mondays.

That is a prediction, so it can be tested. `icallimit_set` makes the budget
settable, and the returned "occurrence" moves with it:

```
budget  100000 -> 29840908 39421221 49010330
budget   50000 -> 25050722 29840913 34631104
budget   10000 -> 21220401 22180202 23131203
budget    1000 -> 20360102 20450807 20550310
```

Linear in the budget. The value `libical` returns is not a property of the
recurrence rule at all; it is a reading of the library's own internal limit.
This is the failure mode [rule 4](../README.md) exists to catch, occurring
inside a library rather than inside my harness: *a cap is not a property of the
thing being measured.*

### How wide it is, and how wide it is not

**It does not affect partially-satisfiable rules.** This is the important
limit on the claim. `FREQ=MONTHLY;BYDAY=MO;BYSETPOS=5` asks for a fifth Monday,
which some months have and some do not, and `libical` master answers it
correctly:

```
FREQ=MONTHLY;BYDAY=MO;BYSETPOS=5    20260629 20260831 20261130 20270329 20270531 20270830
```

Every one of those months has five Mondays. The months without one are skipped,
not turned into garbage, because the search finds a real match inside its budget
and returns before exhausting it. The defect needs a rule for which **no** period
within the budget satisfies the `BYSETPOS` — in practice, a `|BYSETPOS|` larger
than any period of that rule can ever produce.

**It is not a regression from PR #1387.** The build before that merge
(48d52b4b) shows the same budget artifact on the same rules. #1387 does change
one of the probe rows — `BYMONTH=6;BYSETPOS=3` returned a series of 1 June dates
before the merge and returns the budget artifact after it — so the fix moved
that case from one wrong answer to another, but the runaway path predates it.

**Severity.** An always-unsatisfiable `BYSETPOS` is an authoring mistake, so the
input is uncommon. What makes it worth writing down is the *shape* of the wrong
answer: not an empty list, not an error, not a rejected rule, but a plausible
`DATE-TIME` a thousand years out, delivered through the normal iterator API with
no error set. A caller has nothing to check.

## Prior art

Searched `libical/libical` per claim
([rule 38](../README.md)), 2026-09-18.

- `BYSETPOS` issues [#795](https://github.com/libical/libical/issues/795),
  [#944](https://github.com/libical/libical/issues/944),
  [#21](https://github.com/libical/libical/issues/21) and
  [#67](https://github.com/libical/libical/issues/67) are all closed and all
  about `BYSETPOS` being ignored or partly implemented. None concerns an
  unsatisfiable selection.
- [#1156](https://github.com/libical/libical/pull/1156) ("guard against time
  standing still") and [#1279](https://github.com/libical/libical/pull/1279)
  ("prevent infinite looping in `next_unit()`") add the *stall* counter visible
  two lines above the budget in the excerpt. They cover the case where the
  iterator stops advancing; they do not cover the case where it advances
  happily for 100000 steps and is then asked to return.
- [#1374](https://github.com/libical/libical/issues/1374) is this repository's
  own report, opened 2026-09-08 and fixed by
  [#1387](https://github.com/libical/libical/pull/1387) on 2026-09-10. 4edd39a3
  *is* that fix, which is why it is the build the corpus scores. No open issue
  covers what this finding describes.

For `rrule.js`, searched later the same day, and the gap this finding first
admitted is now closed by finding that somebody else got there first.
[PR #668](https://github.com/jkbrzt/rrule/pull/668) (`spokodev`, 2026-06-22,
open) is this defect, and it names the root cause that this page does not:
`buildPoslist` resolves a negative position with `tmp.slice(daypos)[0]`, and
`Array.prototype.slice` clamps a start index below `-length` to `0`, so an
out-of-range negative `BYSETPOS` returns the first element of the set instead of
selecting nothing. That is confirmed against the build the corpus scores —
`js/node_modules/rrule/dist/es5/rrule.js` line 2952 — and it explains the
asymmetry above exactly: the positive branch is a plain index and is correct.
#668 reports it at `FREQ=MONTHLY` with `BYMONTHDAY=20,31;BYSETPOS=-2`, reaching
the same cell from the other direction, and cites `dateutil` as the reference
for the same reason. What this page adds to it is the lineage observation — that
`rust-rrule`, a port *of* `rrule.js`, does not inherit the clamp — and nothing
about the mechanism.

The related [PR #669](https://github.com/jkbrzt/rrule/pull/669) (same author,
2026-07-23, open) is `BYSETPOS` values that coincide emitting a duplicate. That
is the `rrule.js` row of [finding 051](051-what-is-left-after-the-negative-limit-fix.md)'s
defect A — `BYSETPOS=+1,1` — and prior art for it, which 051 did not have
either. Recorded here because this is the page where the search happened.

Neither defect has been reported upstream. Under this repository's current
operating constraint external reporting is paused, and a finding published here
and left here is an accepted outcome.

## Caveats

- Both defects are reproduced at the versions this repository pins:
  `rrule.js` from `js/node_modules`, `libical` master 4edd39a3 and 48d52b4b, and
  `libical` 3.0.20 as the system package. The `libical` probes are compiled
  against the library directly rather than run through
  `conformance/adapters/c/libical_adapter`, so nothing here depends on my
  adapter ([rule 25](../README.md)).
- The `libical` mechanism is read from the source at
  `scratch/libical` checkout 4edd39a3 and confirmed by the budget-scaling
  experiment. I have not stepped through it in a debugger.
- The 958-year and 1917-year figures are arithmetic consistent with a
  100000-iteration budget, not measurements of the iteration count itself.
- `FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-2` is the only case of this shape
  in the scored corpus. The probe rules are validated by `src/validity.py`
  ([rule 45](../README.md)) but are not corpus members, so they carry no score.
