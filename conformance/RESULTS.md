# Results

Produced by `conformance/score.py` against `conformance/cases.ndjson`
(1727 cases: valid rule, synchronized `DTSTART`, `UNTIL` value type matching
`DTSTART`, decidable from the recorded window). Exact list equality; no partial
credit. Every case records up to **25** occurrences within **109500 days** of
`DTSTART`; both numbers were raised on 2026-09-20 and every row below was
re-measured then, under `TZ=UTC`
([finding 066](../findings/066-the-ports-were-not-identical.md)).

Every row on this page was measured against

    cases_id  7bd9731d3a48    corpus_id  38f9320ddfd4    corpus version 1.0.0

recorded in [`corpus/VERSION.json`](../corpus/VERSION.json), where `cases_id` is
the sha256 of `cases.ndjson` — the bytes a run actually reads — and `corpus_id`
covers the whole corpus. `score.py` prints both on every run and writes them
into `--json` output, so a reader can tell whether a row is a measurement of
*this* corpus or of an older one without taking my word for it.
`python3 tools/corpus_id.py --check` recomputes them from the committed files.
**If `cases_id` has moved, every row below is from a different experiment and
has to be re-run before it may be cited.** This is finding 053's rule made
mechanical; it kept having to be remembered instead.

`cases.ndjson` has not changed since commit `5d6745e`, which raised the corpus
to 25 occurrences and 109500 days, and every row below was measured at or after
that commit — so the identifier above really does cover the whole table. The
corpus around it *has* moved since: applying
[finding 067](../findings/067-an-empty-list-nobody-had-proved.md) on 2026-09-20
relabelled 285 cases from `horizon` to `complete`, changing `corpus_id` and not
`cases_id`, because none of those cases is in the scored subset. That is
precisely the distinction the two identifiers exist to make. The `scorer_id` in
`VERSION.json` likewise now differs from the one the rows physically ran under:
adding this reporting changed `score.py` and no bucket in it.

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

It pointed the other way in exactly one place, and that has now been fixed
rather than footnoted. [Finding 056](../findings/056-two-scopes-for-one-word.md)
found 7 of `ical4j`'s plain failures and 7 of `dmfs`'s to be a proper *prefix* of
a rival reading the corpus records, returned short because the Java adapter's
window is `DTSTART` + 10958 days, and reported by a scorer that recognised a
rival reading only by exact equality. `score.py` now has a bucket for it. It is one of two prefix buckets,
and the **short** column below is their sum — see [¶](#prefix).

[Finding 057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md)
rescored every row against the new scorer. The two JVM rows moved by exactly 7
each; **every other row reproduced its published numbers cell for cell**, and
`fail_prefix` — a prefix of the corpus's *own* answer — was zero everywhere,
measured rather than assumed. *That last clause has since expired:* raising the
horizon on 2026-09-20 pushed three `rrule-go` cases and one `ical4j` case into
it, and the sentence stood here unrevised until
[finding 077](../findings/077-a-table-that-outlived-its-corpus.md). The 7 are
the *same* 7 cases for both adapters, in all three JVM locales, which is what identifies the cause as the harness: the
corpus applies `horizon_days` to every `expect` list and to only 99 of its 120
`reading_alternatives` lists, so an adapter clipping at the declared horizon
cannot match the other 21 by equality. Those 21 are the exact bound on this
artifact; 7 of them were ever exposed.

[Finding 040](../findings/040-how-much-a-short-horizon-hides.md) sizes that gap.
Re-run at a 128-occurrence horizon against a two-lineage control, **68 further
`ical4j` cases that score as passes emit a date the control does not** — about a
48% undercount on that row. The gap is not uniform: `rrule.js` gains 2,
`rust-rrule` 2 more than its published 3 (see below), and `dmfs lib-recur`
gains **none**, so its plain-failure count (13 when finding 040 measured this,
6 today) is a lower bound only in principle.

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

That sweep still left one block uncounted: the **146** cases where the Perl
adapter returned no answer at all, which the sweep charges to nobody.
[Finding 047](../findings/047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md)
measures it. It is four different failures, not one: 13 cases were only my own
20s deadline, 12 are a limitation `ICal.pm` declares by name, and 77 are the
library dereferencing its own `undef` after a bounded retry budget runs out.
**Three of those crashes pass their corpus case and appear only at limit 64** —
a horizon can hide a `die`, and a sweep that buckets every error together will
never show it.

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
and `dmfs lib-recur`'s 76 → 13. (Those are the figures *at that moment*; the
corpus and the scorer have both moved since, and the table below is the current
one.)

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
non-passing cases are `FREQ=YEARLY` shapes, and 71 of them are now scored as
the other reading rather than as failures. Finding 019, "Retest".

`score.py` reports a failure that matches one of a case's `reading_alternatives`
as `fail_other_reading` rather than `fail`, broken down by which reading
(finding 018 for `first_period_truncated`, finding 024 for `dtstart_fill`, and
[`PROTOCOL.md`](PROTOCOL.md)). **`rrule.js` is now the only implementation here
with no reading-dependent failures at all** — every failure it has is a
disagreement about behaviour rather than about the text.

All rows rescored 2026-09-17 against the annotated corpus, which gained seven
cases that hour: the first cases anywhere in this set that put `BYMONTHDAY` or
`BYYEARDAY` in their *limiting* role with a negative value
([finding 050](../findings/050-one-cell-of-the-table-four-ways-to-get-it-wrong.md)).

On 2026-09-18 the corpus recorded a `dtstart_fill` alternative on 29 further
scored cases that a length guard of mine had been suppressing
([finding 053](../findings/053-a-short-list-is-not-always-my-horizon.md)). No
`expect` list changed, so no case can change bucket except from `fail` to
`other reading`; every adapter was rescored over exactly those 29 and the
measured move is the whole of the change: `ical4j` 8 (identically in 4.1.1,
4.3.0 and all three locales), `libical` master 14, `libical` 3.0.20 5,
`DateTime::Event::ICal` 14, and nothing at all for the `dateutil` lineage,
`dmfs` or `sabre`.

On 2026-09-19 the corpus recorded a **new** reading, `week_based_year`, and its
composition with `dtstart_fill`, on 7 scored cases
([finding 059](../findings/059-which-year-owns-a-straddling-week.md)): under
`FREQ=YEARLY` with `BYWEEKNO`, the days of a week that straddles 1 January are
taken to belong to the period of the year that *owns* the week rather than the
calendar year they sit in. Again no `expect` list changed, so again no case can
move except from `fail` to `other reading`. Every row above was rescored on the
new cases file. `ical4j` 187 → **183** (and 199 → 196 on `ar`-`EG`,
168 → **164** on `en`-`GB`) — those are the counts *as of 2026-09-19*, before
the horizon was raised; the current `ical4j` figures are 230/243/215 and the
locale table below has been re-measured. `dmfs lib-recur` 6 → **4**,
`libical` master `4edd39a3` 8 → **6**, master `48d52b4b` 16 → **14**, `3.0.20` 108 → **107**, and
nothing at all for the `dateutil` lineage or `sabre`. The `dtstart_fill` counts
in the paragraphs above are unchanged: the composed reading gets its own name, so
no case that scored `dtstart_fill` moved.

`DateTime::Event::ICal`'s row has since been re-run on the 25-occurrence corpus
under `TZ=UTC`, on 2026-09-20, and the figures above are that run:
**1163 pass, 368 fail, 69 other reading, 127 error**, against 1179/385/67/97 at
eight occurrences. Its residual is load-dependent and has never reproduced
across runs
([finding 047](../findings/047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md)),
so the `fail`/`error` boundary in particular should be read as one observation
rather than a stable count — see the note below.

<!-- rowsum: total=cases cols=pass:4,fail:5,other:6,prefix:7,error:8 -->
| implementation | version | lineage | pass | fail | other reading | short [¶](#prefix) | error |
|---|---|---|---:|---:|---:|---:|---:|
| `python-dateutil` | 2.9.0.post0 | corroborating expander | 1727 | 0 | 0 | 0 | 0 |
| `rrule.js` | 2.8.1 | port of dateutil | 1699 | 28 | 0 | 0 | 0 |
| `rrule-go` | 1.8.2 | port of dateutil (Go) | 1724 | 0 | 0 | 3 [§](#go-truncation) | 0 |
| `rust-rrule` | 0.14.0 | port of dateutil (Rust) | 1727 | 0 | 0 | 0 | 0 |
| `ical4j` | 4.1.1 | independent (Java, 2004) | 1420 [†](#ical4j-locale) | 230 | 76 | 1 | 0 |
| `dmfs lib-recur` | 0.17.1 | independent (Java, 2013) | 1640 | 4 | 71 | 0 | 12 |
| `libical` | 3.0.20 (Debian trixie) | independent (C, 2000) | 1517 | 107 | 47 | 0 | 56 |
| `libical` | master `48d52b4b` | independent (C, 2000) | 1601 | 19 | 72 | 0 | 35 |
| `libical` | master `4edd39a3` | independent (C, 2000) | 1614 | 6 | 72 | 0 | 35 |
| `sabre/vobject` | 4.6.1 | independent (PHP, 2011) | 720 | 980 | 23 | 0 | 4 [∞](#sabre-loop) |
| `DateTime::Event::ICal` | 0.13 | independent (Perl, 2003) | 1164 | 370 [‡](#dtical-split) | 69 | 0 | 124 [‡](#dtical-split) |
| `ical.js` | 2.2.1 | port of libical (JS) [♦](#icaljs-lineage) | 1376 | 236 | 31 | 0 | 84 [◊](#icaljs-abort) |

<a id="icaljs-lineage"></a>
**♦ `ical.js` is not an independent witness.** Its recurrence iterator is a port
of `libical`'s `icalrecur.c` — same `expand_map`/`CONTRACT` constants, same
`check_contracting_rules`, same eight checks in the same order. It was added to
this table expecting a fourth independent implementation and it is not one, so
`ical.js` agreeing with `libical` counts once (rule 24).
[Finding 070](../findings/070-icaljs-is-libical-in-javascript.md). The same
conclusion from *behaviour* rather than from shared identifiers, and dated:
`ical.js` ignores `BYSETPOS` at `FREQ=WEEKLY` exactly as `libical` **3.0.20**
does and `libical` master no longer does —
[finding 071](../findings/071-two-of-icaljs-residuals-are-inherited.md).

<a id="icaljs-abort"></a>
**◊ 42 of `ical.js`'s 84 errors are the adapter's deadline, not a refusal.**
`ical.js` 2.2.1 enters an unbounded search inside a single `iterator.next()`
whenever a `BY` part that *contracts* under the rule's own `FREQ` carries a
negative value — `FREQ=DAILY;BYMONTHDAY=-1` is enough. It does not hang
politely; it allocates until the Node heap is exhausted and the process aborts,
so the adapter runs the library in a child process with a per-case deadline and
reports a timeout for the case that killed it. The other 42 errors are ordinary
parse refusals. All 72 corpus cases carrying such a negative value are wrong in
`ical.js`: 42 abort, 27 return a list with the negative value's occurrences
silently missing, 3 match a rival reading. The 42/42 split is stable: raising
the deadline to 10000 ms reproduces the whole score and the *same* case ids on
both sides of it. At 20000 ms, with a probe that reports a worker dying on its
own separately, **39 of the 42 are confirmed aborts** arriving between 9848 ms
and 18730 ms — no abort arrives anywhere near the published 2000 ms, which is
why the deadline is what the adapter sees.
[Finding 070](../findings/070-icaljs-is-libical-in-javascript.md),
[finding 073](../findings/073-which-error-columns-are-really-the-clock.md).

<a id="sabre-loop"></a>
**∞ All four of `sabre/vobject`'s errors are the adapter's alarm, and none of
them is the clock.** `RRuleIterator::nextYearly`'s `BYYEARDAY` branch is a
`while (true)` with no year ceiling, testing a day map numbered PHP's `w` way
(`SU => 0`) against `format('N')`, where Sunday is 7; `BYDAY=SU` and any
*ordinal* `BYDAY` match no date in any year, so the loop never exits
([finding 029](../findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md)).
Re-run at a 180 s per-case deadline — eighteen times the published one — the
same four still return nothing, with `user` time equal to `real` to the tenth
of a second. The count is deadline-*reported* but not deadline-*dependent*
(standing rule 80);
[finding 073](../findings/073-which-error-columns-are-really-the-clock.md)
checks every `error` column in this table the same way and finds
`DateTime::Event::ICal`'s the only one that moves.

<a id="go-truncation"></a>
**§ `rrule-go`'s three.** They are `fail_prefix` — a proper prefix of the
corpus's own `expect` — and until 2026-09-21 they appeared in no column at all
([finding 077](../findings/077-a-table-that-outlived-its-corpus.md)).
All three stop at exactly 105189 days past their own `DTSTART` and
the corpus's next occurrence falls at exactly 107380 days. `math.MaxInt64`
nanoseconds is 106751.99 days, so `rrule-go` silently truncates any recurrence
reaching beyond Go's `time.Duration` ceiling.
[Finding 066](../findings/066-the-ports-were-not-identical.md). `ical4j` has one
entry in the same bucket, which is finding 050's sub-daily `BYYEARDAY` defect;
every other re-measured row is zero there.

<a id="prefix"></a>
**¶ short.** A non-empty *proper prefix* of the answer the case expects: the
implementation agreed for its whole length and then stopped early. Counted
apart from `fail` because stopping short is the signature of a window rather
than of a disagreement. `score.py` splits this in two — `fail_prefix`, a prefix
of `expect`, and `fail_other_reading_prefix`, a prefix of a recorded
`reading_alternatives` list — and this column is their sum.
`fail_other_reading_prefix` is **zero on all eight rows re-measured on
2026-09-21**, so every entry in this column today is `fail_prefix`.

Until 2026-09-20 the second of the two was almost entirely an artifact of the
Java adapters' own `DTSTART` + 10958-day clip, which was the corpus's declared
horizon and which the corpus did not apply to its own alternative readings;
raising the corpus horizon to 109500 days and raising both Java adapters'
windows with it removed all 14
([finding 066](../findings/066-the-ports-were-not-identical.md)). The two
entries that remain are the *first* bucket and were published under the second
one's heading until
[finding 077](../findings/077-a-table-that-outlived-its-corpus.md) merged the
column: `rrule-go`'s 3 were omitted from the table altogether, which is why its
row summed to 1724 against a 1727-case set. The bucket asserts the prefix and
nothing more: it does not claim the implementation would have continued
correctly.
[Finding 057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md).

<a id="ical4j-locale"></a>
**† `ical4j`'s row is a measurement of this container, not of `ical4j` alone.**
When an `RRULE` omits `WKST`, `ical4j` takes the first day of the week from the
JVM's default locale rather than RFC 5545's stated default of `MO`
([finding 036](../findings/036-a-score-that-depends-on-the-host-locale.md)).
The run above was made on an `en`-`US` JVM, where the week starts on Sunday.
The same build, same corpus, changing only the locale — re-measured
2026-09-21 against `cases_id` `7bd9731d3a48`, the identifier at the top of this
page:

<!-- rowsum: total=cases cols=pass:3,fail:4,other:5,short:6 -->
| JVM locale | first day of week | pass | fail | other reading | short |
|---|---|---:|---:|---:|---:|
| `ar`-`EG` | Saturday | 1408 | 243 | 75 | 1 |
| `en`-`US` | Sunday | 1420 | 230 | 76 | 1 |
| `en`-`GB` | Monday | 1435 | 215 | 76 | 1 |

The `en`-`US` row is the `ical4j` row of the main table, cell for cell.

**This table published 1456/196/7, 1468/183/7 and 1487/164/7 until 2026-09-21.**
Those were measurements of the pre-2026-09-20 corpus, left unrevised when the
corpus was raised to 25 occurrences and 109500 days, and they summed to 1659,
1658 and 1658 against a 1727-case set. Every number in this section that was
derived from them has been recomputed or marked below.
[Finding 077](../findings/077-a-table-that-outlived-its-corpus.md).

**15** net of the 230 are the locale and not the algorithm, and the move is not
a clean subset: going from Sunday to Monday takes 16 cases out of the
plain-failure column and puts 1 in. The `short` column does not move with the
locale at all — the same single case, `c5175bbb94b8`, in all three rows, which
is part of how finding 057 identifies that bucket as the harness. The *other
reading* column barely moves either, by one case between Saturday and the other
two. Of the 215 that remain
on the `en`-`GB` row, **72 are one defect in its two forms** — 69 where the
negative value is a `BYMONTHDAY` and 3 where it is a `BYYEARDAY`. Finding 049
counted 72 on the smaller corpus and finding 077 marked the figure as not yet
recounted; it was recounted on 2026-09-24 against `cases_id` `7bd9731d3a48`,
by reproduction rather than by rule shape, and it is still 72 with the same
69/3 split ([finding 078](../findings/078-recounting-the-marked-prose.md)). The value is
resolved correctly when the rule part expands and compared raw when the same
rule part limits, so `FREQ=DAILY;BYMONTHDAY=-1` matches nothing. Finding 049
could only say the 65 it then had were *all* `FREQ=DAILY`; that was a fact
about the corpus, not about `ical4j`, and the seven cases added on 2026-09-17
show the same empty answer at `FREQ=HOURLY`, `MINUTELY` and `SECONDLY` too. 4.3.0 fixes it for `BYMONTHDAY`
and not for `BYYEARDAY`, and the scored set now shows exactly that split:
4.3.0 passes the four new `BYMONTHDAY` cases and fails the three new
`BYYEARDAY` ones (1556 / 99 / 66 / 7 on the `en`-`GB` row — pre-2026-09-20
corpus, and those four cells sum to 1728, one more than that corpus held;
**the 4.3.0 jar is not in this tree, so no 4.3.0 number on this page can be
reproduced from the committed files**, finding 077)
([finding 049](../findings/049-a-negative-day-that-only-counts-when-it-expands.md)).

**The plain failures that survive that fix are now attributed.**
[Finding 051](../findings/051-what-is-left-after-the-negative-limit-fix.md)
categorises every plain failure of both releases. All 69 cases 4.3.0 repaired
are the negative-limit defect above; no other block moves by a single case
between 4.1.1 and 4.3.0. Finding 051 counted 114 of them. Two later corrections
of mine have since taken 15 out of that column: 8 left for the other reading
([finding 053](../findings/053-a-short-list-is-not-always-my-horizon.md)) and 7
for the new prefix bucket
([finding 057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md)),
so **99 remain** — 2 out of 051's `BYWEEKNO` block and 5 out of its unattributed
block, exactly the 5 that
[finding 056](../findings/056-two-scopes-for-one-word.md) had already declared
were an artifact of my own harness rather than a defect. The breakdown below is
051's, taken before both moves. Of the 114, **29 are answers
containing the same
instant twice** — `FREQ=MONTHLY;BYMONTHDAY=31,-1` returns month end twice in a
31-day month, and no other implementation on this page returns a repeated
instant on those cases — and **15 are an ordinal `BYDAY` in its limiting role**,
where `FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO` returns nothing at all while three
independent lineages return the months whose 1st is a Monday. A further 27 have
the shape of [finding 037](../findings/037-a-limit-that-runs-before-the-thing-it-limits.md);
43 remain unaccounted for. 8 of those 43 have since left the plain-failure
column: they are `FREQ=YEARLY;…;BYSETPOS` rules on which `ical4j` returns an
empty list, and the corpus now records an empty `dtstart_fill` alternative for
them ([finding 053](../findings/053-a-short-list-is-not-always-my-horizon.md)),
which empties 051's *other empty answers* bucket from 11 to 3 and leaves 35
unaccounted for. 053 says why a match against an *empty* alternative is the
weakest label the scorer can apply.

The 16 `BYWEEKNO` cases among them are **not** an `ical4j` defect.
[Finding 052](../findings/052-byweekno-is-one-lineage-deep.md) ran all eight
adapters over the 50 scored cases carrying `BYWEEKNO` and split them by whether
the rule also carries `BYDAY`. On the 42 without `BYDAY`, the corpus's `expect`
is matched by `dateutil`, `rrule.js` and `rust-rrule` — **one lineage** — and by
nothing else: `dmfs` matches 16, and `libical`, `ical4j`, `dtical` and `sabre`
match none. That is finding 024's `dtstart_fill` split, which `ical4j`'s
`ByWeekNoRule` implements literally by carrying `DTSTART`'s weekday through the
week-number map. 17 of the 50 are already reported as `fail_other_reading`; the
rest were scored as plain failures because the corpus under-recorded the
alternative — see 052 for the two guards responsible. Both are now fixed; the
second, a length guard that suppressed an alternative shorter than `expect`,
is [finding 053](../findings/053-a-short-list-is-not-always-my-horizon.md).

The harness now watches
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

At the corpus horizon `ical4j` is still the only one whose answers move — 36 of 1728 under
`ar`-`EG`, every one a `FREQ=WEEKLY` rule whose week boundary shifted. The sweep
also caught a locale-dependent *formatter* in this repository's own `dmfs`
adapter, which on an Arabic-locale machine would have scored that row 0 of 1728;
it is fixed, and the `dmfs` row above is unchanged by the fix.

Of the **215** that remain on the `en`-`GB` row — the row where `WKST` defaults
to the value RFC 5545 specifies — **60 are one defect**, characterised in
[finding 037](../findings/037-a-limit-that-runs-before-the-thing-it-limits.md):
at `FREQ=WEEKLY` the `BYMONTH` limit is applied to the period seed rather than
to the expanded occurrences, so over a common horizon all 60 both return dates
in months the rule excludes and omit dates it requires. The same behaviour appears on a further 42
corroborated cases that this set excludes because their `DTSTART` is
unsynchronized; those are not counted as defects. Measured identically on 4.3.0,
the current release. [Finding 039](../findings/039-what-bysetpos-selects-from.md)
extends the same defect to the corpus's `BYSETPOS` cases: a further **18** are
it, and the row remains a count of disagreements within these horizons, so it
undercounts this defect. Findings 037 and 039 counted 18 and 8 against the
pre-2026-09-20 corpus, when this row stood at 164, and finding 077 marked both
as not recounted. They were recounted on 2026-09-24 against `cases_id`
`7bd9731d3a48`: **60** without `BYSETPOS` and **18** with, 78 together, each one
reproduced element for element by the `FREQ=WEEKLY` seed-limit model and none of
them claimed by a narrower mechanism
([finding 078](../findings/078-recounting-the-marked-prose.md)).

Every row is out of 1728. `dmfs lib-recur`'s 63 is the only one that is not all
`dtstart_fill`: 60 are, and 3 are `first_period_truncated`.

**A blind spot that was known and measured is now closed.** Until 2026-09-17
every case in this set put `BYMONTHDAY` and `BYYEARDAY` in their *expanding*
role whenever the value was negative. The corpus guaranteed one case per
§3.3.10 table cell and a test enforced it, but it drew every value from an
all-positive table, so "57 of 57 cells covered" meant each cell had been
*visited* — never that both signs had been tried. The whole Limit column for
those two rule parts was scored by cases that could not see a defect in it.

Seven rules covering every *limiting* cell of the two parts are now in the
scored set, and they are the whole of the difference between these rows and the
previous run. Per case, out of seven:

<!-- rowsum: skip reason="seven hand-picked probe cases, not the scored set" -->
| implementation | correct | how it is wrong |
|---|---:|---|
| `python-dateutil`, `rrule.js`, `rrule-go`, `rust-rrule` | 7 | — |
| `libical` 3.0.20, master `48d52b4b`, master `4edd39a3` | 7 | — |
| `ical4j` 4.1.1 | 0 | returns an empty list for all seven |
| `ical4j` 4.3.0 | 4 | `BYMONTHDAY` fixed, `BYYEARDAY` twin not |
| `dmfs lib-recur` | 4 | throws *too many empty recurrence sets* on all three `BYYEARDAY` cases |
| `sabre/vobject` | 2 | drops the constraint, then repeats one instant |
| `DateTime::Event::ICal` | 3 | promotes the limit to the frequency |

Two of the six lineages get the cell right and four get it wrong, each
differently. `libical` 3.0.20, which [finding 050](../findings/050-one-cell-of-the-table-four-ways-to-get-it-wrong.md)
left unrun, was run for this table and answers all seven correctly.

The lesson is about this instrument and not about the subjects: **a coverage
model earns only the coverage it states, and is silent about every axis it does
not name.** Cell coverage was never value coverage.

<a id="dtical-split"></a>
**‡ `DateTime::Event::ICal`'s `fail`/`error` boundary does not reproduce, and
the previous version of this table presented it as if it did.** The adapter
gives each case a 20-second alarm, so a case that is merely slow lands in
`error` or in `fail` depending on what else the machine was doing. Rescoring
the **byte-identical** 1721-case file that produced the published row gave
`1176 / 394 / 51 / 100` where the row said `1176 / 386 / 51 / 108` — same
machine, same adapter, same input, eight cases across the boundary.

**The `other reading` column moves too, which the previous version of this note
got wrong.** It said `pass` and `fail_other_reading` came back exactly — true of
the two runs it had. The rescore of 2026-09-18 gives `1179 / 385 / 67 / 97`
against the row's earlier `1179 / 386 / 65 / 98`. The adapter discards a partial
answer when the alarm fires, so a timed-out case is always `error` and never a
short list; when the alarm does *not* fire the case lands in whichever answer
bucket it belongs to, and that can be `other reading` as easily as `fail`. The
whole of this delta is two cases arriving from `error` and one leaving for it.
Only `pass` had reproduced across those three runs — and the fourth run, on the
25-occurrence corpus of 2026-09-20 under `TZ=UTC`, moves it too: `1163 / 368 /
69 / 127`. That is expected, because this is the first run whose *input*
changed: at 25 occurrences a case has three times as long to diverge and the
adapter has three times as much work to do inside the same 20-second alarm.
A fifth run, on 2026-09-24 for
[finding 079](../findings/079-attribution-by-reproduction-dtical.md), gives
`1164 / 370 / 69 / 124` on the same corpus, moving `pass` by one; that run is
the one tabulated above.
Read this row as **1164 passing and 563 not**, and treat any comparison of its
`fail`, `error` or `other reading` columns against an earlier run of this
document as noise.

**Scoring this adapter needs `--timeout 14400`.** `score.py`'s default 900s
wall clock is not enough: the run dies in `subprocess.TimeoutExpired` with no
partial result, so the command as documented elsewhere on this page does not
reproduce this row. The seven cases added on
2026-09-17 account for 3 of the passes and 4 of the failures; the rest of the
movement from the previous row is the alarm, not the corpus. This is
[finding 047](../findings/047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md)'s point
arriving a second time: a terminal "no answer" bucket is not one fact, and a
deadline manufactures differences as readily as it hides them.

`DateTime::Event::ICal`'s row carries a second caveat the others do not, and it
is about me rather than about the library: its numbers depend on *how the result
set is enumerated*. The adapter walks `DateTime::Set`'s documented `->iterator`;
walking the identical set by repeated `->next` changes the answer on 68 of the
corpus's 291 `BYSETPOS` cases and moves 5 of them from disagree to agree. See
[finding 046](../findings/046-the-iterator-and-the-next-chain-disagree.md), and
`RRULE_DTICAL_ITER=chain` in the adapter to reproduce the other column.

`DateTime::Event::ICal`'s 563 disagreements are **fully decomposed** by
[finding 079](../findings/079-attribution-by-reproduction-dtical.md): all 443
that are not `BYSETPOS` are reproduced element for element, and 0 are left
unattributed. The claim there is one property of the library rather than a list
of defects — `recur()` rewrites the rule into a fixed set-algebra expression
over `DateTime::Event::Recurrence` and returns whatever that expression means,
filling every gap the rewrite opens from `DTSTART`. So
`FREQ=DAILY;BYMONTHDAY=15` returns the 15th of **March** once a year, and
`FREQ=MINUTELY;BYMINUTE=30` throws an uncaught exception. The 120 `BYSETPOS`
failures are out of scope there and covered by
[046](../findings/046-the-iterator-and-the-next-chain-disagree.md) and
[048](../findings/048-the-last-unswept-column-is-ambient-invariant.md).

[Finding 035](../findings/035-one-deletion-and-a-pinned-day.md)
accounts for the `BYMONTH` share of both: at `FREQ=WEEKLY` and `FREQ=MONTHLY`
the library reads `BYMONTH` as *month ∈ `BYMONTH` **and** day-of-month =
`DTSTART`'s day*, because `recur()` assembles the `BYMONTH` filter from a hash
the frequency handler has already deleted `byday` from. Supplying the one
missing default from the caller takes the 205 non-`BYSETPOS`
`WEEKLY`+`BYMONTH` cases from **0** passing to **205**, errors included. Its
vote on §3.3.10 comes from `_yearly_recurrence` and is unaffected.

`python-dateutil`'s 1728 is **not a result**: it is one of the two expanders
every case was corroborated by, so it only checks the harness.

`rrule-go`'s and `rust-rrule`'s scores are **not independent evidence** either,
for a different reason. Both are `python-dateutil` descendants by their own
READMEs' account, so counting either as a lineage would double-count dateutil.
When the corpus recorded 8 occurrences per case both returned the identical list
to their parent on all 3820 corroborated cases. At 25 occurrences `rust-rrule`
still does and `rrule-go` does not: it silently truncates at 106752 days past
`DTSTART`, which is `math.MaxInt64` nanoseconds, Go's `time.Duration` ceiling
([finding 066](../findings/066-the-ports-were-not-identical.md)). That is a
defect of the port and not of the recurrence logic it inherited, and it does not
change the lineage count.
[Finding 027](../findings/027-a-port-that-did-not-drift.md) has the Go
measurement and sizes `rrule.js`'s divergence from the same parent at 122 of
the 3813 corroborated cases that existed when it ran — the seven added since
are not among them, because `rrule.js` matches its parent on all seven —
decomposing all of it into the mechanisms findings 015 and 004/018/021
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

<!-- rowsum: skip reason="two overlapping property counts, not a partition" -->
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

### An unsatisfiable `BYSETPOS`

Not a corpus measurement — a probe, and the probe rules are not corpus members,
so nothing in the tables above moves. It is recorded here because it is the
kind of defect no `expect` list can catch: it needs a rule that is *wrong on
purpose*.

When `BYSETPOS` asks for the nth member of a set with fewer than n members, the
correct result for that period is the empty set.

<!-- rowsum: skip reason="one case, answers not counts" -->
| implementation | `FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-3` |
|---|---|
| `python-dateutil`, `rust-rrule`, `dmfs`, `ical4j` | *(empty — correct)* |
| `rrule.js` 2.8.1 | a full list, identical to `BYSETPOS=1` |
| `libical` 3.0.20 | a full list, `BYSETPOS` ignored at `WEEKLY` |
| `libical` master `4edd39a3` / `48d52b4b` | `29840908`, `39421221`, `49010330`, … |

`rrule.js` clamps an out-of-range **negative** `BYSETPOS` to the first element
of the set; positive out-of-range is handled correctly. This is the one cell
where `dateutil`, `rrule.js` and `rust-rrule` — one lineage vote by
[rule 24](../README.md) — do not agree with each other.

`libical` master's dates are its own `ICAL_LIMIT_RECURRENCE_SEARCH` budget
(100000, roughly 958 years at two `BYDAY` values per week) read back as an
occurrence: exhausting the budget is not one of the paths in
`icalrecur_iterator_next` that returns a null time. Lowering the limit with
`icallimit_set` moves the returned date linearly. Partially-satisfiable rules
such as `FREQ=MONTHLY;BYDAY=MO;BYSETPOS=5` are unaffected.

[Finding 055](../findings/055-a-question-with-no-answer.md).

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
Rust, C# or Swift. The Go and Rust results came back a perfect 1728 and were
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
