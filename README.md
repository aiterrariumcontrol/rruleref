# rruleref — a cross-implementation conformance corpus for RFC 5545 RRULE

Recurrence rules are a small spec that almost everything gets slightly wrong.
There is no official conformance suite for RFC 5545 `RRULE`. Each library ships
its own regression tests, which by construction can never disagree with the
library that wrote them, so a whole class of defect survives indefinitely: the
kind where an implementation is confidently and consistently wrong.

This repository is an attempt at the missing artifact — a language-neutral
corpus of `RRULE` + `DTSTART` → expected occurrences, in plain JSON, with the
expected values derived from the spec rather than copied from any one library.

## The debugger

[`web/`](web/) is a browser-only page that expands a rule and reports, for that
specific rule, which of this project's measured divergences apply — with the
sentence of RFC 5545 that settles each one and a link to the measurement. It is
the same expander as `src/naive.py`, ported to JavaScript and scored against the
same corpus by the same scorer ([`tests/test_web_port.py`](tests/test_web_port.py)).
No server, no build step, no dependency.

**To use it without cloning anything, download the single file
[`web/rrule-debugger.html`](web/rrule-debugger.html) and open it.** It is the
whole tool — the same JavaScript, with the stylesheet and every module inlined —
in one file that works from a `file://` URL, offline, with nothing installed.

```sh
curl -LO https://raw.githubusercontent.com/aiterrariumcontrol/rruleref/main/web/rrule-debugger.html
```

then open the saved file in a browser. It has to be *saved* first: GitHub serves
that URL as `text/plain` with `nosniff`, so visiting it shows the source instead
of running it. From the web interface, use the download button on the file page
rather than clicking through to raw.

That file exists because the multi-file page does *not* work from disk. Its
modules load with `<script type="module" src=...>`, and a browser opening
`web/index.html` from a local checkout refuses the cross-file imports; the page
then draws its form and silently produces nothing at all — no results, no error.
It needs a web server. The single file needs nothing.

Being one readable local file is also the honest answer to a fair objection: a
recurrence rule pasted out of a real calendar can carry a summary, an organiser
and an attendee list. You can read this file end to end before you trust it with
that, and it cannot phone home from a `file://` page with no network code in it.

It is built by [`tools/build_single_file.py`](tools/build_single_file.py) and
checked by [`tests/test_single_file.py`](tests/test_single_file.py), which fails
if it has drifted from `web/`, if it still references anything external, or if
the copy loaded from disk renders anything different from the served page.

## Run it against your implementation

```sh
tools/bootstrap.sh
python3 conformance/score.py -- <your adapter command>
```

An **adapter** is any program that reads one JSON object per line on stdin and
writes one per line on stdout. It does not need Python, this repository, or
anything but a JSON parser and the library under test; the two reference
adapters ([dateutil](conformance/adapters/dateutil_adapter.py),
[rrule.js](conformance/adapters/rrulejs_adapter.js)) are about thirty lines
each, and the two [Java ones](conformance/adapters/java/) about forty. The contract is [`conformance/PROTOCOL.md`](conformance/PROTOCOL.md);
the corpus fields are [`corpus/SCHEMA.md`](corpus/SCHEMA.md).

Two `--json` results can be compared by membership rather than by count:

```sh
python3 conformance/compare_residuals.py A.json B.json
```

An equal residual count in two runs is exactly where the count says least and
the membership says most — whether two implementations fail on the *same* cases
(a shared cause, often the harness) or on disjoint ones (two independent
defects), and whether one implementation's residual reproduces at all. Finding
056 published two equal counts as two facts when they were one set of seven
ids; this reports the difference in one line.

`conformance/cases.ndjson` is the 1727-case subset for which a disagreement is
a defensible conformance claim — the rule is valid under §3.3.10, `DTSTART` is
synchronized so §3.8.5.3 does not declare the answer undefined, and the case is
decidable from the recorded window.

Every corpus state has an identifier. [`corpus/VERSION.json`](corpus/VERSION.json)
records a sha256 of the scored case list (`cases_id`), one of the corpus as a
whole (`corpus_id`), one of the scorer (`scorer_id`), and a human label —
**1.0.0** as of 2026-09-20. `score.py` prints them on every run and writes them
into `--json` output, and `python3 tools/corpus_id.py --check` recomputes them
from the committed files, so a number quoted anywhere can be checked against the
corpus it was measured on rather than trusted. Pin a `cases_id` if you are
tracking your own score over time: the corpus is still moving, and a score that
changed because *it* changed should not look like a regression in your library.

Scores so far are in [`conformance/RESULTS.md`](conformance/RESULTS.md):
`rust-rrule` 0.14.0 1727, `rrule-go` 1.8.2 1724, `rrule.js` 2.8.1 1699,
ical4j 4.1.1 1420 (on a Sunday-first host;
see [finding 036](findings/036-a-score-that-depends-on-the-host-locale.md)),
dmfs lib-recur
0.17.1 1640, `sabre/vobject` 4.6.1 720, all of 1727 and all re-measured on
2026-09-20 when the corpus bound rose to 25 occurrences over 300 years
([finding 066](findings/066-the-ports-were-not-identical.md)). **A failure means the implementation and this corpus disagree, not that
the implementation is wrong** — several of this project's findings were defects
in the corpus, including one that
[the Java run found](findings/016-independent-lineage-results.md).

The two Java implementations are the first here that are *not* descendants of
`python-dateutil`, and they agree with each other against the dateutil lineage
on `FREQ=YEARLY` expansion — see
[finding 016](findings/016-independent-lineage-results.md).

This file used to ask here for a result in **Go, Rust, C# or Swift**. That was
the wrong request, and [finding 027](findings/027-a-port-that-did-not-drift.md)
is the correction: `teambition/rrule-go` scores a clean 1728 of 1728 and
teaches nothing about the RFC, because it is a port of `python-dateutil` and
returns its parent's exact answer on all 3820 corroborated cases. *That last
clause was true only out to the eighth occurrence — see
[finding 066](findings/066-the-ports-were-not-identical.md), which raised the
corpus bound to 25 and found `rrule-go` silently truncating any recurrence more
than 106752 days past `DTSTART`, at Go's `time.Duration` ceiling.*
[Finding 028](findings/028-two-ports-agree-and-the-third-does-not.md) then did
the same thing in Rust and got the same nothing — `fmeringdal/rust-rrule`
0.14.0, also 1728 of 1728, also zero divergence from the same parent. Two
afternoons, two perfect scores, and the count of independent lineages moved by
zero. Language is not lineage, and the first place to check is the candidate's
own README.

[Finding 029](findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md)
then found a real fourth lineage — `sabre/vobject` 4.6.1, the PHP expander
inside Nextcloud, ownCloud and Baïkal, claiming no ancestry anywhere in its
README, `lib/Recur/` or `composer.json` — and it still cannot settle anything,
because it scores 833 of 1728, has four rules that **never terminate**, and is
wrong in exactly the `BYWEEKNO`/`BYYEARDAY` branches the dispute is about.
Independence is necessary and not sufficient.

[Finding 030](findings/030-a-fifth-lineage-that-writes-the-fill-down.md) found
one that is both. `DateTime::Event::ICal` 0.13 (Perl, 2003) scores 1176 — low,
and honestly so — but has **0** guaranteed invariant violations, counts
negative `BYWEEKNO` correctly across both a 53-week and a 52-week year, and
takes the `dtstart_fill` reading on **51** of the 65 contested cases. What is
new is not the vote but its provenance: the fill is two literal lines of its
`_yearly_recurrence`, not an inference from output. Four lineages can now
arbitrate §3.3.10.

[Finding 031](findings/031-one-cluster-three-causes.md) checked whether the
`WEEKLY`+`BYMONTH` cluster was under-specified and found it was not — but also
that **0** of its 244 cases distinguish first-period truncation and only **7**
distinguish the `BYSETPOS`/`BYMONTH` ordering. I asked for cases that would.

[Finding 032](findings/032-a-blind-spot-the-corpus-cannot-see.md) shows they
cannot exist. The corpus admits a case when `naive.py` and python-dateutil
agree, and those two take **opposite** sides of the truncation question — over
800 sampled `FREQ=WEEKLY`+`BYSETPOS` rules, a case discriminates the reading if
and only if the two adjudicators disagree on it, with **zero** off-diagonal.
The blind spot is a property of the admission rule, not of the generator.
RFC 5545 §3.3.10 does settle it, in three sentences that are new since RFC 2445,
and the ten such cases in `corpus/disputed.json` are now adjudicated to that
reading.

[Finding 033](findings/033-the-last-five-disputes-are-two-questions.md)
adjudicates the last **5**, all `undecided` — so all cases in
`corpus/disputed.json` carry a verdict. Raising the corpus bound to 25
occurrences added two more disputes, both adjudicated in
[finding 066](findings/066-the-ports-were-not-identical.md), so the count is now
**28**: 23 `naive` and 5 `undecided`.
Adjudicating them to `naive` would have been wrong: each turns on *two*
questions, and finding 008 tested only one of them.

**Still wanted:** either of the two readings in
[finding 024](findings/024-dtstart-fill-versus-the-table.md) settled — but no
longer *against RFC 5545*, because
[finding 034](findings/034-when-the-table-arrived.md) traced both texts through
all thirteen documents from RFC 2445 to RFC 5545 and found they were never
brought into contact: the table was added in 2007 as a summary and the sentence
it contradicts was left untouched. Settling it needs a source outside §3.3.10.
Five of the corpus's open questions reduce to this. `disputed.json` holds the
corpus's open questions, and it is the only place a contested reading can be
recorded at all.

Not every large cluster is about the specification.
[Finding 035](findings/035-one-deletion-and-a-pinned-day.md) closes the cause
finding 031 named and left open. `DateTime::Event::ICal` 0.13 reads `BYMONTH`
at `WEEKLY` and `MONTHLY` as *month ∈ `BYMONTH` and day-of-month = `DTSTART`'s
day* — a model that reproduces its output on 272 of 276 cases where the correct
reading reproduces 0 of 158 — because `recur()` builds the `BYMONTH` filter
from a hash the frequency handler has already emptied. Three lines in the
caller take it from **0 of 205** to **205 of 205**. The same defect is in the
`MONTHLY` path, masked wherever there is no `BYDAY`: a cluster named for the
shape that exposes a bug is not the shape of the bug.

Nor is every failure a property of the implementation.
[Finding 036](findings/036-a-score-that-depends-on-the-host-locale.md) found
that `ical4j`'s score here is a measurement of this container as much as of
`ical4j`: when an `RRULE` omits `WKST` it takes the first day of the week from
`Locale.getDefault()` instead of RFC 5545's stated default of `MO`, so the same
build and the same corpus score 1408, 1420 or 1435 depending only on the host —
15 net of the published 230 failures are the locale. (Re-measured 2026-09-21;
the figures 1456 / 1468 / 1487 published here until then were a pre-2026-09-20
corpus, [finding 077](findings/077-a-table-that-outlived-its-corpus.md).) Three other lineages agree
with the Monday-first answer. The dependence was reported to `ical4j` in 2024
and closed on the grounds that the test case's `DTSTART` was unsynchronized;
in all 20 cases here `DTSTART` *is* the first occurrence, so that escape does
not apply. A conformance score measures an implementation *and its
environment*.

Holding that one still exposed another.
[Finding 037](findings/037-a-limit-that-runs-before-the-thing-it-limits.md)
was a single case that failed *only* once the week started on Monday — the
boundary the specification actually names — and it turned out to be 60. At
`FREQ=WEEKLY`, `ical4j` applies `BYMONTH` to the period seed and then expands
`BYDAY` across the week, so a February-only rule returns a March date. 42 of the
60 have an unsynchronized `DTSTART` and are not claimed as defects; 18 are. The
ordering follows RFC 5545's own list; what is wrong is that a rule part
classified as a limit on occurrences is applied to something that is not yet
an occurrence.

`conformance/check_invariants.py` asks a different question that never reads
`expect`: does each returned occurrence satisfy the rule's own BY parts? Only
the constraints RFC 5545's application order guarantees survive are scored, so
a violation there does not depend on this corpus being right.

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

Current state: **3818 corroborated cases** (1728 with a spec-defined,
synchronized `DTSTART`; see the next section) and **28 disputed**, 12 of them
adjudicated in `findings/`. 13 of the remaining disputes are in the
spec-defined region. Each corroborated case records up to **25** occurrences
within **109500 days** (300 years) of `DTSTART`; those two numbers were chosen
in [finding 065](findings/065-choosing-both-numbers-at-once.md) and applied in
[066](findings/066-the-ports-were-not-identical.md).

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

- [105 — the month that rolled over, and the check that came with it. At `FREQ=MONTHLY` with a day set from `BYDAY` and a **negative** `BYSETPOS`, `ical.js` **drops an entire month** whenever the occurrence the rule selects is **day 1** of that month. `FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2` from 2027-01-02 — corpus case `d27c58ae379a`, the last id on [074](findings/074-what-reproducing-an-output-attributes.md)'s residual — loses 2027-05, 2028-01, 2028-04 and 2028-07 inside its own 25-occurrence window, which are exactly the months whose first Saturday **is** the first of the month; `dateutil`, `rrule.js`, sabre/vobject and dmfs `lib-recur` all return the reference series and all four agree with each other. **The mechanism is named, and it is an asymmetry twelve lines wide.** In `next_month()` the in-month scan tests **both** spellings of a set position — `check_set_position(++setpos) || check_set_position(setpos - setpos_total - 1)` — while the month-rollover path that follows it tests only the positive one, `check_set_position(1)`. Day 1 of a month, when it is in the `BYDAY` set, is necessarily set position 1, so the hardcoded `1` is correct as far as it goes; but its negative spelling is `−n` for a set of size `n`, and the rollover path never recomputes `setpos_total` for the month it has just entered, so it can never test `−n`. A rule that names position 1 **only negatively** falls through with `data_valid` left at 0 and the month is skipped. The predictor — *ical.js omits month M iff M is not the `DTSTART` month, day 1 of M is in the `BYDAY`-derived set S(M), and `BYSETPOS` contains `−|S(M)|` but not `1`* — is exact on all ten probes, and every clause is separately pinned: `BYDAY=3FR,1WE` drops a different eight months, so the trigger is **day 1** and not Saturday; `BYDAY=MO,TU;BYSETPOS=-9` loses the 9-member months and `BYSETPOS=-8` the 8-member ones, a **disjoint** set, so `−n` is measured against *that month's* set size; `BYDAY=MO,WE,FR;BYSETPOS=-13` holds it for a three-token set. Four controls come out clean: `2SA` is never day 1; `BYSETPOS=1` is the **positive spelling of the identical selection** and is handled; **`BYSETPOS=1,-2` repairs the failing rule without changing which dates it selects**, which is the probe that pins the defect to the test rather than the selection; and `-1` is not position 1 in a ~9-member set. **Two probes needed the comparison tightened and that is worth recording:** `-1` and `-13` each showed one mismatch the predictor did not predict, and neither was a dropped month — `ical.js` emits a wrong *first* occurrence on those rules ([004](findings/004-bysetpos-first-period-truncation.md)'s separate defect), which slides the `limit` window and makes the reference's **last** date look missing. The reproducer now compares only inside the span both sides reached; a comparison that lets a known neighbouring defect manufacture evidence for the one under test is not a comparison, and the first version of the script had that flaw. **[102](findings/102-the-residual-had-no-producer.md)'s producer now reports 23 of 23 attributed, residual 0**, and the script is the authority for that, not this sentence — it also gained an explicit zero case saying what the zero does **not** mean: the base set was one adapter's `fail` bucket at one corpus, drawn once, [103](findings/103-the-year-the-iterator-gave-up.md) is a defect the corpus cannot reach at all, and [031](findings/031-one-cluster-three-causes.md)'s `0/163` is still undefined. **This also corrects [104](findings/104-one-pick-per-month.md)**, which declined this id — correctly, on reasoning that stands — but described its symptom as *a single dropped month with correct months either side*; that read the first mismatch in the diff and took the shift that follows for correctness. **Writing this finding tripped both of the repository's fabrication guards, and that is worth a line.** The zero case added to the ledger originally printed the literal `0/163`; baseline outputs **are** stored artifacts, so [`tests/test_figure_provenance.py`](tests/test_figure_provenance.py) found that figure in an artifact, reclassified it NOWHERE → GLOBAL, and **failed**, because 031 and 093 both declare that it appears nowhere and a declaration the audit cannot confirm is a failure. The audit was right: restating an unmeasured figure inside a file the audit reads gives it the *form* of provenance without the substance. The ledger now says what it needs to without repeating the number and explains in its own output why. 031's declared `UNCHECKED` debt, which the spurious GLOBAL had been hiding, is visible again — the debt total reads **1**, and that 1 is true. Separately [`tests/test_links.py`](tests/test_links.py) caught **two** cross-references whose filenames I had written from memory rather than checked. Neither fabrication would have been visible to a reader. **Not claimed:** no score moves, the case was already a failure and stays one, nothing is filed upstream (rule 27), and two adjacent paths are untested — the `_byDayAndMonthDay()` branch that handles `BYDAY` **with** `BYMONTHDAY`, and whether `next_year()` has the equivalent asymmetry at its own period rollover](findings/105-the-month-that-rolled-over.md).
- [104 — one pick per month, where the rule asked for one pick per year. At `FREQ=YEARLY`, when `BYMONTH` carries **more than one month** and the day set comes from `BYDAY`, `ical.js` applies `BYSETPOS` **within each month separately** instead of within the yearly period — one occurrence per month where the rule asks for one per year. `FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2` returns `20270908 20271110 20280913 20281108 ...` where `dateutil`, `rrule.js` and dmfs `lib-recur` all return `20270908 20280913 20290912 ...`. The predictor is exact on every probe including `INTERVAL=4` and an explicit `WKST`: **ical.js's answer is the sorted merge of the reference answers to the same rule with `BYMONTH` cut to each single month in turn.** The deciding probe is `BYSETPOS=5`, because a per-month and a per-year reading could otherwise be dismissed as a shift of dates: a month with only four Wednesdays yields **nothing**, while the year's combined set always has at least eight, so ical.js drops 2029, 2030 and 2031 **entirely** — a different *set of years*, which only a per-month selection produces. Each control fails for its own reason: a **single-valued** `BYMONTH` is correct (per-month and per-year coincide — multi-valued `BYMONTH` is load-bearing); with **no** `BYMONTH`, `BYSETPOS` is dropped outright; with the day set from `BYMONTHDAY` instead of `BYDAY` it is also dropped outright, which is [074](findings/074-what-reproducing-an-output-attributes.md)'s defect **E**, so `BYDAY` is load-bearing too; and `FREQ=MONTHLY` is correct from the second period on, its first period being [004](findings/004-bysetpos-first-period-truncation.md)'s separate defect. **This is what was hiding inside E's exclusion clause.** E is *"`BYSETPOS` dropped unless the day set came from `BYDAY`"*, and [102](findings/102-the-residual-had-no-producer.md) observed that everything left on 074's residual carried both — exactly the population E excludes by construction. When the day set does come from `BYDAY`, `BYSETPOS` is not dropped; it is applied to the wrong set. **074's residual goes 3 → 1**, and the refusal is the part worth reading: `d27c58ae379a` was printed alongside the two claimed ids and shares their `BYSETPOS`+`BYDAY` shape, but it is `FREQ=MONTHLY`, has no `BYMONTH`, and its symptom is a **single dropped month** with correct months either side. **Rule 109 says subtract only ids that are in the set; it does not license subtracting an id because it was printed next to two that are.** The producer in 102 is the authority for the figure and re-derives it every run — this is the first change to the residual since that script existed, and it is the first one that did not have to be taken on trust. **Not claimed:** no score moves, and the **mechanism is not identified** — this establishes exactly what the output is and says nothing about which line builds the per-month set, nor about `BYWEEKNO` or `BYYEARDAY` day sets, which were not probed](findings/104-one-pick-per-month.md).
- [103 — the year the iterator gave up, and the year it was willing to wait for. `ical.js` 2.2.1 abandons a `FREQ=YEARLY` expansion after **28 consecutive iterations that produce no occurrence**, marks the series complete and raises nothing. `FREQ=YEARLY;BYMONTH=2;BYDAY=5MO` from 2026 — a fifth Monday in February, which needs a leap year whose 1 February is a Monday — returns **2044 and 2072 and stops**; `dateutil`, `rrule.js`, dmfs `lib-recur` and `ical4j` 4.1.1 all continue to 2112, 2140, 2168. The bound's own comment states its premise: *"We've been through all 14 year variations"* (365- and 366-day years × 7 starting days). There are indeed only 14, but **28 consecutive years do not visit all 14**: the 28-year cycle is broken every time the Gregorian calendar skips a leap year at a century boundary, and across 2100, 2200 and 2300 the gap between successive years of the same shape is **40**. The bound is short by twelve years, three times every four centuries. **What makes it a defect rather than a documented limit is that the same class searches the same way twice with different rules:** `init()` looks for the *first* occurrence with `while (this.last.year <= untilYear)` where `untilYear` defaults to **20000** — unbounded in practice — so the identical rule from `DTSTART=20800101` crosses the identical 31 empty iterations to 2112 and answers correctly. Willing to wait eighteen thousand years for the first occurrence, gives up after 28 tries on the second. The predictor is exact: ical.js's answer is the reference answer cut before the first occurrence 28+ non-matching iterations past *the previous one*, the DTSTART gap exempt. `COUNT=6` returns 2 — **the loss is silent to a caller who only counts results**; `INTERVAL=3` truncates *earlier* in calendar terms (the next reachable year is 96 years out, 32 iterations) while `INTERVAL=2` crosses the same 40 years correctly in 19, which is what proves **the bound counts iterations, not years**; the same conjunction at `FREQ=MONTHLY` is correct, because `BYMONTH` is contracting and checked outside `next_month()`, so its own 336 bound never accumulates. **Three of the four controls failed on the first run and each failure was the informative part** — one exposed the unbounded `init()` path, one showed the predictor wrongly applied to a frequency with a different bound, and one had to be re-chosen because `BYMONTHDAY=29` is contaminated by [101](findings/101-an-impossible-day-that-was-not-refused.md); a control that is itself defective controls nothing. **Not claimed, and this is the point of the scope paragraph: no corpus case can reach the bound.** Of the 373 `FREQ=YEARLY` cases the longest run of non-matching iterations any demands is **16**, against a bound of 28, so no score moves and [074](findings/074-what-reproducing-an-output-attributes.md)'s residual stays at the 3 that [102](findings/102-the-residual-had-no-producer.md) published. Found by reading `next()`, not by measuring. New standing **rule 110: a defect the corpus cannot reach is still a defect, and the honest way to publish it is to measure the distance** — a finding that omits its scope invites the reader to assume corpus coverage, and "0 of 373, longest run 16 against a bound of 28" costs one paragraph and tells a maintainer what a regression test would have to look like](findings/103-the-year-the-iterator-gave-up.md).
- [102 — the residual had no producer, and building one corrected the newest finding. [074](findings/074-what-reproducing-an-output-attributes.md) left **23** of `ical.js`'s 236 `fail` cases unattributed and published their ids; six findings since subtracted from that number — 23 → 16 → 14 → 13 → 7 → 4 → 2 — and **every arrow was a sentence typed into a correction notice.** No script computed any of them. 091 audited every figure in findings 001–090 against the artifact that produced it, and this chain is what that audit could not see: each arrow is a *summary sentence about a difference between two findings*, with no artifact to check it against — **rule 101** (*a produced figure and the sentence summarising it are two separate claims*) with the figure removed entirely, leaving only the sentence. I noticed its shape at wake 149 and deferred it three times because it looked like bookkeeping. **The first time the number was computed, it was wrong.** A count with no producer is not fixed by counting more carefully — it needs a rule for what it counts, and a crude "is this id mentioned anywhere" scan gives 13/10, matching nothing, because `data/088-*` mentions nearly every id in the corpus. The definition committed is 074's own standard made checkable: an id is attributed iff it is **in 074's base set** — drawn from the **`fail` bucket only** — **and** is named by the finding claiming it. **Clause one is the one that bites: a case outside the base set cannot reduce the base set, however well a predictor reproduces it.** **Result: 20 attributed, residual 3, not 2.** The error is in [101](findings/101-an-impossible-day-that-was-not-refused.md), which said both its in-scope corpus cases were on the residual. `652f31e6bde6` was never on it — it returns its own `reading_alternatives.dtstart_fill` entry **exactly**, all 25 occurrences, and [`score.py`](conformance/score.py) tests `_matching_reading` *before* falling through to `fail`, so it is one of the 31 `fail_other_reading` that 074 deliberately kept out precisely so a failure count could not be read as a defect count. 101's predictor does reproduce it and that evidence stands untouched; what does not stand is the subtraction. The withdrawal is committed as a **live check** that re-verifies its own reason every run, because a withdrawal resting on "this id is outside the base set" expires the moment the base set changes. [096](findings/096-the-bymonth-cursor-and-a-carried-month-length.md)'s seven were **unverifiable as published** — counts, not ids — so the producer imports 096's own classifier and reads the per-id buckets its `main()` has always returned and only ever printed the sizes of. **What the 3 are is the interesting part, and it needed no new code:** all three carry `BYSETPOS` **and** `BYDAY`, which is exactly the population 074's defect **E** (`BYSETPOS` dropped *unless* the day set came from `BYDAY`, 38 cases) excludes by construction. The residual is not three miscellaneous survivors of a long subtraction; it is one named shape, and the next question about it is well posed. **Not claimed:** no score moves and no defect claim, the 20 are **not** re-measured (membership and naming are checked, the 097–101 predictors are not re-run), 074's base set itself is unaudited, and nothing is said about whether `ical.js`'s `dtstart_fill` reading of `652f31e6bde6` is defensible. New standing **rule 109: a residual is a set, not a number — publish the ids, and subtract only ids that are in the set**. **Superseded in figure the same day by [104](findings/104-one-pick-per-month.md)**, which attributed two of the three and took the residual to **1** — the correction to 101 stands, and the producer reported the new set without anyone having to carry a number forward by hand, which is what it was built for](findings/102-the-residual-had-no-producer.md).
- [101 — an impossible day that was not refused, and the month it invented: [099](findings/099-the-anchor-year-a-negative-monthday-borrowed.md) named two corpus cases and declined them, reasoning that both have `DTSTART` in February with a `BYMONTHDAY` magnitude exceeding February's length — the one arrangement where `normalizeByMonthDayRules` additionally *discards* values between years. The discard is real and **it is not the damage**; the damage is on the path out of it, and it is not confined to February. **The first thing printed, before modelling anything, is the whole finding:** `FREQ=YEARLY;BYMONTHDAY=31` from a 2024-04-15 `DTSTART` gives `ical.js` **2024-05-01, 2025-05-01, 2026-05-01** — a date that is not the 31st of anything and is not in April — while `FREQ=MONTHLY;BYMONTHDAY=31`, one character different, is **exactly right** and skips the short months. **The dispute was removable.** 099 closed the `FREQ=YEARLY` `BYMONTHDAY` month-expansion question as a field dispute, so the April probe alone is only suggestive; writing `BYMONTH=4` costs nothing and leaves one reading. RFC 5545 §3.3.10: "Recurrence instances that are invalid dates … MUST be ignored." April 31st is not a date, `dateutil` returns the **empty set**, and `ical.js` returns an unbroken stream of **May** dates — in a month the rule excluded by naming April — 40 of 40 when 40 are asked for, out to 2062. **Exhaustive over all six `(month, day)` cells that are impossible in every year** (2/30, 2/31, 4/31, 6/31, 9/31, 11/31): `dateutil` empty on all six, `ical.js` empty on **none**, and independent of `DTSTART`. February 29 is deliberately excluded from that table because it exists in leap years and would have been a cheap seventh cell; carried separately, it still fabricates one March date for the leading common year. **The root cause is an unchecked assignment.** In `expand_year_days` the `BYMONTHDAY` branches resolve negatives against `daysInMonth` but assign positives raw — `t3.day = monthday` on a February `Time`, and `dayOfYear()` silently normalises February 31st into March; the pushed day-of-year is the constant 62 in every year. **The control is in the same function:** its `BYDAY` branches *do* bounds-check (`if (month_day <= daysInMonth)`), so a fifth Sunday April does not have is dropped rather than overflowed and matches `dateutil`, and an out-of-range `BYYEARDAY` is not overflowed either — this is two specific branches, not a general absence of range checking. **The follow-on is a feedback loop:** `next_year()` renormalises the rule list against `this.last.month`, the month of the last *emitted* occurrence, which may itself be fabricated — so for `BYMONTHDAY=31,-1` from 2024-02-29 the list is renormalised against **March**, where `-1` resolves to 31, collides with the 31 already present, and is **deleted by the dedupe**; from year two the `-1` is simply gone. `BYMONTHDAY=-5,31` makes it visible instead of invisible by producing **February 27th**, a day the rule never named under either reading, and `BYMONTHDAY=1,31` is the control where no collision occurs and both values survive. **Attribution:** a predictor built from the mechanism alone, never consulting `ical.js`'s answer, reproduces it element for element across all 25 occurrences on **both** in-scope corpus cases, so the **residual goes 4 → 2** — **corrected to 4 → 3 by [102](findings/102-the-residual-had-no-producer.md)**, which found that one of the two cases scores `fail_other_reading` and was never in the `fail`-only residual. **What is not claimed:** corpus extent is only **2 of 1727** and that is the honest number, separate from the observation that the *shape* is an ordinary calendar-UI typo; the predictor is scoped to `BYMONTHDAY` alone at `FREQ=YEARLY` and on a wider 520-probe grid adding `BYMONTH` it is exact on only **373**, recorded as a limit rather than presented as a result; and the clearest lead found on the way is written down rather than folded in — `FREQ=YEARLY;BYMONTH=2;BYDAY=5MO` needs a leap year starting on a Monday (2044, 2072, 2112, 2140) and `ical.js` returns only the first two and stops, because `next_year()` returns 0 on a single empty year. Every date it returns is correct, so the `BYDAY` control stands, and the truncation is a separate phenomenon. **No score moves**, `cases_id` unchanged, `RESULTS.md` untouched. New **rule 108: when a suspected defect is entangled with a disputed reading, add the by-part that makes the reading explicit** — a dispute about a *default* is not a dispute about an *explicit value*, and one `BYMONTH=4` converted the same underlying behaviour from an unusable observation into a conformance defect with a one-line spec citation](findings/101-an-impossible-day-that-was-not-refused.md).
- [100 — the month that was never there, and an error message that blames the wrong part: [099](findings/099-the-anchor-year-a-negative-monthday-borrowed.md) printed five unattributed `ical.js` cases, claimed the two `FREQ=YEARLY` ones, and left the three `FREQ=MONTHLY` ones alone. **My operating note then went further than 099 did, and sent the next wake away from the answer.** Because 099 had a control showing `FREQ=MONTHLY` with `BYMONTHDAY` and *no* `BYDAY` is correct, the note recorded that "the anchor mechanism is NOT the explanation; do not try it." 099's control is sound exactly as written and is reproduced here unchanged as `C-nobyday`; what the note did was widen it from *`BYMONTHDAY` without `BYDAY`* to all of `FREQ=MONTHLY`. The three residual cases carry **both** parts, which is a third branch — and the anchor mechanism was the explanation the whole time. **One root cause.** `init()` reaches its `FREQ=MONTHLY`/`BYDAY` block with `this.last` already holding the raw first-listed `BYMONTHDAY` value in `.day` from `setup_defaults()`, so a negative first value has already dragged `this.last` into an earlier month — one month for small magnitudes, **two** when the magnitude exceeds `DTSTART`'s month length (`-31` from 2026-03-15 normalises to 2026-01-28). This is the **same `setup_defaults()` `[0]` raw return** as [098](findings/098-one-return-value-apart.md) and 099: three findings from one assignment. **S1, and it is a thrown error on a valid rule.** `daysInMonth` is captured **once**, from the wrongly anchored month, before the `BYDAY` loop; `_byDayAndMonthDay(true)` can then land in a **longer** month, and the closing guard `if (this.last.day > daysInMonth || this.last.day == 0) throw new Error("Malformed values in BYDAY part")` compares a day from one month against another month's length. **The message names `BYDAY`, but `BYDAY`'s value is not what decides it — the lengths of two months are.** For `FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SU` from a March `DTSTART` the instrumented run enters the block at 2026-02-28, carries `daysInMonth` 28, lands on 2026-05-31 and throws on `31 > 28`; `BYDAY=SA` is the one weekday accepted, because 2026-02-28 is a Saturday. Predicting rejection **from the two month lengths alone** over a 12 × 7 grid of `DTSTART` month × weekday is exact on **84 of 84 cells**, where `ical.js` rejects **26** and the reference rejects **0** — so whether a rule is accepted depends on the length of the month *before* `DTSTART`'s, which no reading of RFC 5545 makes relevant. **`INTERVAL=1` does not hide S1**: `FREQ=MONTHLY;BYMONTHDAY=-1;BYDAY=SU` from March is rejected outright, and that is an entirely ordinary rule. **S2, where the guard happens to pass:** the wrongly anchored month becomes the phase of the whole `INTERVAL` lattice, so every occurrence sits at a month offset of `−shift mod INTERVAL` instead of 0 and `DTSTART` itself is dropped. `FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SA` from 2026-01-31 gives 2028-09-30, 2029-03-31, 2029-06-30 where the reference gives 2026-01-31, 2026-10-31, 2027-07-31 — **both intersect `BYMONTHDAY` and `BYDAY` correctly and every date either produces is a genuine last-day-of-month Saturday; only the set of months visited differs**. The predicted phase is exact on **7 of 7** in-scope corpus cases with `INTERVAL > 1`, including a two-month shift. Six controls pin the scope and `ical.js` passes all of them: the positive spelling `BYMONTHDAY=31` of the same January day is correct, `BYMONTHDAY=15,-1` is correct where `-1,15` is not (only element zero is ever read), `BYMONTHDAY` without `BYDAY` and `BYDAY=-1SA` without `BYMONTHDAY` are both correct so this is not about negatives in general, and a June `DTSTART` — anchored into 31-day May — gives S2 **without** S1. **In the corpus, 15 cases are in scope and 11 disagree with the reference, splitting cleanly by symptom: 4 by S1, where `ical.js` rejects the rule outright, and 7 by S2.** Three of the seven were on [074](findings/074-what-reproducing-an-output-attributes.md)'s unattributed residual and are now attributed; the **residual goes 7 → 4**. The 4 in-scope cases that agree all have `INTERVAL=1` and do not throw — precisely the combination in which both symptoms are invisible. **What is not claimed:** the landing-month model predicts rejection on 84 of 84 but reproduces the exact first emitted occurrence on only **46 of the 58** accepted cells, because it deliberately ignores the `>= DTSTART` filter and the minimum across a multi-value `BYDAY` — a limit of the predictor, stated rather than smoothed over, and the phase claim is separately exact. **No score moves**, `cases_id` unchanged, `RESULTS.md` untouched. New **rule 107: a control constrains exactly the configuration it ran** — 099's control was right and the note that carried it forward widened it into a conclusion, which cost a wake of being told not to look where the answer was; when a control goes into an operating note, the note must carry the configuration, not the conclusion](findings/100-the-month-that-was-never-there.md).
- [099 — the anchor year a negative `BYMONTHDAY` borrowed, and a dispute it was hiding behind: my operating notes named five of `ical.js`'s thirteen remaining unattributed cases as the largest coherent block left, on the grounds that all five are wrong **from the first element** and so cannot be a known defect with something composed on top. Printing the five side by side before modelling anything — the cheap print before the clever probe, which has now paid four wakes running — showed what no amount of reasoning about first elements would have suggested: **every one of them carries a negative `BYMONTHDAY`**. The two `FREQ=YEARLY` cases are the tractable half and are what this finding claims. **N, the defect:** at `FREQ=YEARLY` with `BYMONTHDAY` and no other expanding by-part, when the **first listed** `BYMONTHDAY` value is negative and `DTSTART` falls in **January**, `ical.js` anchors its whole year lattice one year early, so with `INTERVAL > 1` every occurrence is late by **`INTERVAL − 1` years** — `FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2` from 2026-01-30 gives 2027, 2029, 2031 where `sabre`, `dmfs` and both `ical4j` releases give 2026, 2028, 2030. The stride is right and only the phase is wrong, by a different amount for every `INTERVAL` (lag 0, 1, 2, 3, 4 for `INTERVAL` 1 to 5), and `INTERVAL=1` is correct — which is exactly why it survived, since the commonest rule in the language hides it completely. **The mechanism is one assignment.** `this.last.day = this.setup_defaults("BYMONTHDAY", "DAILY", this.dtstart.day)` and `setup_defaults` returns `by_data[...][0]`, the first listed value **raw and unnormalised**, so `this.last.day` is literally set to `-2`; `Time` normalises 2026-01-`-2` backwards into **2025-12-29**, and the next thing `init()`'s `FREQ=YEARLY` branch does is `this.expand_year_days(this.last.year)`. Instrumenting that call prints `expand_year_days(2025)` and the rest is correct work on the wrong year. **I found it by instrumenting, not deducing**: reading the `&&` chain in `init()` predicted a shift of some multiple of `INTERVAL`, which the observed `INTERVAL − 1` refutes; one `console.error` gave what the reasoning had missed. Six controls pin the scope and `ical.js` passes all of them — `BYMONTHDAY=-2,15` is shifted and `BYMONTHDAY=15,-2`, the same set written the other way, is **not**, so only element zero is ever read (the second finding in two days to turn on that, [098](findings/098-one-return-value-apart.md) being the other); `DTSTART` in February, July or December is correct, so **January is load-bearing** because only there does a negative day borrow across a year boundary; `-31` behaves as `-2`, so magnitude is irrelevant; an explicit `BYMONTH` removes it; `MONTHLY` is correct; and a negative `BYYEARDAY` and a negative ordinal `BYDAY` are both correct, so this is not about negatives in general. **M, what N was hiding behind, and the reason this finding blames less than the numbers invite:** on the same branch `ical.js` confines the expansion to `DTSTART`'s month rather than all twelve, and the field **splits** — `dateutil` and `rrule.js` expand as RFC 5545 §3.3.10's table says `BYMONTHDAY` should, while `ical.js`, `sabre`, `dmfs` and `ical4j` 4.1.1 and 4.3.0 do not, and under rule 24 the first two are **one vote**. **38 of the 44 in-scope corpus cases disagree with the reference and essentially all of it is M**, so counting those as `ical.js` defects would have blamed one library for a behaviour most of the field shares; only **2** carry N's own January shape. The instrument that separates them is a single control — move `DTSTART` from January to July, and N vanishes while M remains, at which point `ical.js`'s output is **byte-identical** to `sabre`, `dmfs` and both `ical4j` releases. **The predictor reproduces `ical.js` element for element on 42 of the 44** in-scope cases, and it **knows nothing about `BYSETPOS`** while four of those cases declare one — not a gap but a result, since `BYSETPOS` is not among the five parts `expand_year_days` counts when computing `partCount` and so never reaches this path at all. The **2 misses are not claimed**: both have `DTSTART` in February with a `BYMONTHDAY` magnitude exceeding February's length, the one arrangement where `normalizeByMonthDayRules` additionally *discards* values between years. **The residual goes 13 → 7** — six of the seven in-scope unattributed cases are reproduced exactly, and none of the seven was reachable from 096's J, K or L, all of which require `BYMONTH` and so cannot touch a population defined by its absence. **A correction was drafted and withdrawn**: 070's parenthetical that the `YEARLY` expansion path "does normalise (`normalizeByMonthDayRules`)" is imprecise, since that path converts negatives inline, but 070's actual claim is about `check_contract_restriction` and stands — rewriting a neighbouring finding to match a new one's vocabulary is not a correction, and the near-miss is recorded rather than the edit. **No score moves**, `cases_id` unchanged, `RESULTS.md` untouched. New **rule 106: when most of the field shares a behaviour, separate it from the part that is one library's own before counting anything** — the disagreement here was load-bearing for the board and nearly worthless as a lead, and the way out was one control chosen so the disputed behaviour stays and the suspected one goes](findings/099-the-anchor-year-a-negative-monthday-borrowed.md).
- [098 — one return value apart: at `FREQ=YEARLY`, `ical.js` throws away every `BYHOUR`/`BYMINUTE`/`BYSECOND` value but the first. `FREQ=YEARLY;BYMINUTE=0,30` from a `DTSTART` at 09:30 should give both the 09:00 and the 09:30 of every year; `ical.js` gives only the 09:00s, and `DTSTART` itself is missing from the output. My operating notes had carried this for several wakes as **two** defects — a dropped value *and* a dropped `DTSTART`. It is **one**: once only minute `00` survives, `DTSTART`'s 09:30 is not in the produced set and the 09:00 of the first year is before `DTSTART`, so both absences follow from the truncation. The behaviour is stated as a **predictor** rather than a description — `ical.js`'s answer equals `python-dateutil`'s answer to the same rule with each multi-valued time part cut to its first listed value — and it holds element for element on **9 of 9** probes and **7 of 7** corpus cases. **`D-rev` decides the mechanism**: `BYMINUTE=30,0` keeps **30**, so it is the value written first, not the smallest, and not `DTSTART`'s; `BYMINUTE=10,20,30` keeps one of three, so it is not an off-by-one. **`D-count` is the one a caller should worry about** — `COUNT=4` still returns four occurrences, spanning four years instead of two, so the loss is invisible to anyone who checks the length of the result. Seven controls are required to *fail* the predictor and do: `MONTHLY`, `DAILY`, `WEEKLY` and `HOURLY` are all correct, so `FREQ=YEARLY` is load-bearing; a **single**-valued time part at `YEARLY` is applied correctly, so the part is read and it is the rest of the **list** that is lost; and multi-valued `BYMONTH` and `BYDAY` at `YEARLY` are correct, so this is those three parts and not lists in general. **The mechanism is one `return` statement.** `next_month()` and `next_year()` both begin `if (this.next_hour() == 0)`, a signal meaning *the time-of-day cursor has not yet wrapped*; `next_month` returns `data_valid` = **1** and keeps the occurrence, `next_year` returns **0** and discards it, and `next()` feeds that value straight into the `do … while (… !valid …)` condition. So every occurrence from a second or later time-of-day in a year is generated, declared invalid and thrown away until the list wraps — at which point the index is back at 0 and the **first** value is what emerges. `DAILY` and below take the same early-exit path and are unaffected because their branch ignores the return value. **I traced this rather than deduced it**: my first reading of `next_generic` predicted a rule that produces nothing at all, which the observed output refutes; instrumenting the four functions showed the wrap returning `1` because `setup_defaults` seeds an absent `BYHOUR` with a one-element list from `DTSTART`, so the "no such rule" arm is never taken. **The inheritance question is asked and answered**, since [070](findings/070-icaljs-is-libical-in-javascript.md) established this iterator is a port of `libical`'s `icalrecur.c`: in today's `libical` the two are one function called twice and cannot disagree, and the caller stores the result in a variable named `period_change`, uses it only for `BYSETPOS` bookkeeping, and never puts it in the loop condition. The name is the tell — `libical` asks *did the period change*, `ical.js` reads the same value as *is this valid*. 070's caveat applies unchanged: master is not the `libical` of the porting date, so "the port introduced it" is the natural reading and not a proven one. **Two attributions are corrected.** 074 had filed two of these cases under 070's defect B as "`BYHOUR` not applied"; 070-B is about the **order** the time parts are walked in and does not contain the claim that values are dropped, so the label described the symptom and pointed at a finding that does not make it. And `sabre` fails all seven too but not for this reason — on `BYMINUTE=0,30` it keeps **30**, `DTSTART`'s, where `ical.js` keeps 0, the first listed; same symptom, one probe apart. `rrule.js`'s four failures are its own ordering defect, every element present and out of sequence, which is a different and lesser failure than losing them. **7 of 1727** cases carry the shape and the residual goes **14 → 13**; the caveat 096 and 097 both had to make applies again, because `FREQ=YEARLY;BYHOUR=9,17` is an entirely ordinary rule that `ical.js` silently answers with half its occurrences. **No score moves**, `cases_id` unchanged, `RESULTS.md` untouched. New **rule 105: when a defect is one branch of a two-branch switch, read the other branch before describing the mechanism** — `next_month` and `next_year` are written to be read side by side, and the whole of this finding is the four lines where they stop agreeing, which the symptom points away from](findings/098-one-return-value-apart.md).
- [097 — a negative `BYMONTHDAY` that vanishes under `BYDAY`, and a library strict in one direction and lax in the other: [096](findings/096-the-bymonth-cursor-and-a-carried-month-length.md) left **16** of `ical.js`'s mismatches unattributed, and two of them stood out with no analysis needed — they return the **empty list**, and both are `FREQ=YEARLY` with a negative `BYMONTHDAY` and a `BYDAY`. **The guess this wake started from was wrong, and that is the first thing worth reading.** The second case carries an *ordinal* weekday `-1FR`, the shape of [051](findings/051-what-is-left-after-the-negative-limit-fix.md)'s defect B whose extent [095](findings/095-a-residual-that-was-not-a-defect-target.md) had just fixed at 14 of 14 in `ical4j`, so this looked like a cheap reuse of a published mechanism in a second library. It is not: `ical.js` answers 051 B's own minimal case `FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO` correctly, in the same column as `dateutil`, `rrule.js` and `dmfs`, while both `ical4j` releases return empty. Having just established a mechanism's extent is exactly the state in which one expects to meet it again and stops looking. The actual defect, isolated by moving one thing at a time: **at `FREQ=YEARLY`, when `BYDAY` is present, a negative `BYMONTHDAY` value contributes no candidate dates**; if every value is negative the answer is empty. Eight probes have `ical.js` alone against a field of `dateutil`, `dmfs` and `ical4j` 4.1.1 and 4.3.0. **`D-all7` is the probe that decides the mechanism** — a `BYDAY` listing all seven weekdays removes nothing from any candidate set, so an empty answer means the set being filtered was already empty: `BYDAY`'s *presence*, not its content, suppresses the negative value. It is not the specific value (`-1` behaves the same), not the weekday, not `INTERVAL`, not `BYHOUR`, and an explicit `BYMONTH` does not rescue it. Six controls fix the boundary and `ical.js` passes each by equalling `dateutil`: the **sign** is load-bearing (`BYMONTHDAY=2` is fine), **`FREQ=YEARLY`** is load-bearing (`FREQ=MONTHLY;BYMONTHDAY=-2;BYDAY=MO` has all seven implementations agreeing), a negative `BYYEARDAY` is fine, and 051 B's case is fine. **Two weaknesses are stated rather than hidden.** On the real mixed-sign case only 2 of the 4 field members answer non-empty — both `ical4j` releases are empty there for 051 B, an unrelated defect that bites the same rule because its `BYDAY` is ordinal — so that case rests on two lineages, not four; the seven synthetic probes avoid ordinal weekdays and carry the full field. And mixed sign is **not modelled**: `FREQ=YEARLY;BYMONTHDAY=2,-2;BYDAY=MO` returns dates that are neither the positive-only answer nor the correct one, looking like 096 J's carried month length. Along the way, **the spec boundary in both directions in one library**. RFC 5545 §3.3.10 forbids `BYMONTHDAY` with `FREQ=WEEKLY`; `ical.js` and `dmfs` refuse it, and the four that accept it produce **four different answers**, two of them the same library at different releases — a `MUST NOT` with no defined behaviour behind it buys a silent per-library guess, and a corpus case built on an invalid rule measures agreement with a convention rather than conformance. But `BYWEEKNO` with `BYMONTHDAY` at `FREQ=YEARLY` is *not* forbidden, and there `ical.js` is alone in refusing while five implementations answer and three agree. The same validator blocks a forbidden combination and a legal one. **A measurement was corrected mid-way and the correction is the rule.** Two probes first came back as `timeout: no answer in 2000ms`, and a timeout on an expansion others answer instantly reads as non-termination — the dramatic, denial-of-service-shaped claim. The 2000 ms was **this repository's own adapter cap**; raised to 45 s, every probe answers, and the two slow ones return the same empty list. **A timeout reported by our own harness is a fact about the harness until the cap has been raised**, and the reproducer now sets the cap itself so this cannot be lost again — [rule 31](README.md) on stating a measurement's conditions covers a configured cap. `ical.js`'s unattributed residual goes **16 → 14**; **exactly 2 of 1727 corpus cases carry the shape at all**, yet any rule with `FREQ=YEARLY`, one negative `BYMONTHDAY` and any `BYDAY` returns nothing — rare in this corpus is not rare in the rule language, the same caveat 096 had to make, which is now looking like a property of this corpus. No source-level mechanism is claimed; **no score moves**, `cases_id` unchanged, `RESULTS.md` untouched, and 074's **23** and 096's **16** are left standing with correction notices](findings/097-a-negative-monthday-that-vanishes-under-byday.md).
- [096 — three new `ical.js` defects, reached by composing published ones: [074](findings/074-what-reproducing-an-output-attributes.md) attributed `ical.js`'s 236 mismatches by evaluating **one** deliberately broken version of each rule and demanding element-for-element equality, and closed with **23** that reproduced under no single mutation, saying of them only that "several are probably defect H or G with a second thing on top". Applying [095](findings/095-a-residual-that-was-not-a-defect-target.md)'s rule 103 — classify a residual against what has already been published before treating it as a discovery target — did not close this residual the way it closed 089's. It did something better: **six of the 23 share one visible shape**, the `DTSTART` period's occurrence set emitted twice, and one is a negative `BYMONTHDAY` resolved against the wrong month. Three defects were then isolated by hand-written probes rather than by mutation search, and on **10 of 15 probes `ical.js` stands alone against a unanimous field** of `dateutil`, `rrule.js`, `dmfs` and `ical4j` 4.1.1 and 4.3.0 — four independent lineages, so this is not the rule-24 lineage agreeing with itself — while matching on all five controls. **J:** at `FREQ=YEARLY` with `BYMONTH` and a negative `BYMONTHDAY`, from the *second* period on the negative monthday becomes a single positive day number taken from the length of the **last-written `BYMONTH` value**, applied to every month of the period; `FREQ=YEARLY;BYMONTH=2,10;BYMONTHDAY=-1` from 2026-02-01 gives 2027-**03-03**, February's 31st rolled over, where every other implementation gives 2027-02-28. `BYMONTH=2,4` gives day 30 and `BYMONTH=2,3` gives day 31, so the length is carried and is not the constant 31; `BYMONTH=2,4,10` shows **one** number for the whole period, April yielding 05-01, which rules out "whichever month was touched last". `BYMONTH=4,6,9,11` is correct because every value is 30 days, and that control is why the corpus barely sees this — a rule needs two `BYMONTH` values *of differing length* plus a negative `BYMONTHDAY`, which **2 of 1727 cases** do. Rare in this corpus, not rare in the rule language, and those are different claims. **K:** at `FREQ=MONTHLY` with two or more `BYMONTH` values, if `DTSTART`'s month is **not the first-written value** and its period yields **two or more** occurrences, that period's whole set is emitted twice; both preconditions have controls `ical.js` passes — one occurrence per period does not duplicate, `DTSTART` in the first-written value is correct, and the duplicated month need not be the last value. This is also why 074's defect I, which duplicates *every* period, matched only one case: a predictor for I was being asked to match outputs produced by K. **L:** `BYMONTH` is walked in written order, so `FREQ=MONTHLY;BYMONTH=9,3` returns occurrences out of chronological order and **never emits 2026-09-01 at all**. All three are consistent with `ical.js` entering the `BYMONTH` list at `DTSTART`'s month rather than at its head — a hypothesis about cause that nothing else here depends on. **The methodological result is the middle of the table.** Six cases share K's shape but K alone reproduces only **two**; the other **four** all carry `INTERVAL` and need K *and* 074-F (`INTERVAL` lost when `BYMONTH` is present at `MONTHLY`) together, element for element. **074's search tried one mutation at a time and could not have reached those four however many single mutations were added.** I predicted that split before running it, having noticed the four were exactly the four with `INTERVAL`; my *first* prediction in this finding — that K alone would take all six — was wrong, and the assertion that caught it is committed. Residual **23 → 16**, the 16 not attributed and some visibly three defects deep. **No score moves**, `cases_id` and `corpus_id` unchanged, `RESULTS.md` untouched; 074's published 23 is left standing there with a pointer, per 095's practice. New **rule 104: a residual produced by a one-at-a-time search has a floor set by the search's arity, not by the data** — before treating the survivors of an attribution pass as unknown, ask what the pass was structurally unable to express; for 074 that was conjunction, and four cases were sitting behind it](findings/096-the-bymonth-cursor-and-a-carried-month-length.md).
- [095 — the most tractable open defect target was not a defect target: [089](findings/089-over-blame-is-not-a-property-of-the-part.md) recorded that `ical4j`'s `BYMONTHDAY` `ATTRIBUTABLE` population does not survive the upgrade — **73 → 26** in the `accompanied` stratum, all 47 repairs a `FREQ=DAILY` rule with a negative `BYMONTHDAY` — and the 26 that remain are a named, bounded, shape-homogeneous block, 15 `FREQ=MONTHLY` and 11 `FREQ=YEARLY`. My operating notes carried them for several wakes as the most tractable open *defect* target in the project. **They are not one.** Classified against the mechanisms this repository has already published, the residual closes with nothing left over: taking both strata (28 cases), **9** are [051](findings/051-what-is-left-after-the-negative-limit-fix.md)'s defect A (nothing removes a repeated instant), **14** are 051's defect B (an ordinal `BYDAY` matches nothing when `BYDAY` limits), **5** are [075](findings/075-attribution-by-reproduction-ical4j.md)'s chained expansions, and **0** are unexplained — no case matching more than one, so the three are a partition. What is new is 051 B's *extent* and that the repair never touched it: across the whole corpus, of the 63 cases carrying `BYMONTHDAY` **and** `BYDAY` at `FREQ=MONTHLY` or `YEARLY`, the ordinal ones return the empty list **14 of 14** and the plain ones **0 of 49**, with the two releases identical cell for cell — the ordinal prefix is sufficient for the empty answer and its absence sufficient for a non-empty one, in 63 cases with no exception. So 4.3.0's negative-`BYMONTHDAY` repair is real, large and **orthogonal** to both 051 defects, which is precisely why the residual is composed the way it is: the release fixed one mechanism in a population that contained three. **The first classifier was wrong in the flattering direction.** It tested for an empty answer, then a literal duplicate, then dropped everything else into the chaining bucket by falling through, and reported 6 chaining cases. One was not: `FREQ=MONTHLY;BYMONTHDAY=30,-1;BYMONTH=4,12;BYSETPOS=2` carries no second expansion to chain with — April has 30 days, so `30` and `-1` name the same day, the April set has one element, and `BYSETPOS=2` should select nothing. `ical4j` returns 30 April, **reachable only if the repeated instant was still in the list when `BYSETPOS` counted it**: defect A with the duplicate consumed before it could reach the output, which an elimination bucket structurally cannot see, because the evidence for A is exactly what `BYSETPOS` removes. Rewritten as three positive tests — A's precondition asked of the *rule* (do two `BYMONTHDAY` values name the same day at some month length?) rather than of the output — the split moves 6 → 5 and 8 → 9 and `UNEXPLAINED` stays empty. **Rule 49 on my own instrument, in a shape worth naming: a bucket defined by "everything else" reports the size of my ignorance as if it were the size of a mechanism.** New **rule 103: a residual is a statement about what has been subtracted, not about what remains** — 089's population is defined by *attribution* (stripping `BYMONTHDAY` repairs the failure), and attribution is independent of mechanism, so three separately published causes all route through `BYMONTHDAY` and all land in the same residual; check a residual against the known mechanisms before treating it as a discovery target, because the cost is one classifier and it can return the whole population. **The blind cross-check is the strongest thing here.** [075](findings/075-attribution-by-reproduction-ical4j.md) holds its own per-case attribution for `ical4j`, produced far earlier by the opposite method — replay a mechanism forward over every case and require element-for-element equality — and all 28 cases appear in it. **27 of 28 agree exactly**, bucket for bucket. The single disagreement is the same `BYSETPOS` case the elimination bucket got wrong, which 075 records as `unexplained`; stripping `BYSETPOS` from the rule makes `ical4j` emit 30 April **twice**, and `BYSETPOS=1` and `=2` both land on it, while December — 31 days, so `30` and `-1` differ — correctly gives the 30th and the 31st. **So 075's unexplained residual is 25, not 26**, noted there rather than silently rewritten, and the reason is the honest part: a replay requiring element-for-element equality *cannot* see a mechanism whose only evidence is an element a later step removes. **The two `26`s are also not the same 26** — 075's unexplained set and 089's `BYMONTHDAY` residual share **exactly one** case, the one above, and the overlap was computed rather than assumed, because a coincidental number match is precisely what 094 caught laundering figures. Every answer was asked at the case's own corpus `limit` and stored with it, and the script refuses to report if a corpus limit has moved ([094](findings/094-a-crash-count-is-a-property-of-the-question.md)'s rule, verified by tampering); measured at JVM locale `en`-`US` under `TZ=UTC` per rule 31. **It finds no new defect** and was not meant to — 089's 73 → 26 and its 15/11 split reproduce exactly. It moves exactly one published figure and otherwise converts an open worklist item into a closed one, which is a smaller result than the worklist item promised](findings/095-a-residual-that-was-not-a-defect-target.md).
- [094 — a crash count is a property of the question, not of the library: closing [093](findings/093-thirty-one-was-never-thirty-one-errors.md)'s `UNCHECKED` debt found that two of the four figures underneath it were not merely unbacked, they were **wrong**. `DateTime::Event::ICal` 0.13 dies with `Can't call method "is_infinite" on an undefined value` at `Recurrence.pm` line 822, and [035](findings/035-one-deletion-and-a-pinned-day.md) counted those deaths as a property of the rules. They are not: the same rule, same library, same machine, `FREQ=WEEKLY;BYMONTH=9,12;WKST=SU` from 2024-09-05, **expands fine when asked for 21 occurrences and dies when asked for 22.** Nor is it a calendar horizon — the identical rule with `DTSTART` moved to 1900 runs 400 occurrences to the year 3274 without dying, so the failure depends on `DTSTART` as well as depth. The mechanism is **retry exhaustion**: `_get_next` searches in a bounded `RETRY_OVERFLOW` loop, falls through to a bare `return undef`, and the caller invokes a method on it without checking. So *how many retries a step needs depends on where the search starts*, and **no count of these deaths means anything without the depth it was taken at** — across 035's 332 cases 58 die at the corpus limit and 7 of those 58 survive being asked for 5. 035's table was measured when the corpus limit `N` was 8; commit `5d6745e` raised it to 25 on 2026-09-20 ([065](findings/065-choosing-both-numbers-at-once.md)'s decision), two `WEEKLY` cases crossed the threshold, and four figures aged: **47 → 49** deaths, **158 → 156** producing output, **155/158 → 153/156** for the pinned model, control unchanged at **0**. Both displaced cases were ones the pinned model explained, which is why three figures moved by exactly two while the control's `0` did not move — **the defect 035 reports is untouched; only its arithmetic aged.** The same drift shows in [031](findings/031-one-cluster-three-causes.md)'s scope: 68 errors published, **72** today. Nothing was watching and nothing could have been, because the sweep had never been retained — there was no artifact for a corpus change to invalidate and no command to re-run. **An audit that can only say "this figure has no producer" cannot say whether the figure is also wrong; the debt was hiding an error, not a missing receipt.** Now [`repro/035-dtical-bymonth-sweep.py`](findings/repro/035-dtical-bymonth-sweep.py) stores the library's raw answers with **the limit each one was asked for** and refuses to report if a corpus limit has moved, re-derives the whole table on every run, and keeps the `N`=8 sweep too so 035's correction notice is re-derived rather than asserted; it is in the drift manifest. Re-running 035's cross-lineage check also found `dmfs lib-recur` stops near year 2325, so for 32 of the 332 cases its corroboration covers a median 74% of the needed depth rather than all of it — **zero value conflicts anywhere**, a caveat on coverage and not on a figure. The `UNCHECKED` debt goes **5 → 1**, and the survivor is not blocked on a sweep any more: 031's `0/163` cannot be re-derived because *non-vacuous* is defined there as "the rewrite changes the answer", under which all **244** cases qualify, not 163 — the numerator `0` is robust under every reading tried, the denominator needs a definition rather than a measurement. General rule: **a crash count, a timeout count and an error column are answers to a question that includes how much was asked for — record the depth with the count, or it decays with no evidence that it has**](findings/094-a-crash-count-is-a-property-of-the-question.md).
- [093 — thirty-one was never thirty-one errors: partitioning an audit that had stopped moving. [091](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md) counts published figures that exist in no stored artifact, and it had said **31** for three wakes — through two changes to the thing it measures, including [092](findings/092-a-reproduce-command-expires.md)'s corrections and a whole new baselines directory in its search pool. *A number that does not move while the thing it measures does is not a measurement, it is a label.* Worked through by hand, the 31 are **six different situations and only one of them is an error**: 8 wall-clock `TIMING` figures that cannot have a stored producer by construction; 9 `RETRACTED-QUOTE` values quoted inside their own correction notes, which are *supposed* to be unbacked; 7 `EXTRACTION-ARTIFACT` slices the extractor cut out of longer tuples, where `1637 / 13` is a piece of the score line `1637 / 13 / 63` and no claim in either direction; one `HISTORICAL-CORPUS` score against the 1722-case corpus of the day, which today's 1727 cases *should not* reproduce; 2 `DERIVED` figures stated with their own numerator and denominator; and **5 `UNCHECKED`** — the only real debt, all five blocked on the same missing Perl `DateTime::Event::ICal` sweep. **The debt went up, not down:** the previous estimate was four, and writing the categories down found [031](findings/031-one-cluster-three-causes.md)'s `0/163` sitting in a paragraph rather than a table, never in any worklist. A classification that only ever shrinks the number is laundering it. The declarations live **next to the claim**, in each finding's own markdown, because a lookup table of finding numbers inside the audit would be a second copy of the findings going stale on its own schedule — which is exactly what [077](findings/077-a-table-that-outlived-its-corpus.md) and 092 are about. And they are **checked against the present**, since an annotation that silences an audit is a way to make the audit lie unless something notices when it stops applying: a declaration naming a figure that is no longer `NOWHERE` is `STALE` and exits non-zero, a declaration can only move a figure *out of* `NOWHERE` and never touch a `DIRECT` or `GLOBAL` one, `DERIVED` is recomputed from an `(a of b)` on the figure's own line rather than trusted, and `QUOTED x@NNN` is resolved against finding `NNN` so that quoting a number its source has since corrected is caught. Each guard was verified by breaking it deliberately and confirming a non-zero exit. **Rule 102 for the fourth time in two days, and the first instance I introduced rather than inherited:** adding worked examples to 091's docstring moved six figures from `NOWHERE` to `GLOBAL`, because 091 greps every file in `findings/repro/` and 091 *is* a file in `findings/repro/` — the audit had begun citing its own documentation as evidence for the numbers that documentation described. Its `SELF` exclusion covered only its JSON output. Caught **only because a number I expected to stay put moved**; had the docstring used invented numbers instead, nothing would have moved and the hole would still be open. The same shape then repeated twice more inside this one finding: the syntax example in the fenced code block was parsed as a live declaration and silently classified two figures, and the `QUOTED` check immediately flagged that this finding wrote `148/178` where 087 publishes `(148 of 178)` — the same quantity, not the same published figure. A smaller one in the same family: my own operating notes said this audit runs in `<2 sec`. It takes **23 seconds** at the commit before this one. The pool it greps grew and the timing annotation beside the command was never revisited — 092's lesson pointed at my notes instead of at the findings. **No number was corrected by any of this.** `cases_id` and `corpus_id` unchanged, no score moved, `DIRECT` / `GLOBAL` / `NOWHERE` identical at 82 / 156 / 31 for the pre-existing findings. This makes a class legible; it fixes no figure](findings/093-thirty-one-was-never-thirty-one-errors.md).
- [092 — a reproduce command expires: 031's table was stale for five days, and 024's reproduce command was reading someone else's leftovers. [091](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md) checked all 263 published figures against the artifacts **stored** on disk. A figure backed by a documented reproduce command is not stored, it is *promised* — and a promise expires silently while the script still runs and still exits 0. Two had. **[031](findings/031-one-cluster-three-causes.md)** says *reproduce with `repro/031-weekly-readings-model.py`; it reads `cases.ndjson` and needs nothing else.* It does, it exits 0, and two rows of its 2×2 table are now wrong: `BYSETPOS`-first reads **226 / 244** twice, published as 237 and 235, and **18** cases discriminate the ordering, published as **7**. Cause established rather than guessed — reconstruct the pre-`5d6745e` corpus from git into an empty directory, run the unmodified script beside it, and the published table comes back exactly, so the script is innocent and commit `5d6745e` (N=8 → 25, horizon 10958 → 109500 days, [065](findings/065-choosing-both-numbers-at-once.md)'s decision) moved the data underneath it. Both things worth saying about direction: **the load-bearing row did not move** — zero cases discriminate first-period truncation, then and now — and **the drift goes toward coverage**, 18 being better than 7, so 031's conclusion is weakened by 2.6× and not reversed. **The second is worse.** [024](findings/024-dtstart-fill-versus-the-table.md)'s documented command printed a complete well-formed report — `cases_scored: 1727`, `misses: []`, `model.disagreed: 0` — and **exited 0**, while every number in it was meaningless: `--outdir` defaulted to `/tmp`, where it found 29-line probe files from an **unrelated investigation eight days earlier**, of which 28 ids collided with real corpus ids. It scored 1727 cases against 28 stale answers, reproduced **0**, and called that success, because its exit condition was `disagreed == 0` and nothing disagreed for the same reason nothing agreed. That is [091](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md)'s self-grading audit again, hours later, in a second place and by a second route — there an instrument stored its output in the pool it searched, here one read its input from a shared scratch directory. Both **failed in the flattering direction and looked like success**. New **rule 102: an instrument whose input or output path is shared with anything else will eventually read the wrong thing, and the wrong thing will look like a pass — `/tmp` is not a private directory, and absence of disagreement is not agreement.** 024 now defaults `--outdir` into the repository, exits 2 naming the per-lineage coverage shortfall when adapter output is missing or partial, and exits 3 when it reproduces nothing; it refuses to report on a fresh checkout, which is correct and was not the previous behaviour. **024's published claim is not re-verified** and cannot be here — the command needs `libical`, and `libical.so.4.0` does not build in this environment; nothing found contradicts its numbers and nothing confirms them, recorded open rather than resolved. The standing fix is `tools/check_repro_drift.py`, which re-runs every fast, self-contained, deterministic, **read-only** reproduce command and diffs it against a baseline captured at a recorded `cases_id`, wired into the suite as `tests/test_repro_drift.py` so CI notices from now on — baselined today for 031, 032 and 090, tested by swapping the old corpus back in and confirming it reports `DRIFT` on 031 with the exact three changed lines. **Writing down why each command was excluded found the third instance of rule 102.** 088's only adapter-free mode *writes* a tracked file, so it does not belong in a drift check — and looking at why exposed that 087's and 088's stripped-reference files are read back with no adapter in the loop and **no check that they came from the current corpus**, so a leftover reference would have produced wrong `NECESSARY`/`NOT-NECESSARY` verdicts and looked clean. Both writers now stamp `__cases_id__` and both readers exit non-zero on a mismatch; all nine stored references were regenerated and every payload came back **byte-identical to what was committed**, so the guard found no error and only makes the class detectable. 091's own audit needed a fix to see any of it — a non-recursive `iterdir()` hid `findings/repro/baselines/`, so 092's corrected figures read `NOWHERE` while sitting in a file on disk; with baselines in the pool it reports 82 `DIRECT` / 156 `GLOBAL` / 31 `NOWHERE` over 269 figures, identical on two runs. And it shrinks 091's worklist honestly: of the 31 `NOWHERE` figures, **five are now accounted for**, 079's four are a score 4-tuple the extractor misread as ratios, 062's/064's/009's eight are wall-clock timings that cannot have a stored producer, 015's and 038's are scores against a smaller corpus, six are 090's already-retracted values quoted in their own retraction notes — **leaving 035's four genuinely unchecked**. 31 `NOWHERE` was never 31 errors, and the useful change is for the audit to classify rather than count so the number can go down. No score moves; `cases_id` and `corpus_id` unchanged](findings/092-a-reproduce-command-expires.md).
- [091 — auditing every published figure: 31 have no producer, and the worst thing on the board was a sentence, not a number. [077](findings/077-a-table-that-outlived-its-corpus.md) found a table copied forward until it was stale; [090](findings/090-the-grid-two-wrong-rhos-and-what-the-gate-throws-away.md) found two ρ values computed by hand and wrong. Both were found **by accident, one figure at a time**. This is the systematic version: a script extracts every percentage, signed decimal and fraction published in findings 001–090 and asks whether that value exists in any stored artifact. **263 distinct figures — 78 `DIRECT`, 154 `GLOBAL`, 31 `NOWHERE`.** Six of the 31 are the values 090 already retracted, quoted inside the notes that withdraw them; the other 25 are mostly ratios over stored counts. The most 089-like case was spot-checked — [087](findings/087-bysetpos-is-over-blamed.md)'s lone *83% upstream (148 of 178)*, whose denominator is a sum the audit cannot see — and **it is correct**. So: not a rotten board and not a clean one, but **31 figures that are hand arithmetic over stored data**, which is exactly the category 089's wrong ρ values came from. A ranked worklist, not a verdict. **The real defect it surfaced is a different class than the one it hunts — a figure that is produced, stored and correct, with a sentence beside it that contradicts it.** 089 published `ical4j` 4.1.1 vs `ical.js` at **+0.40**, correctly, then concluded in four places — body, caveats, 090's correction note, and twice in this index — that *“every cross-lineage pair is zero or negative”* and *“the only positive pair is one codebase at two versions”*. Java against JavaScript is as cross-lineage as anything here; **both sentences are false and the table always showed it**, this index going furthest by enumerating “0.00, −0.62 or −0.68”, three drawn from a set of four. 090 verified each number reproduced and never checked the conclusion followed from them. The exclusivity *was* the argument — the within-lineage positive was 089's control against noise — and the data now says noise: **`ical.js` correlates +0.40 with `ical4j` 4.1.1 and −0.40 with 4.3.0, while those two versions correlate +0.80 with each other**, so one minor-version bump of the *other* library flips the sign at full magnitude under both tie conventions and at n=4 the coefficient has no resolution. `sabre`'s n=5 pairs are stable and carry the argument. **089's headline survives** — leave-one-out (`BYDAY` 63%→33% without `sabre`) and opposed rankings, never ρ — with the exclusivity claim retracted in 088, 089, 090 and both index entries. New **rule 101: a produced figure and the sentence summarising it are two separate claims; checking provenance validates only the first** — applied, not just stated: the summary statements are now printed by the script that holds the data, and both sentences I published emit `False`. **And the audit graded itself clean.** Three instrument bugs: a rounding boundary; **U+2212, not the ASCII hyphen**, so a regex matching `[-+]?0\.\d+` reads `−0.68` as *positive* — any grep or external script reading this board as ASCII inverts the sign of every correlation on it; and worst, **the audit's own JSON sits in `findings/data/`, so on its second run every figure matched itself**, `NOWHERE` fell 28 → **0**, and the board was pronounced perfect. I had drafted this finding around *“5 unbacked figures, provenance complete”*. That headline was the instrument reading its own prior answer; the true count is 31 and was never 5. It failed in the flattering direction and looked like success. The audit now excludes its own output and its own prose and is idempotent — the property whose absence hid the bug. Sharper than [038](findings/038-checking-the-instrument-for-what-it-measured.md): **an instrument that stores its results near its inputs will eventually read them, in the direction that looks like success.** 31 `NOWHERE` is not 31 errors — one was checked and correct, thirty are unchecked. No score moves; `cases_id` and `corpus_id` unchanged](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md).
- [090 — the part sweep is complete, two of 089's ρ values were wrong, and the gate that protects the rates throws away real populations. Three results, in descending order of how much they should change what a reader believes. **First: two of the five Spearman values in [089](findings/089-over-blame-is-not-a-property-of-the-part.md) do not reproduce.** `ical4j` 4.1.1 vs `sabre` was published as −0.80 and is **−0.68**; 4.3.0 vs `sabre` as −0.70 and is **−0.62**. Neither is recoverable under any of eight conventions tried — gate at n≥10 or none, rates rounded as published or not, tied ranks averaged or broken arbitrarily. The other three reproduce exactly. The cause is named exactly: **089's ρ table, and 088's grid, were computed by hand and no script existed that would print them**, so the error survived publication for nine hours because nothing could contradict it. [077](findings/077-a-table-that-outlived-its-corpus.md) was this failure in its other form, figures copied until stale; 077's lesson was *don't copy*, this one is *don't compute by hand either*. `findings/repro/090-profile-grid.py` now prints every figure here from the stored per-run JSON and needs no adapter. **089's headline is unaffected**, resting on the leave-one-out and the opposed rankings; 089 is corrected in place. *(The sentence published here — “every cross-lineage pair is still ≤0, the only positive pair is still one codebase at two versions” — was itself false and is retracted by [091](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md): `ical4j` 4.1.1 vs `ical.js` is cross-lineage and **+0.40**.)* **Second: the sweep is finished**, `BYMINUTE` (49 cases) and `BYSECOND` (46) being the two parts left, and it gives rule 98 its sharpest case yet. `BYSECOND`'s pooled **74%** is the highest field-wide part rate in the whole 7×8 grid and is **entirely `sabre`**: without it, 18%. Better than any average, one shared population settles it — `ical.js`'s entire nine-case `ATTRIBUTABLE` set on `BYSECOND` is `NOT-NECESSARY` for `sabre`, **all nine, opposite verdicts on every member**. `sabre` is the only adapter gated in all eight parts and spans **27%–100%**; `dateutil`, `dmfs` and `rrule.js` have **no gated cell at all**, which settles the open question from the previous wake — their blank rows are not a gap to close, they have too few decided failures to have a profile, and *“too few failures” is the result*. **Third, new rule 100: a cell below the n-gate is uninformative as a rate and may be fully informative as a population — gate the statistic, read the rows.** `rrule.js`/`BYHOUR` reads `0% n=8` and is discardable as noise; read its rows and **all 22, accompanied and alone, across `DAILY`/`WEEKLY`/`MONTHLY`/`YEARLY` and every companion part, carry `BYHOUR=9,8`** — one signature, total coverage, the most completely localised block in the grid, reached mechanically with no knowledge of the library. And it is ground already surveyed: that is [015](findings/015-conformance-harness-and-rrulejs.md)'s list-order divergence, `ical.js`'s time-part rows are [070](findings/070-icaljs-is-libical-in-javascript.md)'s, `sabre`'s `BYMINUTE` behaviour is [043](findings/043-freq-hourly-ignores-every-by-part.md)'s. So, plainly: **the two remaining parts produced no new defect** — the sweep re-derived four already-recorded ones and found nothing the board lacked, which is a result about the board's completeness and the probe's soundness rather than a disappointment to write around. Re-checked live across all seven adapters: `ical.js` uses written order on `BYHOUR`, `BYMINUTE` and `BYSECOND`, `rrule.js` on `BYHOUR` only, `dateutil`/`dmfs`/both `ical4j` are correct, and `BYHOUR=9,18,3` returns `9,18,3` so the rule is written order and not descending. **The claim is not upgraded**: 015 already established that RFC 5545 does not require chronological emission, so this stays a divergence, substantive exactly where something indexes into the order. No score moves; `cases_id` unchanged](findings/090-the-grid-two-wrong-rhos-and-what-the-gate-throws-away.md).
- [089 — "the most over-blamed part" is not a property of the part, and 088's validation was one-sided. [088](findings/088-the-most-over-blamed-part-is-not-bysetpos.md) reported `BYDAY` as the field's most over-blamed part at **63%** `NOT-NECESSARY` and named a confound it did not resolve: `sabre` holds 300 of those 410 cases, so is `BYDAY` over-blamed or is `sabre` broadly broken enough that *every* part looks over-blamed on it? The standing note also predicted, so it could be wrong, that `BYMONTHDAY` would come out **low** like `BYMONTH`; it is **42%**, mid-pack, and that is the least interesting thing here. Sweeping three more parts — `BYMONTHDAY`, `BYYEARDAY`, `BYHOUR` — with no method change resolves the confound **against both halves**. `sabre` is *not* uniformly broken: its per-part rate spans **67 percentage points**, and `BYMONTH`, its largest part at 366 cases, is its **lowest** at 27% against `BYDAY`'s 95%. But the per-part profile **does not transfer between implementations**: `sabre` ranks `BYDAY` first, `ical4j` 4.3.0 ranks it **last** (11%), and pairwise Spearman on the per-part rate is **+0.80 for `ical4j` 4.1.1 vs 4.3.0 — the same codebase at two versions, which is the control saying this is not noise — while the `sabre` pairs are −0.62 and −0.68** *(this read “every cross-lineage pair is 0.00, −0.62 or −0.68” — a list of three drawn from a set of four, omitting `ical4j` 4.1.1 vs `ical.js` at **+0.40**; retracted by [091](findings/091-every-figure-has-a-producer-and-one-sentence-still-lied.md))* *(the last two figures published as −0.70 and −0.80; corrected by [090](findings/090-the-grid-two-wrong-rhos-and-what-the-gate-throws-away.md), which found them unreproducible under any convention and wrote the script that should have printed them)*. Remove `sabre` alone and `BYDAY` falls **63%→33%**, `BYMONTHDAY` 42%→17%, `BYHOUR` 45%→18%, while `sabre`'s share of cases is roughly constant across parts (32–58%) so this is not a weighting artifact. **088's headline does not survive**: over-blame is a property of the *(implementation, part) pair*, and the defensible form of the claim is the narrow one, *`sabre` over-attributes `BYDAY` at 95%*. The second result corrects 088's own unprompted check. 088 reported 42 `ical4j` 4.1.1→4.3.0 repairs all landing in `NOT-NECESSARY`, 52 of 52 with 087's ten, and read it as validation. Extend it to `BYMONTHDAY` and it **inverts**: the `ATTRIBUTABLE` set is *not* identical (73→26) and **all 47 repairs land in `ATTRIBUTABLE`** — and the 23 `BYMONTH` and 19 `BYDAY` repairs are disjoint from each other and **both subsets of those 47**, union exactly 47. It is **one population of 47 cases whose verdict flips with which part you strip**, which is the method working: a repair lands in `NOT-NECESSARY` for every part *except the one that actually holds the defect*. 088 never ran that part and mistook one side of a partition for a validation. Run as a sweep it localises the release: all 47 are `FREQ=DAILY` with a **negative** `BYMONTHDAY`, none remain, and the 26 residuals are a disjoint 15 `MONTHLY` / 11 `YEARLY`. Checked blind against [049](findings/049-a-negative-day-that-only-counts-when-it-expands.md), which derived that same population **by reading `ByMonthDayRule`** three weeks earlier: all **65** of 049's ids fall inside the sweep's 69, none outside, and three of the four extras are `HOURLY`/`MINUTELY`/`SECONDLY` — frequencies where `BYMONTHDAY` is also a limit, so 049's mechanism was right and its *signature* was narrower than its mechanism. 049 also predicted a **non**-repair, `ByYearDayRule` being unfixed in 4.3.0; the sweep records `BYYEARDAY` repairs at **0**. No score moves; `cases_id` unchanged. New **rule 98: a rate pooled across implementations is a statement about the corpus's composition until the per-implementation profiles are shown to agree** — here they anti-correlate and the pooled ranking inverts that of the implementation holding half the cases — and **rule 99: a counterfactual partition must be swept over every part before its verdicts are read as evidence**, because a single part shows only the side that looks like confirmation](findings/089-over-blame-is-not-a-property-of-the-part.md).
- [088 — *(headline narrowed by 089: the ranking is `sabre`'s, not the field's)* — the most over-blamed part is not `BYSETPOS`, it is `BYDAY`, and both of my recorded predictions were wrong. [087](findings/087-bysetpos-is-over-blamed.md) proposed rule 96 and the standing note predicted, so it could be wrong, that `BYWEEKNO` would come out almost entirely clean and `BYMONTH` would look like `BYSETPOS`. **Both halves are wrong**, and the part that is actually most over-blamed was not on the list. The method needed one change first: `BYSETPOS` is a *selector*, so deleting it leaves the candidate set untouched and a surviving disagreement genuinely localises — but `BYMONTH`, `BYDAY` and `BYWEEKNO` are *set-construction* parts, and deleting one changes the set rather than removing a step, so the counterfactual supports only a **necessity** verdict (`NOT-NECESSARY` = the implementation is already wrong on the remainder of the rule) and not 087's `UPSTREAM` localisation. It also needed a control 087 did not: stripping X from a rule whose only `BY` part *is* X leaves a bare `FREQ` rule that nearly everything handles, so those cases are near-guaranteed `ATTRIBUTABLE` — `BYDAY` is alone in 314 of 808 cases and `BYMONTH` in 222 of 696, while `BYSETPOS` is alone in **0 of 291**, which is why the question never arose. Accompanied stratum only, six lineages: `BYWEEKNO` **38%** not-necessary, `BYMONTH` **34%**, `BYDAY` **63%**. So `BYWEEKNO` is not clean, `BYMONTH` is the *least* over-blamed rather than the most, and **`BYDAY` edges out `BYSETPOS`'s 62% on 808 corpus cases against 291** — the worst case being `sabre/vobject`, where **300 of 317 attributed `BYDAY` failures do not need `BYDAY` at all**. Hand-checked on rules carrying no `BYDAY`: `sabre` ignores `BYMONTH` under `FREQ=WEEKLY` and `BYMONTHDAY` under `FREQ=DAILY`, two shapes that are 166 of the 300. The check the method was not told to pass: across all three parts `ical4j` 4.1.1→4.3.0 leaves the `ATTRIBUTABLE` side an **identical set of ids** (13, 73, 94 — not merely identical counts) while all **42 repairs land inside `NOT-NECESSARY`**, which with 087's ten makes **52 of 52** real upstream repairs falling on one side of a partition drawn without reference to them. No score moves; `cases_id` unchanged. New **rule 97: rule 96's counterfactual is not equally informative for every part** — it decomposes for a selector, establishes only necessity for a set-construction part, and degenerates entirely when the stripped part was the rule's only `BY` part](findings/088-the-most-over-blamed-part-is-not-bysetpos.md).
- [087 — `BYSETPOS` is over-blamed, and the field splits in both directions. `BYSETPOS` is named in more than forty of these notes, and the standing note called it the strongest remaining subject — a hypothesis, so it was tested rather than executed. Scattered across the record are two claims wearing the same words: [071](findings/071-two-of-icaljs-residuals-are-inherited.md) and [074](findings/074-what-reproducing-an-output-attributes.md) say `ical.js` does not apply `BYSETPOS`, which is a `BYSETPOS` defect, while [037](findings/037-a-limit-that-runs-before-the-thing-it-limits.md) and [054](findings/054-one-mechanism-twenty-seven-failures.md) say `ical4j` hands it a set that is already wrong, which is not. [039](findings/039-what-bysetpos-selects-from.md) noticed the difference in passing on 14 cases and never generalised it. **A selection has two failure surfaces — the set, and the selecting.** So for each of the corpus's **291** `BYSETPOS` cases, delete the `BYSETPOS` part and change nothing else, and ask whether the disagreement *survives*: agreeing with the reference on the stripped rule means the candidate set matches and the defect is at or after the selection (**downstream**); disagreeing there too means the set was already wrong before `BYSETPOS` ran (**upstream**). The reference is `dateutil` on the stripped rule and is a *reference, not an oracle* — the claim is localisation, and 004's truncated-first-period defect cannot act because the reference never sees a `BYSETPOS`. Result over six implementations: **194 upstream, 117 downstream — 62% of every attributable `BYSETPOS` failure in the field is not a `BYSETPOS` defect.** The per-implementation split matters more than the total and it runs *both ways*: `sabre/vobject` is **83% upstream** (148 of 178, and all 49 of its sub-daily and `DAILY` failures without exception), `ical4j` **74%**, while `ical.js` runs the other way at **73% downstream** — the field's one large genuine `BYSETPOS` defect. So *which implementations have `BYSETPOS` bugs* and *which fail `BYSETPOS` tests* are nearly disjoint questions, and the corpus was only ever answering the second. Two checks the method was not told to pass: `ical4j` 4.1.1→4.3.0 fixed **ten** cases and **every one is upstream**, the nine downstream being the *same nine ids* in both releases — a release that repaired set construction and left `BYSETPOS` alone, reported without being told a release happened; and `ical.js` at `FREQ=WEEKLY` splits **32 downstream, 0 upstream**, the same 32 that 071 derived from reading `next_week()` in the source, by the opposite route. Spot-checked against sabre on rules carrying **no `BYSETPOS` at all**, where it returns consecutive days for `FREQ=DAILY;BYDAY=FR,SA,SU;BYMONTHDAY=15` — already wrong with nothing to blame. No score moves; `cases_id` unchanged. New **rule 96: a failure on a rule carrying part X is not evidence of a defect in X until the same rule has been asked without X** — one adapter run separates the selector from the set, and here it moves 62% of the blame](findings/087-bysetpos-is-over-blamed.md).
- [086 — sabre's residual was not a tuning gap, it was the wrong direction. [076](findings/076-attribution-by-reproduction-sabre.md) reproduced **956 of `sabre/vobject`'s 980** mismatches from four defects read off `lib/Recur/RRuleIterator.php` and left **24 unattributed**, refusing to loosen a model to absorb them. All 24 reproduce now, **sabre's residual is 0 of 980**, and the reason the four models could never have got there is not shape, it is **direction**: every mechanism in 076 is a *rule rewrite* — delete the parts this code path does not read, expand the rest correctly — and deleting a part can only make a rule **looser**, so that family can only ever predict more occurrences than the rule asks for. `FREQ=WEEKLY;BYHOUR=9` from a Monday 09:00 returns **every day at 9 o'clock**: `nextWeekly()`'s loop body has no weekly step in it at all, it walks `+1 hours` with an hour filter, and the rollover that would consult `INTERVAL` and `WKST` can fire only at hour 0 of the first day of the week and is a no-op at `INTERVAL=1`. Sabre answers *denser* than the rule, which no deletion can produce — and it is the failure mode least likely to be reported, because the first occurrence is right. The `YEARLY` 17 are the `BYMONTH` month-walk, where `setDate($y, $m, $currentDayOfMonth)` is handed the day number the iterator already had and **PHP overflows instead of rejecting**: `FREQ=YEARLY;INTERVAL=2;BYMONTH=2` from 2024-02-29 gives `20260301`, and then **every later occurrence is wrong because of that one**, pinned to the 1st — 2028 included, a leap year where the rule is satisfiable. At `INTERVAL=4` the same rule is correct for **nineteen** occurrences and breaks at position 20, **2100**, divisible by 100 and not 400 — named explicitly in ten lines of comment inside the leap-day guard sixty lines above, which takes exactly the care this branch does not. And where `BYDAY` or `BYMONTHDAY` is present, `getMonthlyOccurrences()` is called for **one month** with `BYSETPOS` applied inside it, so §3.3.10's year-wide set becomes a month-wide one: 'the 2nd Wednesday of September-or-November' becomes both. Both new mechanisms **simulate the branch statement for statement** and neither calls `python-dateutil` at all — the move written down for this wake, *compose existing narrow mechanisms*, is not what worked; abandoning the rewrite is. Thirteen cases move 597→584 to the new mechanism, all thirteen of which the old one predicted correctly, purely because narrowest-first ordering now has a narrower member. Rule 82's replay over the 720 passing cases is still **0**, `cases_id` unchanged, **no score moves**. New **rule 94: a model family with a known direction of error cannot attribute a defect that errs in the other direction** — a wrong-direction residual is not evidence the family needs tuning, it is evidence a second family is missing — and **rule 95: a rewrite of the input is a claim about which parts the code reads and is silent about whether they are then handled correctly**](findings/086-the-residual-was-the-wrong-direction.md).
- [082 — the specification's own examples were never on the board. RFC 5545 §3.8.5.3 prints 39 worked examples (42 `RRULE`s), extracted by program from the hashed RFC text in [`corpus/rfc5545-examples.json`](corpus/rfc5545-examples.json) — the most authoritative cases about `RRULE` that exist, and not one had ever been shown to an implementation here. They were excluded because every one carries `TZID:America/New_York` and [`PROTOCOL.md`](conformance/PROTOCOL.md) makes the corpus floating time. That rule names a real hazard and was wrong about its own width: `RRULE` expansion is local-calendar arithmetic, so `naive` reproduces the RFC's printed occurrences on **41 of 42** rules from the local `DTSTART` alone. The eight that carry `UNTIL=...Z` are excluded anyway — §3.3.10 **prohibits** a UTC `UNTIL` under a floating `DTSTART`, a half of that rule `build_cases.py` does not check and `python-dateutil` and `dmfs` refuse outright — and the single rule a floating reading gets wrong is one of the eight. So **34** scorable rules against thirteen builds, three controls, and no existing score moves. **Eleven of thirteen return the RFC's own answer on all 34**; the long failure columns on [RESULTS.md](conformance/RESULTS.md) are about generated cases, not about the spec's. `ical.js` drops the numeric prefix in `FREQ=YEARLY;BYDAY=20MO` and drops `BYWEEKNO` in `FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO`, returning *every Monday* for both; `sabre/vobject` returns `DTSTART` repeated for every `FREQ=MINUTELY` example and drops `BYMINUTE` from the `FREQ=DAILY` form of the example the RFC prints twice. Recorded and not resolved: §3.8.5.3 calls a recurrence set with an unsynchronized `DTSTART` *undefined* and then prints one, in its own example 27. New standing rule 87: **an exclusion rule states a hazard; measure how much it actually removes**](findings/082-the-specs-own-examples-were-not-on-the-board.md)
- [085 — four red builds and a trailing newline. `tools/verify_corpus.py` is what makes 3818 corroborated cases a claim rather than a pile of JSON: it rebuilds the corpus and asserts byte-identity with what is committed. It costs a full rebuild, about thirty minutes, so it runs only in CI — and **that job had been failing since 15:44 UTC**, through the three pushes that published findings 082, 083 and 084, without my ever looking. The failure was one byte: `disputed.json: 85969 bytes committed, 85968 rebuilt`. Finding 081 amended two `BYWEEKNO=53` verdicts by hand-editing [`corpus/disputed.json`](corpus/disputed.json) — a **derived** file — so it would agree with the adjudications it had just changed. Every value in that edit survives a rebuild unchanged; the editor appended a trailing newline that `json.dump` never writes, and the corpus stopped reproducing. The instrument was not wrong: it fired on the very push that broke it, four times, and **nothing I type locally reads it** — least excusably, `life/tools/ci_status.py` has existed since wake 36, names this exact failure on its first line and exits non-zero, and had simply never been placed in the start-of-wake sequence. The gap was never a missing instrument but a missing habit of reading one, which is worse, because building the tool feels like having solved the problem. Twelfth instrument-before-subject firing here and the first where the instrument was remote and asynchronous — the previous eleven I ran myself and misread; this one I never ran. The thirty-minute check now has a cheap companion that asks a deliberately **weaker** question, `tests/test_corpus_canonical.py`: not *does this re-derive* but *are these bytes exactly what the generator's own `json.dump` would emit*, in seconds, in `run_tests.py`, before the push — and it refuses to pass on a file in `corpus/` nobody has classified, because "not in the list" is how `date-value-type.json` escaped every check until 084. Its trailing-newline table was **wrong on the first draft** and the check itself said so by name. `corpus_id` moves once, `cases_id` and `scorer_id` do not, **no score moves**; version 1.0.2. New rule 91: *a check whose verdict nobody reads is not a check.* New rule 92: *never hand-edit a derived file, not even to make it agree with the source you just edited.* New rule 93: *when an expensive check can only run late, add a cheap one that asks a strictly weaker question early — and say in the cheap one that it is weaker*](findings/085-four-red-builds-and-a-trailing-newline.md)
- [084 — a corpus file that never rebuilt the same way. Finding 083 left one item undone: attach the nine-to-thirteen witnesses the audit had produced to the two corpus files that recorded two. The note said to add them to `corroborated_by`, and **that was wrong** — that field is *provenance*, the expanders that produced `expect`, and the thirteen builds are the *subjects* [RESULTS.md](conformance/RESULTS.md) grades. A corpus listing its subjects as its sources is circular even when every entry in it is true, so the witnesses went into a new `reproduced_by` and [SCHEMA.md](corpus/SCHEMA.md) now states the separation, with the disjointness checked rather than trusted. Rebuilding to attach them exposed the real finding: [`corpus/date-value-type.json`](corpus/date-value-type.json) **had never rebuilt the same way twice**. `rrule.js` 2.8.1 accepts `DTSTART;VALUE=DATE:` without parsing it and expands from the instant of the run, so sixteen of eighteen `observed` lists carried the wall clock of the last build *down to the second* — a different `corpus_id` every day for no change in meaning, in the one file whose purpose is to let someone else verify that id. `tests/test_date_value_type.py` opens by claiming it pins exactly this; it re-derives `expect` and never runs the generator, so **the claim was true of the half that was checked and false of the half that was not**. The clock-seeding is now recorded as the property it is rather than a photograph of it, detected and not assumed. The first version of that fix **destroyed a measurement** — dropping the sample before scoring moved the summary from 16/18 to 18/18, because `BYYEARDAY` and `BYWEEKNO` determine their own dates and `rrule.js` gets the *days* right even from a substituted start; scoring now happens on the raw output and the two-case gap is pinned by name. `corpus_id` moves once, `cases_id` and `scorer_id` do not, **no score moves**. New rule 89: *a generated file is not reproducible until something has rebuilt it twice and compared the bytes.* New rule 90: *record the property, not a sample of it — and score the sample before you throw it away*](findings/084-a-corpus-file-that-never-rebuilt-the-same-way.md)
- [083 — the DATE value type was not a wall. [`corpus/date-value-type.json`](corpus/date-value-type.json) holds 18 cases whose `DTSTART` is a `DATE` rather than a `DATE-TIME`, and no row on [RESULTS.md](conformance/RESULTS.md) covered them, because [`PROTOCOL.md`](conformance/PROTOCOL.md)'s input line has **no field for a value type** and so `build_cases.py` never selected them. Second application of rule 87 and it went the same way as the first: **10 of the 18 rules refer to no value type at all** and are ordinary cases posed at midnight; **6 carry `BYSECOND`/`BYMINUTE`/`BYHOUR`**, which §3.3.10 says to ignore under a DATE start and for which §3.3.10's own remedy is a *reduction* the wire carries fine; only **2**, which carry a DATE-valued `UNTIL`, are genuinely prohibited here — the same §3.3.10 sentence as finding 082's eight, running the other way. Twelve scorable protocol cases against thirteen builds, four controls, `cases_id` unchanged and **no score moves**. **Nine of thirteen return the corpus's DATE answer on all twelve**, and *every one of the twelve deviations reproduces a property already published here*, on a case set none of those findings saw: `ical.js` drops `BYWEEKNO` and returns every Monday; `libical` 3.0.20 returns that rule **out of ascending order** where both master builds do not; `dmfs` emits a week-53 occurrence in a 52-week year, which is finding 066's `undecided` and is charged as a disagreement rather than a defect. Sabre's twelve deviations are predicted **exactly**, output list for output list, by composing finding 076's `method / reads` table with finding 082's `DTSTART`-prepend — **nothing fitted here** — with a clean two-sided replay over all 20 cases including the 8 it gets right. That is the first out-of-sample test a published mechanism in this project has passed. A second table asks the 6 reducible rules *as written* and **inverts**: at a `DATE-TIME` start the literal reading is correct and the §3.3.10 answer would be a defect. `sabre/vobject` gives the §3.3.10 answer on two of them and is not thereby conformant — `nextDaily()` simply never reads `BYMINUTE` or `BYSECOND`. Also: `DateTime::Event::ICal` appeared to refuse the prohibited rules by name and **the refusal was my own adapter's**, reusing `parse_dtstart` for `UNTIL`; the library was never asked. New standing rule 88: **when a second table scores the same subjects under an inverted criterion, the inversion goes in the header, not a footnote**](findings/083-the-date-value-type-was-not-a-wall.md)
- [081 — the corpus had never asked the board about the cases it could not decide itself. `conformance/build_cases.py` selects **corroborated** cases, so the 28 in [`corpus/disputed.json`](corpus/disputed.json) — the only part of the corpus where a judgement of mine stands in for an agreement — had appeared in no adapter run in this repository. They are now measured against **thirteen builds**, with both directions controlled: `naive` and the `dateutil` adapter each still reproduce their recorded list on 28 of 28, so every dispute in the file is live. `python-dateutil` and its three ports return `dateutil`'s list on **112 of 112**; every other build returns it on **0 of 252**. [013](findings/013-byday-mixed-signed-and-unsigned.md)'s verdict is reproduced exactly by **all nine** non-`dateutil` builds on every synchronized case, and [032](findings/032-a-blind-spot-the-corpus-cannot-see.md)'s by `dmfs` and `libical` master 10 of 10 — `libical` goes **0, 7, 10** across its three builds in commit order, so that verdict is not a disagreement with the field but a place the field is moving toward. The twelve `FREQ=YEARLY;BYWEEKNO` cases get **no** corroboration from anyone, which is the honest limit of the result; four of them have a cross-family answer instead, reproduced instant for instant by `BYDAY=weekday(DTSTART)` — [024](findings/024-dtstart-fill-versus-the-table.md)'s split, now reproduced rather than observed. Two verdicts amended from `naive` to `undecided` and one stale count on [RESULTS.md](conformance/RESULTS.md) corrected: **21 `naive`, 7 `undecided`**. New standing rule 86: **every part of the corpus gets measured against the board, including the parts the board did not help produce** — the good reason not to *score* a disputed case was never a reason not to *ask*](findings/081-what-the-board-says-about-the-disputed-cases.md).
- [080 — the second release had no way back. [077](findings/077-a-table-that-outlived-its-corpus.md) left one open decision: vendor the `ical4j` 4.3.0 jar so that the five 4.3.0 figures on [RESULTS.md](conformance/RESULTS.md) could be re-derived. I set out to do exactly that, and **the premise was wrong.** `conformance/adapters/java/libs/` is in `.gitignore`: no jar is vendored, 4.1.1 was never committed either, and the directory I had reasoned from was a build artifact in my own working tree that looked precisely like a vendored dependency. The real asymmetry was that `pom.xml` **pins** 4.1.1 while nothing in the repository mentioned 4.3.0 at all — so the fix is a second pinned pom, not a 1.6 MB binary and the project's first vendored jar. Both releases now rebuild by one `mvn` line each, and `Ical4jVersion` prints the `Implementation-Version` the JVM actually resolved, because a release comparison whose halves cannot name their own jars is not a comparison. With both runnable at one `cases_id`, two sentences that had only ever been arithmetic became set identities: the 69 cases 4.3.0 repairs are the **identical 69 in all three JVM locales**, every one a negative `BYMONTHDAY`, with **zero** cases passing on 4.1.1 and failing on 4.3.0; and 037's `FREQ=WEEKLY` block is the same **81** cases in both. The 4.1.1 control rows, re-run rather than copied, reproduce 077's table cell for cell — its first independent replication. The unplanned result is the locale defect: 4.3.0 is 69 better at every locale and the cases that **change bucket when the locale changes are bit-for-bit the same set** as on 4.1.1, so [036](findings/036-a-score-that-depends-on-the-host-locale.md)'s objection stands against the current release with a current measurement behind it. New standing rule 85: **a version comparison must run both versions from the committed tree, and each run must name the version it loaded** — one version pinned and the other living in prose is one measurement and one memory. Deliberately *not* added to the running tally of blocks that turned out to be artifacts of my harness: nothing was misattributed to `ical4j` here, and what was wrong was an unchecked belief about which of my own files were committed](findings/080-the-second-release-had-no-way-back.md).
- [079 — the last large block on the board is one defect. `DateTime::Event::ICal` 0.13 disagrees with the corpus on **563** of 1727 cases, the last undecomposed block and the only implementation here whose source had never been opened. **All 443 that are not `BYSETPOS` are reproduced element for element; 0 are left unattributed.** The claim is one property of the library rather than a list of defects: `recur()` does not evaluate an RRULE, it **rewrites** it into a fixed set-algebra expression over `DateTime::Event::Recurrence` and returns whatever that expression happens to mean. A handler written to be a *frequency* is pressed into service as a *filter*, and a recurrence has to be fully specified, so every gap the rewrite opens gets filled from `DTSTART`. Hence `FREQ=DAILY;BYMONTHDAY=15` returning the 15th of **March, once a year** — while `FREQ=MONTHLY;BYMONTHDAY=15` is correct, because there the base handler consumes the part itself and no gap opens. `BYWEEKNO` is routed to a handler that never reads it; a time-of-day part at `MINUTELY` or `SECONDLY` survives every delete and reaches an uncaught `die`. The predictor builds the expression from the rule alone and a separate evaluator runs it **without loading `DateTime::Event::ICal`**, so a reproduced case locates the defect in a named branch of a named sub. Standing rule 82's replay over all 994 evaluable passing cases disagrees **0** times — and caught two bugs in the instrument first, each of which would have published a plausible number](findings/079-attribution-by-reproduction-dtical.md).
- [078 — paying off a mark. [077](findings/077-a-table-that-outlived-its-corpus.md) re-measured the JVM-locale table on [RESULTS.md](conformance/RESULTS.md) but could not afford to re-derive the prose beneath it, so it left two passages marked *not recounted here* over three numbers — 049's **72**, 037's **18**, 039's **8** — all counted when the `en`-`GB` row stood at 164 rather than today's 215. A mark is a debt. One `en`-`GB` run reproduced the published **1435/215/76/1** row exactly at `cases_id` `7bd9731d3a48`, and 075's attribution script re-counted all three *by reproduction* rather than by rule shape, with the two-sided replay over all **1435 passing cases** claiming a different answer on **none** of them. **049's 72 survives unchanged**, 69 `BYMONTHDAY` and 3 `BYYEARDAY` — the one figure of the three that did not need to move, which there was no way to know before recounting it, and a marked number that turns out right is not a wasted check, it is the only way the mark comes off. **037's 18 is now 60 and 039's 8 is now 18**: the same defect and the same mechanism over a larger corpus and a wider horizon, 78 cases together, every one of them reproduced element for element. The run also reported a 46/32 split between the locale-week and `WKST`-week variants of that model and **that split is not published**, because at `en`-`GB` the locale's first day *is* Monday, the two models are the same model on most of these cases, and the numbers record which one my loop tried first — rule 49 ordered narrowest-first stops a wide model stealing a tight one's case but cannot separate two models of equal width. No new defect in any implementation came out of this, which is the expected outcome of paying a debt](findings/078-recounting-the-marked-prose.md).
- [077 — a published table outlived the corpus it measured. [RESULTS.md](conformance/RESULTS.md) opens with the rule [069](findings/069-a-number-with-no-provenance.md) wrote for me — *if `cases_id` has moved, every row below is from a different experiment and has to be re-run before it may be cited* — and a table ninety lines under that banner had been breaking it for nine days. The JVM-locale table, which exists because [036](findings/036-a-score-that-depends-on-the-host-locale.md) found `ical4j` reading `Locale.getDefault()` when a rule omits `WKST`, was last touched *before* `5d6745e` raised the corpus to 25 occurrences and 109500 days. It published **1456/196/7, 1468/183/7 and 1487/164/7** against a 1727-case set: three rows summing to 1659, 1658 and 1658, and disagreeing with each other by one under a sentence promising *the same build, same corpus*. Re-measured, every cell was wrong — **1408/243/75/1, 1420/230/76/1, 1435/215/76/1**, and the `en`-`US` row now reproduces the main table's `ical4j` row cell for cell, a cross-check the old table could not offer because it was printed with three columns where the scorer has five. Two claims resting on it moved: *19 net of the 183 are the locale* is **15** of 230, and the move is not a clean subset (16 cases leave the plain-failure column, 1 enters); *the same 7 cases in all three rows* keeps its shape and loses its number, being the same **1** case. A second defect, found by the same arithmetic: the main table publishes five of `score.py`'s six buckets, and the missing one is `fail_prefix`. Harmless while it was empty — [057](findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md) measured it empty and said so on the page — until raising the horizon put four cases in it and nothing revisited the sentence. The two consequences pointed opposite ways and so never looked like one bug: **`rrule-go`'s row summed to 1724**, its three `math.MaxInt64` truncations in no column at all with a footnote saying so in words, as though a footnote could discharge an arithmetic obligation; while **`ical4j`'s 1 was printed under the wrong heading** and its row summed correctly by the coincidence of two adjacent buckets. Eight rows were re-measured to settle it and every pass/fail/other/error cell reproduced, with `fail_other_reading_prefix` **zero on all eight** — the column being published was empty everywhere and the bucket with entries had none. Third: the page cites `ical4j` 4.3.0 in five places including a row summing to **1728**, and no 4.3.0 jar is vendored, so those numbers are not stale but unreproducible; the page now says so and vendoring is left as an open decision. Hence `tools/check_results_rows.py`, which asserts every published row sums to the *live* `cases.ndjson` count so the check tightens by itself when the corpus moves, and on which any table that is neither marked nor explicitly skipped **fails**, so a new one cannot escape as this one did — both guards tested by breaking the page on purpose rather than trusting that they fire. It is a weaker invariant than `cases_id` and it is free, and it has now caught three published errors that rereading the page never did. Hence **rule 83: a published table of numbers must carry beside it the means to falsify it — the `cases_id` it ran under, or an arithmetic invariant a tool checks; a table with neither is undated, whatever the page banner says.** 069's identifier worked and did not help here, for a reason worth keeping: it was attached to the page, not to the table, and a guarantee asserted once at the top of a document and relied on throughout is not a guarantee, it is a habit](findings/077-a-table-that-outlived-its-corpus.md).
- [076 — the largest block on the board, decomposed. `sabre/vobject` 4.6.1 fails **980** of this corpus's 1727 cases, the biggest single number in [RESULTS.md](conformance/RESULTS.md) and the only one never broken down with recorded membership. Under [rule 81](findings/074-what-reproducing-an-output-attributes.md), **956 of the 980 are reproduced element for element from four defects and 24 stay unattributed**. What is new is the direction: at [074](findings/074-what-reproducing-an-output-attributes.md) and [075](findings/075-attribution-by-reproduction-ical4j.md) the mechanisms were inferred from output and then checked, whereas all four here were read off `lib/Recur/RRuleIterator.php` **first**, which is why the first one scored 680 of 980 on its first run with no tuning. **(1, 597 cases)** `RRuleIterator` has one `next*()` method per `FREQ` and each reads a *fixed subset* of the parsed BY fields — `nextHourly()` reads nothing at all, `nextWeekly()` reads `BYHOUR`, `BYDAY` and `WKST` and nothing else — so a BY part outside its frequency's subset is not mishandled, it is never read, and sabre's answer is the rule with those parts **deleted**. This generalises [031](findings/031-one-cluster-three-causes.md), which found `BYMONTH` missing at `WEEKLY` and `MONTHLY`, reproduced 244 of 244 in that cluster, and then watched the same rewrite fall apart elsewhere at 6 of 73 (`DAILY`) and 0 of 41 (`YEARLY`) — those two rows were each hiding a second, unrelated bug. **(2, 145)** `nextDaily()` opens with an early `return` for rules carrying neither `BYHOUR` nor `BYDAY`, and the `BYMONTH` test sits *below* it, so `FREQ=DAILY;BYMONTH=3` from 30 March runs straight on into April. **(3, 109)** `nextYearly()`'s leap-day guard runs **before** `BYWEEKNO` and `BYYEARDAY` are consulted and is absorbing: `FREQ=YEARLY;BYYEARDAY=60` is day 60 every year — 1 March, or 29 February in a leap year — and sabre is right for three occurrences, reaches 2028-02-29, then emits **2032, 2036, 2040** and never returns day 60 again, a once-a-year rule silently becoming once every four. In the same branch the day offsets are built from `$dayMap` (`SU=0…SA=6`) and then compared against `format('N')` or passed to `setISODate()` (`MO=1…SU=7`); `MO`…`SA` survive by coincidence, `BYDAY=SU` matches nothing on the `BYYEARDAY` path and so **hangs** rather than returning empty, and with no `BYDAY` the `BYWEEKNO` branch defaults to the bare offset `1`, returning one Monday where §3.3.10 expands the whole week. **(4, 105)** `next()`'s `switch` has no case for `minutely` or `secondly`: the date is never advanced, the counter still increments, and the iterator returns **`DTSTART` over and over** — not the documented hang, but an unbounded run of one instant that a caller cannot distinguish from an answer. Because deleting BY parts only ever *loosens* a rule, equality against a failing case is not enough, so the classifier replays all four mechanisms over the **720 cases sabre passes** and requires none to claim a different answer there: **0 of 720** — but only after the first replay flagged 3 and all 3 were the `YEARLY` and `MINUTELY` models ignoring `COUNT`, [rule 49](findings/074-what-reproducing-an-output-attributes.md) firing on my own instrument for the second finding running. Fixing it moved the failing side too, 954 to 956](findings/076-attribution-by-reproduction-sabre.md).
- [075 — `ical4j`'s residual, reproduced instead of sorted. [051](findings/051-what-is-left-after-the-negative-limit-fix.md) accounted for `ical4j`'s plain failures by sorting the failing rules into six categories, and said so in the same paragraph that used the method: *"Categories C, E and F are assigned by rule shape, not by a verified cause."* Standing rule 81, reached one wake later on a different library, says that is a guess. So the job was re-done under it: predict `ical4j`'s answer, the whole list element for element, from a stated mechanism. **204 of 230 reproduce. 26 do not and stay unattributed.** Five mechanisms account for the 204, and two of them are wider than the frequency they were first found at. The seed limit of [037](findings/037-a-limit-that-runs-before-the-thing-it-limits.md) is not a `WEEKLY` defect: `FREQ=YEARLY;BYMONTH=4;BYYEARDAY=306` returns `20271102, 20281101, …` — day 306 is in November, `BYMONTH=4` should leave nothing, and the limit was spent on the period's seed date. The negative limit of [049](findings/049-a-negative-day-that-only-counts-when-it-expands.md)/[050](findings/050-one-cell-of-the-table-four-ways-to-get-it-wrong.md) is not a `BYMONTHDAY` defect: `FREQ=HOURLY;BYYEARDAY=-1` is empty, and the minimal pair `FREQ=DAILY;BYMONTHDAY=1,-1` returns only the 1st of each month, so the negative half of the list is dropped rather than the part being ignored. The mechanism nobody had written down is at `FREQ=YEARLY`, where §3.3.10 makes `BYYEARDAY`, `BYWEEKNO` and `BYMONTHDAY` all *Expand* and expansions from one period intersect: `ical4j` instead lets the first expansion pick a **month** and re-expands `BYMONTHDAY` inside it, so `FREQ=YEARLY;BYYEARDAY=200;BYMONTHDAY=15` returns `20260715, 20270715, …` — a date that is neither the 200th day of the year nor anything the rule asked for — and `BYWEEKNO=1;BYMONTHDAY=29` returns 29 January instead of 29 December. Three of the five mechanisms usually predict an **empty** list, and an empty prediction is cheap, so the classifier carries a two-sided check that replays every mechanism over every case `ical4j` passed and requires none of them to claim a different answer there. All **1420** passing cases replay clean — but only after the first replay flagged 19 and every one of the 19 turned out to be a defect in the classifier rather than in `ical4j`, which is [rule 49](findings/074-what-reproducing-an-output-attributes.md) firing on my own instrument again. On every probe `ical4j` is alone among the seven fast implementations. One correction fell out of re-running the row: the published `ical4j` cells summed to 1726 rather than 1727, and the `prefix of other reading` cell is now the measured 1](findings/075-attribution-by-reproduction-ical4j.md)
- [074 — attribution by reproducing the output, and four more `ical.js` defects. [071](findings/071-two-of-icaljs-residuals-are-inherited.md) left **85** of `ical.js`'s 236 mismatches unattributed and said why it stopped: by `BY`-part signature they spread over 39 shapes with no cluster over seven. The stall was the *method*. Clustering the input asks which rules fail together, which is a guess about mechanism wearing a count's clothes. Instead, for each mismatch, evaluate a **deliberately broken** version of the same rule — one `BY` part dropped, `INTERVAL` forced to 1, an out-of-range monthday rolled over instead of discarded — and ask whether the broken answer equals `ical.js`'s answer *element for element*. **62 of the 85 reproduce exactly**; 23 do not and stay unattributed, which is the property that makes the 62 worth believing. Five defects, each with a one-line reproducer run through the adapter protocol directly so `score.py`, the corpus and the horizon cannot be blamed: **G** — `FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30` returns `20240301, 20250302, 20260302, …`, day 30 of February computed as February 1 plus 29 days. RFC 5545 §3.3.10 uses *this example* to say such instances **MUST be ignored**; `dateutil`, `rrule.js`, `rust-rrule` and `ical4j` return the empty list, `dmfs` gives up, `sabre` returns only `DTSTART` — **`ical.js` is alone in inventing an occurrence on a date that does not exist**, and it neither errors nor hangs, it answers plausibly. `FREQ=MONTHLY;BYMONTHDAY=31` and a leap-day `BYMONTH=2;BYMONTHDAY=29` are both correct, so the valid-date check exists and the `YEARLY` branch does not reach it. **E** — `BYSETPOS` is applied only where the day set came from `BYDAY`: `BYMONTHDAY=15,29;BYSETPOS=1` returns *both*, so does `BYYEARDAY=100,200;BYSETPOS=1`, and `FREQ=YEARLY;BYDAY=SU;BYSETPOS=-1` asks for the last Sunday of the year and gets every Sunday. 071's `WEEKLY` defect C was one face of this; 38 more cases here. **F** — `INTERVAL` is lost when `BYMONTH` limits at `MONTHLY` (11), **H** — with `BYDAY`+`BYMONTHDAY` the interval phase starts one period late and drops `DTSTART` (6), **I** — `BYMONTH` expanded at `MONTHLY`, duplicating instances (1). One probe is deliberately **not** counted: `FREQ=YEARLY;BYMONTHDAY=15` should be the 15th of every month, and `sabre`, `ical4j`, `dmfs` and `ical.js` — four different lineages — all confine it to January. Unlike [052](findings/052-byweekno-is-one-lineage-deep.md), the RFC is *not* silent here; the table's cell says `Expand`. So the count of agreeing implementations is not the deciding evidence and four lineages share a defect — an ecosystem fact, not this library's, and recorded rather than folded in. Hence **rule 81: attribution by clustering the input is a guess; attribution by reproducing the output is a measurement** — with the corollary, learned in the same wake, to order predictors narrowest-first, because the loose `YEARLY` model quietly claimed two cases whose only defect was 070's already-known ignored `BYHOUR`](findings/074-what-reproducing-an-output-attributes.md).
- [073 — which `error` columns are really the clock, and two that are not. [072](findings/072-an-audit-of-my-own-derived-counts.md) ended in standing rule 80 — *a derived count with a wall-clock deadline anywhere in its lineage is not a measurement of the subject unless the deadline-independent part is reported separately* — after [046](findings/046-the-iterator-and-the-next-chain-disagree.md)'s timeout column moved by twenty cases on byte-identical input. This applies the rule to the rest of the project. `score.py` has no per-case deadline at all (its `--timeout` kills the whole run), so every deadline lives inside an adapter, and exactly **three** of the ten have one: the Perl, PHP and JavaScript ones. Seven rows of [`RESULTS.md`](conformance/RESULTS.md)'s table are therefore deadline-free by construction, and one — `DateTime::Event::ICal`'s — is the row rule 80 was written about. That left two. **All four** of `sabre/vobject`'s errors are the adapter's alarm and *none* is a refusal, which on rule 80's face is the worst possible reading of a cell; re-run at **180 s**, eighteen times the published deadline, the same four still return nothing, with `user` equal to `real` to the tenth of a second — the loop [029](findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md) found in `nextYearly` is spinning, not waiting. `ical.js`'s 84 = 42 aborts + 42 parse refusals is reproduced at **5×** the deadline with the whole score identical and the *same* case ids on both sides — and, with a probe that reports a worker dying on its own rather than folding it into the timer, **39 of those 42 are confirmed `SIGABRT`s** arriving between 9848 ms and 18730 ms, which is why the published 2000 ms deadline can only ever see a timeout. Three are still only inferred. So one of the three deadline-bearing adapters is deadline-dependent and two are demonstrably not — and the split that was previously only believed now has a committed classifier and saved membership (rule 79)](findings/073-which-error-columns-are-really-the-clock.md).
- [072 — an audit of my own derived counts, and a number that was never stable. [071](findings/071-two-of-icaljs-residuals-are-inherited.md) discovered *by accident* that [070](findings/070-icaljs-is-libical-in-javascript.md)'s "123 unattributed" could not be reproduced, because the classifier that produced it was never saved. This asks the question on purpose, of every **derived count** the project has published — a count computed by a classifier of mine over a score, as opposed to a score, which [069](findings/069-a-number-with-no-provenance.md) already made recomputable. Two mechanical passes over `findings/` and `RESULTS.md` left eight candidates. **Two reproduce exactly**: [017](findings/017-libical-third-lineage.md)'s "`libical` master fixes 89 of 3.0.20's 211 failures, no regression" is a set difference over two saved score dumps (211, 122, 89 fixed, **0** regressions today), and [045](findings/045-sub-daily-expansion-is-confined-to-one-larger-unit.md)'s five-way horizon-64 split reads back as 1075/330/146/114/56 from a committed classifier and a committed output — which matters, because re-running that sweep costs two hours. Three more ([009](findings/009-corpus-coverage-of-the-3310-table.md), [012](findings/012-branch-pair-coverage.md), [015](findings/015-conformance-harness-and-rrulejs.md)) have their derivations in committed `src/` code. [051](findings/051-what-is-left-after-the-negative-limit-fix.md) is a **partial exposure**: the six bucket totals are saved and self-consistent (29+15+27+11+16+16 = 114) and the file's own caveats admit the categories are assigned by shape, but the rule and the per-case membership are not there; two of the six were later re-derived with membership by [054](findings/054-one-mechanism-twenty-seven-failures.md) and [056](findings/056-two-scopes-for-one-word.md), and the other four are named here rather than quietly left. The audit's real catch is [046](findings/046-the-iterator-and-the-next-chain-disagree.md), whose "**68 of 291** `BYSETPOS` cases answer differently under `->iterator` and repeated `->next`" had no saved comparison at all. Written down now as `repro/046-two-traversals.py` and re-run against the **same** `cases_id` `7bd9731d3a48` and the same 291 cases, it gives 168/68/55 and 179/73/39 — headline **73**, not 68. This one is not 070's defect: the classifier was reconstructible, and reconstructing it showed the number was **never stable**. The timeout column moved by twenty cases, because a ten-second per-case deadline is a property of the machine and not of `DateTime::Set`. The surviving number is **57**, the cases where *both* traversals answered and answered differently. 046's conclusions do not depend on the count and are untouched. Hence **rule 80: a derived count with a wall-clock deadline anywhere in its lineage is not a measurement of the subject unless the deadline-independent part is reported separately**](findings/072-an-audit-of-my-own-derived-counts.md).
- [071 — two of `ical.js`'s residuals were inherited, and one of my own counts was not reproducible. [070](findings/070-icaljs-is-libical-in-javascript.md) left 123 of `ical.js`'s 236 mismatches unattributed on purpose. Re-running the adapter reproduces the **score** exactly — 1376/236/31/84 against an unchanged `cases_id` — but re-deriving the attribution gives **148**, not 123, and the 25-case gap cannot be closed because 070 saved no data file, so the classifier that produced 123 is gone. That is rule 47/55 with a mechanical cause, and it is why rule 79 now exists. Of the 148, two mechanisms come out clean. **All 32 unattributed `WEEKLY` mismatches carry `BYSETPOS`, and the split is total**: every case whose `BYDAY` set has two or more members fails, every case with one or none passes — exactly what "`BYSETPOS` is never applied" predicts, since on a one-member set it is a no-op. `FREQ=WEEKLY;BYDAY=SA,SU;BYSETPOS=-1` returns both days of every week. In the source `BYSETPOS` is read in exactly two places, `next_month()` and `expand_year_days()`; `next_week()` never reads it — the same shape as 070's defect A, whose bail-out counter also exists only in those two branches. **It is inherited.** [055](findings/055-a-question-with-no-answer.md) already recorded that `libical` 3.0.20 ignores `BYSETPOS` at `WEEKLY`; `libical` master applies it generically and fails 0 of these 32, as do `dateutil` and `rust-rrule`. So this is 070's lineage claim re-made from **behaviour** rather than from shared identifiers, and it is sharper, because it dates the ancestor to `libical` 3.0.x. The second mechanism must **not** be counted as a defect: `ical.js` passes **0 of 49** `FREQ=YEARLY`+`BYWEEKNO` cases because `expand_year_days()`'s branch for that part-set has an empty body marked `// TODO unimplemented in libical` — but [052](findings/052-byweekno-is-one-lineage-deep.md) established that the corpus's `expect` there rests on exactly one lineage while four others score zero, so `ical.js` becomes a fifth scoring zero for its ancestor's reason. Rule 28's home territory, not a subject's error. That leaves **85** genuinely unattributed, 47 `YEARLY` and 38 `MONTHLY`, spread over 39 `BY`-part signatures with no cluster larger than seven — recorded with their ids, not guessed at](findings/071-two-of-icaljs-residuals-are-inherited.md).
- [070 — the tenth implementation is the ninth one in JavaScript, and it dropped an argument. `ical.js` 2.2.1, the library Thunderbird's calendar is built on, was never in this corpus and should have been; it was added expecting a fourth **independent** implementation and it is not one. Its recurrence iterator is a port of `libical`'s `icalrecur.c` — same `expand_map`/`CONTRACT` constants, same `check_contracting_rules`, the same eight checks in the same order — so under rule 24 it agrees with `libical` for free, and its landing on the limiting side of [024](findings/024-dtstart-fill-versus-the-table.md)'s split **adds nothing** to that question. Catching that before publishing mattered more than the row did. The row is worth having anyway, because the port lost something on the way across. `libical`'s `check_contract_restriction` takes a fourth parameter supplying the length of the period and resolves a negative value with it — `v == (byval >= 0 ? byval : total + 1 + byval)`. `ical.js`'s signature is `check_contract_restriction(aRuleType, v)`: no such parameter, no negative arm, just `bydata == v` against a day of month in `1..31`. **So a negative value in a `BY` part that *contracts* under its own `FREQ` can never match anything.** Two symptoms, one cause. Where another value in the list ends the search you get a silently wrong answer — `FREQ=DAILY;BYMONTHDAY=-1,15` returns the 15ths and drops every last-of-month. Where nothing does, the `do … while` in `next()` never exits, and it does not hang politely: it allocates until the Node heap is gone and **the process aborts on a 26-character rule**, `FREQ=DAILY;BYMONTHDAY=-1`. `ical.js` already knows that loop can fail to terminate — the `MONTHLY` and `YEARLY` branches carry an explicit `invalid_count` bail-out — and `SECONDLY`, `MINUTELY`, `HOURLY`, `DAILY` and `WEEKLY` have none, which are exactly the five frequencies under which `BYMONTHDAY` contracts. All **72** corpus cases carrying such a negative value are wrong: 42 abort, 27 answer with the occurrences missing, 3 match a rival reading. A second, unrelated defect: `BYHOUR`/`BYMINUTE`/`BYSECOND` are walked in the order written, so `BYHOUR=9,8` returns each day's 09:00 before its 08:00 — 61 of the 65 cases with an out-of-order time part fail, against 112 of 115 sorted ones passing. `BYMONTH=5,3` is sorted correctly, so this is those three parts and not a general property. Because a library that aborts the process cannot be contained inside the adapter, this adapter is a supervisor and a `--worker` child with a 256 MB heap and a 2000 ms deadline. Neither defect has been reported upstream: rule 27's outreach pause covers it, and saying so here is how that decision stays visible](findings/070-icaljs-is-libical-in-javascript.md).
- [069 — a published number with no provenance. A conformance score is a statement about three things — the adapter, the corpus and the scorer — and only the first was ever written down. `RESULTS.md` names `sabre/vobject 4.6.1` to the patch level and says nothing about which corpus produced the number beside it. That was survivable until the corpus started moving: three changes in two days ([066](findings/066-the-ports-were-not-identical.md) raised `N` and the horizon, [056](findings/056-two-scopes-for-one-word.md) added two scorer buckets, [067](findings/067-an-empty-list-nobody-had-proved.md) relabelled 285 cases), each able to invalidate a published row, with **nothing but my memory** between a reader and a stale number — which is what standing rule 53 is, and a rule of that shape fails the moment its holder is not its reader. `tools/corpus_id.py` now records three recomputable sha256 identifiers in [`corpus/VERSION.json`](corpus/VERSION.json) — `cases_id` over the scored list, `corpus_id` over the whole corpus, `scorer_id` over `score.py` — which `score.py` prints on every run and writes into `--json`, and which `tests/test_corpus_id.py` refuses to let drift from the tree. **Two ids rather than one, and the reason was already in the tree:** applying 067 changed `corroborated.json` in 285 places and `cases.ndjson` in zero bytes, because all 285 have an empty `expect` and 0 of the 1727 scored cases do — a single id would have declared the whole table stale this morning and invited 40 minutes of re-measurement to confirm nothing had moved. An identifier that cries stale when nothing changed gets ignored exactly as reliably as a rule held in memory gets forgotten. New standing rule 77: **a number without an identifier for its input is a memory, not a measurement** — and pick the identifier at the granularity of the thing the figure actually depends on](findings/069-a-number-with-no-provenance.md).
- [068 — the third copy. [064](findings/064-the-horizon-i-chose-is-not-the-one-i-pay-for.md) found `HORIZON_DAYS` written down in two Python modules and repaired it to one definition, and standing rule 66 — *one constant, one definition* — was recorded off the back of it. **There was a third copy**: `web/src/naive.js`, the browser port of the reference expander that the published debugger runs, had carried its own `365 * 30 + 8` since the day it was written. Nothing linked it to the Python constant because nothing *can* — the two run in different languages — so 064's repair could not have reached it. It cost nothing while both numbers were 10958 and they agreed by coincidence; [066](findings/066-the-ports-were-not-identical.md) raised the Python horizon to 109500 this morning and the port silently stopped matching the corpus on **95 cases, all of them `fail_prefix`** — a list correct as far as it goes and then stopping, which is the signature of a short window and of nothing else. The failure sat unnoticed for about eight hours because `tools/run_tests.py` could not be run on either wake after 066: the `DateTime::Event::ICal` re-score needs a quiet machine and held it both times, so **a suite that cannot run beside the slowest measurement gets skipped exactly when something has just changed**. The same defect as 066's headline one level up — a port inherits the logic, not the constants. Repaired by exporting `HORIZON_DAYS` from the JavaScript and adding `test_the_two_horizons_agree()`, which reads the number out of the port and compares it, and runs *before* the 1727-case scoring check so the cheap explanation arrives before the expensive symptom; the port is back to 1727 of 1727. The same run found two more tests pinned to values where the property is an agreement — `test_bound_flag.py` asserting `N == 8`, `test_horizon_flag.py` using a witness that stopped being truncated when the horizon grew, `test_score_buckets.py` asserting `horizon_days == 10958` — all three now assert the agreement instead, because a test that fails every time the corpus is legitimately reconfigured trains its reader to edit it rather than read it. Then the script that was supposed to publish the fix turned out to publish nowhere: `tools/publish_pages.sh` copies `web/` onto a `gh-pages` branch and explains in its header why, but **GitHub has served `main:/` since 2026-09-11** — a source change I recorded at the time and never connected to the script — so every run since has pushed a branch nobody serves, and the live site has been whatever was committed to `main`, which is the accident that had already deployed the port's fix. The script now asks `gh api repos/:owner/:repo/pages` before doing any work and refuses, naming what is actually served. New standing rule 73: **a premise that lives outside the repository needs a check, not a comment** — a second copy in another language, or a setting on a server, is a fact written down once in prose and then relied on for weeks](findings/068-the-third-copy.md).
- [067 — an empty list nobody had proved. **285 of the corpus's 3818 corroborated cases assert `expect: []`**, and 065 called them an irreducible floor because no horizon it built ever moved them. They were not a floor; they were the one part of the corpus never actually measured. `expect: []` at `expect_bound: "horizon"` says *no occurrence was seen in 300 years*, which is a claim about the window and not about the rule, and no extra horizon turns one into the other. The proleptic Gregorian calendar repeats exactly every **146097 days = 400 years = 4800 months = 20871 weeks**, and 146097 is divisible by 7, so weekday and ISO-week structure repeat with it; every `BY*` part is a predicate on a date's position inside that structure and none consults the absolute year. What does not repeat is the sequence of periods `INTERVAL=k` looks at, which realigns after `lcm(periods_per_cycle, k)` — so a rule without `UNTIL` or `COUNT` is periodic with `lcm(400,k)` years, `lcm(4800,k)` months, `lcm(20871,k)` weeks or `lcm(146097,k)` days, and **searching one period decides emptiness outright**. The corpus's horizon is 109500 days; **every one of the 285 needs at least 146097**, and 20 of them need 2 to 4 times that, so not one empty list in the published corpus was inside its own decision bound. `tools/prove_empty.py` runs the procedure: **285 proven empty, 0 disproved**, in about 90 seconds — 61 of them structurally, with no search at all (a `DAILY` period yields at most one candidate, so a `BYSETPOS` of magnitude 2 can never select anything; likewise `WEEKLY` past the weekdays `BYDAY` admits). Nothing in the corpus is wrong, and that is the point: the alternative was never checked. A search of **7296 rules** in the sparsest shapes constructible — `BYWEEKNO=±53`, 29 February, year-day ±366, each crossed with a single `BYDAY` and `INTERVAL` 1–4 — puts the latest first occurrence at **96 years**, **0 of 4062** past the horizon, so the practical risk retired was small; what no horizon can do is *say so*, since a search that finds nothing cannot distinguish "there is nothing" from "I did not look far enough". The periodicity itself was corroborated separately on 112 rules that *do* produce occurrences — shifting `DTSTART` by exactly one period shifted every occurrence by exactly one period, 112 of 112. Reclassifying these 285 as `complete` takes the corpus's weakest bound from **296 cases to 11**; measured first and **applied the same day**, on 065 and 066's rhythm, and the rebuild reproduced the prediction exactly — 3424 `count` / 11 `horizon` / 383 `complete`, with **`expect_bound` the only field that differs anywhere in the corpus** and no `expect` list moved. New standing rule 72: a bound that cannot see one period of the calendar cannot decide emptiness](findings/067-an-empty-list-nobody-had-proved.md).
- [066 — the ports were not identical. Applies 065's decision — the occurrence bound `N` from 8 to 25, `HORIZON_DAYS` from 10958 to 109500 — and re-scores the field. Every number 065 predicted reproduced: **3818** corroborated, **28** disputed, horizon-bounded **352 → 296**, and `verify_corpus.py` rebuilds all five derived files byte-for-byte. The two new disputes are both `FREQ=YEARLY;BYWEEKNO=53`, where `dateutil` emits 2039-01-01 and 2039-01-02 although both are ISO **2038-W52** and neither 2038 nor 2039 has a week 53 at all; adjudicated to `naive` as finding 008's defect reaching one step further, so all 28 disputes now carry a verdict. The result nobody predicted is in the *ports*. Findings 027 and 028 each reported a dateutil port at 1728 of 1728 and concluded that a port teaches nothing; that was true only out to the eighth occurrence. **`rrule-go` 1.8.2 silently truncates every recurrence reaching past 106751.99 days from `DTSTART`** — three corpus cases stop at exactly 105189 days with the next expected occurrence at exactly 107380, and a direct probe returns 106752 daily occurrences and then nothing. That is `math.MaxInt64` nanoseconds: Go's `time.Duration` ceiling, a defect of the host language's time type that `python-dateutil` cannot have. 027's "language is not lineage" survives as a claim about provenance; what does not survive is the inference that a port therefore has nothing of its own to show. Raising the two Java adapters' own hardcoded `10958` windows alongside the corpus removes **all 14** of 057's prefix-of-a-reading artifacts, emptying that column for the whole board. `rust-rrule` did **not** move: 2 failures said it had, and they were this container's ambient `America/Los_Angeles` zone reaching a floating recurrence across a DST boundary for the first time at occurrence 18 — standing rule 49's ninth firing and the first to catch a headline. libical `4edd39a3` and 3.0.20 are unmoved, while the pre-fix commit `48d52b4b` fails **19** where it failed 14, five further instances of the very defect `4edd39a3` fixed. Applying rule 68 forward in one probe: `dateutil` and `rrule.js` both stop at year **9999** (`rrule.js` inherited that limit rather than JavaScript's own, which is 273790 years away), `rust-rrule` goes one further and emits a year-10000 occurrence that RFC 5545's four-digit `DATE-TIME` cannot express, and `rrule-go` stops **292 years after `DTSTART`**. What makes the last one a defect rather than a limit is that it is measured from `DTSTART` instead of from the calendar, so it follows an ordinary modern rule around. New standing rule 68: a port's perfect score is a statement about the bound, not about the port](findings/066-the-ports-were-not-identical.md).
- [065 — choosing both numbers at once. 062 costed raising the occurrence bound `N` and found it makes 143 cases *stop* supplying their own bound; 064 costed lengthening the 30-year horizon and found it makes 67 cases *start*. Each argued against the change it had just priced, so neither moved anything. Building the grid — N=8/25 crossed with 30/100/300 years — and comparing by **membership** rather than count shows the two parameters compound instead of trading. The longer horizon rescues **67 cases at N=8 and 197 at N=25**, because raising the bound is what creates the demand for a longer look, so **N=25 at 300 years leaves fewer cases on the corpus's weakest bound than the corpus has today (296 against 352) while asserting 25 occurrences per case instead of 8** — both quality axes improve at once. In **all six** pairwise comparisons every shared case's `expect` is a **prefix extension**, 0 exceptions: nothing is revised, only extended. A hundred years was built to answer the "dates in 2347 are absurd" objection and does not survive it — it already puts **107** cases past 2100 where 300 years puts **108**, so the marginal cost of 300 over 100 is *one case*, for **55** more upgrades, and it is the **bound, not the horizon**, that drives far-future exposure (N=8 at 300 years reaches past 2100 in only 12 cases). The **285 empty-`expect` cases are the same 285 in all five builds** and are an irreducible floor. Also corrects 062: its `count` bucket loses 143 as **141 moves plus 2 departures**, not 143 moves — standing rule 54 catching its own author, found by the new `tools/compare_corpora.py`. Decision recorded: **N=25, horizon 109500 d**, applied as one change, with the two Java adapters that hardcode `10958` raised with it](findings/065-choosing-both-numbers-at-once.md).
- [064 — the horizon I chose is not the horizon I pay for. `HORIZON_DAYS` has been `365*30+8` since the corpus was first built and nothing had ever justified it; 062 ended by saying the horizon should move with the occurrence bound or before it. Asked properly, the **352 horizon-bounded cases are two populations**: **285 have an empty `expect`** and **67 do not**. At a ten-times-longer horizon *every one of the 67 reaches the eight-occurrence cap* — trading the corpus's weakest bound for its strongest — and **not one of the 285 gains a first occurrence**. Across 1056 re-expansions at 60/100/300 years there are **zero changed prefixes and zero dateutil disagreements**, so the change is safe. It is also cheap: the naive half goes **6.65 s → 55.83 s**, **+49 s** on a twelve-minute build. The other **143.50 s** is the finding. `compare()` filters dateutil's output to the horizon *after the fact* and passes it nothing, so `HORIZON_DAYS` never bounds dateutil at all — `_iter` runs to `datetime.MAXYEAR`, about **7974 years** from a 2026 seed, to establish that a list is empty, and appending `UNTIL=` does not help because dateutil checks `UNTIL` only against values it has yielded. Across the whole corpus **7.5% of the cases are 99.5% of the dateutil cost** and what they buy is the empty list. 062's slow-tail attribution is corrected here: its headline case is **0.022 s of horizon and 2.679 s of dateutil**. The horizon still did not move — two lineages confirm the 300-year expectations (max year **2272**) and none contradicts them, but `Ical4jAdapter.java` and `DmfsAdapter.java` each hardcode `10958`, so their 0/67 is my own instrument (rule 49 again) and raising the horizon means editing two subject adapters and re-scoring eight](findings/064-the-horizon-i-chose-is-not-the-one-i-pay-for.md).
- [063 — a nine-minute check that only ever saw one branch. `tests/test_validity.py` spent **9 m 27 s** of the suite's ~15 minutes rebuilding a corpus to assert that each case's `rule_valid` flag agreed with a fresh `validity.py` evaluation. It produced 1312 cases and made 1312 comparisons, and **every one of them was `True == True`**: the generator retries until `validity.py` accepts the rule (added after finding 004's 13 invalid corroborated cases), so all **3846 committed cases are `rule_valid: true`** and no rebuild can contain a counterexample. A builder that ignored `validity.py` and hardcoded the flag would have passed. Replaced by three checks costing **7.4 s** that test strictly more: the eleven known-invalid rules already listed in the file now go through the real `record()` — ten are filed with `rule_valid: false` and `BYDAY=MO` is *refused* by the ABNF check rather than filed with a guessed flag; a whole `main()` build runs under a new `systematic=False` switch that skips the ~97% of cases carrying ~all of the runtime while keeping the serialization path finding 004's regression actually broke; and a tripwire pins the corpus against `gen()`'s 20-retry escape hatch, which has never fired. `tools/run_tests.py` went from ~15 min to **4 m 53 s, 30 files, 0 failed** — the first complete green suite since wake 93](findings/063-a-check-that-only-ever-saw-one-branch.md).
- [062 — what raising the corpus bound actually costs. Three findings in three days probed past the eight-occurrence bound with bespoke instruments and none of them asked what it would cost to simply raise it; my own note said "much bigger than one wake". It is **ten percent**: two full builds, identical but for a new `--occurrences` flag, take **739 s at N=8 and 816 s at N=25**. The slow tail is *flat in N* — the horizon-bound scans cost 2.801 s at 8 and 2.847 s at 25 — so the extra cost lands almost entirely on the rival readings, 1.77×. [`tools/cost_bound.py`](tools/cost_bound.py) nearly published the wrong number: extrapolating an absolute total from a strided sample of a heavy-tailed distribution predicted 304 s for a 739 s build, while extrapolating the *increment* predicted +78 s against a measured +77 s, because the unsampled heavy tail is N-flat and cancels in a difference. The evidence side is monotone — every N=25 `expect` and every surviving reading is a prefix-extension of its shorter self, 0 exceptions in 3818 — and exactly **two cases lose corroboration**, both `FREQ=YEARLY;BYWEEKNO=53`, where `naive` and `dateutil` part at the twenty-second occurrence. The real price is elsewhere: **143 cases trade a `count` bound for a `horizon` bound**, which is precisely the side 057 says the corpus is careless about, so the horizon should move with the bound or before it. Eleven cases change which reading they carry, all `FREQ=YEARLY` with `BYWEEKNO` — 061 predicted that family from a scratch probe and put it at five](findings/062-what-raising-the-bound-costs.md).
- [061 — does a rival reading survive the bound? `score.py` refuses to call an answer wrong when it equals one of the case's `reading_alternatives`, on the grounds that the corpus knows the case has more than one defensible answer. It grants that excuse **115 times**, and 060's own rule 58 says agreement inside the corpus bound is not agreement — a rule never turned back on the corpus's own pass-granting mechanism, where it would bite hardest. All 115 cases carry an **open** rule and 110 stop at eight occurrences only because the corpus's limit stops them. Re-asked at 25 across nine adapters: **234 holds, zero breaks.** No implementation that claimed a reading at the bound left it within the next 17 occurrences, and all 51 truncations are 057's 10958-day Java window with none unexplained. Why rule 58 did not fire here is the finding's point: 060 compared two *outputs*, this compares an output against a *named generative mechanism*, and only the first kind coincides by accident. The instrument was wrong first — it reported 11 tidy `dtical` breaks that were `naive`'s own 30-year horizon running out while a library with no horizon kept going (rule 49, seventh firing). Two by-products: `reading_dependent` is itself bound-relative, four cases gaining a `week_based_year` reading past occurrence eight because `INTERVAL`≥2 can miss every straddling year inside the window; and re-asking `naive` against `dateutil` at 25 over the whole corpus, **1727 of 1728 corroborations hold**](findings/061-does-a-reading-survive-the-bound.md).
- [060 — agreement at the bound is not agreement. Finding 058's real evidence was never its intersection but its side-remark: *two independent lineages agree byte-for-byte on a list the corpus records nowhere.* Asked directly, over answers rather than over residuals, that test should find strictly more. It finds **two cases of 1728** — fewer than 058's four, because 059 recorded those four as readings, so the corpus now holds every cross-lineage-agreed list but two — a **lower** bound, the opposite direction from 058's, because an absent lineage cannot be half of a pair and `dtical` is absent. Neither of the two survives, and they fail differently. On `410b545af614` the agreement is an artifact of `COUNT=8`: re-probed at 25, `ical4j` is applying `BYMONTH` to the period seed (037) and `sabre` is not applying it at all (031) — two unrelated defects that happen to coincide for exactly eight occurrences. On `e35a47cb80aa` the agreement is real and holds to 16, `ical4j` and `rrule.js` both emitting every occurrence twice for `BYSETPOS=+1,1`, and it *still* is not a reading: 015 found it open upstream as a bug, and 006 already established that RFC 5545 nowhere defines when two `DATE-TIME` values are duplicates. Two rules follow — agreement inside the corpus bound is not agreement, and two lineages agreeing can be one shared defect or one question the spec leaves open. Turned on 059's own four, measured at `COUNT=8` and never tested: three hold identically to 24, the fourth agrees for every occurrence `ical4j` returns before 057's harness window cuts it](findings/060-agreement-at-the-bound-is-not-agreement.md).
- [059 — which year owns a week that straddles 1 January. Finding 058 left six cases the whole independent field rejects, saw that four of them involved an ISO week crossing the year boundary, and refused to adjudicate because the disagreement ran in **both directions**. It is one mechanism seen from two sides. §3.3.10 says `BYWEEKNO` selects "weeks of the year" and that **a week is a seven-day period**, but never says which yearly *period* the days of a straddling week belong to — the calendar year they sit in, or the year that owns the week. The corpus takes the first, and so its week *number* is resolved against the owning year while its period *index* is the calendar year; that hybrid misattributes days in whichever direction the straddle runs. The readings are **identical** at `INTERVAL=1` without `BYSETPOS`, which is why this survived 58 findings. `INTERVAL=2` separates them and the calendar reading breaks: `FREQ=YEARLY;INTERVAL=2;BYWEEKNO=1;BYDAY=MO` fires **twice inside 2024 and not at all for 2026**. Recorded as a new reading `week_based_year`, and — because on two cases neither half alone reproduces the field — composed with finding 024's rewrite as `week_based_year+dtstart_fill`. `ical4j`'s plain failures fall 187→183, `dmfs` 6→4, `libical` master 8→6, with **zero** regressions, and 058's universal residual falls from six to two. `expect` is unchanged: the RFC still does not say](findings/059-which-year-owns-a-straddling-week.md).
- [058 — what the whole field rejects: six cases, one rule part. The corpus had never been asked the one question that could indict it — *which cases does the entire independent field disagree with me about?* — because residuals are reported as counts and counts cannot be intersected. Comparing **membership** instead, the four independent non-`dateutil` lineages (`libical`, `ical4j`, `dmfs`, `sabre`) jointly reject exactly **6 of the 1728** scored cases, and every one carries `BYWEEKNO` — which was an output, not a filter. On **four of the six, two independent lineages agree byte-for-byte** on an occurrence list the corpus records nowhere, which is this project's own standard for a reading rather than a bug, so the corpus is presenting a contested answer as settled. The count is an upper bound by construction: `dtical` is excluded because its residual is irreproducible, and adding a lineage can only shrink an intersection. The common shape is week numbers whose ISO week straddles the year boundary; the finding names that shape and deliberately does not adjudicate it, because the disagreement runs in both directions](findings/058-what-the-whole-field-rejects.md).
- [057 — a horizon the corpus keeps on one side only. `score.py` gains a bucket for an answer that is a non-empty **proper prefix** of the corpus's answer or of a recorded rival reading: it agreed for its whole length and then stopped, which is a window rather than a disagreement. Rescoring every published row against it moved exactly two, by exactly the 7 cases finding 056 predicted, and every other row reproduced cell for cell; a prefix of `expect` itself is zero everywhere, now measured rather than assumed. The 7 turn out to be **the same 7 cases** on `ical4j` and on `dmfs lib-recur`, in all three JVM locales — two unrelated libraries failing identically is evidence about the harness — and the cause is that the corpus applies its declared `horizon_days` to every `expect` list and to only 99 of its 120 alternative readings. Those 21 over-horizon alternatives are the exact bound on the artifact. Neither widening the adapters nor clipping the alternatives is right: clipping would simply move the artifact onto `libical`, whose adapter has no window and matches these lists in full](findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md).
- [056 — two scopes for one word: Category F, the last of finding 051's six blocks, and the end of that page's unexplained residue. `ical4j`'s `BY` pipeline is reimplemented for `FREQ=YEARLY` from the 4.3.0 sources alone and reproduces 4.1.1 and 4.3.0 byte-for-byte on **all 305** in-scope cases. At `YEARLY`, `ByMonthDayRule` expands within the enclosing **month** of the date it is handed while `ByYearDayRule` expands within the enclosing **year** — both labelled `Expand` in the table the source quotes — so no reading of §3.3.10 makes both right, and a rule carrying both parts returns dates that satisfy neither. That is 10 of the 16; one more is 051's duplicate-instant defect reaching the output through `BYSETPOS`; the last 5 are not a defect at all but the `dtstart_fill` reading truncated by my own adapter window, which `score.py` can only report as a mismatch. Measured across all eight adapters, that scoring artifact is exactly 7 cases of `ical4j` and 7 of `dmfs` and nothing else. With F accounted for, every one of `ical4j` 4.3.0's residual plain failures has a named account — 106 of them today rather than 051's 114, because finding 053 moved eight to a rival reading](findings/056-two-scopes-for-one-word.md).
- [055 — a question with no answer: two ways to invent an occurrence. When `BYSETPOS` asks for the nth member of a set that has fewer than n members, the correct result is the empty set. `rrule.js` clamps an out-of-range *negative* `BYSETPOS` to the first element of the set — diverging from `dateutil` upstream and `rust-rrule` downstream, so the lineage that the one-lineage rule collapses into one vote does not agree with itself here. `libical` master returns a date roughly 958 years out, and the source shows why: exhausting `ICAL_LIMIT_RECURRENCE_SEARCH` is not one of the paths that returns a null time, so the loop falls through and hands back wherever the search ran out of budget. Lowering the budget moves the date linearly](findings/055-a-question-with-no-answer.md).
- [054 — one mechanism, twenty-seven failures. Finding 051 filed 27 of `ical4j`'s residual failures under "looks like 037" and said so. A 40-line reimplementation of 037's mechanism and nothing else reproduces `ical4j` 4.1.1 and 4.3.0 byte-for-byte on **all 362** in-scope `FREQ=WEEKLY` corpus cases — the 335 it gets right as well as the 27 it gets wrong — and the 27 it gets wrong are exactly Category C. So the block is one mechanism counted 27 times, and no second `WEEKLY` defect is hiding in this corpus. The mechanism is finding 022's `seed-limit` reading, generalised to an arbitrary `WKST`; 022's own independent implementation agrees with the predictor and with `ical4j` on all 314 `WKST=MO` cases. The 27 split exhaustively into three consequences once `BYSETPOS`-selecting-from-a-contaminated-set is added to 037's two](findings/054-one-mechanism-twenty-seven-failures.md).
- [051 — what is left after the negative-limit fix: the 114 residual `ical4j` failures, attributed. Every case 4.3.0 fixed is findings 049/050; of what remains, 29 are a pipeline that never removes a repeated instant (`BYMONTHDAY=31,-1` yields month end twice) and 15 are an ordinal `BYDAY` that can never match in its limiting role, both unchanged since 4.1.1](findings/051-what-is-left-after-the-negative-limit-fix.md).
- [053 — a short list is not always my horizon. The corpus refused to record the rival `dtstart_fill` reading whenever it yielded fewer occurrences than `expect`, on the stated grounds that only my own 30-year window could shorten a list — false on the sparse `FREQ=YEARLY` shapes, where `ical4j` and `dmfs` return the short list with no horizon at all. A `FREQ=YEARLY` rule's calendar repeats exactly every 400 Gregorian years, so the two meanings of a short list are decidable rather than a matter of choosing a bigger number. 87 corpus cases gain the alternative, 29 of them scored, and two independent lineages reproduce it instant for instant](findings/053-a-short-list-is-not-always-my-horizon.md).

- [052 — the `BYWEEKNO` column of the corpus is one lineage deep. On the 42 scored cases with `BYWEEKNO` and no `BYDAY`, `expect` is matched by the `dateutil` lineage and by nothing else; `dmfs` matches 16, `libical`, `ical4j`, `dtical` and `sabre` match none. It is finding 024's `dtstart_fill` split, under-recorded by my own builder: one rewrite returned before applying the second fill (fixed here), and a length guard suppresses the alternative on sparse rules (fixed in 053)](findings/052-byweekno-is-one-lineage-deep.md).
- [049 — a negative day that only counts when it expands: 65 of `ical4j`'s 176 locale-corrected failures are one bug in the limit path, fixed in 4.3.0; the `BYYEARDAY` twin is still open in the current release, and the corpus was blind to it because cell coverage is not value coverage](findings/049-a-negative-day-that-only-counts-when-it-expands.md).
- [050 — one cell of the table, four ways to get it wrong: negative `BYMONTHDAY`/`BYYEARDAY` in their *limiting* role is got wrong by four of the six independent lineages, each differently — silence, a thrown guard, a dropped constraint, a promoted period — and the corpus could not see it because cell coverage is not value coverage](findings/050-one-cell-of-the-table-four-ways-to-get-it-wrong.md).
- [048 — the last unswept column is ambient-invariant, and its five apparent differences were my own deadline](findings/048-the-last-unswept-column-is-ambient-invariant.md).
  The 291 `BYSETPOS` cases of `DateTime::Event::ICal` were the only part of the
  scored corpus never checked against the host's zone and locale. They do not
  move. The five cases that looked like they did were the 20-second deadline
  being crossed in both directions under parallel load.
- [047 — the 146 unmeasured `DateTime::Event::ICal` cases are four different failures, and a crash can hide behind a short horizon](findings/047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md).
  `subject_error` was one bucket holding a deadline I chose, a declared
  limitation, and a `die` on the sixth retry. Three of the crashes pass their
  corpus case and appear only at a longer horizon.
- [046 — the three unexplained rows of finding 045 are not a `BYSETPOS` bug: `DateTime::Set`'s iterator and its `next` disagree](findings/046-the-iterator-and-the-next-chain-disagree.md).
  One set object, two documented traversals, two different answers, on 68 of
  the corpus's 291 `BYSETPOS` cases. Part of the published `dtical` column is a
  fact about how I chose to enumerate, not about anyone's reading of RFC 5545.
- [045 — at sub-daily `FREQ`, `DateTime::Event::ICal` expands one larger unit and then leaves](findings/045-sub-daily-expansion-is-confined-to-one-larger-unit.md).
  The last unmeasured horizon bound. 56 hidden cases, no early stops, and 53 of
  them are a single structural bug: a `BY*` part coarser than the frequency
  advances the outer period instead of filtering.
- [044 — the last two rows of finding 042, and they are two different bugs](findings/044-what-bysetpos-selects-from-at-freq-yearly.md).
  At `FREQ=YEARLY`, `sabre/vobject` applies `BYSETPOS` only on the `BYMONTH`
  path, and there to one month's set rather than the year's (reported upstream
  as sabre-io/vobject #730); on the `BYYEARDAY` and `BYWEEKNO` paths it is
  dropped entirely. Separately, `FREQ=YEARLY;INTERVAL=4;BYMONTH=2` from a
  February 29 `DTSTART` overflows at 2100 to March 1 and emits February **1**
  forever after — the same rule without the redundant `BYMONTH` is correct.
  Finding 042's hidden-case table is now fully attributed.
- [043 — `FREQ=HOURLY` ignores every `BY*` part, by a 2012 decision](findings/043-freq-hourly-ignores-every-by-part.md).
  `sabre/vobject`'s `nextHourly()` is four lines and applies no filter at all,
  so all eight `BY*` parts §3.3.10 defines for the `HOURLY` column are parsed
  and dropped. 40 of the corpus's 58 `HOURLY`+`BY*` cases diverge from the
  control. The omission is a deliberate 2012 decision recorded in the tracker,
  made on advice about redundant `BYx`/`FREQ=x` pairings that does not reach
  most of the column.
- [042 — what the fourth lineage hides past occurrence eight](findings/042-what-the-fourth-lineage-hides-past-occurrence-eight.md).
  `sabre/vobject` now runs under the horizon sweep. 135 cases that score as
  passes emit a date the two-lineage control does not by occurrence 64 — a ~17%
  undercount on its row — and **none** of its hidden rows are early stops,
  unlike both Java implementations. 45 of the 135 are a `BYMONTH` omission at
  `FREQ=DAILY` that finding 031's per-method source count could not see: all
  three `byMonth` references in `nextDaily()` sit after an early `return` taken
  whenever neither `BYDAY` nor `BYHOUR` is present.
- [041 — a duplicate instant, and what a floating `DTSTART` is owed](findings/041-a-duplicate-instant-in-a-floating-recurrence.md).
  Adjudicates the three cases finding 040 left open. Under a DST-observing
  `TZ`, `rust-rrule` 0.14.0 expands an hourly rule across US spring-forward by
  dropping 02:30 and returning the *same absolute instant* twice (checked with
  offsets, so it is not a formatting artifact). Wrong both as floating time
  (§3.3.5 FORM #1) and, granting the crate's zone substitution, as zoned time.
  `rrule.js`, its upstream, is unaffected.
- [040 — how much a short horizon hides](findings/040-how-much-a-short-horizon-hides.md).
  Standing rule 33b says every published count is a lower bound; this measures
  the gap. Re-running the 1721 scored cases at horizons up to 128 occurrences,
  68 further `ical4j` cases that score as passes emit a date the two-lineage
  control does not — a 48% undercount on that row — while `dmfs lib-recur`'s
  13 turns out not to be a lower bound at all. It also corrects
  [038](findings/038-checking-the-instrument-for-what-it-measured.md):
  `rust-rrule` resolves floating times through the machine's `TZ` and moves on
  three cases under a DST-observing zone, which the ambient sweep could not see
  because neither of its zones observed DST and it ran at the corpus horizon.

- [039 — what `BYSETPOS` selects from](findings/039-what-bysetpos-selects-from.md).
  The scope question finding 037 left open. Of the 39 corpus cases combining
  `FREQ=WEEKLY`, `BYMONTH` and `BYSETPOS`, `ical4j` differs from the control on
  14 — exactly the same 14 it gets wrong with `BYSETPOS` removed. `BYSETPOS`
  neither creates nor masks the defect; it selects from the wrong week set, so
  in four cases it returns the out-of-month date *in preference to* the correct
  one, with the output keeping the shape a correct answer would have had. Only 8
  of the 14 are scored failures; the rest diverge past the corpus's own horizon.

- [038 — checking the instrument for the defect it had just measured](findings/038-checking-the-instrument-for-what-it-measured.md).
  All eight adapters run over the scored corpus in three environments that move
  the time zone, the locale's first day of the week and the locale's digit
  shapes. `ical4j` is the only one whose answers move, and it moves as finding
  036 says it does. The sweep's real catch was in the instrument: the
  `dmfs lib-recur` adapter formatted dates with a `String.format` that had no
  `Locale`, so on an Arabic-locale machine it would have emitted Arabic-Indic
  digits and scored **0 of 1721** — a harness carrying a weaker form of the
  defect it had just published about someone else. Now `conformance/ambient_sweep.py`.

- [037 — a limit that runs before the thing it limits](findings/037-a-limit-that-runs-before-the-thing-it-limits.md).
  At `FREQ=WEEKLY`, `ical4j` 4.1.1 and 4.3.0 apply the `BYMONTH` **limit** to
  the period seed — one date, always on `DTSTART`'s weekday — and then let
  `BYDAY` expand that seed across the whole `WKST` week, with no month check
  afterwards. So `FREQ=WEEKLY;BYMONTH=2;BYDAY=FR,TH,WE` returns `20240301`:
  a March date from a February-only rule. Of 161 corroborated cases in this
  shape the two readings disagree on **60**, and `ical4j` follows the
  seed-limited one on **60 of 60** and the correct one on **0 of 60**; the
  correct reading reproduces the corroborated expectation **161 of 161**.
  42 of the 60 have an unsynchronized `DTSTART`, where §3.8.5.3 makes the set
  undefined, and are not claimed; the **18** that remain are all in the scored
  set, and over a common horizon every one of them both omits required
  occurrences and emits spurious out-of-month ones.
- [036 — a conformance score that depends on the host machine's
  locale](findings/036-a-score-that-depends-on-the-host-locale.md).
  `ical4j` 4.1.1 and 4.3.0 read the first day of the week from
  `Locale.getDefault()` when an `RRULE` omits `WKST`, instead of RFC 5545's
  `MO`. The same build scores **1408 / 1420 / 1435** on this corpus on a
  Saturday-, Sunday- and Monday-first host. All 20 affected cases have a
  synchronized `DTSTART`, so §3.8.5.3's "undefined" escape — the grounds on
  which [ical4j #727](https://github.com/ical4j/ical4j/issues/727) was closed
  in 2024 — does not cover them. Appending `;WKST=MO` fixes 20 of 20; the
  control fixes 0 of 20. The same path also explains why
  `FREQ=YEARLY;BYMONTH=1,8;BYWEEKNO=20,52` emits May dates, with duplicates.
- [035 — one deletion explains every `WEEKLY`+`BYMONTH` failure in a 2003
  expander](findings/035-one-deletion-and-a-pinned-day.md).
  [Finding 031](findings/031-one-cluster-three-causes.md) left one of its three
  causes named but uncharacterised: `DateTime::Event::ICal` 0.13 passes **0 of
  244**. It reads `BYMONTH` at `FREQ=WEEKLY` and `FREQ=MONTHLY` as *month ∈
  `BYMONTH` **and** day-of-month = `DTSTART`'s day*. That model reproduces its
  output on **155 of 158** `WEEKLY` cases and **117 of 118** `MONTHLY` cases,
  where the correct reading reproduces **0** of the `WEEKLY` ones. The cause is
  one line: `recur()` builds the `BYMONTH` filter out of a hash the frequency
  handler has already deleted `byday` from, so the `[ 1 .. 31 ]` default that
  would make it a whole-month filter never fires and the day set falls back to
  `$dtstart->day`. `FREQ=DAILY` carries the workaround explicitly, which is why
  it is correct. Supplying the missing default from the caller — three lines,
  no change to the library — takes the `WEEKLY` set from **0 of 205** to **205
  of 205** with no errors, and stops **47 of 56** crashes. The defect is also
  in the `MONTHLY` path, masked on exactly the cases that have no `BYDAY`.

- [034 — the table arrived in 2007 as a summary, and the sentence it
  contradicts was never touched](findings/034-when-the-table-arrived.md). The
  project's headline open question was whether §3.3.10 can settle
  [finding 024](findings/024-dtstart-fill-versus-the-table.md)'s split. It
  cannot, and the drafting history says why. Both texts were traced through all
  thirteen documents in the line — RFC 2445, the eleven
  `draft-ietf-calsify-rfc2445bis` drafts, and RFC 5545. The `DTSTART`-fill
  sentence has **two** wordings in eleven years, differing by two serial commas.
  The table appears in exactly one edit, draft-07 of July 2007, whose change log
  calls it *"Issue 11: Added a table that shows the dependency…"* and whose own
  prose says it *summarizes* the section. It went in on the page before the
  sentence it contradicts, and neither text was edited then or in the three
  drafts that followed. Notes 1 and 2 arrived in the same edit, and Note 2
  resolves precisely this collision for `BYDAY` — so the two unresolved cells
  look like an omission, not a decision. The five `undecided` cases stay
  undecided.

- [033 — the last five disputes are two questions, and finding 008 answered only
  one](findings/033-the-last-five-disputes-are-two-questions.md). The five
  `FREQ=YEARLY`+`BYWEEKNO` cases left in `disputed.json` looked settled: finding
  008 showed python-dateutil with PR #1537 applied agrees with `naive.py` on all
  five. It is not evidence enough. Those cases turn on a second, orthogonal
  question — `BYWEEKNO` expands a year to *weeks*, and with no `BYDAY` present
  something must supply the day-of-week. Both adjudicators expand the week to
  all seven days; `libical`, `dmfs lib-recur` and `ical4j` — three independent
  lineages, byte-identical to each other — fill it from `DTSTART`. That is
  [finding 024](findings/024-dtstart-fill-versus-the-table.md)'s unadjudicated
  rewrite rule reappearing at `BYWEEKNO`, so agreement between `naive` and
  patched dateutil is agreement *within one reading*. Two of the five are worse:
  `BYWEEKNO`+`BYYEARDAY` draws **five different answers** from eight
  implementations, including `UNIMPLEMENTED` from `libical` and an empty
  recurrence set from `dmfs`. All five adjudicated **undecided**, with reasons.

- [032 — a question the corpus cannot
  ask](findings/032-a-blind-spot-the-corpus-cannot-see.md). Finding 031 asked
  for corpus cases that discriminate first-period truncation at `FREQ=WEEKLY`.
  They cannot exist. A case admits to the corpus when `naive.py` and
  python-dateutil agree, and those two take opposite sides of that exact
  question: over 800 sampled rules a case discriminates the reading **if and
  only if** the adjudicators disagree, **zero** off-diagonal. RFC 5545 §3.3.10
  settles it — "A set of recurrence instances starts at the beginning of the
  interval defined by the FREQ rule part", three sentences with no counterpart
  in RFC 2445 — and the ten such cases in `disputed.json` are now adjudicated
  to it. Across eight implementations the untruncated reading is held by **two
  independent lineages** and the truncated one by **one lineage in three
  incarnations**, python-dateutil and its two ports. The general point: two-
  expander corroboration is silently blind to whatever the two expanders
  disagree about.

- [031 — the largest `FREQ=WEEKLY` cluster is three unrelated causes, not
  one](findings/031-one-cluster-three-causes.md). The 244 cases with
  `FREQ=WEEKLY`+`BYMONTH` that every lineage looked weak on are not a contested
  reading. `sabre/vobject` ignores `BYMONTH` entirely at `WEEKLY` and
  `MONTHLY` — one rewrite reproduces all **244 of 244**, and `nextWeekly()` and
  `nextMonthly()` contain **zero** references to the field; `DateTime::Event::ICal`
  fails the same cluster for an unrelated reason the rewrite explains **0** of;
  and three lineages, `python-dateutil`, `dmfs lib-recur` and current `libical`
  master, pass every one of the 244. The useful part is
  about the corpus itself: **0** of the 244 cases discriminate first-period
  truncation and only **7** discriminate the `BYSETPOS`/`BYMONTH` ordering.
  *(That **7** is **18** on today's corpus, and the two `BYSETPOS`-first rows of
  031's model table are stale — corrected by
  [092](findings/092-a-reproduce-command-expires.md). The script was right and
  `5d6745e` moved the corpus under it; the truncation row, which is the
  load-bearing one, did not move, and the drift makes the corpus **less** blind
  than published, not more.)*

- [030 — a fifth lineage, and the first one that writes the DTSTART fill
  down](findings/030-a-fifth-lineage-that-writes-the-fill-down.md).
  `DateTime::Event::ICal` 0.13 (Perl, Flavio Soibelmann Glock, 2003) scores
  **1179 of 1728** with **0** guaranteed invariant violations and **0**
  order-dependent mismatches, and takes the `dtstart_fill` reading on **51** of
  the 65 contested cases. Unlike the three lineages that were *observed* to
  agree with that reading, this one states it: `_yearly_recurrence` fills
  `BYDAY` from `DTSTART`'s weekday when `BYWEEKNO` has none, and `BYMONTH` from
  `DTSTART`'s month when nothing else selects one — the two rewrites of
  [finding 024](findings/024-dtstart-fill-versus-the-table.md), in source, from
  an implementer reading RFC 2445 §4.3.10 in 2003. Evidence about how the text
  reads to an implementer, not about what it means. Its 386 mismatches are
  concentrated in `FREQ=WEEKLY` with `BYMONTH` (179, all of them), and 27 of
  its 108 errors are `BYSETPOS` rules that do not terminate.

- [029 — the fourth independent lineage, and a loop that does not
  end](findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md).
  `sabre/vobject` 4.6.1 — hand-written PHP, no ancestry claimed, and the
  expander inside Nextcloud, ownCloud and Baïkal — scores **833 of 1728**, the
  lowest here, with **414** guaranteed-invariant violations against 0 or 1 for
  every other row. Four `FREQ=YEARLY;BYYEARDAY` rules with a `BYDAY` **loop
  forever**: `$dayMap` numbers Sunday 0 (PHP's `w`) while the `BYYEARDAY`
  branch compares against ISO-8601 `format('N')`, where Sunday is 7, so
  `BYDAY=SU` matches no date in any year and the year search has no ceiling.
  The same off-by-one is silent under `BYWEEKNO`, which returns the Sunday of
  the week *before* the selected one. Because those are the branches the
  §3.3.10 dispute turns on, a fourth lineage arrives and the count that can
  arbitrate stays at three.

- [028 — two ports agree exactly with their parent; the third does not](findings/028-two-ports-agree-and-the-third-does-not.md).
  `fmeringdal/rust-rrule` 0.14.0 scores **1728 of 1728** and diverges from
  `python-dateutil` on **0** of 3820 corroborated cases — as `rrule-go` does.
  (`rust-rrule` still does at 25 occurrences; `rrule-go` does not —
  [066](findings/066-the-ports-were-not-identical.md).)
  Its README credits `rrule.js` as an inspiration alongside dateutil, yet it
  picked up **none** of `rrule.js`'s 122 divergences from that same parent. With
  two independently written ports reproducing dateutil to the case, `rrule.js`
  is the outlier and those 122 are its own behaviour, not inherited subtlety.
  Adds no lineage vote. Also records 29 failures that turned out to be the
  adapter's own normalisation rather than the library's behaviour.

- [027 — a port that did not drift, and a request that was wrong](findings/027-a-port-that-did-not-drift.md).
  `teambition/rrule-go` 1.8.2 scores **1728 of 1728** — the first implementation
  other than the corroborating expander to pass the whole subset — and returns
  `python-dateutil`'s exact answer on all **3820** corroborated cases, including
  the 2092 the conformance subset discards. It is a dateutil port by its own
  README, so it adds no lineage vote, and this project's standing request for
  "a result from Go, Rust, C# or Swift" was asking for the wrong thing: language
  is not lineage. The same comparison sizes `rrule.js`'s divergence from the
  same parent at 122 of the 3813 then corroborated and decomposes all of it — 67 non-ascending lists
  (finding 015's mechanism, and the RFC does not require chronological order),
  55 `BYSETPOS` (findings 004/018/021).
- [026 — converting `UNTIL` through JSCalendar loses an hour, and can drop an
  instance](findings/026-until-roundtrip-repeated-hour.md). `draft-ietf-calext-jscalendar-icalendar-26`,
  **in WG Last Call**, converts `UNTIL` to a JSCalendar `LocalDateTime` in the
  event's zone. With a TZID-form `DTSTART`, RFC 5545 requires `UNTIL` to be a UTC
  *instant*, and in the repeated hour at the end of daylight saving two instants
  share one wall-clock label. RFC 5545 §3.3.5 and `jscalendarbis` §1.5.5 both resolve
  that label to the *first* occurrence, so the round trip deterministically moves
  `UNTIL` one hour earlier and can silently shorten the recurrence set. Worked
  `Europe/Berlin` example: two instances become one. The draft's §1.4 treats
  losslessness purely as element coverage, so this is invisible to it.

- [025 — §3.3.10 contradicts itself about nonexistent local times, and a Verified
  errata decides it](findings/025-nonexistent-local-time-errata.md). §3.3.10 says
  an instance at a nonexistent local time `MUST be ignored`, and 110 lines later
  says it is localized per §3.3.5 — shifted forward through the gap and kept.
  **Errata ID 4271, status Verified**, splits the paragraph: an invalid date like
  30 February is still dropped, a gap local time is shifted and *counted*. So the
  two now differ in `COUNT`. This corrects [finding 006](findings/006-dst-gap-and-repeat-instances.md),
  whose conclusion was right but which quoted only one of the two sentences and
  called the question settled.

- [024 — the lineage split is one rewrite rule, and §3.3.10 contains both
  readings](findings/024-dtstart-fill-versus-the-table.md). Why `libical`,
  `ical4j` and `dmfs lib-recur` disagree with this corpus on `FREQ=YEARLY`:
  §3.3.10's table says `BYMONTHDAY` expands, and §3.3.10's DTSTART-fill sentence
  says the missing month comes from `DTSTART`. Both apply; the section never says
  which wins. Filling the unspecified field from `DTSTART` reproduces all **56**
  three-way-identical disagreements exactly — 41 `BYMONTHDAY`, and 15 `BYWEEKNO`
  that finding 017 had missed. It is exactly the two `YEARLY` cells where the
  table is the only authority; `BYDAY`, which Note 2 covers in prose, is not
  split. RFC 2445, which the three oldest implementations were written against,
  had no table at all. No erratum against §3.3.10 addresses the precedence.
  The corpus now records this as a named alternative reading, `dtstart_fill`,
  and [`conformance/RESULTS.md`](conformance/RESULTS.md) scores a match as
  `fail_other_reading`: `ical4j`'s plain failures fall 260 → 187, `libical`
  master's 79 → 8, `dmfs lib-recur`'s 76 → 6. No pass count moved. *(024's
  reproduce command was found in [092](findings/092-a-reproduce-command-expires.md)
  to pass vacuously — it read stale files out of `/tmp` and reported success over
  nothing. Fixed to refuse. The figures here are **not** re-verified: the command
  needs `libical`, which no longer builds in this environment.)* (Each
  left-hand figure is that row's `fail` + `other reading`; both sides grew with
  the corpus, and the right-hand ones moved again with
  [finding 053](findings/053-a-short-list-is-not-always-my-horizon.md) and with
  [finding 057](findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md),
  which took 7 cases off each Java row into a new prefix bucket.)

- [023 — the two footnotes under §3.3.10's table, as a shipped
  bug](findings/023-byday-limit-footnotes.md). A calendar user reports that a
  Friday-the-13th rule fires every Friday. All six implementations here get it
  right **on a plain weekday** — put an ordinal on it and `ical4j` returns
  nothing, which is
  [finding 051](findings/051-what-is-left-after-the-negative-limit-fix.md) — so
  there is nothing to report upstream from this case: the footnotes that turn
  `BYDAY` from an expanding part into a limiting one are missed by people
  writing an expander from the table, not by the libraries that already did.
  The debugger now says the intersection out loud, checked over the corpus.
  Turned up a stale claim in the debugger and this README — the `FREQ=YEARLY`
  reading split has three independent lineages on the other side, not two.

- [022 — what "the current set of evaluated occurrences" is, for `FREQ=WEEKLY`
  with `BYMONTH`](findings/022-weekly-bymonth-ordering.md). Six implementations
  measured and two readings stated mechanically, in response to the discussion
  on the libical Issue that finding 019 opened. Not a defect claim.

- [021 — the `BYSETPOS` first-interval question is answered in RFC 5545, by a
  sentence with a missing full stop](findings/021-bysetpos-first-interval-resolved.md).
  I spent several days treating "does `BYSETPOS` index the whole first interval
  or only the part from `DTSTART`?" as an open interpretive question, and tried
  to settle it by comparing implementations. §3.3.10 answers it outright — the
  set "starts at the beginning of the interval defined by the FREQ rule part" —
  and the calsify draft history shows the working group added that sentence
  deliberately under Issue 81 in `draft-08` (2008). The same edit dropped the
  full stop before it, so in the published RFC the deciding sentence runs on from
  a WEEKLY example and reads like an aside. This closes the open question in 004
  and the hole in 020.

- [020 — whether `DTSTART` is synchronized is itself reading-dependent](findings/020-synchronization-is-reading-dependent.md).
  A mechanical audit of every example in the finding set. Four flagged examples
  were already handled, one document was missing its caveat, and the remaining
  case showed that the synchronization test I use to validate examples is not
  reading-neutral when `BYSETPOS` is present.

- [019 — libical loses occurrences in the week that straddles a `BYMONTH`
  boundary](findings/019-libical-weekly-bymonth-bysetpos.md). Eight cases in
  libical master `48d52b4`, every `FREQ=WEEKLY` failure it has, outside the
  known-issue set its own tracker documents. `BYSETPOS` indexes the set
  *before* `BYMONTH` limits it, and the straddling week is skipped outright
  when iteration arrives after a gap of unselected months. Unreported and
  unauthorized to report.
- [018 — 54 corroborated cases are committed to a contested reading,
  unmarked](findings/018-reading-dependence-of-the-corpus.md). A defect in this
  corpus's labelling. `disputed.json` records where two implementations
  disagree, which is not the same as where the answer is contested; 54
  corroborated `BYSETPOS` cases would change answer under the other reading of
  finding 004 and say nothing about it. Retracts the closing claim of finding
  017, which had dismissed libical's eight surviving failures as finding 004's
  reading on the strength of a probe that dropped the `BYMONTH` making them
  reading-independent.
- [017 — libical, a third lineage and the oldest](findings/017-libical-third-lineage.md).
  `icalrecur.c` predates dateutil's `rrule`; 3.0.20 scores 1517/1728 and master
  1599. 41 cases where libical, ical4j and lib-recur all fail *identically*,
  every one `FREQ=YEARLY` with `BYMONTHDAY`. Both of those closing claims were
  wrong: see finding 018 for the dismissal it should not have made, and finding
  024 for the count, which is 56 rather than 41.
- [016 — the first results from implementations that are not `python-dateutil`](findings/016-independent-lineage-results.md).
  ical4j 4.1.1 and dmfs lib-recur 0.17.1, neither descended from dateutil,
  **agree with each other and disagree with the dateutil lineage** on
  `FREQ=YEARLY;BYMONTHDAY=15` and `FREQ=YEARLY;BYWEEKNO=20` — one occurrence per
  year against §3.3.10's Expand. lib-recur also refused a corpus case that
  really is invalid (`UNTIL` a DATE under a DATE-TIME `DTSTART`), a defect three
  other implementations accepted silently. Includes the 31 violations
  `invariants.py`'s first version would have published against ical4j and did
  not, because they turn on the disputed reading rather than on the RFC text.

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
  Not a defect report. A computed instance at a nonexistent or twice-occurring
  local time is interpreted under §3.3.5 — per one sentence of §3.3.10 and, after
  [finding 025](findings/025-nonexistent-local-time-errata.md), per Verified
  errata 4271 rather than the body text, which contradicts itself here; 30
  assertions across four zones confirm both expanders do that. Records two counterintuitive but
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

- [012 — two coverage models at 100%, and an interaction model at 54%](findings/012-branch-pair-coverage.md).
  Both single-branch models had saturated, and a saturated presence measure has
  stopped measuring. The bugs this corpus has caught were *interactions*:
  `BYSETPOS` **under** `WEEKLY`, `BYWEEKNO` **at** a year boundary. So the
  third model is the pair: of the C(79,2) = **3081** branch pairs, **2751 are
  realizable** — each demonstrated by a rule the ABNF parses, `validity.py`
  accepts, and the classifier confirms takes both — and the other 330 are
  refused with a recorded reason (`no-common-freq`, `arity-conflict`,
  `invalid:count-until-exclusive`, …). The corpus covered **1485 of 2751**.
  Building the denominator found two bugs of my own: a greedy host frequency
  that invented 70 false gaps, and a list-varying step that turned
  `BYDAY=SU,MO` into `BYDAY=SU,TU` and hid all 21 two-weekday pairs.
  **2751/2751** now.
- [013 — `BYDAY=+2SU,MO` expands to nothing](findings/013-byday-mixed-signed-and-unsigned.md).
  The first thing the pair model asked for that the corpus had never held: a
  `BYDAY` list mixing a signed element with an unsigned one. `python-dateutil`
  2.9.0 returns **no occurrences at all**; `2SU,SU` silently drops the
  unsigned `SU`. §3.3.10's own example `BYDAY=1SU,-1SU` → "the first *and* the
  last Sunday" makes the list a union, and `dateutil`'s `BYMONTHDAY` handling —
  three lines below in the same condition — unions signed and unsigned
  correctly. Only `BYDAY` intersects them. `rrule.js` inherits it, and it has
  been reported *there* since 2014
  ([jkbrzt/rrule#71](https://github.com/jkbrzt/rrule/issues/71), still open,
  zero comments) but seemingly never against `dateutil`. Six cases adjudicated.
- [014 — seven properties instead of expected
  values](findings/014-metamorphic-properties.md). Every case in this corpus
  is an expected value you have to trust me for, describing one eight-occurrence
  window. A *property* is a relation between the outputs of two rules
  (`COUNT=n` is the first n of the unbounded rule; dropping a `Limit` part
  cannot lose occurrences; `WKST` is inert outside the two situations
  §3.3.10 names), so it needs no expected value from anyone and costs nothing
  to run over years. Seven of them, each carrying the RFC sentence it derives
  from and a test that re-reads the pinned bytes to confirm the quote is real.
  Run over all 1,722 synchronized rules they caught **a defect in my own
  expander** — `naive` folded `UNTIL`, and separately the caller's horizon,
  into the candidate stream, truncating the last period *before* `BYSETPOS`
  selected from it, which §3.3.10 forbids in as many words ("BYSETPOS; then
  COUNT and UNTIL are evaluated"). That is finding 004's first-period
  truncation, at the other end, in my code. They also produced two documented
  counterexamples to readings the RFC invites: `WKST` **is** significant for
  `FREQ=WEEKLY;INTERVAL=1` when `BYSETPOS` is present, a third situation the
  RFC's list does not name, and a `Limit` part can *add* occurrences when
  `BYSETPOS` follows it. Both hold identically in both expanders.
- [015 — a language-neutral harness, and the first implementation run through
  it](findings/015-conformance-harness-and-rrulejs.md). Writing the corpus
  schema down for a stranger exposed a defect in the schema: the per-case
  `truncated` flag recorded only the 8-occurrence cap and not the 30-year
  horizon, so its false branch read as "this is the whole recurrence set" and
  was wrong for **67 cases**, every one of which continues past the horizon
  under an unbounded expansion. A consumer trusting it would have generated 67
  false failures against every implementation it tested. Replaced by
  `expect_bound` (`complete`/`count`/`horizon`), decided from the rule text
  rather than from an expander — and its own first version was wrong too, in a
  way its own check caught. With the schema honest, `conformance/` scores any
  implementation over a documented NDJSON protocol: `rrule.js` 2.8.1 passes
  **1696 of 1722**, and the 26 failures fall into three clusters, one of which
  is already open upstream and one of which I have deliberately not
  adjudicated.

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
src/pairs.py         realizable *pairs* of grammar branches, and a rule for each
src/datevalue.py     RFC 5545's rules for a DATE-valued DTSTART
src/datevalue_cases.py  systematic DATE cases + what implementations do
src/build_corpus.py  runs the differential and writes the corpus
src/properties.py    seven metamorphic properties, each quoting its RFC sentence
src/expanders.py     one bounded interface both expanders are asked through
src/run_properties.py  every property over every synchronized corpus rule
src/longrun.py       three-year differential, far past the corpus window
src/env.py           where the RFC text, dateutil and rrule.js come from
tools/bootstrap.sh   provisions all three into vendor/ and js/
tools/run_tests.py   runs every check; reports skips as skips
tools/verify_corpus.py  rebuilds the corpus and compares it byte-for-byte
corpus/              corroborated.json, disputed.json, adjudications.json,
                     coverage.json, grammar-coverage.json,
                     date-value-type.json, pair-coverage.json
findings/            adjudicated divergences, written up
```

## Running it

The corpus itself is plain JSON and needs nothing to read. Re-running the
checks — which is the only way to verify that it says what it claims — needs
three things, and `tools/bootstrap.sh` provisions all of them into `vendor/`
and `js/` (both git-ignored):

```sh
git clone https://github.com/aiterrariumcontrol/rruleref
cd rruleref
./tools/bootstrap.sh        # RFC text (sha256-pinned), dateutil 2.9.0.post0, rrule.js 2.8.1
python3 tools/run_tests.py  # every check, plus what was skipped and why
python3 tools/verify_corpus.py  # rebuild and assert the committed corpus reproduces (slow)
```

| input | why it is pinned | override |
| --- | --- | --- |
| RFC 5545 and RFC 2445 text | every expected value in the corpus traces to these bytes; the digest is re-checked on each use, not trusted by filename | `RFC5545_TXT`, `RFC2445_TXT` |
| `python-dateutil` 2.9.0.post0 | part of the suite records dateutil's *current* behaviour on purpose, so the version is part of the claim | `RRULEREF_PYLIBS` |
| `rrule.js` 2.8.1 | the third witness in the cross-check | `RRULEREF_NODE_DIR` |

`rrule.js` is optional: without it the cross-check is skipped and everything
else runs. Missing inputs produce a message saying how to get them, and
`tools/run_tests.py` prints the state of all three before it runs anything —
a check that silently disappears with its dependency is worse than one that
fails, because the suite still reports success.

Until 2026-09-06 none of this was true: twenty call sites hardcoded absolute
paths under the author's home directory, so the suite ran on exactly one
machine. That contradicted the premise of the repository — a reader is
supposed to be able to re-run the adjudications rather than take my word for
them — and it went unnoticed for as long as it did precisely because the one
machine it ran on was mine.

Individual entry points:

```sh
python3 src/differ.py 7 300      # differential run, seed 7, 300 rules
python3 src/build_corpus.py      # rebuild corpus/ (slow; minutes)
python3 src/build_corpus.py --out DIR  # rebuild somewhere else, for comparison
python3 tests/rfc_examples.py       # known-answer tests, no dependencies
python3 tests/test_tz.py            # RFC 5545 section 3.8.5.3, all 39 worked examples
python3 tests/test_dst_recurrence.py  # instances in a DST gap or repeat, 4 zones
python3 tests/test_vtimezone.py       # RFC 5545 section 3.6.5, all five VTIMEZONE examples
python3 tests/test_byweekno.py        # week numbering at the year boundary (finding 008)
python3 tests/test_coverage.py        # coverage of section 3.3.10's table (finding 009)
python3 tests/test_grammar.py         # coverage of section 3.3.10's ABNF (finding 010)
python3 tests/test_date_value_type.py # DATE-valued DTSTART (finding 011)
python3 tests/test_pairs.py           # pairwise branch coverage (finding 012)
python3 tests/test_byday_mixed.py     # signed + unsigned BYDAY list (finding 013)
python3 tests/test_properties.py      # the seven properties, and that their quotes are real
python3 tests/test_setpos_bounds.py   # a bound must not truncate BYSETPOS's period
python3 src/run_properties.py         # every property over every synchronized rule (~2 min)
python3 src/longrun.py                # three-year differential, past the corpus window
python3 src/coverage.py               # (module) the table, parsed out of the RFC
python3 src/enumerate_cells.py        # print the 57 systematic cases
python3 src/enumerate_branches.py     # print the 79 synthesized branch cases
python3 src/pairs.py                  # realizable/unrealizable pair counts by reason
python3 src/datevalue_cases.py        # rebuild corpus/date-value-type.json
python3 src/byweekno_check.py         # sweep BYWEEKNO x WKST against the RFC's definition
python3 src/vtimezone.py              # print the five extracted components
```

## Honest limits

- **Coverage is stated but thin.** It is stated on two independent axes, both
  of them printed by §3.3.10 itself: all 57 permitted cells of its
  `BYxxx`/`FREQ` table ([finding 009](findings/009-corpus-coverage-of-the-3310-table.md))
  and all 79 branches of its `recur` ABNF
  ([finding 010](findings/010-grammar-branch-coverage.md)), and all 2751
  realizable *pairs* of those branches
  ([finding 012](findings/012-branch-pair-coverage.md)). What is still
  unmeasured: triples and beyond; pairs that cross the two axes (a table cell
  together with a grammar branch); `INTERVAL` appears only as 2 and 3 and
  `COUNT` only as 3, so the pair model covers "`COUNT` is present with a
  negative `BYSETPOS`" and not "`COUNT=1`". The random cases still carry that
  weight, and their coverage of it is unmeasured.
- **DATE-valued `DTSTART` is covered separately and thinly.**
  `corpus/date-value-type.json` has 18 systematic cases and 4 recorded as
  undefined ([finding 011](findings/011-date-valued-dtstart.md)); the main
  corpus is still entirely `DATE-TIME`, because `python-dateutil` — the second
  opinion the main corpus is adjudicated against — has no DATE value type. The
  DATE cases are corroborated one step removed, on the *reduced* rule.
- **The corpus is adjudicated by two expanders, and one of them is mine.**
  `expect` comes from this repository's expander corroborated by
  `python-dateutil`, and per
  [finding 003](findings/003-implementation-lineage.md) most RRULE
  implementations descend from `python-dateutil`, so agreement between them is
  weak evidence about the *specification*. This limit is unchanged.
  What has changed is that four further implementations are now *scored*
  against the corpus rather than used to build it — `rrule.js` 2.8.1, ical4j
  4.1.1, dmfs lib-recur 0.17.1 and libical (3.0.20 and master), see
  [`conformance/RESULTS.md`](conformance/RESULTS.md) and
  [findings 015](findings/015-conformance-harness-and-rrulejs.md)–[017](findings/017-libical-third-lineage.md).
  Three of them are independent lineages. Use them as cross-checks, not as
  adjudication: where they disagree with the corpus it is recorded rather than
  silently adopted, and on 56 `FREQ=YEARLY` cases — `BYMONTHDAY` without
  `BYMONTH`, and `BYWEEKNO` without `BYDAY` — all three independent lineages
  take the other reading, which is a precedence question RFC 5545 §3.3.10 leaves
  open ([finding 024](findings/024-dtstart-fill-versus-the-table.md)).
- **The corpus** is naive-datetime: no timezones, no DST, no `VTIMEZONE`. That
  is a deliberate scope cut so transitions do not contaminate it. Timezone and
  DST behaviour is covered separately and from the spec's own answers, by
  `tests/test_tz.py` and `tests/test_dst_recurrence.py` (findings 005 and 006).
  `VTIMEZONE` — a calendar carrying its own transition rules rather than naming
  an IANA zone — is covered by `tests/test_vtimezone.py` (finding 007), but
  only over the five components the RFC itself prints. No `VTIMEZONE` appears
  in the generated corpus.
- **`UNTIL` and `COUNT` are present but shallow.** 51 and 50 cases
  respectively out of 3,813, and where they meet `BYSETPOS` (4 cases) the
  candidate set has one member and the bound sits exactly on an occurrence —
  which is precisely why a `BYSETPOS` truncation defect survived in
  `src/naive.py` until a property found it
  ([finding 014](findings/014-metamorphic-properties.md)).
- **Every expected value describes an eight-occurrence window.** Agreement
  further out is now checked separately rather than assumed: `src/longrun.py`
  runs both expanders over all 1,722 synchronized rules for three years and
  reports 0 divergences. That is agreement, not correctness, and it is two
  expanders, one of them mine.
