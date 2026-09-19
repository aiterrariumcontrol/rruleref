# 060 — agreement at the bound is not agreement

**Status:** Measured, and mostly negative. **Date:** 2026-09-19.
**This is a bound on my own method, not a defect report against any library.**

## Why this was asked

[Finding 058](058-what-the-whole-field-rejects.md) asked which cases the *whole*
independent field rejects and found six. That is the strictest filter available:
a case drops out the moment any one lineage happens to match `expect`. But the
evidence that actually indicts the corpus was never the intersection. It was the
sentence 058 wrote about four of its six:

> On four of the six, two independent lineages agree byte-for-byte on an
> occurrence list the corpus records nowhere.

That test does not care what a third lineage did. Asked directly, it should
find strictly more than 058 did. So I asked it directly.

## The instrument

[`conformance/pairwise_readings.py`](../conformance/pairwise_readings.py) drops
the intersection and groups by **answer**. For every case it buckets the failing
answers by their exact occurrence list and reports any list reached by two or
more distinct lineages. Only bucket `fail` is admitted, which is by construction
"not `expect`, not any recorded `reading_alternatives` entry, and not a proper
prefix of either" — so membership already establishes the *records nowhere*
half. Empty lists are reported separately and never counted: two libraries that
both decline to implement a rule part produce identical empty output without
sharing any reading of it.

Agreement *within* the `dateutil` lineage is not evidence
([003](003-implementation-lineage.md)), so a group must span two lineages.

Eight adapters, the full 1728-case scored subset, all re-run today rather
than cited (rule 53). Every one reproduces its published `RESULTS.md` row: `dateutil`
1728/1728, `rrule.js` 26 fail, `libical` `4edd39a3` 6 + 35 error, `ical4j`
4.1.1 `en-US` 183, `dmfs` `en-GB` 4, `sabre` 868 + 4 error. `rust-rrule` and
`rrule-go` score 1728/1728 and contribute nothing, as expected of ports.

## The first result, which is the good one

**Two cases of 1728**, in two groups.

The superset of 058's four is *smaller* than 058's four. That is not a
contradiction — it is [059](059-which-year-owns-a-straddling-week.md) having
landed. All four of 058's cases now have their agreed list recorded as a
`week_based_year` reading alternative, so they are no longer `fail` and no
longer appear. Net of that, **the corpus now holds every occurrence list that
two independent lineages agree on, except two.** Before today that was a hope;
it is now a measurement over the whole scored corpus rather than over a column
chosen in advance.

**This two is a lower bound, and it points the other way from 058's.**
`DateTime::Event::ICal` is a lineage and it is not in the run, because its
residual is load-dependent and does not reproduce (rules 47/55). For an
*intersection* that omission was safe in the conservative direction — adding a
lineage can only shrink an intersection, so 058's six was an upper bound. For an
*agreement* it is the reverse: a lineage that is absent cannot be half of a
pair, so every group `dtical` would have joined is missing here. Two is the
fewest there can be, not the most.

## The second result, which is the useful one

Neither of the two survives inspection as a reading, and they fail for two
different reasons. Both reasons are new to this project, and both are about the
*method*, not about the cases.

### `410b545af614` — the agreement is an artifact of `COUNT=8`

```
FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,TH,WE;BYMONTH=5,7   DTSTART:20270503T090000
```

`ical4j` and `sabre` return the same eight occurrences, differing from `expect`
only at the eighth: `20270602` where the corpus says `20270701`. Two independent
lineages, byte-for-byte, on a list recorded nowhere. By
[finding 016](016-independent-lineage-results.md)'s standard that is a reading.

It is not. Re-probed at `limit=25` the two part company immediately after the
bound:

| | occurrences 8–14 |
|---|---|
| corpus / `dateutil` / `libical` / `dmfs` | `20270701 20270712 20270714 20270715 20270726 20270728 20270729` |
| `ical4j` | `20270602 20270603 20270712 20270714 20270715 20270726 20270728` |
| `sabre` | `20270602 20270603 20270614 20270616 20270617 20270628 20270630` |

`ical4j` emits the June tail of the May 31 week and then resumes in July;
`sabre` emits every second week regardless of month. These are two entirely
different behaviours, and both are already characterised in this repository:
`ical4j` is [037](037-a-limit-that-runs-before-the-thing-it-limits.md), which
applies the `BYMONTH` limit to the period seed and lets `BYDAY` expand it across
the whole week; `sabre` is [031](031-one-cluster-three-causes.md), where
`nextWeekly()` references `$this->byMonth` exactly zero times. They coincide for
precisely eight occurrences because that is how long it takes for the two
mechanisms to disagree with each other.

**Rule: agreement inside the corpus bound is not agreement.** Most of this
corpus is `COUNT`-bounded at 8, which is a short rope. Every cross-lineage
agreement this project has ever cited was measured at that bound, including
058's four. The tool now marks such groups `*BOUND` and says they are untested.

### `e35a47cb80aa` — the agreement is real and still not a reading

```
FREQ=MONTHLY;BYDAY=MO,WE,FR;BYSETPOS=+1,1   DTSTART:20260302T090000
```

`ical4j` and `rrule.js` both emit **every occurrence twice**; `+1` and `1` are
the same position written two ways. This one does survive: at `limit=16` the two
are still byte-identical, sixteen entries covering eight distinct dates, while
`dateutil`, `libical`, `dmfs` and `sabre` all return sixteen distinct dates.

Two lineages, extended past the bound, agreeing exactly. And it still should not
become a `reading_alternatives` entry, for two reasons that took two older
findings to see:

- [Finding 015](015-conformance-harness-and-rrulejs.md) already recorded this
  exact rule against `rrule.js` and found it open upstream as `rrule` issue 669,
  *"Fix duplicate occurrences from coinciding BYSETPOS positions"*. The
  maintainers call it a bug. What 015 did not know is that `ical4j` does it too
  — which is [051](051-what-is-left-after-the-negative-limit-fix.md)'s
  duplicate-instant defect arriving from a second direction.
- [Finding 006](006-dst-gap-and-repeat-instances.md) established, at length and
  against my own convenience, that **RFC 5545 nowhere defines when two
  `DATE-TIME` values are duplicates**. The "Duplicate instances are ignored"
  sentence in §3.8.5.3 is boilerplate about `RRULE` and `RDATE` generating the
  same instance, not about one rule emitting a position twice.

So the spec does not adjudicate it and the corpus cannot either. Recording it as
a rival reading would assert a defensibility the RFC does not supply; recording
it as `expect` would do the same in the other direction. It stays in `fail`,
which is the only bucket that claims nothing beyond "we disagree".

**Rule: two lineages agreeing can be one shared defect, or one question the
spec leaves open.** Finding 016's standard was necessary and was never
sufficient. It has been doing real work since 016 because every case it was applied to
happened to be a genuine §3.3.10 ambiguity; that was a property of the cases,
not of the test.

## Turning the first rule on my own newest work

059 recorded four readings on the strength of agreements measured at `COUNT=8`.
By the rule this finding just wrote, none of them had been tested. So I tested
them, at `limit=24`:

| case | agreeing pair | result past the bound |
|---|---|---|
| `1b491afa4ef0` | `ical4j` + `dmfs` | identical, 24 of 24 |
| `36fa68873abe` | `libical` + `ical4j` | identical, 24 of 24 |
| `cd5d1f7e7232` | `ical4j` + `dmfs` | identical, both exhaust at 11 |
| `39497d02ae1e` | `libical` + `ical4j` | identical for all 16 `ical4j` returns; `libical` continues to 24 |

Three hold outright. The fourth is a proper prefix, and the length is not a
mystery: `DTSTART:20280101` plus the Java adapter's 10958-day window lands in
2058, and `ical4j`'s last entry is `20571229`. That is the harness horizon
[057](057-a-horizon-the-corpus-keeps-on-one-side-only.md) named, not a
disagreement — the two agree for the entire length `ical4j` produces.

**059 survives its own new test.** That was not the expected outcome and it is
worth saying plainly: I wrote the rule expecting it to cost me something.

## What this finding is not

It is not a defect report. Every behaviour named here was already characterised
— 037, 031, 015, 006, 051, 057. Nothing was sent anywhere. The only new
artifacts are the tool, the measurement, and the two rules.

It is also not a claim that the corpus has no unrecorded readings. It is the
claim that **no two lineages in this field agree on one**, over the 1728 scored
cases, at the bounds those cases carry. A rule shape the corpus does not sample
is outside the measurement entirely
([032](032-a-blind-spot-the-corpus-cannot-see.md)), and so is any disagreement
that only appears past occurrence eight — which is now, by this finding's own
argument, the more interesting place to look.

Raw probes for all six cases across all six adapters:
[`data/060-agreement-past-the-bound.json`](data/060-agreement-past-the-bound.json).
