# Results

Produced by `conformance/score.py` against `conformance/cases.ndjson`
(1722 cases: valid rule, synchronized `DTSTART`, decidable from the recorded
window). Exact list equality; no partial credit.

**A failure is a disagreement between an implementation and this corpus.** It
is not, by itself, a defect in the implementation. See
[`../findings/015-conformance-harness-and-rrulejs.md`](../findings/015-conformance-harness-and-rrulejs.md)
and the caveats in `PROTOCOL.md`.

| implementation | version | pass | of | date | notes |
|---|---|---:|---:|---|---|
| `python-dateutil` | 2.9.0.post0 | 1722 | 1722 | 2026-09-07 | **Not a result.** dateutil is one of the two expanders every case was corroborated by, so this only checks the harness. |
| `rrule.js` | 2.8.1 | 1696 | 1722 | 2026-09-07 | 26 failures in three clusters; see finding 015. |

## Reproducing

```sh
tools/bootstrap.sh                       # fetch the RFCs, vendor dateutil, npm install rrule
python3 conformance/build_cases.py
python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
python3 conformance/score.py -- node conformance/adapters/rrulejs_adapter.js
```

## Wanted

Any implementation that is **not** a descendant of `python-dateutil`. Every
result above is either dateutil or a port of it
([finding 003](../findings/003-implementation-lineage.md)), so the corpus has
still never been read by genuinely independent machinery. An adapter for a Go,
Rust, Java or C# implementation is 30 lines and would be worth more than any
further measurement I can make from here.
