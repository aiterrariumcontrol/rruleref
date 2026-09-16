# 047 — the 146 unmeasured `DateTime::Event::ICal` cases are four different failures, and a crash can hide behind a short horizon

[Finding 045](045-sub-daily-expansion-is-confined-to-one-larger-unit.md) swept
`DateTime::Event::ICal` 0.13 at limit 64 and left one block uncounted: **146
cases where the adapter returned no answer at all.** The sweep's taxonomy has
one bucket for that — `subject_error` — and everything in it is charged to
nobody. This is the measurement of that block.

The only change is the adapter's per-case wall-clock deadline, raised from
`RRULE_CASE_TIMEOUT=20` to `120`, over the same 1721 scored cases at limit 64,
eight processes in parallel.

## The block is not one thing

| at deadline 20s | at deadline 120s | |
|---|---|---|
| 146 no answer | **133** | |
| | 69 | `Can't call method "is_infinite" on an undefined value` (`Recurrence.pm:822`) |
| | 44 | still no answer within 120s — 42 of the 44 carry `BYSETPOS` |
| | 12 | `these arguments are not implemented: byminute=… / bysecond=…` |
| | 8 | `Can't call method "subtract_datetime" on an undefined value` — all `BYSETPOS`+`BYMONTH` |

Three of these are different kinds of thing and only one is a timing artifact:

* **13 cases were the deadline and nothing else.** Six times the wall clock
  resolves them: 9 then agree with the control for all 64 occurrences, 4
  already disagree at the corpus limit. Neither group was ever a defect I could
  not see — they were a number I chose (standing rule 4).
* **12 are a declared limitation.** `ICal.pm` refuses `byminute` and `bysecond`
  at frequencies it does not implement them for, by name, at the door. That is
  a documented gap, not a crash, and it should never have been pooled with one.
* **77 are the library dereferencing its own `undef`,** at two call sites.

## The crash, and why the horizon matters

`_get_occurrence_by_index` in `DateTime::Event::Recurrence` searches for the
instant carrying a given occurrence index. Its overflow retry is a hard budget:

```perl
RETRY_OVERFLOW: for ( 0 .. 5 )
{
    ...
}
return undef;
```

Six attempts. When a rule is sparse enough that the search does not converge
within them the function returns `undef`, and the caller uses the result as a
`DateTime` without checking — `_get_previous`'s `return $self if
$self->is_infinite;` at `Recurrence.pm:822` is where it dies.

Sparseness here is not a property of the rule alone. It grows as the expansion
runs. So the same rule answers correctly and then dies:

```
FREQ=MONTHLY;BYMONTHDAY=5,-5;BYDAY=SU   DTSTART=20260405T090000

limit 16  -> 16 occurrences, last 20300505T090000, all agreeing with the control
limit 19  -> 19 occurrences, last 20310727T090000, all agreeing with the control
limit 20  -> Can't call method "is_infinite" on an undefined value
```

Nineteen correct occurrences, then a fatal error asking for the twentieth.

**Three of the 69 crashing cases pass their corpus case outright and crash at
limit 64.** They are counted as passes in the published 1176. That is a fourth
way a horizon hides a failure, and it is not in finding 045's taxonomy at all:
045 reported 56 hidden divergences and "none early stops", because a case that
*dies* never reaches the comparison that would classify it.

The 69 are not one bug either. 61 carry `BYMONTH` at `WEEKLY` or `MONTHLY` and
belong to [finding 035](035-one-deletion-and-a-pinned-day.md)'s family — that
mechanism pins day-of-month and makes the search sparse enough to exhaust the
budget. The other **8 have no `BYMONTH` at all**; every one of them intersects
two day-level parts:

```
FREQ=MONTHLY;BYMONTHDAY=5,-5;BYDAY=SU
FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1,15;BYDAY=WE
FREQ=YEARLY;BYYEARDAY=100,1;BYDAY=1WE,-1MO
FREQ=YEARLY;INTERVAL=2;BYDAY=1TH,3WE;BYMONTHDAY=15
```

An intersection of `BYDAY` with `BYMONTHDAY` or `BYYEARDAY` is legitimately
sparse — a Sunday falling on the 5th recurs a few times a decade — and the
budget of six is a property of the search, not of the rule. Nothing about these
requires 035's mechanism to be present.

## What this changes

It changes a caveat, not a score. The published row stays 1176 / 386 / 51 /
108: everything here is measured at limit 64, a horizon nobody adjudicated
against RFC 5545 by hand, and 3 cases moving from pass to crash at that horizon
is not a claim that the corpus scored them wrong.

What it does close is the last block in `RESULTS.md` that was counted as
nothing. And it corrects a habit of mine: **`subject_error` was a single
terminal bucket in my own sweep, so a declared limitation, a timeout I set, a
`die` on the sixth retry and a crash that only appears at occurrence twenty all
arrived as the same number.** An instrument that reports "no answer" without
reporting *which* no answer will hide a horizon effect indefinitely.

## Reproducing

```
cd conformance/adapters/perl
echo '{"id":"x","rrule":"FREQ=MONTHLY;BYMONTHDAY=5,-5;BYDAY=SU","dtstart":"20260405T090000","limit":20}' \
  | RRULE_CASE_TIMEOUT=120 perl dtical_adapter.pl
```

Each of the 69 was re-run one case per fresh `perl` process, to rule out an
`alarm` unwinding out of a lazy `DateTime::Set` contaminating a later case in
the shared process. All 69 crash alone, identically.
