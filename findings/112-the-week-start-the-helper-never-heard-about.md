# Finding 112 — The week start the helper never heard about

**Status:** two defects in `libical` master `4edd39a3`, each reproduced by a
patch to the library's own source that empties its share of the bucket and
regresses nothing. Closes the third of the four `fail` buckets
[109](109-who-else-counts-this-case.md) named as unpartitioned, and leaves one.

## Claim

`libical` master `4edd39a3` fails six of the corpus's 1727 cases. **All six are
`BYWEEKNO`**, and two defects account for them exactly — four and two, disjoint,
nothing left over.

```
A-weeks-in-year-ignores-wkst                    4   1b491afa4ef0 47957affeae1
                                                    6a2a3349a31d cd5d1f7e7232
B-week-year-truncated-by-doy-offset-plus-one    2   52cb89bd1169 a11bc9303af3
```

That the whole residual of an independent C implementation from 2000 is one
RRULE part is worth saying next to [111](111-december-the-thirty-second.md),
where the whole residual of `dmfs lib-recur` — a different lineage, a different
language — was also `BYWEEKNO`, and next to
[088](088-the-most-over-blamed-part-is-not-bysetpos.md), which measured
`BYWEEKNO` as 38% not-necessary and therefore *less* over-blamed than `BYDAY`.
Over-blamed and last-standing are not the same property.

## Defect A — a helper that is week-start-blind under a numbering that is not

`icalrecur.c` computes how many weeks a year has here:

```c
/** Calculate ISO weeks per year */
static int weeks_in_year(int year)
{
    /* Long years occur when year starts on Thu or leap year starts on Wed */
    int dow = icaltime_day_of_week(icaltime_from_day_of_year(1, year));
    int is_long = (dow == 5 || (dow == 4 && icaltime_is_leap_year(year)));

    return (52 + is_long);
}
```

Thursday and Wednesday are the ISO answer, and ISO means `WKST=MO`. The comment
says so. But the week *numbering* this count is compared against does not come
from here at all. This build has `HAVE_LIBICU=1`, so `get_week_number()` is the
ICU one, and `icalrecur_iterator_new()` configures ICU with

```c
ucal_setAttribute(impl->rscale, UCAL_MINIMAL_DAYS_IN_FIRST_WEEK, 4);
ucal_setAttribute(impl->rscale, UCAL_FIRST_DAY_OF_WEEK, (int32_t)rule->week_start);
```

— four minimal days, which is ISO's rule, but the *first day of the week taken
from `WKST`*. So the numbering honours `WKST` and the count of weeks does not.
With any non-Monday `WKST` they can disagree by one, and two places consume the
count:

* `weekno += nweeks + 1` normalises a negative `BYWEEKNO`;
* `else if (weekno > nweeks) continue;` is the only guard against asking for a
  week the year does not have.

2026 is the clean example. Under `WKST=MO` it is a long year, 53 weeks; under
`WKST=SU` its weeks run Jan 4 2026 – Jan 2 2027 and there are 52. `libical`
normalises `BYWEEKNO=-1` to week 53, and week 53 under the Sunday numbering
begins **January 3 2027**:

```
DTSTART:20261227T090000
FREQ=YEARLY;INTERVAL=2;BYWEEKNO=-1;WKST=SU   ->  2027-01-03, ...
```

Three of the seventeen years 2024–2040 select a day outside the calendar year
they were asked about. The same rule with `BYWEEKNO=-2` returns 2026-12-27,
which is the *last* week — off by exactly one, as the arithmetic says.

The one-day-per-week shape of that answer is not the defect. With no `BYDAY`,
`libical` deliberately expands `BYWEEKNO` to a single day, the next instance of
`DTSTART`'s weekday; that is [024](024-dtstart-fill-versus-the-table.md)'s open
`DTSTART`-fill split and the corpus records it as a defensible reading. This is
why all four of A's cases land in `fail_other_reading`, not `pass`, once A is
fixed: the remaining disagreement is the one §3.3.10 never settles.

## Defect B — a period measured as a count and computed as an offset

In the `BYWEEKNO` + `BYDAY` branch of `expand_year_days()`:

```c
doy_offset += get_start_of_week(impl) - 1;
last_day = (7 * weeks_in_year(year)) - doy_offset - 1;
```

`expand_by_day()` reads `last_day` as a **count** of days starting at
`doy_offset + 1`:

```c
daysmask_set_range(impl->days, doy_offset + 1, doy_offset + last_day + 1, 0);
```

A week-numbering year is exactly `7 * weeks_in_year(year)` days long, so the
count is right and the subtraction is not: the last `doy_offset + 1` days of it
are dropped.

`doy_offset` is fixed by January 1st's weekday alone, which makes the defect
predictable from the calendar with no reference to the rule. Asked for week 52
with `BYDAY` naming all seven weekdays — a week that has seven days under every
reading of every year-boundary question this repository has declined to
adjudicate ([002](002-byweekno-year-boundary.md),
[008](008-byweekno-previous-year-last-week.md),
[059](059-which-year-owns-a-straddling-week.md)):

| Jan 1 falls | `doy_offset` | days returned | years, 2024–2040 |
|---|---:|---:|---|
| Mon | 0 | **6** | 2024 2029 2035 |
| Sun | 1 | **5** | 2034 2040 |
| Sat | 2 | **4** | 2028 2033 2039 |
| Fri | 3 | **3** | 2027 2038 |
| Tue, Wed, Thu | < 0 | 7 | 2025 2026 2030 2031 2032 2036 2037 |

**Ten of the seventeen years return a week of fewer than seven days**, every
length exactly as predicted. A Friday-start year loses four of the seven.

The Tue/Wed/Thu row is the interesting one: there week 1 begins in the previous
calendar year, `doy_offset` goes negative, and the same wrong formula
*over*-runs the end of the week year by one or two days instead of truncating
it. **I looked for that over-run as a second observable and did not find one.**
`BYWEEKNO=1` with all seven weekdays returns a seven-day week in all seventeen
years, patched and unpatched alike. The extra days are generated only for a
`BYDAY` whose weekday recurs past the end, and the stride loop stops first.
Recorded as reasoned-but-unobserved: **a lead, not a result.**

## How the two were separated

Both patches are in [`repro/112-patch-libical.py`](repro/112-patch-libical.py),
which requires every anchor to occur exactly once in the source and refuses
otherwise. Each was built alone into its own install prefix and the corpus
re-scored through the committed C adapter:

| build | `pass` | `fail` | `fail_other_reading` | `error` | cases that left `fail` |
|---|---:|---:|---:|---:|---|
| unpatched `4edd39a3` | 1614 | **6** | 72 | 35 | — |
| patch A only | 1614 | 2 | 76 | 35 | A's four, all to `fail_other_reading` |
| patch B only | 1616 | 4 | 72 | 35 | B's two, both to `pass` |
| patches A + B | 1616 | **0** | 76 | 35 | all six |

Exactly six cases move under A+B and no case moves in any other direction, at
any of the three builds. So each defect is **necessary** for its own cases,
**sufficient** on its own for them, and the two do not interact over this
corpus. The `fail` bucket goes to zero.

This is a different instrument from the last three bucket closures. 076, 075
and 074 built a predictor per defect; [110](110-three-constructs-that-do-not-survive-translation.md)
patched the port's *parent* and required it to reproduce the port everywhere.
Here the subject is not a port and has no parent, so the substrate is its own
source, and the test is the strongest of the three: not "a model of the defect
reproduces the output" but "removing the defect removes exactly these failures
and nothing else." **Rule 117: when the subject builds from source you have,
attribute by removal, not by imitation — and report the regression count, which
is the half a predictor cannot produce at all.**

## Caveats

* Bounded by the corpus and by each case's recorded `limit`, as every count
  here is.
* Only `4edd39a3` was patched. `libical` 3.0.20 (107 `fail`) and master
  `48d52b4b` (19) are still unpartitioned; whether these two defects are the
  tail of those buckets is **not** measured and is not claimed.
* Defect A is stated for `HAVE_LIBICU=1`. The non-ICU `get_week_number()` in
  the `#else` branch derives the week number itself and normalises by
  `week_start`, so it is week-start-aware too and the same disagreement with
  `weeks_in_year()` should arise — but this build does not compile that branch
  and I did not build one that does.
* Patch B reproduces an observable and a reading of `expand_by_day()`'s
  contract. I did not find an upstream statement that `last_day` is a count;
  that reading comes from `daysmask_set_range(doy_offset + 1, doy_offset +
  last_day + 1)` and from the patch behaving correctly on 1727 cases.
* Nothing here has been reported upstream. External outreach is paused; see
  [`REQ-0013`](https://github.com/kaz8096/ai-terrarium-agent-control/issues/14).

## Reproduce

```
python3 findings/repro/112-libical-week-start-blind.py            # ~25s
python3 findings/repro/112-libical-week-start-blind.py --check    # the guard
python3 findings/repro/112-libical-week-start-blind.py --rebuild  # the table above
```

The default needs only the committed adapter and a `libical` build at
`$LIBICAL_LIB`; `--rebuild` additionally needs the source checkout and cmake and
is therefore not in `tools/repro-drift.json`. The guard is
`tests/test_libical_week_start.py`, which skips where no build is provisioned.
Per **rule 102** the patched builds install to their own prefixes: the run
finishes by rebuilding the pristine source into the canonical prefix, and the
restored `libical.so.4.0.6` is byte-identical to the one the published rows were
measured through.
