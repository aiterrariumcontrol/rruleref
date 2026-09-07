# 015 — A language-neutral harness, and the first implementation run through it

2026-09-07. Two things: a protocol that lets any implementation be scored
against this corpus without Python, and the first score produced by it. Along
the way the corpus schema turned out to carry a defect that only became visible
when I tried to write it down for a stranger.

## Why

The project's premise is that a third party can re-run the adjudications rather
than trust me. Until now that premise was only half true: the corpus was
language-neutral JSON, but consuming it meant reading `build_corpus.py` to
learn which of ten per-case fields mattered, and there was no documented way to
feed it to a non-Python implementation. The repository had no user but me, and
the reason was not the corpus's contents.

## The schema defect: `truncated`

Each corroborated case carried `truncated: len(expect) == 8`. Writing
`corpus/SCHEMA.md` forced the question of what the *false* branch means, and the
obvious reading — "this is the whole recurrence set" — is wrong.

`build_corpus.py` imposes **two** caps: 8 occurrences per case, and a ~30-year
horizon. `truncated` records only the first. A case that stopped because the
horizon ran out looks identical to one whose rule genuinely ended.

Measured, not assumed. Of the 450 cases marked not-truncated, 67 have neither
`COUNT` nor `UNTIL` and a non-empty `expect`; expanding every one of them with
an **unbounded** dateutil produced further occurrences in all 67. Examples:

    FREQ=MONTHLY;BYDAY=+2SU;BYMONTHDAY=-15   DTSTART 20260302T090000
      expect has 4 occurrences; a 5th falls on 2066-02-14.
    FREQ=YEARLY;BYDAY=MO;BYYEARDAY=-60       DTSTART 20260301T090000
      expect has 5; a 6th falls on 2065-11-02.

A consumer treating `truncated: false` as "complete" would have produced 67
false failures against **every** implementation it tested — failures that look
like defects in the implementation and are defects in my metadata. This is
standing rule 4 in the plainest possible form: *a cap I set is not a property
of what I am measuring.*

`truncated` is replaced by `expect_bound`, one of `complete` / `count` /
`horizon`, documented in [`../corpus/SCHEMA.md`](../corpus/SCHEMA.md). It is
decided from the rule text and the two caps, never from an expander.

The first version of that classifier was also wrong, and its own check caught
it: it returned `complete` whenever `UNTIL` fell inside the horizon, which is
unsound when the 8-occurrence cap bit first — three `FREQ=HOURLY/MINUTELY/`
`SECONDLY` cases with a 3-day `UNTIL` have thousands of occurrences and were
labelled complete. The count cap is now checked first. All 98 surviving
`complete` cases were then verified against an unbounded expansion: each ends
exactly where `expect` ends, none early, none late.

## The harness

[`conformance/PROTOCOL.md`](../conformance/PROTOCOL.md). An adapter is any
process: NDJSON in, NDJSON out, one line per case. No dependency on this
repository, on Python, or on anything but a JSON parser and the library under
test. The two reference adapters are 30 and 33 lines.

`conformance/cases.ndjson` is the subset for which a disagreement is a
defensible conformance claim — valid rule, synchronized `DTSTART`, and
decidable from the recorded window. **1722 of 3813 cases.** The 2091 excluded
are not weaker tests; they are cases where §3.8.5.3 declares the answer
undefined or §3.3.10 prohibits the rule, so a mismatch would mean nothing.

The third exclusion — a case whose `expect` is empty only because the horizon
ran out, which would pass vacuously — currently drops nothing, because every
such case is also unsynchronized and had already gone. Rule 10: that branch has
not been seen to fire, so it is a guard rather than a verified filter, and the
test prints the number it drops.

`python3 conformance/score.py -- <command>`. Exact list equality, no partial
credit. `python-dateutil` scores 1722/1722, which is a check of the harness and
not a result: dateutil is one of the two expanders every case was corroborated
by.

## rrule.js 2.8.1: 1696 / 1722

The first number this project has produced about an implementation that did not
help build the corpus. Every failure below is a place where rrule.js differs
from **both** expanders.

### 17 failures — `BYHOUR` values are not sorted

`FREQ=DAILY;BYHOUR=9,8` from `20260302T090000`:

    corpus:    ... 20260303T080000, 20260303T090000, 20260304T080000 ...
    rrule.js:  ... 20260303T090000, 20260303T080000, 20260304T090000 ...

rrule.js emits each period's instances in the order the rule *lists* the hours.
15 of the 17 differ only in that order, and **RFC 5545 does not say a recurrence
set must be emitted chronologically** — I grepped for it; the only "ascending
order" in the document is about `FREEBUSY` in §3.8.2.6. So for those 15 this is
a divergence, not a demonstrated violation, and a consumer that sorts is
unaffected.

The other two are substantive, because ordering stops being presentational the
moment something indexes into it:

    FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1   DTSTART 20260302T090000
    corpus:    20260302T090000, 20260303T090000, 20260304T090000, ...
    rrule.js:  20260303T080000, 20260304T080000, 20260305T080000, ...

Each day's set is {08:00, 09:00}. `BYSETPOS=-1` selects its last member.
Unsorted, rrule.js's last member is 08:00, so it selects a different instance
every day — and drops `DTSTART` itself, though `DTSTART` is the rule's own
first occurrence. §3.3.10: "the nth occurrence within the set of recurrence
instances", and "A set of recurrence instances starts at the beginning of the
interval defined by the FREQ rule part." *Hedged:* that "starts at the
beginning" is the strongest ordering language I found, and it constrains where
the set begins rather than stating outright that `-1` means "latest in time".

One search of the rrule.js issue tracker for the `BYHOUR` ordering behaviour
found nothing. That is a weak negative; three times this week I have been
second.

### 1 failure — duplicate `BYSETPOS` values, already reported

`FREQ=MONTHLY;BYDAY=MO,WE,FR;BYSETPOS=+1,1` emits every occurrence twice —
`+1` and `1` are the same position. **Already open upstream as rrule issue
669**, "Fix duplicate occurrences from coinciding BYSETPOS positions". Not new;
recorded because the corpus reaches it.

### 4 failures — `FREQ=WEEKLY` + `BYMONTH` + `BYSETPOS`

    FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-2   DTSTART 20260601T090000
    corpus:    ... 20260622T090000, 20270607T090000 ...
    rrule.js:  ... 20260622T090000, 20260629T090000, 20270602T090000 ...

rrule.js produces occurrences the corpus does not, at the boundary where
`BYMONTH` truncates the week that straddles it. This is the same *family* as
finding 004 — a `BYxxx` limit applied to a period before `BYSETPOS` selects
from it — at the far end of the month rather than at `DTSTART`. **Not
adjudicated here.** Finding 004's argument turns on a disputed reading of
§3.8.5.3 and I am not going to resolve at the June/July boundary what is
unresolved at `DTSTART`.

## What this is not

A conformance score is a measurement against *this corpus*. Three of the
defects this project has found were in my own expander (009, 014), and finding
001 was a bug report against dateutil that I withdrew because the corpus was
wrong. 26 failures out of 1722 in a mature, widely-used library should raise
the prior that some of the 26 are mine. The two clusters I have hedged above
are the ones I would look at first.

Nothing here has been reported upstream and nothing here is authorized to be.
