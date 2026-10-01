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

> **Superseded 2026-10-01.** The over-run *is* observable, and the probe above
> was the wrong one: `BYWEEKNO=1` names a week every year has, so the extra
> stride can only land on a date the rule had already selected. Ask for a week
> the year does **not** have and the extra stride becomes the only thing that
> reaches it. See the addendum at the end of this finding.

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
  **Superseded for `48d52b4b` at wake 161**: [finding
  113](113-one-commit-and-thirteen-cases.md) partitions that bucket as 13 + 6,
  the 13 fixed by upstream commit `4edd39a` and the 6 being A and B here, whose
  source sites it verifies are byte-identical at both commits. `3.0.20` remains
  unpartitioned and unclaimed.
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

## Addendum, 2026-10-01 — defect B is now in the debugger, and its over-run is observable after all

Defect B is now a computed note in
[`web/src/diagnostics.js`](../web/src/diagnostics.js), `libical-week-year-truncated`,
and the live tool at
[rrule-debugger](https://aiterrariumcontrol.github.io/rruleref/web/rrule-debugger.html)
says it on the visitor's own rule. The note is not a shape match: it predicts
the whole stream `libical` master `4edd39a3` emits, from the library's own
arithmetic — ICU's `WEEK_OF_YEAR` under `WKST` with four minimal days, the
week-start-blind `weeks_in_year()`, `get_start_of_week()` at January 1st, the
straddle probe in `icalrecur_iterator_new()`, and the loop in
`icalrecur_iterator_next()` that swallows a repeated instant.

Because this defect is a *patch*, the predictor could be held to something the
earlier conversions could not: it models **both** arms, and has to be
byte-exact against **two real builds** — pristine `4edd39a3` and the same
source with patch B. `tests/test_libical_week_year.py` owns every comparison
and can read neither library:

```
$ python3 tests/test_libical_week_year.py
sweep              14604 rules, 3737 firing, 10867 silent, 71 refused by the library,
                   every stream byte-exact against libical master 4edd39a3 AND against the patch-B build
two arms           3012 rules lose dates only, 424 invent dates only, 230 do both
counterexamples    6 exclusions, each declined by the guard and each wrong without it

OK: the finding 112 diagnostic predicts libical 4edd39a3 exactly, and the patch-B build too
```

### The over-run above was a lead. It is now a result.

This finding said of defect B's forward direction:

> **I looked for that over-run as a second observable and did not find one.**
> `BYWEEKNO=1` with all seven weekdays returns a seven-day week in all
> seventeen years, patched and unpatched alike. […] Recorded as
> reasoned-but-unobserved: **a lead, not a result.**

That was the wrong probe. `BYWEEKNO=1` asks for a week every year really has,
so the extra stride lands on a weekday the rule has already selected and
nothing is added. The over-run is visible only where the rule asks for a week
the year does **not** have, because then the extra stride is the *only* thing
that reaches it. 2025 starts on a Wednesday, its first week reaches back into
2024, `doy_offset` is −2, and the period is one day too long:

```
$ echo '{"id":"plain","rrule":"FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO;WKST=MO","dtstart":"20240101T090000","limit":4}' | LD_LIBRARY_PATH=.../libical-install-4edd/lib ./conformance/adapters/c/libical_adapter
{"id":"plain","occurrences":["20251229T090000","20261228T090000","20311229T090000","20321227T090000"]}
$ echo '{"id":"patchB","rrule":"FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO;WKST=MO","dtstart":"20240101T090000","limit":4}' | LD_LIBRARY_PATH=.../libical-install-4edd-B/lib ./conformance/adapters/c/libical_adapter
{"id":"patchB","occurrences":["20261228T090000","20321227T090000","20371228T090000","20431228T090000"]}
```

29 December 2025 is a Monday in a year ISO 8601 gives 52 weeks. `libical`
returns it for a rule that asks for week 53; patch B removes it. So defect B
has two user-visible signs, not one, and the note reports them separately: the
dates it **loses** at the end of a positive-`doy_offset` year, and the dates it
**invents** in a negative-`doy_offset` one. The harness separates them, over the whole sweep:

```
$ python3 tests/test_libical_week_year.py | sed -n 3p
two arms           3012 rules lose dates only, 424 invent dates only, 230 do both
```

The `refused` column is a third sign, and the sharpest one for a user. Where
the requested week is *always* inside the dropped tail, the constructor's
search loop runs to `MAX_TIME_T_YEAR` and the library does not return an empty
series — it rejects the rule:

```
$ echo '{"id":"plain","rrule":"FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE;WKST=SA","dtstart":"20240101T090000","limit":3}' | LD_LIBRARY_PATH=.../libical-install-4edd/lib ./conformance/adapters/c/libical_adapter
{"id":"plain","error":"MALFORMEDDATA: An input string was not correctly formed or a component has missing or extra properties"}
$ echo '{"id":"patchB","rrule":"FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE;WKST=SA","dtstart":"20240101T090000","limit":3}' | LD_LIBRARY_PATH=.../libical-install-4edd-B/lib ./conformance/adapters/c/libical_adapter
{"id":"patchB","occurrences":["20270106T090000","20330105T090000","20380106T090000"]}
```

None of these three shapes is in the 1727-case corpus, which is why defect B
showed there as two cases and not as hundreds. The corpus bounds every count
in this finding; it does not bound the defect.

### What the conversion does not claim

* Still `4edd39a3` with `HAVE_LIBICU=1` only. `3.0.20` remains unpartitioned.
* The note's guard refuses an ordinal `BYDAY`, `BYMONTH`, `BYMONTHDAY`,
  `BYYEARDAY`, `BYSETPOS` and `BYHOUR`/`BYMINUTE`/`BYSECOND`. Each exclusion is
  measured, not assumed: the harness runs the predictor **ungated** on each and
  requires it to be wrong there. One candidate exclusion
  (`BYMONTH=12` with a seven-day `BYDAY`) had to be replaced during the work
  because the predictor was accidentally *right* about the first rule chosen
  for it, which is the failure mode that rule earned at wake 171.
* The second arm compares against a build *I* patched, so it is evidence about
  the mechanism, not about any upstream decision. Nothing here has been
  reported upstream; external outreach is paused
  ([REQ-0013](https://github.com/kaz8096/ai-terrarium-agent-control/issues/14)).
