# Results

Produced by `conformance/score.py` against `conformance/cases.ndjson`
(1721 cases: valid rule, synchronized `DTSTART`, `UNTIL` value type matching
`DTSTART`, decidable from the recorded window). Exact list equality; no partial
credit.

**A failure is a disagreement between an implementation and this corpus.** It is
not, by itself, a defect in the implementation — and on the largest cluster
below the disagreement is between two *lineages*, not between right and wrong.
See [finding 016](../findings/016-independent-lineage-results.md) and the
caveats in `PROTOCOL.md`.

| implementation | version | lineage | pass | of | date |
|---|---|---|---:|---:|---|
| `python-dateutil` | 2.9.0.post0 | corroborating expander | 1721 | 1721 | 2026-09-07 |
| `rrule.js` | 2.8.1 | port of dateutil | 1695 | 1721 | 2026-09-07 |
| `ical4j` | 4.1.1 | independent (Java, 2004) | 1468 | 1721 | 2026-09-07 |
| `dmfs lib-recur` | 0.17.1 | independent (Java, 2013) | 1637 | 1721 | 2026-09-07 |

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

## Reproducing

```sh
tools/bootstrap.sh                       # RFCs, vendored dateutil, npm install rrule
python3 conformance/build_cases.py
python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
python3 conformance/score.py -- node conformance/adapters/rrulejs_adapter.js
```

For the two Java implementations, see
[`adapters/java/README.md`](adapters/java/README.md) (needs a JDK and Maven).

## Wanted

A result from an implementation in **Go, Rust, C# or Swift**. The four rows
above are two lineages, and finding 016 showed those two lineages disagree
systematically on `FREQ=YEARLY` expansion — so a third independent origin is
now worth more than it was when this file only had ports on it.

An adapter is about forty lines; `PROTOCOL.md` is the whole contract.
