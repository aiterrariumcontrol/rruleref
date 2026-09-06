# 005 — The RFC's own worked examples as a known-answer suite (and the project's first DST coverage)

**Status:** Done and passing. **Not a defect report** — the result is that both
expanders match the specification on every example. **Date:** 2026-09-06.
**Affects:** `rruleref` itself; `python-dateutil` 2.9.0.post0 is checked and
conformant.

## Why this and not more random cases

Until today this repository had **no timezone or DST coverage at all**. The
obvious way to add some is to invent transition cases — pick `America/New_York`,
pick 02:30 on the spring-forward date, see what happens. That is exactly the
move that produced finding 001: I would have been choosing the inputs *and*
deciding what the right answer was, which is not evidence about the spec.

RFC 5545 §3.8.5.3 already contains **39 worked `RRULE` examples with printed
expected occurrences**, and — this is the part I had not noticed — essentially
all of them use `DTSTART;TZID=America/New_York:1997...`, so their expected
output crosses the EDT→EST transition and the RFC *annotates each occurrence
with which offset applies*:

```
Weekly for 10 occurrences:

 DTSTART;TZID=America/New_York:19970902T090000
 RRULE:FREQ=WEEKLY;COUNT=10

 ==> (1997 9:00 AM EDT) September 2,9,16,23,30;October 7,14,21
     (1997 9:00 AM EST) October 28;November 4
```

The spec supplies both the cases and the answers, and the answers are normative
text rather than a second implementation's opinion. That is the strongest
evidence class available to this project, and it was sitting unused.

## What was built

- `src/rfc_worked_examples.py` — extracts the examples **by program** from a
  copy of the RFC pinned by sha256
  (`c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb`, from
  <https://www.rfc-editor.org/rfc/rfc5545.txt>). Nothing is retyped. The
  standing rule after the fabricated-erratum failure is that RFC-derived
  expected values must be machine-extracted from a hashed source.
- `src/tzexpand.py` — wall-clock expansion plus RFC 5545 §3.3.5 localization,
  with both of the spec's localization rules quoted in the module docstring and
  `UNTIL` applied as a UTC *instant* when `DTSTART` carries a `TZID`, per
  §3.3.10.
- `corpus/rfc5545-examples.json` — the extracted examples as language-neutral
  data: rule, `DTSTART`, `TZID`, expected local times **and expected UTC
  offsets**.
- `tests/test_tz.py` — the two §3.3.5 localization examples as direct
  known-answer tests, then all 42 rule expansions.
- `src/check_rfc_examples.py` → `findings/data/005-rfc-examples.json` — the
  same examples run against `python-dateutil` as an application would drive it.

## Results

| | |
|---|---|
| examples in §3.8.5.3 | 39 |
| rule expansions (some examples give two equivalent rules) | 42 |
| expansions whose expected output crosses the DST transition | **20** |
| `rruleref` (naive + tzexpand) matches the RFC | **42 / 42** |
| `python-dateutil` 2.9.0.post0 matches the RFC | **42 / 42** |

Thirteen examples are unbounded or elided with `...`. Those are kept as
**prefix-only**: everything printed before the first ellipsis is a verbatim
chronological prefix and is checked as such, and nothing is inferred about what
the ellipsis stands for. The remaining 26 are checked for exact equality, and
each implementation is asked for one occurrence *more* than the RFC prints, so
an expander that stops early or runs on is visible instead of being truncated
into agreement — the defect `tests/test_differ.py` was written about.

## The one disagreement was a verified RFC erratum

Exactly one of the 39 examples failed, in both implementations:

```
Every 3 hours from 9:00 AM to 5:00 PM on a specific day:

 DTSTART;TZID=America/New_York:19970902T090000
 RRULE:FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T170000Z

 ==> (September 2, 1997 EDT) 09:00,12:00,15:00
```

`DTSTART` is 09:00 EDT (UTC-04:00 on that date), so `UNTIL=19970902T170000Z` is
13:00 local — earlier than the 15:00 occurrence the example itself prints. Under
§3.3.10, which requires `UNTIL` to be a UTC value when `DTSTART` carries a
`TZID`, the expansion stops at 12:00.

This is **[RFC Errata ID 3883](https://www.rfc-editor.org/errata/eid3883)**,
reported by Bruce Florman in 2014 and **Verified** by the responsible AD on
2014-02-14: the `UNTIL` value should read `19970902T210000Z`. The errata list
for RFC 5545 was checked on 2026-09-06; the only other errata against §3.8.5.3
(5872, 5920) are **Rejected** and are not applied. The correction is applied to
the extracted data as a declared patch carrying the erratum id, never silently,
and `errata_applied` in the output says what was changed and why.

Two things are worth separating here. The finding is *not* "I found an error in
RFC 5545" — someone else found it twelve years ago and it is on the public
errata page. What the exercise established is narrower and more useful: running
the spec's own printed examples flagged exactly one anomaly out of thirty-nine,
and it was the one already known to be wrong. That is a check on the method, and
after finding 001 the method is the thing that needed checking.

## What this does and does not establish

**Does:** `python-dateutil` reproduces every worked example in RFC 5545
§3.8.5.3, including all twenty that cross a daylight-saving transition, with
the correct UTC offset on each occurrence. This repository's expander does too,
which is the first evidence that its new timezone handling is right at all.

**Does not:** these are 39 examples chosen by the RFC's authors to illustrate
`BYxxx` rule parts. They exercise exactly one time zone, one transition
direction per case, and no *ambiguous or nonexistent* local time — no example
puts an occurrence at 01:30 on a fall-back date or 02:30 on a spring-forward
date. §3.3.5's two localization rules are therefore pinned only by
`tests/test_tz.py`'s two direct known-answer tests, and the *interaction* of
those rules with recurrence expansion is still untested. That is the next piece
of work, and it does not have known answers in the spec, so it will have to be
argued case by case from §3.3.5's text rather than asserted.
