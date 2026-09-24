# The adapter protocol

Everything in this directory exists to answer one question for someone who
maintains an RRULE implementation in any language:

> How long does it take to run this corpus against my library?

The answer should be an afternoon, and the corpus should not require Python,
this repository's machinery, or trust in me.

## The contract

An **adapter** is any program. It reads one JSON object per line on stdin and
writes one JSON object per line on stdout. Nothing else is prescribed:
language, startup, buffering and ordering are yours.

Input line:

```json
{"id":"3f9a1c2b7d04","rrule":"FREQ=MONTHLY;BYDAY=1FR","dtstart":"20260102T090000","limit":8}
```

* `rrule` — the value of an `RRULE` property, **without** the `RRULE:` prefix.
* `dtstart` — an RFC 5545 `DATE-TIME` in **local (floating) form**, no `Z`, no
  `TZID`. The whole corpus is floating time on purpose: a timezone would make
  every case also a test of your tz database. Timezone behaviour is covered
  separately in [findings 005–007](../findings/), not here.

  **This rule excludes far less than it looks like it does, and for a while it
  was read as excluding much more.** `RRULE` expansion is local-calendar
  arithmetic: a DST transition changes an occurrence's UTC offset, never its
  local time. So a case is timezone dependent only where the *rule text* names
  an absolute instant — in practice `UNTIL=...Z`. RFC 5545's own 39 worked
  examples all carry `TZID:America/New_York` and were kept off the board on
  this paragraph's authority for the whole life of the corpus; measured, 41 of
  their 42 rules reproduce the RFC's printed occurrences from the local
  `DTSTART` alone, and the one that does not is excluded anyway by §3.3.10.
  [Finding 082](../findings/082-the-specs-own-examples-were-not-on-the-board.md),
  standing rule 87.

* **`dtstart` has no value type, and that excludes less than it looks like
  too.** RFC 5545 allows `DTSTART` to be a `DATE` rather than a `DATE-TIME`,
  and this line cannot say so. `corpus/date-value-type.json`'s 18 such cases
  were therefore never selected by `build_cases.py` and never posed to an
  adapter. Measured: **10 of the 18 rules refer to no value type at all** and
  are ordinary cases posed at `00:00:00`; **6 carry `BYSECOND`/`BYMINUTE`/
  `BYHOUR`**, which §3.3.10 says to ignore under a DATE start, and §3.3.10's
  own remedy is a reduction whose reduced rule this line carries fine; **2
  carry a DATE-valued `UNTIL`** and those are prohibited here for the reason
  in the next bullet, running the other way. Nine of thirteen builds return the
  corpus's DATE answer on all 12 scorable rules.
  [Finding 083](../findings/083-the-date-value-type-was-not-a-wall.md),
  standing rules 87 and 88.

  Careful with the second group: asked *as written* at a `DATE-TIME` start,
  the literal reading is the **correct** answer and the §3.3.10 answer would be
  a defect, because MUST-ignore is conditioned on a value type this line cannot
  express. `sabre/vobject` gives the §3.3.10 answer on two of them for an
  unrelated reason and is not thereby conformant.

* **`UNTIL` may not carry a `Z` here.** §3.3.10: "if the 'DTSTART' property is
  specified as a date with local time, then the UNTIL rule part MUST also be
  specified as a date with local time." Every `dtstart` in this protocol is
  floating, so a UTC `UNTIL` is a prohibited rule and an implementation's
  behaviour on it is not a conformance fact. No generated case carries one.
  `python-dateutil` and `dmfs lib-recur` refuse the combination outright; the
  other eleven builds accept it silently.
* `limit` — stop after this many occurrences. Producing fewer is a result, not
  an error; producing more is ignored.

Output line, one per input line, in any order:

```json
{"id":"3f9a1c2b7d04","occurrences":["20260102T090000","20260206T090000"]}
```

or, if your library refuses the rule:

```json
{"id":"3f9a1c2b7d04","error":"unsupported BYWEEKNO"}
```

An `error` scores as a failure but is reported in its own column, because
"refuses to parse" and "parses and answers differently" are different facts
about an implementation. Occurrences must be `YYYYMMDDTHHMMSS`, ascending,
starting with the first occurrence of the recurrence set — `DTSTART` itself,
since every case here is synchronized.

## Scoring

```sh
python3 conformance/build_cases.py                 # regenerate cases.ndjson
python3 conformance/score.py -- <your adapter command>
python3 conformance/score.py --json result.json -- <cmd>   # every failure
```

A case passes when the returned list **equals** `expect`. There is no partial
credit and no tolerance.

`expect_bound` (see [`../corpus/SCHEMA.md`](../corpus/SCHEMA.md)) decides what
`limit` was asked for:

* `complete` — the recurrence set provably ends inside the recorded window.
  `limit` is `len(expect) + 1`, so an implementation that keeps going past the
  end fails.
* `count` / `horizon` — the corpus knows only a **prefix**. `limit` is
  `len(expect)`, and nothing is asserted about what comes after.

  Consequence, and it runs the opposite way from the usual warning about short
  prefixes: a prefix can *hide* a defect as easily as it can invent one. A rule
  whose implementation goes wrong only past `limit` scores as a pass. Every
  failure count produced from this corpus is therefore a lower bound on the
  disagreement, not a measurement of it —
  [finding 039](../findings/039-what-bysetpos-selects-from.md) has a worked case
  where 6 of 14 defective results were scored as passes.

## `reading_alternatives`, and why some failures are not defects

Some cases carry a `reading_alternatives` field: a map from the name of a rival
reading of RFC 5545 §3.3.10 to the occurrence list that reading produces. The
corpus recorded one reading as `expect` and these are the others. See
`reading_dependent` in [`../corpus/SCHEMA.md`](../corpus/SCHEMA.md). Two
readings are named today:

* **`first_period_truncated`** — whether `BYSETPOS` indexes the whole period
  containing `DTSTART` or that period cut at `DTSTART` (findings 004, 018).
* **`dtstart_fill`** — whether, in the two `YEARLY` cells where §3.3.10's
  expand/limit table is the sole authority and leaves a coarser field
  unspecified, that field is expanded over or filled from `DTSTART`
  (finding 024).
* **`week_based_year`** — under `FREQ=YEARLY` with `BYWEEKNO`, whether the days
  of a week that straddles 1 January belong to the period of the calendar year
  they sit in or of the year that *owns* the week (finding 059).
* **`week_based_year+dtstart_fill`** — the two above composed. It is named
  separately because on some cases neither one alone reproduces what any
  implementation returns.

`score.py` compares against `expect` first. A mismatch that equals one of these
is reported as **`fail_other_reading`**, counted separately from `fail`, and
broken down by reading name. That is a disagreement about the specification,
not evidence of a bug, and it should not be added to a defect count. Adapters
need do nothing with the field; only the scorer reads it.

An answer that is a non-empty **proper prefix** of `expect`, or of one of these
alternatives, is reported as **`fail_prefix`** or
**`fail_other_reading_prefix`** — it agreed for its whole length and then
stopped, which is the signature of a window rather than of a disagreement. The
empty list is excluded on purpose: answering nothing is not a truncated version
of every reading. The bucket asserts the prefix and nothing more; it does not
claim the implementation would have continued correctly.

This matters because the corpus applies its own horizon unevenly. No `expect`
list runs past `horizon_days` (10958), but **21 of its 120
`reading_alternatives` lists do** — so an adapter that honours the declared
horizon cannot match those 21 by equality however correct the library behind it
is. Today that bites 7 cases, identically on both Java adapters.
[Finding 057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md).

## Comparing two runs

```sh
python3 conformance/compare_residuals.py A.json B.json          # both --json outputs
python3 conformance/compare_residuals.py A.json B.json --bucket fail
```

A residual **count** is a summary; the **membership** is what decides a cause.
Two runs with an equal count in the same bucket are exactly where the count is
least informative, so `compare_residuals.py` reports, per bucket, how many ids
each side has, how many they share, and which belong to only one — and calls
out an equal count with different members as the loudest line in its report.

The same command answers two different questions depending on what the files
are. Two implementations: do they fail on the *same* cases, which points at a
shared cause such as the harness, or on disjoint ones, which means two
independent defects? One implementation twice: does the residual reproduce? A
count that reproduces while the membership does not is a nondeterministic
adapter, which the Perl `dtical` adapter's 20-second alarm is.

This exists because [finding 056](../findings/056-two-scopes-for-one-word.md)
published "7 `ical4j` cases and 7 `dmfs` cases" as though that were two facts.
It was one — the same seven ids — and the identity, not the count, is what
identified the shared Java adapter rather than either library as the cause
([057](../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md)). One
command now reproduces that:

```
=== fail_other_reading_prefix ===
  left 7   right 7   shared 7   left-only 0   right-only 0
  SAME CASES.
```

Result files written before `score.py` recorded an explicit `bucket` field are
classified from their `why` text instead, so the published
`findings/data/*.json` can still be compared.

## What a failure means

It means this implementation and this corpus disagree. It does **not** mean
your library is wrong. Three of the defects this project has found were in my
own expander (findings 009 and 014), and finding 001 was a bug report against
`python-dateutil` that I withdrew because the corpus was wrong, not dateutil.

If you think a case is wrong, that is the most useful thing you can send:
open an issue with the rule, the `DTSTART`, and the RFC 5545 sentence you are
reading it against.

## Which cases are here

`cases.ndjson` is not the whole corpus. It is the subset for which a
disagreement is a defensible conformance claim: the rule is valid under
§3.3.10, `DTSTART` is synchronized so §3.8.5.3 does not declare the answer
undefined, and the case is decidable from the recorded window. The reasoning
and the exclusions are in `build_cases.py`'s docstring.

All 2091 exclusions are currently made by the validity and synchronization
tests alone. The third test — dropping a case whose `expect` is empty only
because the horizon ran out — removes **nothing** at present, because every
such case is also unsynchronized (`DTSTART` cannot be the first occurrence of a
set with no occurrences) and was already gone. It is kept because that
coincidence is a property of today's generator, not a theorem, and
`tests/test_conformance.py` prints the count it drops.

`id` is `sha256(rrule + "\n" + dtstart)` truncated to 12 hex characters, so it
survives corpus rebuilds and you can track a specific failure over time.
