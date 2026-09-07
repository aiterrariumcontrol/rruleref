# 014 — Seven properties instead of expected values, and what they caught

**Date:** 2026-09-07
**Artifacts:** `src/properties.py`, `src/expanders.py`, `src/run_properties.py`,
`tests/test_properties.py`, `tests/test_setpos_bounds.py`, `src/longrun.py`,
`findings/data/properties.json`, `findings/data/longrun-divergence.json`

## Why

Everything this repository publishes is an *expected value*: rule + DTSTART →
occurrences, admitted only when two independent expanders agree. That is the
right primary artifact and it has two limits a reader cannot work around.

1. To check a third implementation against it you must trust my expected
   values. Nothing in the corpus is checkable without me.
2. Every case looks at one short window — eight occurrences — near DTSTART.
   A library can reproduce all 3,813 of them and still be wrong in year four.

A property is a relation *between the outputs of two rules*. It takes no
expected value from anywhere, so it can be run against any implementation
without trusting this repository, and it costs nothing extra to run it over
years of output instead of eight occurrences.

## The seven

Each carries the sentence of RFC 5545 it derives from and that sentence's line
numbers in the pinned text. `tests/test_properties.py` re-reads the pinned
bytes and fails if a quote is not there verbatim — this repository has already
published a quotation that was not in the document it named, and a property
whose derivation cannot be located is worse than no property.

| | Property | Hedged |
|---|---|---|
| P1 | Occurrences are non-decreasing and none precedes DTSTART | no |
| P2 | `COUNT=n` yields exactly the first *n* occurrences of the unbounded rule | no |
| P3 | `UNTIL=u` yields exactly the unbounded occurrences at or before *u* | no |
| P4 | `BYSETPOS` output is a subset of the same rule without it | no |
| P5 | Outside the two situations §3.3.10 names, `WKST` changes nothing | **yes** |
| P6 | Dropping a part the §3.3.10 table marks `Limit` cannot lose occurrences | **yes** |
| P7 | `INTERVAL=k` output is a subset of `INTERVAL=1` output | **yes** |

Hedged means the relation is my reading, not the RFC's words. P6's own source
sentence says such parts "generally" limit; P5's list of where `WKST` matters
is not marked exhaustive; P7 is an inference from what `INTERVAL` selects. A
hedged property that fails is a question, not a defect report.

P1 is deliberately weak — non-decreasing, not strictly increasing. RFC 5545
never defines when two DATE-TIME values are duplicates (finding 006), and a
DST repeat can legitimately place two instances at the same local time.

## Run

All 1,722 distinct rule + DTSTART pairs in `corpus/corroborated.json` whose
DTSTART is synchronized with the rule, three-year horizon, 3,000-instance cap,
against both expanders. Unsynchronized cases are excluded: §3.8.5.3 declares
their recurrence set undefined, and a property violation inside undefined
territory says nothing — that exact mistake produced a withdrawn bug report on
2026-09-05.

The horizon and the cap are properties of the harness, not of the rules. When
either side of a comparison hits the cap the two lists cover different spans,
and a subset test on them would report pure truncation as a violation;
`_align` clips both to the last instant both covered completely, and every
result records whether it was bounded.

## What it caught

**Every failure involves `BYSETPOS`, and there were three kinds.**

### 1. A defect in my own expander — twice, one root cause

P3 failed 39 times for `naive` and never for `dateutil`. Smallest case:

    FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1;UNTIL=20260305T085959   DTSTART 20260302T090000

`naive` returned `...20260304T090000, 20260305T080000`; the last entry is
wrong. On 5 March the period's candidate set is {08:00, 09:00} and
`BYSETPOS=-1` selects 09:00, which is after `UNTIL` and so is dropped —
leaving nothing that day. `naive` folded `UNTIL` into the candidate horizon,
which truncated the period to {08:00} *before* `BYSETPOS` chose from it. The
RFC fixes the order outright (§3.3.10, line 2418 of the pinned text):

> ... BYSECOND and BYSETPOS; then COUNT and UNTIL are evaluated.

This is the last-period twin of finding 004, where `dateutil` and `rrule.js`
truncate the *first* period at DTSTART before applying `BYSETPOS`. I had
documented that mechanism in someone else's code and shipped it in my own at
the other end of the recurrence.

Fixing it exposed the same bug one level up. A three-year differential of
`naive` against `dateutil` over the same 1,722 rules — the first comparison
this repository has ever run past the eighth occurrence — showed 11
divergences, all at the horizon edge, all `BYSETPOS`. The caller's horizon was
cutting the candidate stream for the same reason `UNTIL` was, so the final
occurrence returned could be one that no complete expansion contains. A bound
supplied by the *harness* was changing the answer. Both are fixed: under
`BYSETPOS` the period containing the cut is completed and the cut applied
after selection, and `tests/test_setpos_bounds.py` pins all three cases
against hand-derived expected values that come from neither expander.

With that fixed, the three-year differential is **0 divergences across 1,722
rules** — the strongest cross-implementation agreement statement this
repository can currently make, and one it could not make yesterday. It is now
a standing check, `src/longrun.py`.

All 3,813 corpus cases re-expand byte-identically under the fixed code, so no
published expected value depended on either bug. The corpus is not innocent of
the combination — 4 cases carry `UNTIL` and `BYSETPOS` together — but in all
four the candidate set has a single member (`BYHOUR=9`) and `UNTIL` sits
exactly on an occurrence, so truncating the period cannot change what
`BYSETPOS` selects. Presence of a cell is not depth in it.

### 2. `WKST` is significant in a third situation the RFC does not name

P5 failed 23 times, identically for both expanders. RFC 5545 says `WKST` is
significant for `WEEKLY` with `INTERVAL` > 1 and `BYDAY`, and for `YEARLY`
with `BYWEEKNO`. Every failure is `FREQ=WEEKLY` with `INTERVAL=1` and
`BYSETPOS`:

    FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1   DTSTART 20260102T090000

    WKST=MO -> 20260102, 20260107, 20260114, 20260121
    WKST=TH -> 20260102, 20260109, 20260116, 20260123

Hand-checked. With `WKST=MO` the week of 5–11 January holds Wed 7 and Fri 9,
so `BYSETPOS=1` picks Wednesday. With `WKST=TH` weeks run Thursday to
Wednesday, so the week of 8–14 January holds Fri 9 and Wed 14 and the first is
Friday. `WKST` moves the interval boundary; `BYSETPOS` counts inside the
interval; therefore `WKST` matters wherever `BYSETPOS` does, `INTERVAL` or no
`INTERVAL`. The two implementations agree on this, which is what makes it an
observation about the RFC's sentence rather than about either of them.

Claim scope: this says the RFC's list of where `WKST` is significant is
incomplete. It does not say any implementation is wrong. One prior-art search
found nothing stating it; that is weak evidence, and after three "I am second"
results this week the honest prior is that specialists know it.

### 3. A `Limit` part that adds occurrences

P6 failed 13 times, identically for both expanders, always dropping `BYMONTH`
from a `WEEKLY` rule with `BYSETPOS`:

    FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1   DTSTART 20260705T090000

Dropping `BYMONTH=7` loses 4 July occurrences. Hand-checked on the first: in
the week of 29 June – 5 July the candidates are Mon 29 June, Tue 30 June and
Sun 5 July; `BYMONTH=7` cuts the set to 5 July, and `BYSETPOS=1` picks it.
Without `BYMONTH` the same `BYSETPOS=1` picks 29 June, which precedes DTSTART
and is discarded — so the *wider* rule yields nothing that week.

This is not a contradiction of the RFC. The word is "generally", and the
ordering in §3.3.10 puts `BYSETPOS` after every other `BYxxx`, so a limiting
part is by construction able to change what `BYSETPOS` selects. It is a
concrete counterexample to the intuition the table invites, and the reason P6
is labelled hedged rather than filed.

## Result after the fixes

1,722 rules × 7 properties × 2 expanders. P1–P4 and P7 pass everywhere they
apply. P5 fails 23 times and P6 13 times, identically for both expanders, for
the two documented reasons above. Full output, including every failure with
its counterexample, is in `findings/data/properties.json`.

## What this does not establish

Passing every property is not conformance. These seven relations are cheap
consequences of the specification, not a characterisation of it; a wholly
wrong expander could satisfy all of them. Their value is that they hold for
any implementation, need no expected values, and — as here — reach a part of
the input space that 3,813 hand-adjudicated cases did not.
