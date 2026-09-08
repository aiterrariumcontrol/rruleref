# Corpus file formats

Everything in `corpus/` is generated. `build_corpus.py` writes it; nothing is
hand-edited except `adjudications.json`, which is an *input*.

Reading order for a new consumer: this file, then
[`../conformance/PROTOCOL.md`](../conformance/PROTOCOL.md). If you only want to
run the corpus against an implementation, you want
`conformance/cases.ndjson` and can skip everything below.

All datetimes are `YYYYMMDDTHHMMSS` in **local (floating) time** — no `Z`, no
`TZID`. That is deliberate; see PROTOCOL.md.

---

## `corroborated.json` — the corpus

```
{"meta": {...}, "cases": [ {...}, ... ]}
```

`meta` records the two caps this builder imposes: `occurrences_per_case` (8)
and `horizon_days` (10958 ≈ 30 years + 8 days). **Both are properties of the
builder, not of the recurrences.** That distinction is the whole reason
`expect_bound` exists.

Each case:

| field | meaning |
|---|---|
| `rrule` | the `RRULE` property value, no `RRULE:` prefix |
| `dtstart` | the start; also the first occurrence whenever `dtstart_synchronized` |
| `expect` | occurrences, ascending, beginning at the first. **Read with `expect_bound`.** |
| `expect_bound` | `"complete"`, `"count"` or `"horizon"` — see below |
| `dtstart_synchronized` | `DTSTART` is itself the rule's first occurrence. When false, RFC 5545 §3.8.5.3 declares the recurrence set **undefined** and the case is an interop observation, not a conformance expectation. Computed by `naive`, so it is implementation-relative exactly where the two expanders disagree. |
| `rule_valid` | no `MUST NOT` of §3.3.10 that `src/validity.py` checks is violated. A *detector*, not a guarantee: `validity.NOT_CHECKED` lists what it does not test. |
| `reading_dependent` | `expect` would differ under the *other* reading of §3.3.10's first period. Always present; see below. |
| `reading_alternative` | present **only** when `reading_dependent`: what `expect` would have been under that other reading. |
| `corroborated_by` | the expanders that agreed. Always both, since disagreement files the case elsewhere. |
| `cells` | which cells of §3.3.10's `BYxxx`/`FREQ` table the rule exercises (`src/coverage.py`) |
| `branches` | which branches of §3.3.10's `RECUR` ABNF it takes (`src/grammar.py`) |
| `systematic_for` | the cell or branch this case was generated to cover, or `null` for a random case |

### `reading_dependent`

`corroborated_by` says two expanders agreed. It does **not** say the answer is
uncontested, because both expanders share a reading of §3.3.10: when `BYSETPOS`
selects from the period containing `DTSTART`, does it index the whole period
(instances before `DTSTART` are dropped afterwards) or the period cut at
`DTSTART`? Finding 004 argues the text does not settle it. `disputed.json`
cannot answer this either — it records *implementation disagreement*, and
implementations agreeing on a contested reading land in `corroborated.json`.

So the builder asks the question directly. Every `BYSETPOS` case is expanded
under both readings; `reading_dependent` is true when the first `len(expect)`
occurrences differ, and `reading_alternative` then records the other answer.

A consumer that treats `expect` as ground truth without looking at this flag
silently inherits my position on finding 004. `conformance/cases.ndjson`
carries `reading_alternative` through for the same reason, and
`conformance/score.py` counts an implementation matching it as
`fail_other_reading` rather than `fail` — a disagreement about the
specification, not a defect.

One consequence is sharper than the flag itself. All 25 reading-dependent cases
that are also `dtstart_synchronized` have `DTSTART` as their first occurrence
*because of* the reading taken — expanding them under the other reading, 24 of
the 25 no longer start at `DTSTART`, and §3.8.5.3 would then declare their
recurrence set undefined. So those cases are scorable conformance evidence only
under one reading. They are kept and marked rather than dropped: dropping them
would shrink the corpus by a decision the reader could no longer see.

`reading_dependent` is false for every case without `BYSETPOS`: the question
does not arise there. It is present on every case so that its absence can never
be mistaken for "not checked".

### `expect_bound`

`expect` is a **prefix** of the recurrence set unless this says otherwise.

* **`complete`** — the rule provably terminates inside the recorded window, so
  `expect` is the entire recurrence set and a consumer may assert there is
  nothing after it. Decided from the rule text alone: `COUNT` ≤ `len(expect)`,
  or `UNTIL` inside the horizon *and* the occurrence cap did not bite first.
* **`count`** — stopped at the 8-occurrence cap. The set continues.
* **`horizon`** — fewer than 8 occurrences were found within ~30 years. The set
  may still continue **after** the horizon.

An earlier schema had a boolean `truncated` (`len(expect) == 8`) whose false
branch invited exactly the wrong reading. On 2026-09-07, 67 of the 450 cases it
marked "not truncated" demonstrably continued past the horizon — a consumer
treating that flag as "complete" would have generated 67 false failures against
every implementation it tested. `truncated` was replaced rather than
documented. The three values above collapse to the old boolean nowhere.

Distribution in the current corpus: 3363 `count`, 352 `horizon`, 98 `complete`.
All 98 `complete` cases were checked against an *unbounded* dateutil expansion
and end exactly where `expect` ends.

## `disputed.json`

Same shape, but instead of `expect` there are `naive` and `dateutil` — the two
answers — and an optional `adjudication`. These are the cases the corpus does
**not** vouch for. Do not score against them.

## `adjudications.json`

Hand decisions, keyed by rule + `DTSTART`, re-attached on every rebuild so
regenerating the corpus cannot silently lose them. The only file here that is
an input rather than an output.

## `date-value-type.json`

Finding 011: `DTSTART` with `VALUE=DATE`. Separate because `dateutil` has no
DATE value type and so cannot adjudicate these, so `expect` here comes from
§3.3.10's own "MUST be ignored" remedy rather than from expander agreement.
`observed_same_days` and `observed_midnight_only` are kept apart because an
earlier version compared date strings against date-time strings and was
measuring formatting.

## `rfc5545-examples.json`

Finding 005: the 39 worked `RRULE` examples printed in RFC 5545 §3.8.5.3,
extracted **by program** from the hashed RFC text and never retyped.
`expected_is_prefix_only` marks the examples the RFC itself abbreviates with
`...`. `errata_applied` records the one place the printed text is corrected,
citing Verified Erratum 3883 — someone else's finding, not mine.

## `coverage.json`, `grammar-coverage.json`, `pair-coverage.json`

Measurements *about* the corpus, not cases: which cells of the §3.3.10 table,
which ABNF branches, and which realizable pairs of branches have at least one
case. Presence, not exhaustiveness. `uncovered` and
`unrealizable_by_reason` are the parts worth reading.
