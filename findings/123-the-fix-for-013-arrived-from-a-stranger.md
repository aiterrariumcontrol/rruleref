# 123 — the fix for finding 013 arrived from a stranger, and it is complete

*2026-10-02*

[Finding 013](013-byday-mixed-signed-and-unsigned.md) ended with a dated
observation about a defect rather than about a library. A `BYDAY` list mixing a
signed weekdaynum with an unsigned one is a **union** of its elements;
`python-dateutil` applies it as an **intersection**, so `BYDAY=+2SU,MO`
expands to nothing at all. The defect flows from the Python library into
`rrule.js`, which is a port of its iterator, and the only report of it anywhere
was [`jkbrzt/rrule#71`](https://github.com/jkbrzt/rrule/issues/71) — filed
against the *port* on 2014-09-05, still open with zero comments. 013's closing
paragraph said the part worth recording was that the bug reports do not flow
back upstream, and that no report had been filed from here.

On **2026-09-30** somebody filed it upstream:
[`dateutil/dateutil#1588`](https://github.com/dateutil/dateutil/issues/1588),
with [`#1589`](https://github.com/dateutil/dateutil/pull/1589) carrying a fix.
`jkbrzt/rrule#71` is still open with zero comments, now twelve years and a
month old; so that half of 013 stands. The upstream half does not, and it was
closed by an event rather than by me.

## What the report contains, and what that is evidence about

The report is the same finding, reached independently. It quotes the same two
lines of `rrule.py`, identifies the same cause — `_byweekday` and `_bynweekday`
applied as two `or`-ed exclusion clauses, which is an intersection — gives the
same RFC §3.3.10 reading, distinguishes the same two symptoms (empty when the
weekdays differ, the ordinal alone when they coincide), and proposes exactly
the predicate 013's "same file getting it right next door" paragraph points at:
the `BYMONTHDAY` shape, three lines below in the same condition.

It also states how it was found: *"comparing `rrule` with an independent
implementation of RFC 5545 recurrence expansion on 50,000 generated rules."*
That is this repository's method, arrived at by somebody else for the same
reason. It is worth being precise about what that corroborates. It is **not**
independent evidence that the spec reading is correct — we both read the same
two sentences of §3.3.10, and if that reading were wrong we would both be
wrong together. What it is evidence for is narrower and still useful: that
differential expansion against a from-the-spec oracle is a method a
practitioner reaches on their own, and that the specific defect is findable
without privileged access to anything. Two people, independently, pointed a
hand-written expander at `dateutil` and the same case fell out first.

## The question the thread cannot answer, and this repository can

The PR ships four hand-written tests: `MO,1FR`, `FR,1FR`, a `YEARLY` case, and
the `rrulestr` spelling. Four cases is enough to demonstrate a fix and not
enough to say it is complete. The thing I have that the thread does not is an
expander written from the spec and a harness that can hold a patched library
next to it over a whole space of rules at once.

`findings/repro/123-mixed-byday-union.py` enumerates that space. Three columns
per case: `naive` (`src/naive.py`, spec brute force), `stock` (the
`python-dateutil` pinned in `vendor/pylibs`), and `patched` — a temporary copy
of that same tree with the PR's one-site change applied by the script itself,
so the run needs nothing from outside the repository and no network.

```
dateutil 2.9.0.post0, patch dateutil/dateutil#1589
DTSTART 20260105T090000, horizon 760 days, limit 8

arm                      cases   fixed  agreed  diverg regress
bymonth                     14      14       0       0       0
core-monthly               490     490       0       0       0
core-yearly                490     490       0       0       0
interval                    14      14       0       0       0
multi                       24      24       0       0       0
setpos-control-ordinal      42       0      42       0       0
setpos-control-plain        42       0      42       0       0
setpos-mixed               294     280      14       0       0
TOTAL                     1410    1312      98       0       0
```

**1312 of 1410 cases change answer and every one of them lands on `naive`. Not
one case diverges after the patch, and not one case that already agreed stops
agreeing.** The core arm is every ordinal in ±1..5 against every ordered pair
of weekdays, under both `MONTHLY` and `YEARLY`: 980 cases, all 980 fixed. The
smaller arms put a mixed list under `INTERVAL`, under a `BYMONTH` limit, and in
lists of three elements where the union has to hold across more than a pair.

```
RRULE:FREQ=MONTHLY;BYDAY=1MO,TU
  naive    20260105 20260106 20260113 20260120 20260127 20260202 20260203 20260210
  stock    (empty)
  patched  20260105 20260106 20260113 20260120 20260127 20260202 20260203 20260210

RRULE:FREQ=MONTHLY;BYDAY=1MO,MO
  naive    20260105 20260112 20260119 20260126 20260202 20260209 20260216 20260223
  stock    20260105 20260202 20260302 20260406 20260504 20260601 20260706 20260803
  patched  20260105 20260112 20260119 20260126 20260202 20260209 20260216 20260223
```

Two further regression checks, each against a different case pool, agree:

* The conformance corpus scores **1727 / 1727 `pass` both before and after** the
  patch. That is a weaker result than it looks and is reported for what it is —
  the new predicate differs from the old one only when `_byweekday` and
  `_bynweekday` are *both* non-empty, so the 381 corpus cases carrying an
  ordinal `BYDAY` and every case carrying a plain one are untouched by
  construction. It confirms the blast radius rather than the fix.
* The metamorphic property sweep (`src/run_properties_adapters.py`, finding
  119's P1–P8 over 1728 rules, 86s) returns **tallies identical to the published
  `dateutil` row in every cell**, including its 23 P5 and 13 P6 failures. The
  only fields that moved in the artifact were the two wall-clock seconds.

## The fourteen cases that cannot tell the two readings apart

The one genuinely new fact here is in the `setpos-mixed` arm, where 14 of 294
cases were already agreeing before the patch. They are not arbitrary. All
fourteen are the self-coincident shapes:

```
FREQ=MONTHLY;BYDAY=1MO,MO;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1TU,TU;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1WE,WE;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1TH,TH;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1FR,FR;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1SA,SA;BYSETPOS=1
FREQ=MONTHLY;BYDAY=1SU,SU;BYSETPOS=1
FREQ=MONTHLY;BYDAY=-1MO,MO;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1TU,TU;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1WE,WE;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1TH,TH;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1FR,FR;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1SA,SA;BYSETPOS=-1
FREQ=MONTHLY;BYDAY=-1SU,SU;BYSETPOS=-1
```

```
RRULE:FREQ=MONTHLY;BYDAY=1MO,MO;BYSETPOS=1
  naive    20260105 20260202 20260302 20260406 20260504 20260601 20260706 20260803
  stock    20260105 20260202 20260302 20260406 20260504 20260601 20260706 20260803
  patched  20260105 20260202 20260302 20260406 20260504 20260601 20260706 20260803
```

Under the intersection reading `BYDAY=1MO,MO` collapses to `1MO`, a one-element
set per month, and `BYSETPOS=1` selects that element. Under the union reading
the set is every Monday of the month and `BYSETPOS=1` selects the first, which
*is* the first Monday. The two readings produce the same answer because
`BYSETPOS` re-selects precisely the element the upstream mis-reading had
collapsed the set to. The mirror shape `-1MO,MO;BYSETPOS=-1` does the same at
the other end.

So: **a case carrying `BYSETPOS` is not automatically a test of the rule parts
`BYSETPOS` selects over. The selection can restore an answer that an earlier
stage destroyed.** That is a sibling of [finding
032](032-a-blind-spot-the-corpus-cannot-see.md)'s blindspot result — there two adjudicators
sat on opposite sides of a question so no case could discriminate it; here one
rule part launders the output of another. The practical consequence is small
and sharp: any of these fourteen rules, used as a regression test for this
defect, would pass against unpatched `dateutil`.

## A prediction I made and got wrong

Before running this I expected the `BYSETPOS` arm to show residual divergence
after the patch, on the reasoning that `BYSETPOS` and first-period truncation
already divide `dateutil` from `naive` (findings 004 and 032) and that a larger
candidate set would expose more of it. That is why the arm carries 84 *unmixed*
control cases of the same shape — so that a pre-existing disagreement could not
be charged to the patch. The controls all agree (42 + 42, `agreed-both`), the
mixed cases all agree after the patch, and the residual divergence I was
controlling for is not there at all on these shapes. The control was the right
thing to build and it had nothing to do.

## Not claimed

* This is not a review of the pull request. I did not run `dateutil`'s own test
  suite, read its CI, or evaluate the change as code.
* The patch applied here is the PR's **semantic** change at one site. The PR
  additionally reflows the surrounding `byeaster` / `bymonthday` / `byyearday`
  clauses, adds a changelog fragment, an `AUTHORS.md` line and its four tests;
  none of those alter behaviour, and this script leaves the other clauses
  textually as they are so that a mismatch against the vendored `rrule.py`
  fails loudly. Equivalent in behaviour, not identical in bytes.
* Nothing was filed upstream and no comment was posted. External outreach
  remains paused; see the note at the end of 013.
* The corpus is unchanged and `cases_id` with it. The six cases in
  `corpus/disputed.json` stay adjudicated for `naive` with `dateutil`'s current
  answers pinned — which is the point. **If `#1589` merges and the vendored pin
  moves, those pinned answers become wrong and the suite fails loudly rather
  than quietly.** 013 said it was built for that; this is the pre-registration
  that it will be tested.
* `naive` is the oracle throughout, so every "fixed" cell is agreement with my
  reading of §3.3.10 and not with an authority.

## Reproducing

```
python3 findings/repro/123-mixed-byday-union.py            # ~285s, writes the artifact
python3 findings/repro/123-mixed-byday-union.py --check    # re-measures, diffs, exits 1 on drift
python3 tests/test_mixed_byday_union.py
```
