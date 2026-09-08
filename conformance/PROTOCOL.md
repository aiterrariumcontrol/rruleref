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

## `reading_alternative`, and why some failures are not defects

Some cases carry a `reading_alternative` field. Those are the ones where
`expect` depends on which reading of RFC 5545 §3.3.10 you take for the period
containing `DTSTART` — see `reading_dependent` in
[`../corpus/SCHEMA.md`](../corpus/SCHEMA.md) and finding 018. The corpus
recorded one reading; `reading_alternative` is the list the other reading
produces.

`score.py` compares against `expect` first. A mismatch that equals
`reading_alternative` is reported as **`fail_other_reading`** and counted
separately from `fail`. That is a disagreement about the specification, not
evidence of a bug, and it should not be added to a defect count. Adapters need
do nothing with the field; only the scorer reads it.

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
