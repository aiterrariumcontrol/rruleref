# Corpus file formats

Everything in `corpus/` is generated. `build_corpus.py` writes it; nothing is
hand-edited except `adjudications.json`, which is an *input*, and
`VERSION.json`, whose `version` label and its explanation are the only fields a
human sets.

**Every state of this corpus has an identifier.** `VERSION.json` records a
sha256 of the scored case list (`cases_id`), one of the whole corpus
(`corpus_id`), one of `conformance/score.py` (`scorer_id`), and a human label.
`score.py` prints them on every run; `python3 tools/corpus_id.py --check`
recomputes them from the committed files. A count published against one
`cases_id` is not a count against another, and this is how a consumer tells the
two apart without asking me (finding 069).

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

`meta` records the two caps this builder imposes: `occurrences_per_case` (25)
and `horizon_days` (109500 = 365 × 300 days). **Both are properties of the
builder, not of the recurrences.** That distinction is the whole reason
`expect_bound` exists.

**The horizon binds `expect` and not `reading_alternatives`.** No `expect` list
runs past it; 9 of the 361 recorded alternative readings, spread over 330
cases, do. An adapter that
clips at the declared horizon is therefore unable to match those 21 by equality
— see [finding 057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md)
for why neither clipping the alternatives nor widening the adapters is the right
fix, and what `score.py` does instead.

Each case:

| field | meaning |
|---|---|
| `rrule` | the `RRULE` property value, no `RRULE:` prefix |
| `dtstart` | the start; also the first occurrence whenever `dtstart_synchronized` |
| `expect` | occurrences, ascending, beginning at the first. **Read with `expect_bound`.** |
| `expect_bound` | `"complete"`, `"count"` or `"horizon"` — see below |
| `dtstart_synchronized` | `DTSTART` is itself the rule's first occurrence. When false, RFC 5545 §3.8.5.3 declares the recurrence set **undefined** and the case is an interop observation, not a conformance expectation. Computed by `naive`, so it is implementation-relative exactly where the two expanders disagree. |
| `rule_valid` | no `MUST NOT` of §3.3.10 that `src/validity.py` checks is violated. A *detector*, not a guarantee: `validity.NOT_CHECKED` lists what it does not test. |
| `reading_dependent` | `expect` would differ under at least one rival reading of §3.3.10. Always present; see below. |
| `reading_alternatives` | present **only** when `reading_dependent`: a map from the name of each rival reading to what `expect` would have been under it. |
| `corroborated_by` | the expanders that agreed. Always both, since disagreement files the case elsewhere. |
| `cells` | which cells of §3.3.10's `BYxxx`/`FREQ` table the rule exercises (`src/coverage.py`) |
| `branches` | which branches of §3.3.10's `RECUR` ABNF it takes (`src/grammar.py`) |
| `systematic_for` | the cell or branch this case was generated to cover, or `null` for a random case |

### `reading_dependent` and `reading_alternatives`

`corroborated_by` says two expanders agreed. It does **not** say the answer is
uncontested, because both expanders share a *reading* of §3.3.10.
`disputed.json` cannot answer this either — it records *implementation
disagreement*, and implementations agreeing on a contested reading land in
`corroborated.json`.

So the builder asks the question directly: each rival reading is implemented as
a second expansion, and where it gives a different answer that answer is
recorded under its own name. Four are known.

**`first_period_truncated`** — when `BYSETPOS` selects from the period
containing `DTSTART`, does it index the whole period (instances before
`DTSTART` are dropped afterwards) or the period cut at `DTSTART`? Finding 004
argues the text does not settle it; finding 018 measured it. Every `BYSETPOS`
case is expanded both ways.

**`dtstart_fill`** — in exactly two `YEARLY` cells, §3.3.10's expand/limit
table is the sole authority *and* leaves a coarser date field unspecified, and
the DTSTART-fill sentence on the same page then says where that field comes
from. The table says expand; the sentence says the field is already
determined. Neither says which wins, and three independent lineages behave
exactly as if the field had been filled from `DTSTART`. Finding 024
implements that as a source-to-source rewrite —
`FREQ=YEARLY`+`BYMONTHDAY` without `BYMONTH` gains `BYMONTH=month(DTSTART)`,
`FREQ=YEARLY`+`BYWEEKNO` without `BYDAY` gains `BYDAY=weekday(DTSTART)` — and
expands the rewritten rule.

The `dtstart_fill` reading is recorded only when the rewritten rule clears the
same bar as everything else in this file: both expanders agree on it, **and**
it yields a full `len(expect)` occurrences. It fires strictly less often than
`expect`'s reading, so it can run out inside the expander's ~30-year horizon
where `expect` did not — and a list cut short by a cap I chose is not "the same
answer read differently". Of the 404 corroborated cases with one of the two
shapes, 201 carry the reading, 28 have it coincide with `expect`, and 175 are
left unannotated by that horizon rule.

**`week_based_year`** — RFC 5545 §3.3.10 says `BYWEEKNO` names "weeks of the
year", numbered as in ISO 8601, and that "a week is defined as a seven day
period". Such a week can hold days of two calendar years; §3.3.10 never says
which `FREQ=YEARLY` *period* those days belong to. `expect` takes the calendar
year the day sits in — and so resolves the day's week *number* against the year
that owns the week while assigning its *period* by the calendar year, a hybrid
that misattributes straddling days in whichever direction the straddle runs.
This reading takes the owning year for both. The two are indistinguishable at
`INTERVAL=1` without `BYSETPOS`; finding 059 has the demonstration that
separates them.

**`week_based_year+dtstart_fill`** — the two composed, recorded under its own
name because on `BYWEEKNO` rules with no `BYDAY` neither half alone reproduces
what the independent lineages return. It is omitted where it would duplicate
one of the others.

Both week-based readings are declined on a list shorter than `len(expect)`,
for the reason given above for `dtstart_fill` but without the
`_short_of_horizon` analysis that would separate "the rule ran out" from "my
horizon did"; finding 059 measures what that costs.

A consumer that treats `expect` as ground truth without looking at this flag
silently inherits my position on findings 004, 024 and 059.
`conformance/cases.ndjson` carries `reading_alternatives` through for the same
reason, and `conformance/score.py` counts an implementation matching any of
them as `fail_other_reading` rather than `fail`, naming which — a disagreement
about the specification, not a defect.

One consequence is sharper than the flag itself. 114 cases are both
reading-dependent and `dtstart_synchronized`, and for 26 of them `DTSTART` is
the first occurrence *because of* the reading taken: under a rival reading
recorded beside them the expansion no longer starts at `DTSTART`, and §3.8.5.3
would then declare their recurrence set undefined. So those 26 are scorable
conformance evidence only under one reading. (Counted on 2026-09-18 by asking,
for each such case, whether every list in `reading_alternatives` still begins
at `DTSTART`. This paragraph previously read "all 25 … 24 of the 25", a count
left behind by corpus growth; the 24 was right for the corpus of the day.) They are kept and marked rather than dropped: dropping them
would shrink the corpus by a decision the reader could no longer see.

`reading_dependent` is false for every case that carries neither `BYSETPOS` nor
one of the two `YEARLY` shapes: the question does not arise there. It is
present on every case so that its absence can never be mistaken for "not
checked".

### `expect_bound`

`expect` is a **prefix** of the recurrence set unless this says otherwise.

* **`complete`** — the rule provably terminates inside the recorded window, so
  `expect` is the entire recurrence set and a consumer may assert there is
  nothing after it. Decided from the rule text alone: `COUNT` ≤ `len(expect)`,
  `UNTIL` inside the horizon *and* the occurrence cap did not bite first, or —
  for an *empty* `expect` — a proof that the rule never fires at all.
* **`count`** — stopped at the 25-occurrence cap. The set continues.
* **`horizon`** — fewer than 25 occurrences were found within the horizon, and
  the set may still continue **after** the horizon. This is the corpus's only
  bound that is a statement about the *window* rather than about the rule, and
  it is now down to 11 cases.

An empty `expect` used to land here, and that was the weakest claim in the
corpus: an absence observed inside a window is not an absence.
[Finding 067](../findings/067-an-empty-list-nobody-had-proved.md) supplies the
missing decision procedure. The proleptic Gregorian calendar is exactly
periodic over 146097 days (400 years = 4800 months = 20871 weeks), every `BY*`
part is a predicate on a date's position inside that structure, and `INTERVAL=k`
extends the period to an `lcm` — so searching one full period decides emptiness
outright. Every one of the 285 empty lists was outside its own decision bound:
the shortest period any of them needs is 146097 days and the horizon is 109500.
`tools/prove_empty.py` proves all 285 empty (61 structurally, 224 by period
search) and `src/build_corpus.py` now calls it, so those cases are `complete`.
Where the argument does not reach — sub-daily `FREQ`, or an `UNTIL` past the
horizon — an empty `expect` still says `horizon`, which remains honest.

An earlier schema had a boolean `truncated` (`len(expect) == N`) whose false
branch invited exactly the wrong reading. On 2026-09-07, 67 of the 450 cases it
marked "not truncated" demonstrably continued past the horizon — a consumer
treating that flag as "complete" would have generated 67 false failures against
every implementation it tested. `truncated` was replaced rather than
documented. The three values above collapse to the old boolean nowhere.

Distribution in the current corpus: 3424 `count`, 11 `horizon`, 383 `complete`
(before finding 067 was applied: 3424 / 296 / 98). The 98 `complete` cases that
predate 067 were checked against an *unbounded* dateutil expansion and end
exactly where `expect` ends; the 285 added by 067 are empty and proved so. The
11 that remain `horizon` are genuinely sparse rules — `FREQ=YEARLY;INTERVAL=3`
and `INTERVAL=4` shapes, and one `MONTHLY;INTERVAL=2;BYSETPOS` pair — that do
fire but not 25 times in 300 years.

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
