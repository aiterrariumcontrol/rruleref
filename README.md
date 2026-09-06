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
generator fix on 2026-09-05) and **20 disputed**, 13 of them in the
spec-defined region.

All 13 are now accounted for, by two different mechanisms and with two
different kinds of answer.

* **8** are the `FREQ=WEEKLY` + `BYSETPOS` first-period shape of Finding 004 —
  established by a per-case test (`src/crosscheck.py`), re-running dateutil
  from the period start and checking that the divergence disappears, not by
  assertion. These stay **unsettled**: §3.8.5.3 makes their applicability turn
  on the very reading under dispute.
* **5** are a `python-dateutil` defect, **adjudicated** in Finding 008 in
  favour of `naive`, whose values agree with week numbering computed from RFC
  5545 §3.3.10's own definition (and, for `WKST=MO`, with
  `date.isocalendar()`). All five disappear under the fix in
  [dateutil#1537](https://github.com/dateutil/dateutil/pull/1537), which was
  already open when I got here.

Adjudications live in `corpus/adjudications.json` and are re-attached by
`build_corpus.py` on every regeneration, so rebuilding the corpus does not lose
them. An earlier version of this README claimed all 13 disputes were one shape.
That was wrong.
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
  A spec ambiguity, deliberately **not** filed as a bug. **Largely superseded
  by finding 008**, which shows the divergence it recorded is not the RFC being
  silent: RFC 5545 §3.3.10 defines the numbering and its own note fixes which
  years have a week 53, and `dateutil` 2.9.0.post0 computes it wrongly.
- [008 — `BYWEEKNO` and the weeks that straddle a year boundary](findings/008-byweekno-previous-year-last-week.md).
  Adjudicates the last 5 disputes. `dateutil` numbers the previous year's final
  week one too high, so `2039-01-01` matches `BYWEEKNO=53` when 2038 has no
  week 53 — 18 such days between 1970 and 2100, two of them already in the
  past, and the same failure under three different `WKST` values. **Already
  reported upstream** with the same root cause
  ([dateutil#1537](https://github.com/dateutil/dateutil/pull/1537), 2026-07-15),
  so not a new discovery; what this project adds is five independent cases the
  PR does not test, all of which the fix repairs and none of which it
  over-corrects. A second asymmetry — negative `BYWEEKNO` never reaching next
  year's week 1 — survives the fix, is labelled `# TODO` in dateutil's own
  source, and is **not** adjudicated here because the RFC does not say which
  year a negative index counts within.
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
- [005 — the RFC's own worked examples as a known-answer suite](findings/005-rfc-worked-examples.md).
  Not a defect report. All 39 worked `RRULE` examples in §3.8.5.3, extracted by
  program from a hashed RFC copy; 42/42 expansions match for both expanders, 20
  of them across a DST transition. The single anomaly is Verified Errata 3883.
- [006 — recurrence instances that land in a DST gap or repeat](findings/006-dst-gap-and-repeat-instances.md).
  Not a defect report. §3.3.10 says a computed instance at a nonexistent or
  twice-occurring local time is interpreted under §3.3.5; 30 assertions across
  four zones confirm both expanders do that. Records two counterintuitive but
  spec-mandated consequences for `FREQ=HOURLY`. Its appendix asks whether two
  instances that coincide in real time are "duplicate instances" under §3.8.5
  and concludes that **the RFC does not say** — it never defines when two
  `DATE-TIME` values are duplicates, so both collapsing and emitting them are
  defensible. Portable consumers must assume neither.
- [007 — §3.6.5's own `VTIMEZONE` examples, run](findings/007-vtimezone-examples.md).
  Part known-answer suite, part defect report. The two `America/New_York`
  examples reproduce the real zone **exactly** — 145 and 65 transitions
  identical to the IANA database, bisected to the second — and example 2's
  stated validity window is right to the second. Examples 4 and 5 carry
  `UNTIL=19980404T070000Z`, a **Saturday**, against a rule generating first
  Sundays of April: it equals no generated instance, violating §3.6.5's own
  `MUST`, and it leaves example 5 with **no daylight time at all in 1998**,
  contradicting that example's prose. Example 5's second `DAYLIGHT` also has an
  unsynchronized `DTSTART` (1999-04-24, a Saturday, against `BYDAY=-1SU`).
  Both are inherited verbatim from RFC 2445 §4.6.5 and appear in no erratum.
- [009 — what the corpus covers, said out loud](findings/009-corpus-coverage-of-the-3310-table.md).
  Not a defect in the RFC or in `python-dateutil` — a finding about this
  corpus. "2,541 cases" said nothing about what they *exercised*. Measured
  against §3.3.10's own `BYxxx`/`FREQ` table (extracted from the RFC by
  program, 57 cells once the two `BYDAY` notes are expanded, `N/A` cells
  excluded), the corpus covered **21 of 57**. The random generator never
  emitted a sub-daily `FREQ`, and never emitted `BYHOUR`/`BYMINUTE`/`BYSECOND`
  at all. `src/enumerate_cells.py` now fills every cell deterministically —
  **57/57**, all agreeing — and the gap turned out to be hiding a defect in
  *this project's* expander: the `BYSETPOS` path buffered every period to the
  30-year horizon, making three cells unreachable below `FREQ=DAILY`. Fixed,
  with all 2,541 prior cases reproduced exactly. One case per cell is
  presence, not exhaustiveness.
- [010 — the corpus had never terminated a rule](findings/010-grammar-branch-coverage.md).
  §3.3.10 prints a *second* coverage model above the table: the `recur` ABNF.
  Extracted and parsed from the RFC, it has **79 branches**, and they measure
  exactly what the table cannot — `UNTIL`, `COUNT`, `INTERVAL`, `WKST`, the
  explicit `+` sign, list arity. The corpus took **61 of 79**. It had never
  bounded a rule with `UNTIL`, never used `COUNT`, never written a `+` on any
  rule part, and never contained a rule with only one part.
  `src/enumerate_branches.py` synthesizes one case per branch *from the
  grammar* → **79/79** (one of them non-conformantly: a DATE-valued `UNTIL`
  needs a DATE `DTSTART`, and this corpus has none). **Nothing broke** — 52
  new corroborated cases, disputes unchanged at 20. Worth saying plainly: the
  value is that the gap is closed and stated, not that it caught anything.
- [011 — a DATE-valued `DTSTART`, and a MUST that nothing implements](findings/011-date-valued-dtstart.md).
  Every all-day event has one, and no case in this corpus did. §3.3.10 says
  `BYSECOND`/`BYMINUTE`/`BYHOUR` MUST NOT be used with a DATE-valued `DTSTART`
  and — unusually — *defines the remedy*: they "MUST be ignored". Neither
  sentence exists in RFC 2445, which predicts who gets it wrong. Of the 6
  systematic cases carrying such a part, `python-dateutil` 2.9.0 and
  `rrule.js` 2.8.1 apply it in **6 of 6**: an all-day event with
  `BYHOUR=9,17` becomes two events a day in both. `rrule.js` additionally
  cannot parse `DTSTART;VALUE=DATE:` at all and silently starts the rule at
  the current time — already reported as
  [jkbrzt/rrule#315](https://github.com/jkbrzt/rrule/issues/315) in 2019, so
  not re-filed. 18 cases, 4 refused as undefined by the RFC, and the last
  non-conformantly-covered grammar branch closed: **79/79, none of them
  non-conformant**.

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
`findings/005-rfc-worked-examples.md` has the detail.

### Instances in a DST gap or repeat

None of those 39 examples places an occurrence at an ambiguous or nonexistent
local time, so their interaction with expansion needed its own suite:
`tests/test_dst_recurrence.py`, **30 assertions, all passing for both
expanders**. RFC 5545 §3.3.10 states the rule outright — a computed instance
whose local start time "does not exist, or occurs more than once" is
interpreted exactly as a literal `DATE-TIME` under §3.3.5 — so the expected
values are derived from quoted text plus the installed tz database, not from
either implementation. Four zones, chosen for what they can catch:
`America/New_York`, `Australia/Sydney` (southern hemisphere), a
**30-minute** shift in `Australia/Lord_Howe`, and `Europe/Dublin` (transitions
at 01:00 local). Two consequences worth knowing before you rely on
`FREQ=HOURLY`: it **skips an hour of real time** at the autumn transition, and
it emits **two instances at the same instant** at the spring one, so the
sequence of UTC instants is non-decreasing but not strictly increasing.
`findings/006-dst-gap-and-repeat-instances.md`.

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
src/vtimezone.py     VTIMEZONE extraction from the RFC + offset resolution
src/differ.py        random rule generator + differential comparison
src/coverage.py      RFC 5545 sec. 3.3.10's BYxxx/FREQ table, read from the RFC
src/enumerate_cells.py  one systematic case per cell of that table
src/grammar.py       sec. 3.3.10's RECUR ABNF, read from the RFC: branches + classifier
src/enumerate_branches.py  one synthesized case per branch of that grammar
src/datevalue.py     RFC 5545's rules for a DATE-valued DTSTART
src/datevalue_cases.py  systematic DATE cases + what implementations do
src/build_corpus.py  runs the differential and writes the corpus
corpus/              corroborated.json, disputed.json, adjudications.json,
                     coverage.json, grammar-coverage.json,
                     date-value-type.json
findings/            adjudicated divergences, written up
```

## Running it

`python-dateutil` is the only dependency and only the *builder* needs it; the
corpus itself is plain JSON and can be consumed by anything.

```sh
python3 src/differ.py 7 300      # differential run, seed 7, 300 rules
python3 src/build_corpus.py      # rebuild corpus/ (slow; minutes)
python3 tests/rfc_examples.py       # known-answer tests, no dependencies
python3 tests/test_tz.py            # RFC 5545 section 3.8.5.3, all 39 worked examples
python3 tests/test_dst_recurrence.py  # instances in a DST gap or repeat, 4 zones
python3 tests/test_vtimezone.py       # RFC 5545 section 3.6.5, all five VTIMEZONE examples
python3 tests/test_byweekno.py        # week numbering at the year boundary (finding 008)
python3 tests/test_coverage.py        # coverage of section 3.3.10's table (finding 009)
python3 tests/test_grammar.py         # coverage of section 3.3.10's ABNF (finding 010)
python3 tests/test_date_value_type.py # DATE-valued DTSTART (finding 011)
python3 src/coverage.py               # (module) the table, parsed out of the RFC
python3 src/enumerate_cells.py        # print the 57 systematic cases
python3 src/enumerate_branches.py     # print the 79 synthesized branch cases
python3 src/datevalue_cases.py        # rebuild corpus/date-value-type.json
python3 src/byweekno_check.py         # sweep BYWEEKNO x WKST against the RFC's definition
python3 src/vtimezone.py              # print the five extracted components
```

## Honest limits

- **Coverage is stated but thin.** It is stated on two independent axes, both
  of them printed by §3.3.10 itself: all 57 permitted cells of its
  `BYxxx`/`FREQ` table ([finding 009](findings/009-corpus-coverage-of-the-3310-table.md))
  and all 79 branches of its `recur` ABNF
  ([finding 010](findings/010-grammar-branch-coverage.md)). Both are
  *presence* claims. Nothing systematic covers combinations — cell pairs,
  branch pairs, three-part interactions, `COUNT` together with `BYSETPOS`; the
  two axes are measured independently rather than crossed; `INTERVAL` appears
  only as 2 and 3 and `COUNT` only as 3. The random cases still carry that
  weight, and their coverage of it is unmeasured.
- **DATE-valued `DTSTART` is covered separately and thinly.**
  `corpus/date-value-type.json` has 18 systematic cases and 4 recorded as
  undefined ([finding 011](findings/011-date-valued-dtstart.md)); the main
  corpus is still entirely `DATE-TIME`, because `python-dateutil` — the second
  opinion the main corpus is adjudicated against — has no DATE value type. The
  DATE cases are corroborated one step removed, on the *reduced* rule.
- Only two implementations in the corpus, and one of them is mine. A third
  opinion is available and used ad hoc — `rrule.js` 2.8.1 runs on this machine
  and its output is in `findings/data/` — but per
  [finding 003](findings/003-implementation-lineage.md) most RRULE
  implementations descend from `python-dateutil`, so agreement between them is
  weak evidence about the *specification*. Use third implementations as
  cross-checks, not as adjudication.
- **The corpus** is naive-datetime: no timezones, no DST, no `VTIMEZONE`. That
  is a deliberate scope cut so transitions do not contaminate it. Timezone and
  DST behaviour is covered separately and from the spec's own answers, by
  `tests/test_tz.py` and `tests/test_dst_recurrence.py` (findings 005 and 006).
  `VTIMEZONE` — a calendar carrying its own transition rules rather than naming
  an IANA zone — is covered by `tests/test_vtimezone.py` (finding 007), but
  only over the five components the RFC itself prints. No `VTIMEZONE` appears
  in the generated corpus.
- The generator does not yet emit `FREQ=HOURLY/MINUTELY/SECONDLY`, `UNTIL`, or
  `COUNT` combinations, so the corpus says nothing about them.
- Coverage is random, not systematic. It is not yet a claim of completeness.
