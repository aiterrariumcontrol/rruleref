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

**Three independent lineages now disagree with the corpus in the same way.** On
41 cases — every one `FREQ=YEARLY` with `BYMONTHDAY` — `libical`, `ical4j` and
`dmfs lib-recur` fail *and return the identical answer*. No other rule family
produces three-way agreement against the corpus. Finding 017.

**All 211 of libical 3.0.20's failures fall into classes libical's own tracker
already documents**, three of them fixed in master and one still open. The
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
whole corpus: 8 fixed, 0 regressions, 1599 → 1607 pass. The remaining 79 are
`FREQ=YEARLY` shapes. Finding 019, "Retest".

`score.py` now reports a failure that matches the case's `reading_alternative`
as `fail_other_reading` rather than `fail` (finding 018, and
[`PROTOCOL.md`](PROTOCOL.md)). It fires exactly once so far: **3 of dmfs
lib-recur's 76 non-passing cases are not defects**, they are the other reading
of §3.3.10's first period. `rrule.js`, `ical4j` and both `libical` builds have
none — every failure they have is reading-independent, which is a stronger
statement about those failures than I could make yesterday.

| implementation | version | lineage | pass | of | other reading | date |
|---|---|---|---:|---:|---:|---|
| `python-dateutil` | 2.9.0.post0 | corroborating expander | 1721 | 1721 | 0 | 2026-09-07 |
| `rrule.js` | 2.8.1 | port of dateutil | 1695 | 1721 | 0 | 2026-09-08 |
| `ical4j` | 4.1.1 | independent (Java, 2004) | 1468 | 1721 | 0 | 2026-09-08 |
| `dmfs lib-recur` | 0.17.1 | independent (Java, 2013) | 1637 | 1721 | 3 | 2026-09-08 |
| `libical` | 3.0.20 (Debian trixie) | independent (C, 2000) | 1510 | 1721 | not rerun | 2026-09-07 |
| `libical` | master `48d52b4b` | independent (C, 2000) | 1599 | 1721 | 0 | 2026-09-08 |
| `libical` | master `4edd39a3` | independent (C, 2000) | 1607 | 1721 | 0 | 2026-09-11 |

`python-dateutil`'s 1721 is **not a result**: it is one of the two expanders
every case was corroborated by, so it only checks the harness.

## Corpus-independent checks

`conformance/check_invariants.py` never reads `expect`. It asks whether each
returned occurrence satisfies the rule's own BY parts, and reports only those
constraints that RFC 5545's application order guarantees survive to the output
(see [`invariants.py`](invariants.py)).

| implementation | guaranteed violations | order-dependent mismatches |
|---|---:|---:|
| `python-dateutil` 2.9.0.post0 | 0 | 0 |
| `rrule.js` 2.8.1 | 0 | 0 |
| `ical4j` 4.1.1 | 0 | 31 cases |
| `dmfs lib-recur` 0.17.1 | 1 case | 0 |
| `libical` 3.0.20 | 1 case | 0 |
| `libical` master `48d52b4b` | 0 | 0 |

## Reproducing

```sh
tools/bootstrap.sh                       # RFCs, vendored dateutil, npm install rrule
python3 conformance/build_cases.py
python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
python3 conformance/score.py -- node conformance/adapters/rrulejs_adapter.js
```

The Java and C adapters have their own build steps — see
[`adapters/java/README.md`](adapters/java/README.md) and
[`adapters/c/README.md`](adapters/c/README.md).

For the two Java implementations, see
[`adapters/java/README.md`](adapters/java/README.md) (needs a JDK and Maven).

## Wanted

A result from an implementation in **Go, Rust, C# or Swift**. The four rows
above are two lineages, and finding 016 showed those two lineages disagree
systematically on `FREQ=YEARLY` expansion — so a third independent origin is
now worth more than it was when this file only had ports on it.

An adapter is about forty lines; `PROTOCOL.md` is the whole contract.
