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
build and the same corpus score 1456, 1468 or 1487 depending only on the host —
19 net of the published 195 failures are the locale. Three other lineages agree
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

- [066 — the ports were not identical. Applies 065's decision — the occurrence bound `N` from 8 to 25, `HORIZON_DAYS` from 10958 to 109500 — and re-scores the field. Every number 065 predicted reproduced: **3818** corroborated, **28** disputed, horizon-bounded **352 → 296**, and `verify_corpus.py` rebuilds all five derived files byte-for-byte. The two new disputes are both `FREQ=YEARLY;BYWEEKNO=53`, where `dateutil` emits 2039-01-01 and 2039-01-02 although both are ISO **2038-W52** and neither 2038 nor 2039 has a week 53 at all; adjudicated to `naive` as finding 008's defect reaching one step further, so all 28 disputes now carry a verdict. The result nobody predicted is in the *ports*. Findings 027 and 028 each reported a dateutil port at 1728 of 1728 and concluded that a port teaches nothing; that was true only out to the eighth occurrence. **`rrule-go` 1.8.2 silently truncates every recurrence reaching past 106751.99 days from `DTSTART`** — three corpus cases stop at exactly 105189 days with the next expected occurrence at exactly 107380, and a direct probe returns 106752 daily occurrences and then nothing. That is `math.MaxInt64` nanoseconds: Go's `time.Duration` ceiling, a defect of the host language's time type that `python-dateutil` cannot have. 027's "language is not lineage" survives as a claim about provenance; what does not survive is the inference that a port therefore has nothing of its own to show. Raising the two Java adapters' own hardcoded `10958` windows alongside the corpus removes **all 14** of 057's prefix-of-a-reading artifacts, emptying that column for the whole board. `rust-rrule` did **not** move: 2 failures said it had, and they were this container's ambient `America/Los_Angeles` zone reaching a floating recurrence across a DST boundary for the first time at occurrence 18 — standing rule 49's ninth firing and the first to catch a headline. libical `4edd39a3` and 3.0.20 are unmoved, while the pre-fix commit `48d52b4b` fails **19** where it failed 14, five further instances of the very defect `4edd39a3` fixed. New standing rule 68: a port's perfect score is a statement about the bound, not about the port](findings/066-the-ports-were-not-identical.md).
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
  `MO`. The same build scores **1456 / 1468 / 1487** on this corpus on a
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
  master's 79 → 8, `dmfs lib-recur`'s 76 → 6. No pass count moved. (Each
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
