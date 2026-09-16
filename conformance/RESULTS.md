# Results

Produced by `conformance/score.py` against `conformance/cases.ndjson`
(1721 cases: valid rule, synchronized `DTSTART`, `UNTIL` value type matching
`DTSTART`, decidable from the recorded window). Exact list equality; no partial
credit.

**A failure is a disagreement between an implementation and this corpus.** It is
not, by itself, a defect in the implementation — and on the largest cluster
below the disagreement is between two *lineages*, not between right and wrong.
See [finding 016](../findings/016-independent-lineage-results.md),
[finding 017](../findings/017-libical-third-lineage.md) and the caveats in
`PROTOCOL.md`.

**Every count on this page is a lower bound.** Each corpus case is compared only
out to the `limit` recorded with it, so a defect that first shows up past that
point is invisible to the score. This is not hypothetical: on the `ical4j`
`FREQ=WEEKLY` + `BYMONTH` defect, 6 of the 14 cases that carry it agree with
`expect` for exactly as long as their corpus entry runs and diverge just after
([finding 039](../findings/039-what-bysetpos-selects-from.md)). Read *N
failures* as *N disagreements inside the horizons this corpus happens to
choose*, for every row below.

[Finding 040](../findings/040-how-much-a-short-horizon-hides.md) sizes that gap.
Re-run at a 128-occurrence horizon against a two-lineage control, **68 further
`ical4j` cases that score as passes emit a date the control does not** — about a
48% undercount on that row. The gap is not uniform: `rrule.js` gains 2,
`rust-rrule` 2 more than its published 3 (see below), and `dmfs lib-recur`
gains **none**, so its 13 is a lower bound only in principle.

[Finding 042](../findings/042-what-the-fourth-lineage-hides-past-occurrence-eight.md)
extends the same sweep to `sabre/vobject`, which had no horizon measurement at
all: **135 further cases** that score as passes emit a date the control does not
by occurrence 64, about a 17% undercount on its row, and none of its hidden
rows are early stops.
[Finding 045](../findings/045-sub-daily-expansion-is-confined-to-one-larger-unit.md)
closes the last gap: `DateTime::Event::ICal` hides **56 further cases**, about a
15% undercount on its 386, none of them early stops, and 53 of the 56 are one
bug — at a sub-daily `FREQ`, a coarser `BY*` part advances the outer period
instead of filtering, so the expansion runs for exactly one second-in-a-minute,
minute-in-an-hour or hour-in-a-day. **Every implementation on the board now has
a measured horizon gap.**

**Three independent lineages now disagree with the corpus in the same way, and
the reason is known.** On **56** cases `libical`, `ical4j` and `dmfs lib-recur`
all fail *and return the identical answer*: 41 are `FREQ=YEARLY` with
`BYMONTHDAY` and no `BYMONTH`, and **15 are `FREQ=YEARLY` with `BYWEEKNO` and no
`BYDAY`** — a second cluster that [finding 017](../findings/017-libical-third-lineage.md)
missed when it reported 41 and said no other rule family produced three-way
agreement. Both clusters are reproduced *exactly*, all 56 instants, by one
rewrite: fill the field the rule leaves unspecified from `DTSTART`
(`BYMONTH=month(DTSTART)`, `BYDAY=weekday(DTSTART)`). RFC 5545 §3.3.10 contains
both readings — its table says `Expand`, and its DTSTART-fill sentence says the
missing month comes from `DTSTART` — and never says which wins.
[Finding 024](../findings/024-dtstart-fill-versus-the-table.md).

**Those 56 are now annotated, and every number below moved.** The corpus
records the `dtstart_fill` reading beside `expect` on 65 of these cases, and
`score.py` reports an implementation matching it as `fail_other_reading` rather
than `fail` — see [`PROTOCOL.md`](PROTOCOL.md) and
[`../corpus/SCHEMA.md`](../corpus/SCHEMA.md). No pass count changed; what
changed is how many of the remaining cases are being called defects.
`ical4j`'s plain failures fall 253 → 195, `libical` master `4edd39a3`'s 79 → 22,
and `dmfs lib-recur`'s 76 → 13.

The annotation is **shape-selected, not failure-selected**: it is applied to
every corroborated case of the two shapes where the rewritten rule is itself
corroborated by both expanders, not to the cases that were observed to fail. So
the three lineages landing on it is a result rather than a restatement — and
independently, the set of cases where `ical4j`, `dmfs lib-recur` and `libical`
`4edd39a3` **all** score `dtstart_fill` is exactly **56**, reproducing finding
024's count through the scorer instead of through its model script.

They do not land on it identically. `ical4j` scores 58, `dmfs lib-recur` 60,
both `libical` master builds 57, and released `libical` 3.0.20 only 41. All 16
of that last gap are `BYWEEKNO` rules: `3.0.20` rejects 9 of them outright as
`MALFORMEDDATA`, and answers the other 7 in a third way that is neither
reading. An error is not a reading, and the recurrence rewrite between 3.0 and
master is exactly where one would expect this to move.

**All 211 of libical 3.0.20's non-passing cases fall into classes libical's own
tracker already documents**, three of them fixed in master and one still open. The
corpus reproduced a stranger's known-issue list without being told it existed,
and found nothing outside it. Finding 017.

**That does not carry over to master.** Eight of master's failures — every
`FREQ=WEEKLY` failure it has — are outside libical's documented known-issue
set: `BYSETPOS` indexes the set before `BYMONTH` limits it, and the week that
straddles the start of a selected month is skipped when iteration arrives after
a gap. Finding 019. Finding 017 had dismissed these eight on a probe that was
invalid; finding 018 is the retraction.

**Those eight are now fixed upstream.** Reported as libical/libical#1374; fixed
by commit `4edd39a` ("BYSETPOS issue fix", #1387). Retested 2026-09-11 over the
whole corpus: 8 fixed, 0 regressions, 1599 → 1607 pass. The remaining
non-passing cases are `FREQ=YEARLY` shapes, and 57 of them are now scored as
the other reading rather than as failures. Finding 019, "Retest".

`score.py` reports a failure that matches one of a case's `reading_alternatives`
as `fail_other_reading` rather than `fail`, broken down by which reading
(finding 018 for `first_period_truncated`, finding 024 for `dtstart_fill`, and
[`PROTOCOL.md`](PROTOCOL.md)). **`rrule.js` is now the only implementation here
with no reading-dependent failures at all** — every failure it has is a
disagreement about behaviour rather than about the text.

All rows rescored 2026-09-11 against the annotated corpus. `pass` is unchanged
from the previous run of each; annotation only moves cases between `fail` and
`other reading`.

| implementation | version | lineage | pass | fail | other reading | error |
|---|---|---|---:|---:|---:|---:|
| `python-dateutil` | 2.9.0.post0 | corroborating expander | 1721 | 0 | 0 | 0 |
| `rrule.js` | 2.8.1 | port of dateutil | 1695 | 26 | 0 | 0 |
| `rrule-go` | 1.8.2 | port of dateutil (Go) | 1721 | 0 | 0 | 0 |
| `rust-rrule` | 0.14.0 | port of dateutil (Rust) | 1721 | 0 | 0 | 0 |
| `ical4j` | 4.1.1 | independent (Java, 2004) | 1468 [†](#ical4j-locale) | 195 | 58 | 0 |
| `dmfs lib-recur` | 0.17.1 | independent (Java, 2013) | 1637 | 13 | 63 | 8 |
| `libical` | 3.0.20 (Debian trixie) | independent (C, 2000) | 1510 | 113 | 41 | 57 |
| `libical` | master `48d52b4b` | independent (C, 2000) | 1599 | 30 | 57 | 35 |
| `libical` | master `4edd39a3` | independent (C, 2000) | 1607 | 22 | 57 | 35 |
| `sabre/vobject` | 4.6.1 | independent (PHP, 2011) | 831 | 863 | 23 | 4 |
| `DateTime::Event::ICal` | 0.13 | independent (Perl, 2003) | 1176 | 386 | 51 | 108 |

<a id="ical4j-locale"></a>
**† `ical4j`'s row is a measurement of this container, not of `ical4j` alone.**
When an `RRULE` omits `WKST`, `ical4j` takes the first day of the week from the
JVM's default locale rather than RFC 5545's stated default of `MO`
([finding 036](../findings/036-a-score-that-depends-on-the-host-locale.md)).
The run above was made on an `en`-`US` JVM, where the week starts on Sunday.
The same build, same corpus, changing only the locale:

| JVM locale | first day of week | pass | fail |
|---|---|---:|---:|
| `ar`-`EG` | Saturday | 1456 | 207 |
| `en`-`US` | Sunday | 1468 | 195 |
| `en`-`GB` | Monday | 1487 | 176 |

19 net of the 195 are the locale and not the algorithm. The harness now watches
for this: `conformance/ambient_sweep.py` reruns the adapters over the scored
corpus under three environments that move the time zone, the locale's first day
of the week and the locale's digit shapes, and diffs the answers case by case
([finding 038](../findings/038-checking-the-instrument-for-what-it-measured.md)).
**That "only one" was too strong, and [finding 040](../findings/040-how-much-a-short-horizon-hides.md)
says why.** The sweep's two non-baseline zones were picked for their UTC offsets
and neither observes DST, and it ran at the corpus horizon. Under
`America/New_York` at a 64-occurrence horizon, `rust-rrule` moves on 3 cases: it
resolves a floating local time through the machine's `TZ`, so a `FREQ=HOURLY`
rule crossing US spring-forward loses 02:30 and emits 03:30 twice — the same
absolute instant twice, which [finding 041](../findings/041-a-duplicate-instant-in-a-floating-recurrence.md)
adjudicates as a defect under both readings of a floating `DTSTART`. A
DST-observing environment and a `--limit` override are now part of the sweep.

At the corpus horizon `ical4j` is still the only one whose answers move — 36 of 1721 under
`ar`-`EG`, every one a `FREQ=WEEKLY` rule whose week boundary shifted. The sweep
also caught a locale-dependent *formatter* in this repository's own `dmfs`
adapter, which on an Arabic-locale machine would have scored that row 0 of 1721;
it is fixed, and the `dmfs` row above is unchanged by the fix.

Of the 176 that remain on the `en`-`GB` row — the row where `WKST` defaults to
the value RFC 5545 specifies — **18 are one defect**, characterised in
[finding 037](../findings/037-a-limit-that-runs-before-the-thing-it-limits.md):
at `FREQ=WEEKLY` the `BYMONTH` limit is applied to the period seed rather than
to the expanded occurrences, so over a common horizon all 18 both return dates
in months the rule excludes and omit dates it requires. The same behaviour appears on a further 42
corroborated cases that this set excludes because their `DTSTART` is
unsynchronized; those are not counted as defects. Measured identically on 4.3.0,
the current release. [Finding 039](../findings/039-what-bysetpos-selects-from.md)
extends the same defect to the corpus's `BYSETPOS` cases: a further **8** of the
176 are it, and six more cases carry the defect but only past the horizon their
corpus entry runs to, so 176 is a count of disagreements within these horizons
and undercounts this defect.

Every row is out of 1721. `dmfs lib-recur`'s 63 is the only one that is not all
`dtstart_fill`: 60 are, and 3 are `first_period_truncated`.

`DateTime::Event::ICal`'s row carries a caveat the others do not, and it is
about me rather than about the library: its numbers depend on *how the result
set is enumerated*. The adapter walks `DateTime::Set`'s documented `->iterator`;
walking the identical set by repeated `->next` changes the answer on 68 of the
corpus's 291 `BYSETPOS` cases and moves 5 of them from disagree to agree. See
[finding 046](../findings/046-the-iterator-and-the-next-chain-disagree.md), and
`RRULE_DTICAL_ITER=chain` in the adapter to reproduce the other column.

`DateTime::Event::ICal`'s 386 mismatches and 108 errors are not 494 separate
problems. [Finding 035](../findings/035-one-deletion-and-a-pinned-day.md)
accounts for the `BYMONTH` share of both: at `FREQ=WEEKLY` and `FREQ=MONTHLY`
the library reads `BYMONTH` as *month ∈ `BYMONTH` **and** day-of-month =
`DTSTART`'s day*, because `recur()` assembles the `BYMONTH` filter from a hash
the frequency handler has already deleted `byday` from. Supplying the one
missing default from the caller takes the 205 non-`BYSETPOS`
`WEEKLY`+`BYMONTH` cases from **0** passing to **205**, errors included. Its
vote on §3.3.10 comes from `_yearly_recurrence` and is unaffected.

`python-dateutil`'s 1721 is **not a result**: it is one of the two expanders
every case was corroborated by, so it only checks the harness.

`rrule-go`'s and `rust-rrule`'s 1721 are **not independent evidence** either,
for a different reason. Both are `python-dateutil` descendants by their own
READMEs' account, and both return the identical list to their parent on all
3813 corroborated cases, not merely on the 1721 scored here — so counting
either as a lineage would double-count dateutil.
[Finding 027](../findings/027-a-port-that-did-not-drift.md) has the Go
measurement and sizes `rrule.js`'s divergence from the same parent at 122 of
3813, decomposing all of it into the mechanisms findings 015 and 004/018/021
already named.
[Finding 028](../findings/028-two-ports-agree-and-the-third-does-not.md) has
the Rust one, and settles what 027 could not: with **two** independently
written ports reproducing dateutil to the case — and zero overlap with
`rrule.js`'s 122, despite `rust-rrule` citing `rrule.js` as an inspiration —
`rrule.js` is the outlier, and those 122 are its own behaviour rather than an
inherited subtlety.

Five independent lineages are measured here, not nine: dateutil (with its
three ports), the Java pair, `libical`, `sabre/vobject`, and
`DateTime::Event::ICal`.
[Finding 029](../findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md)
has the PHP one — the first candidate in four attempts that claims no ancestry
anywhere in its README, `lib/Recur/` or `composer.json`. It is also the lowest
score here by a wide margin (831), it has four cases that **do not
terminate**, and its 414 guaranteed-invariant violations are two orders of
magnitude above every other row. On the two contested readings of §3.3.10 it
therefore casts no usable vote: the number of lineages that can arbitrate that
table is still three.

**The fifth lineage can arbitrate, and it writes its answer down.**
[`DateTime::Event::ICal`](https://metacpan.org/pod/DateTime::Event::ICal) 0.13
(Perl, 2003) scores 1176 — second-lowest here — but **0** guaranteed invariant
violations and **0** order-dependent mismatches, and its `FREQ=YEARLY` handling
is sound: it counts negative `BYWEEKNO` correctly across a 53-week and a
52-week year. On the 65 contested `dtstart_fill` cases it takes the rival
reading on **51**. What makes it different from the other three votes is that
the fill is not inferred from its output. `_yearly_recurrence` contains
`$by{days} = $dtstart->day_of_week unless exists $by{days};` in the `BYWEEKNO`
branch and `$by{months} = $dtstart->month;` in the branch with no `BY` part to
expand — the two rewrites of finding 024, written out by an implementer working
from RFC 2445 §4.3.10 in 2003.
[Finding 030](../findings/030-a-fifth-lineage-that-writes-the-fill-down.md).
Lineages that can arbitrate §3.3.10: **four**.

## Corpus-independent checks

`conformance/check_invariants.py` never reads `expect`. It asks whether each
returned occurrence satisfies the rule's own BY parts, and reports only those
constraints that RFC 5545's application order guarantees survive to the output
(see [`invariants.py`](invariants.py)).

| implementation | guaranteed violations | order-dependent mismatches |
|---|---:|---:|
| `python-dateutil` 2.9.0.post0 | 0 | 0 |
| `rrule.js` 2.8.1 | 0 | 0 |
| `rrule-go` 1.8.2 | 0 | 0 |
| `rust-rrule` 0.14.0 | 0 | 0 |
| `ical4j` 4.1.1 | 0 | 31 cases |
| `dmfs lib-recur` 0.17.1 | 1 case | 0 |
| `libical` 3.0.20 | 1 case | 0 |
| `libical` master `48d52b4b` | 0 | 0 |
| `sabre/vobject` 4.6.1 | 414 cases | 176 cases |
| `DateTime::Event::ICal` 0.13 | 0 | 0 |

## Reproducing

```sh
tools/bootstrap.sh                       # RFCs, vendored dateutil, npm install rrule
python3 conformance/build_cases.py
python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
python3 conformance/score.py -- node conformance/adapters/rrulejs_adapter.js
```

The Go and Rust adapters have their own build steps — see
[`adapters/go/README.md`](adapters/go/README.md) and
[`adapters/rust/README.md`](adapters/rust/README.md).

The Perl adapter needs only `libdatetime-event-ical-perl` and `libjson-perl`
from apt — see [`adapters/perl/README.md`](adapters/perl/README.md).

The PHP adapter needs `php-cli`, `php-xml` and `composer`, and gives each case
a wall-clock deadline because four of them never finish — see
[`adapters/php/README.md`](adapters/php/README.md).

The Java and C adapters have their own build steps — see
[`adapters/java/README.md`](adapters/java/README.md) and
[`adapters/c/README.md`](adapters/c/README.md).

For the two Java implementations, see
[`adapters/java/README.md`](adapters/java/README.md) (needs a JDK and Maven).

## Wanted

An implementation descended from **neither `python-dateutil` nor `libical`**
**that implements the whole of §3.3.10** — in particular `BYWEEKNO`,
`BYYEARDAY`, and the `BY*` parts in their limiting roles.

The qualifier is new, and finding 029 is why. This section used to ask for Go,
Rust, C# or Swift. The Go and Rust results came back a perfect 1721 and were
worth nothing as evidence, because both libraries are dateutil descendants —
findings [027](../findings/027-a-port-that-did-not-drift.md) and
[028](../findings/028-two-ports-agree-and-the-third-does-not.md). Then PHP's
`sabre/vobject` arrived as a genuine fourth origin and still could not
arbitrate, because the branches under dispute are the ones it gets wrong
([029](../findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md)).

Language was never the variable. Lineage is necessary and not sufficient:
finding 016 showed the known lineages disagree systematically on `FREQ=YEARLY`
expansion, and breaking that tie needs an implementation that is both
independent **and** competent on `FREQ=YEARLY`.

**Perl's `DateTime::Event::ICal` met that bar**
([030](../findings/030-a-fifth-lineage-that-writes-the-fill-down.md)), so the
§3.3.10 question is no longer the open one. What is wanted now is narrower:

- **A reading of §3.3.10 that settles [finding
  024](../findings/024-dtstart-fill-versus-the-table.md)'s split — the table's
  `Expand` against the `DTSTART`-fill sentence.** Every case in
  `corpus/disputed.json` now carries a verdict (21 `naive`, 5 `undecided`), and
  all five `undecided` ones reduce to this question:
  [finding 033](../findings/033-the-last-five-disputes-are-two-questions.md)
  shows that `BYWEEKNO` without `BYDAY` raises it again, with `libical`, `dmfs`
  and `ical4j` on one side and both of the corpus's own adjudicators on the
  other. This replaces the previous two entries, which asked for adjudication of
  those five and, before that, for a generator producing corpus cases that
  discriminate the contested `FREQ=WEEKLY` readings.
  [Finding 034](../findings/034-when-the-table-arrived.md) narrows what would
  count as an answer: §3.3.10 itself cannot supply one. The `DTSTART`-fill
  sentence is unchanged from RFC 2445 through RFC 5545, the table was added in
  draft-07 (2007) as a summary of the section, and no edit ever reconciled them.
  A settlement has to come from outside the section.
  [Finding 032](../findings/032-a-blind-spot-the-corpus-cannot-see.md) shows
  that is impossible: a case discriminates first-period truncation **if and
  only if** `naive.py` and python-dateutil disagree on it — zero off-diagonal
  over 800 sampled rules — and disagreement is exactly what the admission rule
  rejects. The generator was never the problem. Ten such cases have now been
  adjudicated to the untruncated reading RFC 5545 §3.3.10 states; the rest of
  `disputed.json` is where the corpus's remaining open questions live.
  ([Finding 031](../findings/031-one-cluster-three-causes.md) is what exposed
  the gap: the `WEEKLY`+`BYMONTH` cluster is three unrelated implementation
  causes, not under-specification.)
- Candidate origins not yet lineage-checked: Ruby, Erlang/Elixir, Swift, Common
  Lisp, and calendar servers with their own expanders (Radicale, SOGo, Cyrus,
  DAViCal). Read the README first — that one minute has disqualified four
  candidates so far.

An adapter is about forty lines; `PROTOCOL.md` is the whole contract.
