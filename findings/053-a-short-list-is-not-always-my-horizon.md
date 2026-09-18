# 053 — A short list is not always my horizon: deciding it with the 400-year cycle

**Status:** Measured. **Date:** 2026-09-18.
**This is a defect report against my own corpus builder.** No new
implementation defect is claimed.

## What was open

[Finding 024](024-dtstart-fill-versus-the-table.md) records, beside `expect`,
what each contested case would look like under the rival *DTSTART-fill*
reading of RFC 5545 §3.3.10, so that a consumer can see both answers instead
of inheriting mine silently. [Finding 052](052-byweekno-is-one-lineage-deep.md)
found that two guards inside `src/build_corpus.py` were suppressing that
record on cases that needed it. One was a plain bug and was fixed there. This
is the other one.

The guard: `_dtstart_fill_reading` required the rewritten rule to yield
*exactly* `n` occurrences, and returned `None` — recording nothing — when it
yielded fewer. Its stated reason was that the DTSTART-fill reading fires
strictly less often, so it can run out inside the expander's 30-year horizon
where `expect` did not, and that

> a shorter list is not "the same answer read differently" — it is an artifact
> of a cap I chose (and an adapter, which has no horizon, would not produce
> it).

The parenthesis is false. On `FREQ=YEARLY;BYWEEKNO=53` at `DTSTART=20261228`,
`ical4j` and `dmfs lib-recur` return exactly the six-item short list
(finding 052). The horizon explanation and the reading's own answer had been
collapsed into one `return None`.

## The fix, and why it is a decision rather than a bigger number

Standing rule 33 says a difference measured inside a truncated window is not
an omission, and its remedy is to compare over a longer window. Applied
naively that only moves the cap: 30 years becomes 200, and a rule sparse
enough still gets dropped for the same unexamined reason.

For this rewrite the question is decidable instead. `_dtstart_fill_rewrite`
only ever applies to `FREQ=YEARLY` rules, and a `FREQ=YEARLY` rule selects
dates out of the calendar's configuration — month lengths, weekday alignment,
ISO-8601 week numbering — and nothing else. **That configuration repeats
exactly every 400 Gregorian years: 146097 days, which is also exactly 20871
whole weeks.** With `INTERVAL=k` the rule's own phase repeats every
`lcm(k, 400)` years. So one full cycle from `DTSTART` settles it:

* **some occurrences, fewer than `n`** — the set is infinite (whatever the
  cycle contains, the next cycle contains again), and the 30-year window was
  the only reason the list was short. Expand over as many cycles as the
  observed density needs and take the first `n`.
* **none at all in a full cycle** — the rewritten rule selects no date in any
  configuration the calendar can present. Its occurrence set is empty, and the
  empty list *is* the reading's answer, not a truncation of it.
* **anything else** — still short after enough cycles to cover `n` at the
  observed density, which a rule bounded by its own `COUNT` or `UNTIL` will
  be. Still returns `None`, still unrecorded. Verified to fire on
  `FREQ=YEARLY;BYWEEKNO=53;UNTIL=20400101T090000` and on `;COUNT=3`.

Either way the answer is corroborated at its own reach, not inside my window:
`dateutil` is asked for `n` occurrences with no horizon imposed, and must
return the same list. Of the 87 cases the guard had been dropping, **all 87
agree** — 38 reach `n` inside one cycle, 49 are empty over a full cycle, none
needed a second cycle, and none disagreed with `dateutil`.

`src/build_corpus.py`, `_short_of_horizon`.

## What it changes in the corpus

Standing rule 12: the corpus was rebuilt into a temporary directory and every
published file compared against the committed one. `disputed.json` (26 cases),
`coverage.json`, `grammar-coverage.json` and `pair-coverage.json` are
**byte-identical**, and so is `corroborated.json`'s `meta`. The case set is
unchanged: 3820 corroborated, the same 3820 identities, 1728 of them scorable.

The whole of the change is **87 cases that gain a `dtstart_fill` entry under
`reading_alternatives`**, and nothing else in any file moves — no `expect`
list, no `rule_valid`, no `dtstart_synchronized`, no coverage cell. Of the 87,
77 previously had no alternative at all and so flip `reading_dependent` from
`false` to `true`; the other 10 already carried a `first_period_truncated`
alternative, which is preserved beside the new one unchanged. All 87 are
`FREQ=YEARLY` — the only shape `_dtstart_fill_rewrite` applies to. 52 carry
`BYWEEKNO`, 64 `BYMONTH`, 62 `BYMONTHDAY`, 23 `BYYEARDAY`, 21 `BYSETPOS`,
15 `BYDAY`, 14 an `INTERVAL` above 1.

38 of the new alternatives are non-empty — the list the reading yields once the
30-year horizon is out of the way — and 49 are empty, meaning the rewritten
rule selects no date anywhere in a full Gregorian cycle. Re-running
`conformance/build_cases.py` propagates exactly 29 of the 87 into
`conformance/cases.ndjson`, changing only those cases' `reading_alternatives`
field; 21 of the 29 alternatives are non-empty and 8 are empty.

## What it changes in the scores

29 of the 87 are in the scored subset (`conformance/cases.ndjson`; standing
rule 32 — `corroborated.json` is a superset and its counts are not scores).
`score.py` was run over those 29 against the rebuilt corpus, for every version
`RESULTS.md` publishes a row for. `alt` is `fail_other_reading`: the adapter's
answer equals the newly recorded `dtstart_fill` list exactly, where before this
change the same answer scored as a plain `fail`. `empty` is the part of `alt`
where that list is the empty one.

| | pass | **alt** | *of which empty* | fail | error |
|---|---:|---:|---:|---:|---:|
| dateutil 2.9.0 | 29 | 0 | 0 | 0 | 0 |
| rrule.js 2.8.1 | 29 | 0 | 0 | 0 | 0 |
| rust-rrule 0.14.0 | 29 | 0 | 0 | 0 | 0 |
| libical 3.0.20 | 0 | **5** | 0 | 0 | 24 |
| libical master `48d52b4b` | 0 | **14** | 8 | 0 | 15 |
| libical master `4edd39a3` | 0 | **14** | 8 | 0 | 15 |
| ical4j 4.1.1 | 0 | **8** | 8 | 21 | 0 |
| ical4j 4.3.0 | 0 | **8** | 8 | 21 | 0 |
| dtical 0.13 (`DateTime::Event::ICal`) | 5 | **14** | 0 | 10 | 0 |
| dmfs lib-recur 0.17.1 | 14 | 0 | 0 | 7 | 8 |
| sabre/vobject 4.6.1 | 3 | 0 | 0 | 26 | 0 |

Three independent lineages move; `dmfs` and `sabre` do not. The `dateutil`
lineage passes all 29, which is what a shape-selected annotation should do —
the annotation is applied by rule shape, never by observed failure. `ical4j`
4.1.1 and 4.3.0 are identical here, as they are on every block finding 051
looked at, and the `ical4j` figure does not move across the `ar`-`EG`,
`en`-`US` and `en`-`GB` locales either.

I expected more `ical4j` movement than this. Finding 052 predicted that this
guard was holding 13 of the 19 cases it could not attribute; the measured
number is 8, and all 8 are cases where the recorded alternative is the *empty*
list. The 8 are all `FREQ=YEARLY` with `BYSETPOS`, six of them a
`BYMONTHDAY`, one a `BYWEEKNO`.

## The weak half of this result, stated plainly

All 8 `ical4j` matches, and 8 of `libical` master's 14, are matches against an
empty alternative. **Returning nothing is also what an implementation does when
it gives up**, so on those cases `fail_other_reading` is the least
discriminating label the scorer can apply: any empty answer earns it, whatever
produced it. The reading's answer there is genuinely empty, and provably so
rather than by exhaustion — but the *match* is weak evidence about the
implementation, which a non-empty match of eight instants is not.

The rest are not like that. `dtical`'s 14 matches are all non-empty, as are all
5 of `libical` 3.0.20's and 6 of `libical` master's, so **two independent
lineages reproduce the reading's dated answer instant for instant** on cases the
corpus was previously scoring as outright failures. That, not the `ical4j`
movement, is the result here.

The 8 empty ones all carry `BYSETPOS`, which is a plausible independent cause on
its own ([finding 037](037-a-limit-that-runs-before-the-thing-it-limits.md)),
and `libical` master matching the same 8 is consistent with the fill reading
rather than with two separate collapses. I have not separated those
explanations, and the honest summary is that they are bookkeeping.

`score.py` could report an empty-alternative match as its own bucket. It does
not today; the counts above are the breakdown a reader needs to do it by hand.

## Standing rules this came out of

Rule 33 (a truncated window is not an omission) is what motivated the fix, and
rule 4 (a cap I set is not a property of what I am measuring) is what the old
guard had got backwards: it treated *its own* 30-year horizon as the only
possible explanation of a short list and stopped there. Rule 49 from finding
052 — a block of failures I cannot attribute to a subject may be an artifact
of my own instrument — is how it was found. Rule 10 (a safeguard is unverified
until seen to fire) is why the `None` branch has two rules named above it.
