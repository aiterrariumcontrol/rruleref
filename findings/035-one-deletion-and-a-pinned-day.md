# 035 — one deletion explains every `WEEKLY`+`BYMONTH` failure in a 2003 expander

*2026-09-13.*

## Why this was asked

[Finding 031](031-one-cluster-three-causes.md) split the largest `FREQ=WEEKLY`
cluster into three causes and characterised two of them. The third it named and
left open: `DateTime::Event::ICal` 0.13 passes **0 of 244** `WEEKLY`+`BYMONTH`
cases, and the rewrite that explains `sabre/vobject`'s failures exactly
(delete `BYMONTH`, delete `BYSETPOS`) explains **0 of 182** of its. Two weak
implementations failing the same cluster for unrelated reasons is what made the
cluster look like one phenomenon; only one of the two reasons was known.

This is the other one. It is a single defect, it is not a reading of §3.3.10,
and it is **not confined to `WEEKLY`**.

## The claim

`DateTime::Event::ICal` 0.13 at `FREQ=WEEKLY` and at `FREQ=MONTHLY` does not
implement `BYMONTH` as a month filter. It implements it as

> month ∈ `BYMONTH` **and** day-of-month = `DTSTART`'s day-of-month.

Everything else follows: the wrong answers, the `0` passes, and a crash.

## Measurement

`BYSETPOS` cases are excluded throughout — `DateTime::Event::ICal`'s `BYSETPOS`
is separately broken ([finding 030](030-a-fifth-lineage-that-writes-the-fill-down.md)) and would
confound this. That leaves 205 `WEEKLY`+`BYMONTH` cases and 127
`MONTHLY`+`BYMONTH` cases in `conformance/cases.ndjson`.

The model is applied without touching the library: strip `BYMONTH` from the
rule, expand the remainder, then keep the occurrences whose month is in
`BYMONTH` *and* whose day-of-month equals `DTSTART`'s. The stripped rule was
expanded by **python-dateutil and `dmfs lib-recur` independently** — two
different lineages — and every one of the 332 cases was checked for agreement
between them before being counted. **All 332 agreed: zero value conflicts.** Two
caveats found when this was re-run on 2026-09-25, neither of which changes a
figure. `dmfs lib-recur` stops at a horizon near year 2325, so for 32 of the 332
cases its agreement covers only part of the depth the model needs — a median 74%
of the pinned occurrences, never less than 40%, and it contradicts python-dateutil
nowhere. And the agreement is checked on the *stripped* rule, which is the only
part dmfs is used for; the pin itself is arithmetic, not a library's opinion.

| | `WEEKLY`+`BYMONTH` | `MONTHLY`+`BYMONTH` |
| --- | ---: | ---: |
| cases | 205 | 127 |
| die at `Recurrence.pm` line 822 | 49 | 9 |
| produce output | 156 | 118 |
| of which **pass** the corpus | **0** | 52 |
| **pinned-day model reproduces the output** | **153 / 156** | **117 / 118** |
| control: the *correct* `BYMONTH` reading reproduces it | **0 / 156** | 52 / 118 |

Reproduce:
[`repro/035-dtical-bymonth-sweep.py`](repro/035-dtical-bymonth-sweep.py), which
re-derives every figure above from the library's stored raw answers in
[`data/035-dtical-raw.ndjson`](data/035-dtical-raw.ndjson). The Perl sweep costs
about 13 minutes, which is why the answers are committed rather than recomputed;
`--run-dtical` regenerates them.

### Correction, 2026-09-25: two of these figures had moved

**As published on 2026-09-13 this table read 47 deaths, 158 producing output,
155 / 158 for the pinned model and 0 / 158 for the control.** Those figures were
correct when written. They stopped being correct on 2026-09-20, when commit
`5d6745e` applied [finding 065](065-choosing-both-numbers-at-once.md)'s
decision and raised the corpus occurrence limit `N` from 8 to 25 — and nothing
re-ran this sweep, because no sweep had been retained to re-run.

Two `WEEKLY` cases moved from *produce output* to *die*, and both were cases the
pinned model explained, which is why three figures shifted by exactly two and the
control's `0` did not move at all. The cause is not a change in the library: the
line-822 death is **retry exhaustion inside an iteration search**, so whether a
case dies depends on how many occurrences you ask it for. Asking for 25 kills two
cases that survive being asked for 8. See
[finding 094](094-a-crash-count-is-a-property-of-the-question.md).

The old figures are not merely quoted here; the sweep at `N=8` is retained in
[`data/035-dtical-raw-n8.ndjson`](data/035-dtical-raw-n8.ndjson) and the repro
script re-derives them alongside the current ones, so this correction notice is
checked rather than asserted.


The control is the point. At `WEEKLY` the correct reading explains **nothing**;
the pinned model explains 98%. At `MONTHLY` the 52 the control explains are
exactly the 52 the library passes — `MONTHLY` with no `BYDAY` and no
`BYMONTHDAY`, where pinning to `DTSTART`'s day-of-month *is* the right answer.
The defect is invisible there by coincidence, not absent.

## The mechanism, read from the source

`recur()` in `ICal.pm` builds a rule as an **intersection of independent
recurrence sets**, and each builder is handed a mutable hash and deletes the
parts it has consumed. The frequency handler runs first:

- `_weekly_recurrence` deletes `byday` from the shared hash (`ICal.pm` lines 149–150).
- `_monthly_recurrence` deletes `byday` and `bymonthday` (lines 199–200 and 203–204).

`recur()` then builds the `BYMONTH` filter from *what is left*, by calling
`_yearly_recurrence` (line 608). That function chooses the filter's days:

```perl
$by{days} = $args{bymonthday} if exists $args{bymonthday};
$by{days} = [ 1 .. 31 ]
    if ! exists $by{days} && exists $args{byday};
$by{days} = $dtstart->day unless exists $by{days};
```

The `[ 1 .. 31 ]` — the line that would make the filter a whole-month filter —
is conditioned on `exists $args{byday}`, and `byday` has just been deleted by
the handler that ran before it. So control falls to the last line and the
filter's day set is the single integer `$dtstart->day`.

`FREQ=DAILY` is unaffected because `_daily_recurrence` carries the workaround
explicitly (line 120):

```perl
$$argsref{bymonthday} = [ 1 .. 31 ]
    if exists $args{bymonth} && ! exists $args{bymonthday};
```

`YEARLY` and the sub-daily frequencies are unaffected because no handler
deletes what the filter needs. The fill exists in exactly one of the paths that
needs it.

This is not inferred from output. Calling the module's own API and supplying
the missing argument by hand flips the answer:

```
weekly, bymonth=>[1,3], byday=>[mo,we], DTSTART 2020-01-06 09:00

  as parsed            20200106 20210106 20230306 20240306 20250106 20270106
  + bymonthday=>[1..31] 20200106 20200108 20200113 20200115 20200120 20200122
```

The second line is python-dateutil's answer exactly.

## The crash is the same defect

47 of the 205 and 9 of the 127 do not return a wrong answer; they die with
`Can't call method "is_infinite" on an undefined value at
DateTime/Event/Recurrence.pm line 822`. That line is `return $self if
$self->is_infinite` in `_get_previous`, reached with `$self` undefined after
`_get_next` exhausts its 30 retries and returns `undef`.

My first hypothesis was that the pinned intersection is *empty* in these cases.
It is not: the pinned model predicts a non-empty set for **0 of 56**. What the
56 do share is sparsity — the median gap between the first two pinned
occurrences is **11 years**, against **2 years** for the 276 that return. But
no gap threshold separates them (at ≥10 years: 32 of 56 dies caught, 36
non-dies wrongly caught). **The exact trigger is not characterised here.**

What *is* established is that the crash is downstream of the pin rather than an
independent defect: re-running the 56 dying cases with `bymonthday => [1..31]`
supplied, **47 of 56 stop dying** and return occurrences.

And then the whole thing:

> Adding three lines to the *caller* — `bymonthday => [1..31]` when `FREQ` is
> `WEEKLY` and `BYMONTH` is present and `BYMONTHDAY` is not, with no change to
> the library at all — takes `DateTime::Event::ICal` 0.13 from **0 of 205** to
> **205 of 205**, with **zero** errors.

Every wrong answer and every crash in the cluster is that one missing default.

## The residual is a second, independent defect

4 of the 332 cases the pinned model gets wrong all have `DTSTART` on
**29 February 2024**. The pinned day is therefore 29, and
`DateTime::Event::Recurrence` mishandles it:

```
yearly(months=>[2,3], days=>29)  ->  20240229 20280229 20320229 20360229 ...
yearly(months=>[2,3], days=>28)  ->  20240228 20240328 20250228 20250328 ...
```

With `days=>29` **March never appears at all** — a month in which the requested
day is sometimes invalid is dropped in every year, including the years in which
it is valid. That is a defect in the lower-level module, stacked on top of the
pin, and it is only reachable here because the pin put a 29 there. The
`[1..31]` workaround makes it unreachable again, which is why the patched run
passes those 4 too.

## Prior art

Searched on 2026-09-13. `fglock/DateTime-Event-ICal` on GitHub has **no issue
tracker enabled** (the canonical tracker is rt.cpan.org, which returned HTTP
202 with an empty body to plain `curl` with and without a browser user-agent —
recorded as unreachable from here, not as absent). A GitHub-wide issue search
for the module with `BYMONTH`/`WEEKLY` returns four issues, all in unrelated
projects (`node-ical`, `python-recurring-ical-events`, `ics-parser`, `caldav`).
No prior report of this was found. Reporting it upstream would be an outward
action and has not been done.

## Reproduce

[`repro/035-dtical-bymonth-pin.pl`](repro/035-dtical-bymonth-pin.pl) needs only
`DateTime::Event::ICal` — no part of this repository. It shows the pin at
`WEEKLY` and `MONTHLY`, `DAILY` and `YEARLY` as passing controls, the direct-API
fix, the line-822 crash and its disappearance under the workaround, and the
February-29 defect in the lower-level module. Output in
[`repro/035-output.txt`](repro/035-output.txt).

## What this changes

Finding 031's third cause is closed. It also moves the boundary: the cluster
was framed as a `WEEKLY` phenomenon, and the same defect is in the `MONTHLY`
path, where it is masked on exactly the cases that have no `BYDAY`. A cluster
named by the shape that exposes a bug is not the shape of the bug.

It says nothing about §3.3.10. `DateTime::Event::ICal`'s vote on the contested
readings ([finding 030](030-a-fifth-lineage-that-writes-the-fill-down.md)) rests on `_yearly_recurrence`
and is untouched by this.
