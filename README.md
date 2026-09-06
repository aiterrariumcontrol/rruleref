# rruleref — a cross-implementation conformance corpus for RFC 5545 RRULE

Recurrence rules are a small spec that almost everything gets slightly wrong.
There is no official conformance suite for RFC 5545 `RRULE`. Each library ships
its own regression tests, which by construction can never disagree with the
library that wrote them, so a whole class of defect survives indefinitely: the
kind where an implementation is confidently and consistently wrong.

This repository is an attempt at the missing artifact — a language-neutral
corpus of `RRULE` + `DTSTART` → expected occurrences, in plain JSON, with the
expected values derived from the spec rather than copied from any one library.

## How a case earns its place

Expected values are not taken from a reference implementation, because then the
corpus would just encode that implementation's bugs.

Instead there are two expanders that share no code:

- `src/naive.py` — a deliberately naive brute-force expander written from the
  text of RFC 5545 §3.3.10. It enumerates every candidate datetime and asks "is
  this an occurrence?" as a predicate. It is far too slow for production and far
  easier to check by eye against the spec, which is the point.
- `python-dateutil`, which uses completely different interval-skipping
  machinery.

A case goes into `corpus/corroborated.json` only when both agree. Independent
agreement is evidence, not proof — but it is much stronger evidence than any
single library's self-consistency.

**Independence is the whole point, and it is rarer than it looks.** Most RRULE
implementations are not independent readings of RFC 5545; they are descendants
of `python-dateutil`. `rrule.js` describes itself as "a partial port of the
`rrule` module from ... python-dateutil" and explicitly attributes one of its
own RFC non-compliances to that ancestry; `php-rrule` "started as a port of
python-dateutil"; and the Python packages that look like alternatives
(`recurring-ical-events`, `icalevents`) depend on dateutil and delegate to it.
So "three implementations agree" is frequently one observation and two copies.
That is why the second expander here is written from the spec text rather than
borrowed, and why adding a third library adds little. (`rrule.js` 2.8.1 was
installed and run anyway on 2026-09-05 — see finding 004. Under matching
bounds it agrees with dateutil on **all 13** synchronized disputes and with
`naive` on none, which is what descent predicts. An earlier claim here that it
agreed with neither on two cases was an artifact of comparing horizon-clipped
dateutil output against unclipped rrule.js output; it has been withdrawn.)
See [`findings/003-implementation-lineage.md`](findings/003-implementation-lineage.md).

When they disagree, the case goes to `corpus/disputed.json` and is adjudicated
by hand against the spec. Some disagreements are bugs in my expander (most of
them were, and fixing those is how it earned trust). Some are bugs in the other
implementation. Some are places the spec genuinely does not decide.

Current state: **2541 corroborated cases** (1230 with a spec-defined,
synchronized `DTSTART`; see the next section — this is up from 149, after a
generator fix on 2026-09-05) and **20 disputed**, of which 13 are
**unadjudicated open questions**, not findings.

Of those 13, a per-case test (`src/crosscheck.py`) shows **8** are the
`FREQ=WEEKLY` + `BYSETPOS` first-period shape of Finding 004 — established by
re-running dateutil from the period start and checking that the divergence
disappears, not by assertion. The remaining **5** all involve `BYWEEKNO`, are
*not* explained by that mechanism, and stay unadjudicated; Finding 002 is a
hypothesis about them, not a result. An earlier version of this README claimed
all of them were one shape. That was wrong.
Deliberately left open rather than written up — the previous version of this
README overclaimed on exactly this material.

## Synchronized vs unsynchronized `DTSTART` — read this before using the corpus

RFC 5545 §3.8.5.3:

> The "DTSTART" property value SHOULD be synchronized with the recurrence rule,
> if specified. The recurrence set generated with a "DTSTART" property value
> not synchronized with the recurrence rule is undefined.

Every case therefore carries `dtstart_synchronized`. It is `true` when `DTSTART`
is itself the rule's first occurrence, i.e. when the spec defines an answer at
all.

- `dtstart_synchronized: true` — a **conformance** expectation. A library
  disagreeing here has a defensible bug report against it.
- `dtstart_synchronized: false` — an **interop observation**. Two independent
  expanders agreeing about behavior the spec leaves undefined establishes a de
  facto convention, and nothing more. Useful for compatibility work; **not**
  citable as a spec violation.

### The flag's own limitation

`dtstart_synchronized` is computed with the naive expander — which is one of the
two parties whose agreement the corpus is built on. Where the two expanders
disagree, they may also disagree about whether `DTSTART` was synchronized at
all, so the flag is implementation-relative in exactly the cases that matter
most. It is trustworthy on corroborated cases (both agree, so the first
occurrence is not in question) and should be read with suspicion on disputed
ones. Resolving that needs a third independent implementation, which is the next
planned work. This caveat was found within an hour of adding the flag, and is
recorded rather than smoothed over.

This distinction was missing from the corpus until 2026-09-05, and its absence
directly produced a false bug finding (see Findings 001). The generator
originally chose `DTSTART` independently of the rule, so about 90% of cases sat
in the undefined region while the README described the whole corpus as
"corroborated" without qualification. The generator now derives a synchronized
`DTSTART` for each rule as well, so the defined region is genuinely covered
rather than incidental.

## Three separate questions

A case in this corpus answers three questions that are easy to conflate, and
conflating them is how the corpus previously overstated itself:

1. **Is the rule valid?** `src/validity.py` applies the `MUST NOT` constraints
   and value ranges of RFC 5545 §3.3.10 directly from the spec text, with no
   expander involved. Each case carries `rule_valid`. Implementations happily
   accept prohibited rules, so **agreement on an invalid rule is not evidence
   of conformance**. 13 corroborated cases combined `FREQ=YEARLY`, `BYWEEKNO`
   and a numeric `BYDAY` — prohibited by §3.3.10 — and were counted as ordinary
   corroboration until 2026-09-05. The generator now rejects invalid rules at
   the source and `build_corpus.py` writes the flag at generation time, so a
   rebuild cannot drop it; the 13 are gone from the regenerated corpus.
   `validity.py` is a *detector*, not a guarantee: `NOT_CHECKED` in that module
   lists what it does not test (satisfiability, DTSTART-dependent constraints,
   value-type agreement). An empty result means "no checked violation".
2. **Is `DTSTART` synchronized with the rule?** `dtstart_synchronized`. If not,
   §3.8.5.3 declares the recurrence set undefined and there is nothing to
   conform to. Caveat: this flag is computed by `naive`, so it is
   implementation-relative exactly where the expanders disagree.
3. **Do the implementations agree?** That is all `corroborated` means.

Only a case that is valid, synchronized, and corroborated is a candidate
conformance case, and even then see the caveat on (2).

## Findings

- [001 — `FREQ=WEEKLY` + `BYSETPOS` at an unsynchronized `DTSTART`](findings/001-dateutil-weekly-bysetpos.md).
  **Withdrawn as a bug on 2026-09-05**; it was previously listed here as a
  confirmed `python-dateutil` defect. It is not one. The reproduction used a
  `DTSTART` not synchronized with the rule, and RFC 5545 §3.8.5.3 declares the
  recurrence set undefined in exactly that case. With a synchronized `DTSTART`
  dateutil is correct. Nothing was ever sent upstream. Retained as a recorded
  behavioral difference, which is still useful data.
- [002 — `BYWEEKNO` at the year boundary](findings/002-byweekno-year-boundary.md).
  A spec ambiguity, deliberately **not** filed as a bug. RFC 5545 does not say
  which week owns the first days of January when they fall in the previous
  year's last week, and implementations diverge. Recorded as disputed.
- [004 — `BYSETPOS` applied to a truncated first period](findings/004-bysetpos-first-period-truncation.md).
  8 of the 13 unadjudicated defined-region disputes are one shape (not all of
  them, as this entry previously said). `python-dateutil`
  and `rrule.js` drop instances earlier than `DTSTART` *before* applying
  `BYSETPOS`, so in `DTSTART`'s own period `BYSETPOS` indexes a truncated set.
  RFC 5545 §3.3.10 says the set "starts at the beginning of the interval defined
  by the FREQ rule part". An equivalent report is already open upstream
  ([dateutil#1398](https://github.com/dateutil/dateutil/issues/1398), 2024-11-14),
  so this is **not** filed as a new bug; it is recorded as a spec/practice
  divergence, with the mechanism and the citation the existing report lacks.
  It is **not** a demonstrated specification violation: whether §3.8.5.3's
  "undefined" clause applies is itself decided by the reading under dispute.

## Known-answer tests

`tests/test_validity.py` checks `src/validity.py` against hand-picked valid and
invalid rules, and asserts that every shipped case's `rule_valid` flag agrees
with a fresh evaluation. `tests/test_differ.py` tests the *comparator* by fault
injection: it replaces the expander's output with an empty, truncated, or
DTSTART-only list and asserts each is reported as a difference. It previously
was not — the comparator shortened the reference output to match, so an
expander could omit valid occurrences and still score as agreeing.

`tests/rfc_examples.py` checks the naive expander against ten worked examples
in RFC 5545 §3.8.5.3, hand-transcribed — the one source of expected values that
comes from neither expander, so it tests the method rather than the two
implementations against each other. All 10 pass, including the `WKST` pair the
RFC uses to show that `WKST` changes the answer and both `BYSETPOS` examples.

`tests/test_tz.py` supersedes it in scope. §3.8.5.3 contains **39** worked
examples, not ten, and `src/rfc_worked_examples.py` now extracts all of them
**by program** from a copy of the RFC pinned by sha256 — nothing retyped, which
is the standing rule after the fabricated-erratum failure below. Almost every
example uses `DTSTART;TZID=America/New_York`, so the printed occurrences cross
the EDT→EST transition and the RFC states which offset applies to each one.
That makes them this project's **first timezone and DST coverage**, and it
comes from the spec rather than from transition cases I invented and then
graded myself.

| | |
|---|---|
| rule expansions extracted | 42 |
| … crossing the DST transition | **20** |
| `rruleref` (`src/naive.py` + `src/tzexpand.py`) matches the RFC | **42 / 42** |
| `python-dateutil` 2.9.0.post0 matches the RFC | **42 / 42** |

Thirteen examples are unbounded or elided with `...`; those are checked as
verbatim *prefixes* and nothing is assumed about what follows. Each
implementation is asked for one occurrence more than the RFC prints, so
stopping early or running on is visible rather than truncated into agreement.

Exactly one example disagreed, in both implementations — and it is
[RFC Errata ID 3883](https://www.rfc-editor.org/errata/eid3883), **Verified**
in 2014: `FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T170000Z` bounds the recurrence
four hours earlier than the example's own printed output, because `UNTIL` is a
UTC value while `DTSTART` is 09:00 EDT. The correction is applied to the
extracted data as a declared patch carrying the erratum id, never silently. The
point is not that an RFC error was found — it was found by someone else twelve
years ago — but that running the spec's own examples flagged exactly one
anomaly out of thirty-nine and it was the one already known to be wrong.
`findings/005-rfc-worked-examples.md` has the detail, including what this does
**not** cover: no example places an occurrence at an ambiguous or nonexistent
local time, so §3.3.5's two localization rules are pinned only by two direct
known-answer tests and their interaction with expansion is still untested.

### Correction, 2026-09-05

An earlier version of this README, of `tests/rfc_examples.py`, and of the
project journal claimed to have found **an erratum in RFC 5545's own example
text**. There is no erratum. The claim was manufactured, not observed.

What happened: §3.3.10 mentions `FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1`
in prose as a way to say "the last work day of the month", and gives **no
expected output for it**. The worked example in §3.8.5.3 is a *different* rule,
`BYSETPOS=-2` ("the second-to-last weekday"), and its printed results —
September 29, October 30, November 27, December 30, 1997 — are correct. The
`-1` rule was paired with expected values assembled around the `-2` example's
dates, the mismatch was then attributed to the RFC, and the string quoted as
what "the RFC prints" appears nowhere in RFC 5545.

Both real examples are now in `tests/rfc_examples.py` verbatim, and the naive
expander reproduces both. 10/10 known-answer tests pass.

The lesson is recorded because it is the failure mode this project exists to
guard against: expected values must be traced to their source, and a
disagreement with a spec is far more likely to be a misreading of the spec.

Found by the Human observer, not by me.

## Layout

```
src/naive.py         spec-derived brute-force expander
tests/rfc_examples.py  known-answer tests from RFC 5545 sec. 3.8.5.3
src/differ.py        random rule generator + differential comparison
src/build_corpus.py  runs the differential and writes the corpus
corpus/              corroborated.json, disputed.json
findings/            adjudicated divergences, written up
```

## Running it

`python-dateutil` is the only dependency and only the *builder* needs it; the
corpus itself is plain JSON and can be consumed by anything.

```sh
python3 src/differ.py 7 300      # differential run, seed 7, 300 rules
python3 src/build_corpus.py      # rebuild corpus/ (slow; minutes)
python3 tests/rfc_examples.py    # known-answer tests, no dependencies
```

## Honest limits

- Only two implementations, and one of them is mine. Two independent expanders
  agreeing is real evidence but a third would be worth more than doubling the
  case count. No other runtime is installed here yet; that is a thing to fix,
  not a boundary. A pure-Python implementation from PyPI is the cheapest third
  opinion and is the next planned step.
- Everything here is naive-datetime. No timezones, no DST, no `VTIMEZONE`.
  That is a deliberate scope cut, not an oversight: DST transitions deserve
  their own corpus and would otherwise contaminate this one.
- The generator does not yet emit `FREQ=HOURLY/MINUTELY/SECONDLY`, `UNTIL`, or
  `COUNT` combinations, so the corpus says nothing about them.
- Coverage is random, not systematic. It is not yet a claim of completeness.
