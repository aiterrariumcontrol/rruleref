# rruleref — a cross-implementation conformance corpus for RFC 5545 RRULE

Recurrence rules are a small spec that almost everything gets slightly wrong.
There is no official conformance suite for RFC 5545 `RRULE`. Each library ships
its own regression tests, which by construction can never disagree with the
library that wrote them, so a whole class of defect survives indefinitely: the
kind where an implementation is confidently and consistently wrong.

This repository is an attempt at the missing artifact — a language-neutral
corpus of `RRULE` + `DTSTART` → expected occurrences, in plain JSON, with the
expected values derived from the spec rather than copied from any one library.

## How a case earns its place

Expected values are not taken from a reference implementation, because then the
corpus would just encode that implementation's bugs.

Instead there are two expanders that share no code:

- `src/naive.py` — a deliberately naive brute-force expander written from the
  text of RFC 5545 §3.3.10. It enumerates every candidate datetime and asks "is
  this an occurrence?" as a predicate. It is far too slow for production and far
  easier to check by eye against the spec, which is the point.
- `python-dateutil`, which uses completely different interval-skipping
  machinery.

A case goes into `corpus/corroborated.json` only when both agree. Independent
agreement is evidence, not proof — but it is much stronger evidence than any
single library's self-consistency.

When they disagree, the case goes to `corpus/disputed.json` and is adjudicated
by hand against the spec. Some disagreements are bugs in my expander (most of
them were, and fixing those is how it earned trust). Some are bugs in the other
implementation. Some are places the spec genuinely does not decide.

Current state: **1465 corroborated cases, 9 disputed**, all 9 accounted for by
the two findings below.

## Findings

- [001 — dateutil mis-numbers `BYSETPOS` in the first week of a `FREQ=WEEKLY`
  rule](findings/001-dateutil-weekly-bysetpos.md). Confirmed. Positions are
  numbered within a set truncated at `DTSTART` instead of the full week, so the
  rule emits an instance that is not at any requested position. `MONTHLY` and
  `YEARLY` handle the identical shape correctly, which is what makes it a bug
  rather than a policy.
- [002 — `BYWEEKNO` at the year boundary](findings/002-byweekno-year-boundary.md).
  A spec ambiguity, deliberately **not** filed as a bug. RFC 5545 does not say
  which week owns the first days of January when they fall in the previous
  year's last week, and implementations diverge. Recorded as disputed.

## Layout

```
src/naive.py         spec-derived brute-force expander
src/differ.py        random rule generator + differential comparison
src/build_corpus.py  runs the differential and writes the corpus
corpus/              corroborated.json, disputed.json
findings/            adjudicated divergences, written up
```

## Running it

`python-dateutil` is the only dependency and only the *builder* needs it; the
corpus itself is plain JSON and can be consumed by anything.

```sh
python3 src/differ.py 7 300      # differential run, seed 7, 300 rules
python3 src/build_corpus.py      # rebuild corpus/ (slow; minutes)
```

## Honest limits

- Only two implementations, and one of them is mine. Two independent expanders
  agreeing is real evidence but a third would be worth more than doubling the
  case count. That needs runtimes this machine does not have (no node, no PHP,
  no Ruby, no Go).
- Everything here is naive-datetime. No timezones, no DST, no `VTIMEZONE`.
  That is a deliberate scope cut, not an oversight: DST transitions deserve
  their own corpus and would otherwise contaminate this one.
- The generator does not yet emit `FREQ=HOURLY/MINUTELY/SECONDLY`, `UNTIL`, or
  `COUNT` combinations, so the corpus says nothing about them.
- Coverage is random, not systematic. It is not yet a claim of completeness.
