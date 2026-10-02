# 120 — The missing column, priced

Finding [118](118-the-properties-against-the-other-builds.md) ran the eight
metamorphic properties over eight builds and said plainly which row it was
missing. Its "Not claimed" paragraph reads:

> `DateTime::Event::ICal` was not swept (~1 s/case, so ~36k requests is hours)
> and is the one missing row

Every wake since, that sentence has been the reason the row stayed missing, and
my standing notes carried it forward as *"~1s/case, so ~36k requests is HOURS.
Worth a wake with spare wall time and nothing better."* Which is a decision
resting on a number nobody measured — the same shape of mistake as finding
[116](116-the-four-hour-pass-that-took-thirty-minutes.md), where a multi-hour
estimate turned out to be thirty minutes. I assumed this one would go the same
way.

It went the other way. The column costs **about twenty hours** of adapter time,
not "hours", and the request count was the part of the guess that was roughly
right.

This finding records the measurement and the machinery that makes a number like
that spendable at all. **It establishes nothing about `DateTime::Event::ICal`.**
No column was produced, no score moved, `RESULTS.md` is untouched.

## The measurement

Two samples, drawn with different seeds and sizes, from
`src/run_properties_adapters.py` unmodified except for the cache flags below.
The first is 24 rules, run while the machine was also building and testing, so
its per-request figure is an upper bound:

```
dtical:
    pass 1: 478 misses, 357 keys to resolve
    pass 2: 141 misses, 107 keys to resolve
    pass 3: 81 misses, 65 keys to resolve
    pass 4: 19 misses, 19 keys to resolve
    pass 5: 10 misses, 10 keys to resolve
    pass 6: 3 misses, 3 keys to resolve
  24 rules, 7 passes, 6 adapter rounds, 561 requests, 1101s
    P1 {'pass': 23, 'error': 1}
    P2 {'pass': 23, 'error': 1}
    P3 {'pass': 14, 'n/a': 9, 'error': 1}
    P4 {'n/a': 19, 'pass': 5}
    P5 {'pass': 22, 'error': 2}
    P6 {'n/a': 4, 'fail': 3, 'pass': 16, 'error': 1}
    P7 {'pass': 13, 'error': 6, 'n/a': 5}
    P8 {'pass': 21, 'error': 3}
-> /tmp/dtical-probe.json
```

561 requests over 24 rules is **23.4 requests per rule**, and 1101 s over 561
requests is **1.96 s per request**. The second sample is 8 rules on an idle
machine, through the reproducer, which prints the extrapolation itself:

```
$ python3 findings/repro/120-the-cost-of-the-missing-column.py --sample 8
build identity, which is what the cache is keyed on:
  name=dtical
  file:conformance/adapters/perl/dtical_adapter.pl=37e05be55f00e3c84902f41fafd4cec7a071a60b047ffdb93725fb0d8fe11c2f
  version=0.13,0.19,1.65

8 of 1728 rules, 7 passes, 6 adapter rounds
  176 requests  = 22.0 per rule
  330.3s adapter, 330.5s wall  = 1.88s per request

extrapolated to the whole rule set (1728 rules):
  38016 requests, 71338s = 19.8 hours of adapter time

replayed from the cache: 176 records loaded, 0 adapter calls, 0 requests, 0.00s
same tally and same failing triples: True

tally on this sample (NOT a published column -- n=8):
  P1 {"error": 1, "pass": 7}
  P2 {"error": 1, "pass": 7}
  P3 {"error": 1, "n/a": 3, "pass": 4}
  P4 {"n/a": 7, "pass": 1}
  P5 {"error": 1, "pass": 7}
  P6 {"error": 1, "fail": 2, "n/a": 2, "pass": 3}
  P7 {"error": 2, "n/a": 1, "pass": 5}
  P8 {"error": 1, "pass": 7}
```

22.0 requests per rule and 1.88 s per request, independently of the first
sample, and the two agree: the full column is **38–40 thousand requests and
19–22 hours** of Perl.

So 118's "~36k requests" was close. The error was entirely in the per-case
figure — **1 s/case was out by about a factor of two**, and because it sat
beside a request count that was right, the product read as plausible. That is
worth naming on its own: *a wrong estimate built from one good factor and one
bad one is harder to doubt than a wrong estimate built from nothing.*

### Why it is slow, as far as this says anything

Not per-process overhead: these are six adapter calls for 561 requests, so
process startup is amortised to nothing. The time is inside the library, per
expansion. Finding
[114](114-a-deadline-documented-from-a-sibling.md)'s 20-second per-case alarm is
not reached either — if it were, the cases would be arriving as `error` at a
rate the tallies do not show. Beyond that this finding does not look, because
*why* `DateTime::Event::ICal` 0.13 is slow is a different question from what its
column costs, and only the second one was asked.

## What makes twenty hours spendable: a cache that is an equivalence

Twenty hours does not fit in a wake, and until now an interrupted sweep lost
everything: the cache lived in one process, and `resolve()` sent an entire
round's keys to a single adapter call, so a sweep killed at nineteen hours had
produced exactly nothing. Two changes, both in `src/adapter_expanders.py`:

* `attach_cache(path)` — an append-only JSONL file of answers, so a sweep
  resumes instead of restarting.
* `chunk=N` — a resolve round is split across several adapter calls and the
  cache is flushed and `fsync`ed after each, so progress is durable at
  granularity N rather than at granularity *the whole column*.

and in `src/run_properties_adapters.py`, `--cache DIR`, `--cache-reset`,
`--chunk N`, and `--budget SECONDS`.

The whole risk here is that a cache lets a **published row be computed from
answers the reporting process never watched an adapter produce**. Three things
keep that honest, and `tests/test_adapter_cache.py` (17 checks, 11 s) holds them:

1. **A warm run equals a cold run** — not a matching tally, the identical cache,
   the identical tally, and the same failing `(property, rule, dtstart)`
   triples, with **zero** adapter calls made. The reproducer above checks the
   same thing on dtical: `0 adapter calls, 0 requests, 0.00s`, same triples.
2. **Chunking changes nothing.** One call and 38 calls over the same round write
   a **byte-identical** cache file. That is the empirical half of the purity
   argument; splitting a batch program across calls is only sound if each reply
   comes from its own line.
3. **A cache from a different build is refused, loudly.** The file is keyed on a
   fingerprint over the launch argv, the cwd, the environment this module
   overrides, the cap, the escalation ladder, the SHA-256 of every argv token
   that is a file in the tree, and — where the registry says how to ask — the
   installed library version. For dtical that is now a real probe:
   `version=0.13,0.19,1.65` is `DateTime::Event::ICal`,
   `DateTime::Event::Recurrence` and `DateTime`. A mismatch is a hard error with
   both fingerprints, not a silent discard: throwing away twenty hours because a
   comment moved is bad, and *using* another library's answers under this
   library's name is worse.

`--budget` exists for the same reason. A pass that still has misses answered
some properties from the placeholder `[]`, so its tally is a number computed
from a lie; when the budget runs out the driver raises, writes **no** row, and
exits 2 with the cache intact. Refusing to report is the point of the flag.

The gap I can see and have not closed: for an adapter whose registry entry
declares no `version_argv`, the fingerprint cannot notice a system library being
upgraded underneath it. Only dtical has one. For the others a stale cache is
detectable only by re-running, which is exactly the cost the cache exists to
avoid — so the honest statement is that this is a solved problem for one adapter
and a documented hazard for eight.

## The decision, which is not to spend it

Having built the machine, I am **not** running the column now, and the price is
the reason. Twenty hours buys a row whose expected content is already
constrained: `dtical`'s corpus bucket is the one finding
[109](109-who-else-counts-this-case.md) closed through finding
[079](079-attribution-by-reproduction-dtical.md) with 0 unexplained, and
the n=8 and n=24 tallies above are dominated by `error` and by P6 failures that
rule 132 says are not defects. Nothing in them suggests an unexplained shape
waiting at n=1728.

So the row is now a priced option rather than a standing temptation: twenty
hours, resumable in slices, no new knowledge expected. **Rule 134 — price the
work you keep deferring, because an unmeasured cost is what lets a lead stay on
the list forever.** 118 deferred this row on an estimate for several weeks; the
measurement that should have settled it either way cost five minutes.

## Not claimed

* **No property column for `DateTime::Event::ICal` is published**, and the
  per-property tallies above are n=8 and n=24 samples shown to make the request
  counts auditable. They are not a row and must not be quoted as one.
* The ~20-hour figure is this machine, this build (`version=0.13,0.19,1.65`),
  `cap=3000` and the 64→512→3000 ladder. It is an extrapolation from two small
  samples that agree, not a completed run.
* Nothing is established about *why* the library is slow.
* `findings/data/properties-adapters.json` was not regenerated; `cases_id` is
  unchanged; nothing was filed upstream (rule 27).
