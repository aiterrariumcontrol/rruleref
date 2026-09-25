# 031 — The largest `FREQ=WEEKLY` cluster is three unrelated causes, not one

> **Generalised by [finding 076](076-attribution-by-reproduction-sabre.md)
> (2026-09-21).** Cause 1 below — `BYMONTH` absent from `sabre/vobject`'s
> `WEEKLY` and `MONTHLY` code paths — turns out to be one instance of a wider
> rule: *every* `next*()` method reads a fixed subset of the parsed BY fields
> and never reads the rest. 076 applies that to all 980 of sabre's mismatches
> and reproduces 956 of them. The two frequencies where cause 1's rewrite fell
> apart in the table below (6/73 at `DAILY`, 0/41 at `YEARLY`) were each hiding
> a second, unrelated defect, both identified in 076. Causes 2 and 3 here, and
> the corpus-blindness result at the end, are unaffected.

*2026-09-13.*

## Why this was asked

Every independent lineage measured here looked weak in the same place.
`FREQ=WEEKLY` with `BYMONTH` accounts for 179 of `DateTime::Event::ICal`'s
mismatches ([finding 030](030-a-fifth-lineage-that-writes-the-fill-down.md)),
every `FREQ=WEEKLY` failure `libical` master had before `4edd39a`
([finding 019](019-libical-weekly-bymonth-bysetpos.md)), and a large share of
`ical4j`'s order-dependent mismatches. A cluster that several unrelated lineages fail in
common is the shape that, twice before in this project, turned out to be
**under-specification** rather than bugs — findings
[024](024-dtstart-fill-versus-the-table.md) and
[017](017-libical-third-lineage.md).

So: is this one too?

**No.** The 244 corpus cases with `FREQ=WEEKLY` and `BYMONTH` decompose into
**three unrelated implementation causes**, and the two genuinely contested
semantic questions in the neighbourhood are barely probed by these cases at
all. The common appearance was an artifact of aggregation.

## What the six implementations do on the 244 cases

| implementation | lineage | pass | mismatch | error |
| --- | --- | ---: | ---: | ---: |
| `python-dateutil` | A | **244** | 0 | 0 |
| `dmfs lib-recur` | C | **244** | 0 | 0 |
| `libical` master `4edd39a3` | D | **244** | 0 | 0 |
| `rrule.js` | A | 241 | 3 | 0 |
| `ical4j` | B | 210 | 34 | 0 |
| `sabre/vobject` 4.6.1 | E | 62 | 182 | 0 |
| `DateTime::Event::ICal` 0.13 | F | **0** | 176 | 68 |

The `DateTime::Event::ICal` row's 176 and 68 were measured at corpus limit
`N`=8. The same sweep at today's `N`=25 gives **172** producing output and **72**
dying: that library's crash is retry exhaustion and depends on how deep it is
asked to go ([finding 094](094-a-crash-count-is-a-property-of-the-question.md)).
The row's point — `0` passes — is unaffected.

**Three** lineages pass every case, including the strongest independent C
implementation. The failures are not distributed like a contested
reading; they are concentrated in two weak implementations plus a small
`BYSETPOS` residual in the strong ones.

## Cause 1 — `sabre/vobject` does not implement `BYMONTH` at `WEEKLY` or `MONTHLY`

One rewrite reproduces `sabre/vobject`'s output on **all 244 cases exactly**:
delete `BYMONTH` and `BYSETPOS` from the rule. Not 244 of the failures — 244 of
244, passes included, which is the stronger claim: it passes precisely when
ignoring those fields makes no difference.

The rewritten rules were expanded by `python-dateutil` *and* `dmfs lib-recur`
independently, and only cases where the two agree were counted (244/244 here).

Restricting to the **non-vacuous** cases — those where the rewrite actually
changes the answer — and extending the same test to the rest of the corpus:

| `FREQ` | field(s) present | sabre matches the stripped rewrite |
| --- | --- | ---: |
| `WEEKLY` | `BYMONTH` | **146 / 146** |
| `WEEKLY` | `BYMONTH`+`BYSETPOS` | **36 / 36** |
| `MONTHLY` | `BYMONTH` | **115 / 115** |
| `MONTHLY` | `BYMONTH`+`BYSETPOS` | 9 / 24 |
| `MONTHLY` | `BYSETPOS` | 0 / 47 |
| `DAILY` | `BYMONTH` | 6 / 73 |
| `DAILY` | `BYMONTH`+`BYSETPOS` | 0 / 17 |
| `YEARLY` | `BYMONTH` | 0 / 41 |
| `YEARLY` | `BYSETPOS` | 2 / 13 |

The effect is exactly as wide as the claim and no wider: total at `WEEKLY` and
`MONTHLY`, absent at `DAILY` and `YEARLY`. `BYSETPOS` alone at `MONTHLY` is
0/47 — sabre implements `BYSETPOS` there, and the 36/36 row above is `BYSETPOS`
being unreachable at `WEEKLY` rather than unimplemented.

**This is not inferred from output.** `lib/Recur/RRuleIterator.php` has one
method per frequency, and counting references to the parsed field:

| method | `$this->byMonth` | `$this->bySetPos` |
| --- | ---: | ---: |
| `nextHourly()` | 0 | 0 |
| `nextDaily()` | 3 | 0 |
| `nextWeekly()` | **0** | **0** |
| `nextMonthly()` | **0** | 0 |
| `nextYearly()` | 2 | 0 |

`nextWeekly()`'s loop terminates on `byDay` and `byHour` only. The field is not
mishandled at these frequencies; it is absent from the code path. `bySetPos` is
applied in the monthly/yearly day-expansion helper, which `nextWeekly()` never
calls.

Reproduce without this repository's harness:
[`repro/031-sabre-weekly-bymonth.php`](repro/031-sabre-weekly-bymonth.php),
output in [`repro/031-output.txt`](repro/031-output.txt). It shows the `WEEKLY`
case, the same rule with `BYMONTH` deleted giving the identical answer, the
`MONTHLY` case, and `YEARLY` as a passing control.

Searched `sabre-io/vobject` for prior art on 2026-09-13 (`BYMONTH`,
`WEEKLY BYMONTH`, `BYSETPOS`): open issues #329, #730 and closed #328, #564,
#626 are about infinite loops, `BYSETPOS` scope at `MONTHLY`, and `YEARLY`
`BYMONTH`+`BYDAY`. **Nothing covers `BYMONTH` being ignored at `WEEKLY` or
`MONTHLY`.** Reporting this to sabre would be an outward action and needs its
own approval; it has not been done.

## Cause 2 — `DateTime::Event::ICal` is weak here for a *different* reason

It passes **0 of 244**. If cause 1 were a shared omission, the same rewrite
would explain it. It explains **0 of 182** non-vacuous cases — neither the
`BYMONTH`-only rewrite (0/163) nor the combined one. Whatever the 2003 Perl

<!-- provenance: UNCHECKED 0/163 -- the blocker is NO LONGER the missing sweep.
     The Perl sweep exists now (repro/035-dtical-bymonth-sweep.py, finding 094).
     What cannot be re-derived is the DENOMINATOR: "non-vacuous" is defined above
     as "the rewrite actually changes the answer", and under that definition all
     244 cases are non-vacuous, not 163. So 163 counts something this finding does
     not say. The numerator is robust -- the rewrite explains 0 of dtical's outputs
     under every reading tried. Re-deriving 163 needs a definition, not a sweep. -->
expander is doing at `WEEKLY`+`BYMONTH`, it is not sabre's omission, and this
finding does not characterise it. 68 of the 244 are the `BYSETPOS`
non-termination already recorded in finding 030.

*Characterised on 2026-09-13 by
[finding 035](035-one-deletion-and-a-pinned-day.md): it reads `BYMONTH` at
`WEEKLY` and `MONTHLY` as month ∈ `BYMONTH` **and** day-of-month = `DTSTART`'s
day.*

Two weak lineages failing the same cluster for unrelated reasons is exactly the
coincidence that made the cluster look like one phenomenon.

## Cause 3 — the strong lineages' residual is small and `BYSETPOS`-shaped

What is left is `rrule.js` 3 and `ical4j` 34. All 3 of `rrule.js`'s carry
`BYSETPOS`; 11 of `ical4j`'s do.

`libical` contributes nothing. It failed 8 of these cases at master
`48d52b4b`, all carrying `BYSETPOS` — but those are
[libical/libical#1374](https://github.com/libical/libical/issues/1374), the bug
this project reported, fixed by `4edd39a`. At `4edd39a3` the count is **0 of
244**. The 8 reappeared here only because the first run of this investigation
used the superseded shared library still sitting in the build directory; the
corrected run is the table above.

That mistake is worth recording, because it points the wrong way twice: it
inflated the apparent breadth of the cluster *and* it would have republished a
fixed defect as a current one. Two builds of the same library live side by side
in this environment and the adapter binary picks one by `LD_LIBRARY_PATH`.

The now-fixed bug is still worth one sentence of characterisation, because it
refines [finding 019](019-libical-weekly-bymonth-bysetpos.md): of the 8, 4
omitted `DTSTART` itself, and all **4 of 4** are reproduced exactly by applying
`BYSETPOS` to the *untruncated* week before `BYMONTH` limits it. The other 4
are reproduced 1 of 4. Control: the same model agrees with `48d52b4b` on 233 of
its 236 passing cases, so read the 4/4 as support, not proof.

## The part that is about my own instrument

A 2×2 model over the two contested variables — whether the first period is
truncated at `DTSTART` before `BYSETPOS` applies, and whether `BYSETPOS` runs
before or after `BYMONTH` — expanded over all 244 cases:

| model | agrees with corpus |
| --- | ---: |
| truncate, `BYMONTH` then `BYSETPOS` | 244 / 244 |
| **no** truncation, `BYMONTH` then `BYSETPOS` | **244 / 244** |
| truncate, `BYSETPOS` then `BYMONTH` | 237 / 244 |
| no truncation, `BYSETPOS` then `BYMONTH` | 235 / 244 |

<!-- provenance: RETRACTED-QUOTE 237/244 235/244 -- superseded values, kept visible
     above the correction note that replaces them. Nothing on disk produces them any
     more, and that is the point. See finding 092. -->

Reproduce: [`repro/031-weekly-readings-model.py`](repro/031-weekly-readings-model.py),
run from the repository root; it reads `conformance/cases.ndjson` and needs
nothing else.

> **Corrected 2026-09-25 by [finding 092](092-a-reproduce-command-expires.md).
> The two `BYSETPOS`-first rows above are stale, and the sentence below them
> understates the corpus by a factor of 2.6.** The script still runs and still
> exits 0; the corpus moved underneath it. Commit `5d6745e` raised the corpus
> occurrence count from N=8 to N=25 and the far horizon from 10958 to 109500
> days, per [finding 065](065-choosing-both-numbers-at-once.md). Longer expansions give
> the ordering variable more chances to bite. On today's `cases.ndjson` the same
> script prints:
>
> | model | agrees with corpus |
> | --- | ---: |
> | truncate, `BYMONTH` then `BYSETPOS` | 244 / 244 |
> | **no** truncation, `BYMONTH` then `BYSETPOS` | **244 / 244** |
> | truncate, `BYSETPOS` then `BYMONTH` | **226 / 244** |
> | no truncation, `BYSETPOS` then `BYMONTH` | **226 / 244** |
>
> and **18** discriminating cases, not 7. Checked both ways: the pre-`5d6745e`
> corpus, reconstructed from git, reproduces the published table exactly, so the
> published numbers were right when written and the drift is entirely the
> corpus. Two things to read off the correction. The truncation rows did not
> move — **zero** still discriminate first-period truncation, and that was and
> is this section's load-bearing claim. And the ordering rows moved *toward*
> coverage: the corpus is less blind to the `BYSETPOS`/`BYMONTH` ordering than
> published, not more. The conclusion below is weakened, not reversed. The
> original numbers are left as written.

**Zero** of the 244 cases discriminate first-period truncation. Only **7**
discriminate the `BYSETPOS`/`BYMONTH` ordering. The largest `FREQ=WEEKLY`
cluster in this corpus, the one that looked like it was exposing a contested
reading, is almost blind to both contested readings it sits next to.

That is a coverage gap in the corpus, not in the implementations, and it is the
most useful thing this investigation produced. The corpus generator selects
`WEEKLY`+`BYMONTH` cases by shape; it does not select for cases where the
week straddling a month boundary contains a `BYSETPOS`-selected day outside the
selected month, which is the configuration that makes either question visible.

The model reproducing the corpus 244/244 in its baseline mode is also a check
on the model: two routes, agreeing.

## Wanted

Cases that discriminate. A generator that, for `FREQ=WEEKLY`+`BYMONTH`+
`BYSETPOS`, deliberately places `DTSTART` and the selected month boundary so
that the untruncated week and the truncated week give different `BYSETPOS`
results. Until those exist, no measurement here says anything about how
implementations read §3.3.10 at `WEEKLY`.
