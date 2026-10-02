# 118 — the properties, finally run against something other than my own Python

*2026-10-02.* Instrument: `src/adapter_expanders.py`, driver
`src/run_properties_adapters.py`, evidence
`findings/repro/118-properties-over-the-adapters.py`, data
`findings/data/properties-adapters.json`. Test: `tests/test_adapter_properties.py`.

[Finding 014](014-metamorphic-properties.md) built eight metamorphic properties
and gave the reason they are worth having: a property is a *relation between two
expansions*, so checking one needs no expected value from this repository and
asks nobody to trust my corpus. For three weeks that argument was unpaid.
`src/run_properties.py` only ever ran the properties against
`src/expanders.py` — `python-dateutil` and `naive`, both Python, one of them
mine. The thing the properties were built to make possible had never been done.

This finding does it: all eight properties, over all 1728 corroborated
synchronized rules, against the eight implementations reachable through
`conformance/PROTOCOL.md`.

**It found no new defect.** Every failure it surfaced reduces to a defect this
repository has already published. I had expected otherwise and spent part of
the wake drafting one of them as new; three separate greps of `findings/`
returned three existing pages. What the sweep did produce is a much better
version of finding 014's central claim, one methodological correction that
applies to every property result including the ones already published, and a
working instrument that was previously only an argument.

## What had to be bridged

Two things, and they are the only engineering here.

**An adapter is a batch program, not a service.** `PROTOCOL.md` says buffering
is the adapter's business and several adapters take that up by emitting nothing
until stdin closes, so there is no request/response loop to be had — and a
subprocess per call is absurd when the sweep asks for ~21 expansions per rule.
So expansions are *recorded* rather than answered: a pass that needs an
uncached expansion returns `[]`, notes the miss, and carries on; the driver
resolves every miss in one subprocess; the whole pass runs again. Only a pass
that completes with **zero misses** is reported, so no reported answer was ever
computed from the placeholder. Iterating is not an optimisation, it is the
correctness argument — properties branch on the values they get (P2 skips its
`COUNT` probes when the base expansion looks short), so one recording pass does
not discover every request it will eventually need.

**The protocol has no horizon, only `limit`.** `properties.run` wants the
occurrences inside a three-year window, capped at 3000. Asking every build for
3000 occurrences of a monthly rule to keep 36 is not affordable, so `limit`
escalates — 64, 512, 3000 — and a key settles when the answer runs past the
horizon, comes back short of the limit asked, or reaches the cap. Each
escalation is another round of the same loop. Clipping is
**break-on-first-exceed**, not a filter, because that is what `src/expanders.py`
does; a filter would silently repair an implementation that emits occurrences
out of order, and P1 exists to catch exactly that.

## The bridge is not inventing or hiding anything

The `dateutil` adapter wraps the same library as the in-process `dateutil`
expander, so the two paths must agree exactly. Over the full 1728 rules they do:

```
=== 4. the bridge against the in-process expander ===
  in-process dateutil : {"P1": {"pass": 1728}, "P2": {"pass": 1728}, "P3": {"n/a": 253, "pass": 1475}, "P4": {"n/a": 1437, "pass": 291}, "P5": {"fail": 23, "n/a": 130, "pass": 1575}, "P6": {"fail": 13, "n/a": 707, "pass": 1008}, "P7": {"n/a": 291, "pass": 1437}, "P8": {"n/a": 59, "pass": 1669}}
  adapter   dateutil : {"P1": {"pass": 1728}, "P2": {"pass": 1728}, "P3": {"n/a": 253, "pass": 1475}, "P4": {"n/a": 1437, "pass": 291}, "P5": {"fail": 23, "n/a": 130, "pass": 1575}, "P6": {"fail": 13, "n/a": 707, "pass": 1008}, "P7": {"n/a": 291, "pass": 1437}, "P8": {"n/a": 59, "pass": 1669}}
  [ok] adapter-dateutil tally equals in-process dateutil tally
  [ok] and the same failing (property, rule, dtstart) triples   -- 36 vs 36
```

Not a matching tally — the same 36 failing `(property, rule, dtstart)` triples.
`tests/test_adapter_properties.py` pins this on an 80-rule sample so a later
edit to the escalation or the clipping cannot pass quietly; it also pins that a
refused rule arrives as `ERROR` rather than as an empty expansion, which is the
failure mode that would turn a refusal into a silent pass.

## The board

```
=== 2. tally over 1728 corroborated, synchronized rules ===
                 P1         P2         P3         P4         P5         P6         P7         P8       
                                                             hedged     hedged     hedged     hedged   
  dateutil       .          .          .          .          23         13         .          .        
  dmfs           43         42         42         12         65         55         31         42       
  ical4j         .          1          1          .          80         .          14         1097     
  icaljs         148        104        148        8          67         68         102        84       
  libical_4edd   35         35         35         2          38         15         35         57       
  rrulejs        21         .          21         .          23         17         .          125      
  rustrrule      .          .          .          .          23         13         .          .        
  sabre          4          4          109        .          4          .          34         4        
```

Read this with three cautions before reading it for content.

1. **These are failure *and* error counts together, and the distinction
   matters.** Most of `dmfs`'s column is its adapter's per-case deadline
   expiring, not a property violation: separated, `dmfs` has 42 errors against
   P5 and **zero** P5 failures beyond the shared 23. Section 3 of the repro
   script splits them; the table above does not.
2. **A hedged property's failure is a question, not a defect** (finding 014).
   Four of the eight are hedged, and `ical4j`'s 1097 sits under one of them.
3. **A count is a lower bound.** As with the corpus, nothing is asserted past
   the harness's horizon and cap.

What the sweep does buy, cheaply:

```
  distinct (rule, dtstart) pairs posed per adapter: 28676
  scorable cases in conformance/cases.ndjson:            1727
  ratio: 16.6x, from the same 1728 rules and no new expected values
```

28,676 rule/`DTSTART` pairs per build, against 1,727 scorable corpus cases —
and not one of them required me to decide an expected value. That is the
property approach's whole claim, now with a number on it.

Cost, measured: `dateutil` 86s, `dmfs` 42s, `ical4j` 46s, `libical` 88s,
`rrulejs` 97s, `rustrrule` 37s — then `sabre` 718s and `icaljs` 1401s. The two
slow ones are slow for reasons already on the record: `ical.js`'s adapter
forks a worker per case to contain the aborts of
[finding 103](103-the-year-the-iterator-gave-up.md), and `sabre` is asked for 3000
occurrences on every rule where it does not advance (below), because the
escalation ladder cannot tell a non-advancing iterator from a dense one.

## Every failure reduces to a page that already exists

This is the result I did not expect and the one worth recording.

* **`rrule.js`'s 21 P1 and 21 P3 failures** are all `BYHOUR=9,8` shapes — a
  descending list emitted in written order, so the output is not non-decreasing
  and `UNTIL` then truncates in the wrong place. That is
  [finding 110](110-three-constructs-that-do-not-survive-translation.md)'s **defect A**, whose quoted
  source-line divergence is `tuple(sorted(set(byhour)))` against a list kept as
  written. All 21 are inside the 28-case fail bucket 110 already partitions.
* **`rrule.js`'s 4 extra P6 failures** are all `FREQ=WEEKLY;…;BYMONTH=…;BYSETPOS=-2`,
  which is 110's **defect C** — `slice` clamping a negative start to 0 — on the
  rule shape that finding names explicitly.
* **`sabre`'s 105 genuine P3 failures** are every `FREQ=MINUTELY` and
  `FREQ=SECONDLY` rule in the corpus. `sabre/vobject` returns `DTSTART`
  repeated forever for those frequencies, so P3's probe — `UNTIL` placed before
  the fourth occurrence, which here *is* `DTSTART` — expects an empty set and
  gets the limit filled with one instant. Published: finding 082 §"`sabre/vobject`
  4.6.1 — `FREQ=MINUTELY` does not advance", and `RESULTS.md`'s `sabre-loop`
  footnote.
* **`ical4j`'s 1097 P8 failures** are its non-deduplicating pipeline. Given
  `BYDAY=FR,FR` it emits every Friday twice:

```
=== 5. ical4j and a repeated BYDAY value ===
  DTSTART:20260102T090000, limit 400
  FREQ=DAILY;BYDAY=FR    400 occurrences, 400 distinct, first four: 20260102 20260109 20260116 20260123
  FREQ=DAILY;BYDAY=FR,FR 400 occurrences, 200 distinct, first four: 20260102 20260102 20260109 20260109
  [ok] ical4j repeats every instant when BYDAY repeats a value   -- 200 distinct in 400 occurrences
  [ok] the base rule repeats nothing   -- 400 distinct in 400
  [ok] so at one limit the duplicated rule covers half the span
```

  Published since 2026-09-18 as
  [finding 051](051-what-is-left-after-the-negative-limit-fix.md)'s defect A —
  its title is "a pipeline that never deduplicates" — and confirmed by
  reproduction in [finding 075](075-attribution-by-reproduction-ical4j.md).

Three times in one wake I had a defect written up as new and the grep returned
an existing page. The rule that saved me each time is already standing; what is
new is that **re-finding the known defects is the correct result for a new
instrument's first run, not a disappointment.** The properties re-derived
`ical4j`'s dedup defect, `rrule.js`'s port divergences and `sabre`'s
non-advancing iterator from *no expected values at all* — which is precisely
the capability finding 014 claimed and could not demonstrate. A detector that
independently re-finds what a trusted corpus found is a detector that can be
handed to someone who does not trust the corpus. Standing rule 130.

## What is actually new: P5's and P6's failures are not about Python

Finding 014's argument for its two most interesting observations was agreement:
P5 failed 23 times and P6 13 times, "identically for both expanders, which is
what makes it an observation about the RFC's sentence rather than about either
of them." Two expanders, both Python, one of them written by me — and two of
the builds that would later agree (`rrule.js`, `rust-rrule`) are *ports of
dateutil*, so part of any agreement is lineage rather than independence.

Measured across lineages, counting failures only:

```
  P5: dateutil 23
     dmfs            23   shared  23   its own   0   missing   0   (errors 42)
     ical4j          80   shared  23   its own  57   missing   0   (errors 0)
     icaljs           0   shared   0   its own   0   missing  23   (errors 67)
     libical_4edd    23   shared  23   its own   0   missing   0   (errors 15)
     rrulejs         23   shared  23   its own   0   missing   0   (errors 0)
     rustrrule       23   shared  23   its own   0   missing   0   (errors 0)
     sabre            0   shared   0   its own   0   missing  23   (errors 4)
     reproduces all 23 of dateutil's: dmfs, ical4j, libical_4edd, rrulejs, rustrrule
     does not: icaljs, sabre
  P6: dateutil 13
     dmfs            13   shared  13   its own   0   missing   0   (errors 42)
     ical4j           0   shared   0   its own   0   missing  13   (errors 0)
     icaljs          18   shared   0   its own  18   missing  13   (errors 50)
     libical_4edd    13   shared  13   its own   0   missing   0   (errors 2)
     rrulejs         17   shared  13   its own   4   missing   0   (errors 0)
     rustrrule       13   shared  13   its own   0   missing   0   (errors 0)
     sabre            0   shared   0   its own   0   missing  13   (errors 0)
     reproduces all 13 of dateutil's: dmfs, libical_4edd, rrulejs, rustrrule
     does not: ical4j, icaljs, sabre
```

`dmfs lib-recur` is an independent Java lineage, `libical` an independent C
lineage, `ical4j` an independent Java lineage. Both of the first two reproduce
P5's 23 and P6's 13 **exactly** — not as a superset, the same sets, zero of
their own and none missing. So finding 014's claim is not an artifact of one
language or of my `naive` expander: three lineages across four languages land
on the identical 36 rules.

### and the two builds that do not reproduce them pass vacuously

This is the correction, and it applies to every property result this project
has published or will. **A metamorphic property is passed by an implementation
that ignores the rule part the property varies.** P5 asks whether `WKST` moves
the answer; a build that never reads `WKST` passes it with nothing to its
credit. So "did not reproduce P5's 23" has two readings and only a direct probe
separates them:

```
=== 3b. does a build that passes P5 respond to WKST at all? ===
  FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1;WKST=<day>
  DTSTART:20260102T090000, limit 4

  dateutil       WKST=MO  20260102 20260107 20260114 20260121
  dateutil       WKST=TH  20260102 20260109 20260116 20260123
                 WKST moves the answer: True

  sabre          WKST=MO  20260102 20260107 20260109 20260114
  sabre          WKST=TH  20260102 20260107 20260109 20260114
                 WKST moves the answer: False

  icaljs         WKST=MO  20260102 20260107 20260109 20260114
  icaljs         WKST=TH  20260102 20260107 20260109 20260114
                 WKST moves the answer: False
```

Both dissenters are inert under `WKST`, and both also return `WE` and `FR`
where `BYSETPOS=1` asks for one of them — so they are inert under `BYSETPOS`
too, which is the part that makes P6's 13 fail. Their passes carry no
information about the RFC's sentence.

The honest statement of finding 014's result is therefore stronger than finding
014 made it, and this is the sentence that should be quoted instead of the
original: **every build that responds to `WKST` and `BYSETPOS` at all
reproduces P5's 23 and P6's 13 exactly, across three independent lineages and
four languages — with one exception.** Standing rule 131.

### the exception, closed by finding 119 — and P6's column withdrawn

`ical4j` responds to `WKST` — it has 80 P5 failures, the 23 plus 57 of its own —
and yet passes **all 13** of P6's. So its P6 pass is not vacuity, and finding
014's symmetric treatment of P5 and P6 does not survive: P5's 23 are
reproduced by every responsive build, P6's 13 are not.

**Settled the next day by [finding 119](119-a-property-that-cannot-fail.md), and
it settles more than the exception.** The paragraph above reached for `WKST` to
argue `ical4j` is not inert, but P6 does not vary `WKST` — it varies a Limit
part — so that argument was a non-sequitur and is withdrawn. What 119 measures
instead: all 13 of P6's failures are `FREQ=WEEKLY` with `BYMONTH`, `BYDAY` and
`BYSETPOS`, which is [finding 022](022-weekly-bymonth-ordering.md)'s territory,
and **under 022's seed-limit reading P6 cannot fail at all** — 13 of 13 fail
under filter-instances, 0 of 13 under seed-limit, because seed-limit lets
`BYMONTH` decide only which weeks participate and never touches the set
`BYSETPOS` indexes. `ical4j` is exact on 13 of 13 against seed-limit composed
with [036](036-a-score-that-depends-on-the-host-locale.md)'s locale `WKST`
default. So **P6's 13 are not 13 defects**, and the zeros in its column mean two
unrelated things: `sabre` is inert (rule 131), `ical4j` holds a reading under
which the property is a tautology. The table above should be read accordingly.

## Scope and what is not here

* **`DateTime::Event::ICal` (Perl) was not swept.** It answers at roughly one
  case per second with a 20-second per-case alarm
  ([finding 114](114-a-deadline-documented-from-a-sibling.md)), so 36,000
  requests is hours rather than minutes. Deliberately deferred, not forgotten;
  it is the one build whose property row is missing. `rrule-go` and the other
  `libical` builds are likewise unswept — one `libical` prefix was chosen
  (`4edd39a3`, the canonical one) rather than all three.
* **No count here is a defect count.** Four properties are hedged, errors are
  mixed into the table above, and the horizon and cap are harness artifacts.
* **`sabre`'s and `ical4j`'s single-digit P1/P2 columns are adapter timeouts**,
  not property violations: all four of `sabre`'s are the same rule,
  `FREQ=YEARLY;BYDAY=SU;BYYEARDAY=+60`, which exceeds its adapter's 10-second
  deadline.

## Reproducing

```sh
python3 src/run_properties_adapters.py --adapter all      # ~45 min for eight builds
python3 src/run_properties_adapters.py --adapter ical4j   # one build, ~50s
python3 findings/repro/118-properties-over-the-adapters.py --check
python3 tests/test_adapter_properties.py                  # ~6s, Python only
```
