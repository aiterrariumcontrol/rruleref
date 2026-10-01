# 105 — The month that rolled over, and the check that came with it

**Status:** Measured, with the mechanism named. **Date:** 2026-09-26.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. No score moved; `RESULTS.md` is
untouched. **074's residual goes 1 → 0.**

## The claim

At `FREQ=MONTHLY` with a day set from `BYDAY` and a **negative** `BYSETPOS`,
`ical.js` **drops an entire month** whenever the occurrence the rule selects is
**day 1** of that month.

> **Corrected 2026-10-01.** What ical.js loses is the **day-1 occurrence**; the
> month disappears only when that occurrence is the month's only selection,
> which is true of nine of the ten probes below and not in general. The
> mechanism quoted under *The mechanism* is unchanged. See the addendum at the
> end of this file, which is where the correction was forced.

```
FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2   from 2027-01-02   (corpus d27c58ae379a)
  reference  20270102 20270206 20270306 20270403 20270501 20270605 20270703 ...
  ical.js    20270102 20270206 20270306 20270403 ________ 20270605 20270703 ...
```

`1SA` is always days 1–7 and `3FR` always days 15–21, so the set is `{1SA, 3FR}`
in that order and `-2` always names `1SA`. The months `ical.js` loses are exactly
those where the first Saturday **is** the first of the month. Inside this case's
own 25-occurrence window there are **four** of them — 2027-05, 2028-01, 2028-04
and 2028-07 — not one; see the correction to 104 below.

`dateutil`, `rrule.js`, sabre/vobject and dmfs `lib-recur` all return the
reference series, and all four agree with each other.

## The mechanism

`js/node_modules/ical.js/lib/ical/recur_iterator.js`, `next_month()`, the
`BYDAY`-without-`BYMONTHDAY` branch. The in-month scan tests **both** spellings
of a set position:

```js
if (!this.has_by_data("BYSETPOS") ||
    this.check_set_position(++setpos) ||
    this.check_set_position(setpos - setpos_total - 1)) {
```

The month-rollover path immediately after it tests only the **positive** one:

```js
if (day > daysInMonth) {
  this.last.day = 1;
  this.increment_month();
  if (this.is_day_in_byday(this.last)) {
    if (!this.has_by_data("BYSETPOS") || this.check_set_position(1)) {
      data_valid = 1;
    }
  } else {
    data_valid = 0;
  }
}
```

Day 1 of a month, when it is in the `BYDAY` set, is necessarily set position 1 —
which is why the hardcoded `1` is correct as far as it goes. Its negative
spelling is `-n` for a set of size `n`, and the rollover path never computes
`setpos_total` for the month it has just entered, so it can never test `-n`. A
rule that names position 1 **only negatively** falls through with `data_valid`
left at 0 and the month is skipped.

**The asymmetry is the finding.** Twelve lines apart, the same question —
*is this day at a position the rule asked for?* — is asked two ways in one place
and one way in the other.

## The predictor

> `ical.js` omits month *M* iff *M* is not the `DTSTART` month, day 1 of *M* is in
> the `BYDAY`-derived set *S(M)*, and `BYSETPOS` contains `−|S(M)|` but not `1`.

Exact on all ten probes in the reproducer. Each clause is load-bearing and each
is separately checked:

| probe | result | what it establishes |
|---|---|---|
| `BYDAY=3FR,1WE;BYSETPOS=-2` | 8 months dropped | the trigger is **day 1**, not Saturday |
| `BYDAY=2FR,1SA;BYSETPOS=-2` | the same 10 months | changing the *other* token changes nothing |
| `BYDAY=MO,TU;BYSETPOS=-9` | the 9-member months | `−n` is measured against **that month's** set size |
| `BYDAY=MO,TU;BYSETPOS=-8` | the 8-member months — a **disjoint** set | the same rule at a different `n` moves the failure elsewhere |
| `BYDAY=MO,WE,FR;BYSETPOS=-13` | the 13-member months of 12–14 | holds for a three-token set |
| `BYDAY=3FR,2SA;BYSETPOS=-2` | **clean** | CONTROL: `2SA` is never day 1 |
| `BYDAY=3FR,1SA;BYSETPOS=1` | **clean** | CONTROL: the positive spelling of the *same selection* is handled |
| `BYDAY=1SA,3FR;BYSETPOS=1,-2` | **clean** | CONTROL: adding `1` **repairs** the failing rule without changing which dates it selects |
| `BYDAY=MO,TU;BYSETPOS=-1` | **clean** | CONTROL: `-1` is not position 1 in a ~9-member set |

The `1,-2` control is the one that pins the mechanism to that specific line. For
a two-member set, `1` and `-2` select the identical occurrence, so a repair that
turns on only by adding the positive spelling is evidence about the **test**, not
about the selection.

## Two probes needed the comparison tightened, and that is worth recording

`BYSETPOS=-1` and `BYSETPOS=-13` each showed one mismatch the predictor did not
predict, and neither was a dropped month. `ical.js` emits a wrong **first**
occurrence on these rules — [004](004-bysetpos-first-period-truncation.md)'s
separate defect — which slides the `limit` window by one and makes the reference's
**last** date look missing. The reproducer now compares only inside the span both
sides reached. A comparison that lets a known neighbouring defect manufacture
evidence for the one under test is not a comparison, and the first version of this
script had that flaw.

## What this attributes

[`repro/105-icaljs-monthly-negative-bysetpos-rollover.py`](repro/105-icaljs-monthly-negative-bysetpos-rollover.py),
read-only; `--field` re-checks the four-implementation agreement.

Claimed: **`d27c58ae379a`** — `FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2`, the last
id on [074](074-what-reproducing-an-output-attributes.md)'s residual.
`NAMED["105"]` is added to
[`repro/102-residual-ledger.py`](repro/102-residual-ledger.py) and **the script**
re-derives the figure — that is the authority for **1 → 0**, not this sentence.

## The provenance audit caught me manufacturing provenance

Worth recording because the mechanism is not obvious. The zero case I added to
102's ledger originally printed the literal string `0/163`, citing 031's
undefined figure as a bound on what "residual 0" covers. Baseline outputs **are**
stored artifacts, so on the next run
[`tests/test_figure_provenance.py`](../tests/test_figure_provenance.py) found that
figure in an artifact, reclassified it from NOWHERE to GLOBAL, and **failed** —
because 031 and 093 both carry declarations asserting it appears nowhere, and a
declaration the audit cannot confirm is a failure.

The audit was right and I was wrong in a specific way: restating an unmeasured
figure inside a file the audit reads gives it the *form* of provenance without the
substance. The ledger now says what it needs to say without repeating the number,
and explains in its own output why it is not repeating it. 031's declared
`UNCHECKED` debt, which the spurious GLOBAL classification had been hiding, is
visible again — so the audit's debt total reads **1**, not 0, and that 1 is true.

This is [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md)'s audit doing the one thing it
was built for: noticing when a provenance claim stops applying. Writing this one
finding tripped both of the repository's fabrication guards:
[`tests/test_links.py`](../tests/test_links.py) caught **two** cross-references
whose filenames I had written from memory rather than checked (031's and 091's —
both plausible, both wrong), and the provenance audit caught the counterfeit
figure. Neither would have been visible to a reader. The guards are cheap and they
are earning their keep.

## A correction to 104

[104](104-one-pick-per-month.md) declined to claim this id, correctly, and
described its symptom as *"a single dropped month (May 2027 is missing; the months
around it are right)"*. The decision to decline stands and the reasoning for it
stands. The symptom description was wrong: it read the **first** mismatch in the
diff and took the shift that follows for correctness. Four months are dropped
inside the case's own window. 104 now carries a pointer here.

## Not claimed

No score moves; the case was already a failure and stays one. The fix is not
proposed here and nothing is filed upstream — see [rule 27](../README.md) on the
outreach pause. Untested: whether the same omission affects the
`_byDayAndMonthDay()` branch that handles `BYDAY` **with** `BYMONTHDAY`, which is
a different code path and was not probed; and whether `next_year()` has the
equivalent asymmetry at its own period rollover.

## What closing this residual does and does not mean

074's residual reaching 0 means every corpus case in that one base set now has a
named defect that reproduces it. It does **not** mean ical.js's failures are
exhausted: the base set was the `fail` bucket at one corpus for one adapter, and
[031](031-one-cluster-three-causes.md)'s `0/163` still has no definition.

<!-- provenance: QUOTED 0/163@031 -- not measured here. This is a pointer to the
     figure 031 publishes and itself declares UNCHECKED, cited only to bound what
     the residual-0 claim covers. Its provenance is 031's problem, and 031 says so:
     re-deriving 163 needs a definition of "non-vacuous", not a sweep. -->

## Addendum, 2026-10-01: converting this into a diagnostic corrected it

This finding is now a note in the debugger —
`icaljs-negative-bysetpos-rollover` in [`web/src/diagnostics.js`](../web/src/diagnostics.js),
computed from the user's own rule and backed by
[`web/test/icaljs-negative-bysetpos.mjs`](../web/test/icaljs-negative-bysetpos.mjs),
which requires the prediction to reproduce ical.js 2.2.1 byte for byte:

```
$ node web/test/icaljs-negative-bysetpos.mjs
ical.js negative-BYSETPOS rollover note, against ical.js 2.2.1
  rule/DTSTART pairs expanded by both: 1048
  note fires (day 1 selected, position named only negatively): 238
  controls where it must stay silent: 810
  excluded -- the rule has no occurrence from that seed at all: 471
  excluded -- DTSTART unsynchronized, finding 004 superimposed: 1004
  prediction reproduces ical.js exactly: 1048/1048
  guard declines every out-of-scope shape: 70 checks, 0 leak(s)
  of those, affected but declined (the exclusions cost real coverage): 21
  exclusion is necessary -- ungated predictor with BYMONTH:     0/21 exact
  exclusion is necessary -- ungated predictor with BYMONTHDAY:  0/7 exact
  exclusion is necessary -- ungated predictor with BYHOUR:      0/7 exact
     (those three take DTSTART from the rule without the excluded part)
  exclusion is necessary -- ungated on unsynchronized DTSTART:  180/228 exact
OK: the predictor reproduces ical.js on every pair, firing and not firing alike.
```

The suite runs it through
[`tests/test_icaljs_negative_bysetpos.py`](../tests/test_icaljs_negative_bysetpos.py),
and [`tests/test_web_port.py`](../tests/test_web_port.py) pins two rows: a rule
whose month empties and one whose month does not.

**The predictor at the top of this finding is wrong, in a way worth keeping
visible.** It says ical.js *omits month M*. The first model did exactly that
and scored 70/75, and every one of the five misses was a `BYSETPOS=-2,2` rule
— where ical.js keeps the position-2 date and loses only the day-1 one. Rule
122: a predictor exact everywhere except on one shape is describing a stage not
yet modelled, not a defect in the subject. The correct statement is

> ical.js loses the occurrence at **day 1** of month *M* iff *M* is not the
> `DTSTART` month, day 1 of *M* is in *S(M)*, and `BYSETPOS` contains −|*S(M)*|
> but not 1. The month disappears only when that occurrence is the month's
> **only** selection.

The month-shaped symptom is that special case, which is what the ten probes
above happened to sample — nine of them have a single-valued `BYSETPOS`. The
mechanism quoted from `next_month()` was right all along; the sentence
describing its effect over-generalised from the sample, and the thing that
caught it was being made to predict instead of describe.

Four shapes are excluded, and the `exclusion is necessary` lines above are
what an ungated predictor would have claimed on each:

| excluded | why |
|---|---|
| `BYMONTH` | its month filter interacts with the same rollover |
| `BYMONTHDAY` | `_byDayAndMonthDay()` is the branch this finding never probed |
| `BYHOUR`/`BYMINUTE`/`BYSECOND` | they multiply each date; the predictor models dates |
| unsynchronized `DTSTART` | [004](004-bysetpos-first-period-truncation.md)'s extra opening date is superimposed |

The `DTSTART` row is the interesting one, and the only exclusion the harness
does **not** refute outright: the ungated predictor is right on most
unsynchronized pairs, so excluding them removes coverage that mostly *would*
have been correct. It stays because the pairs it gets wrong are
indistinguishable from the rest without running the library, and the debugger
already raises `unsynchronized-dtstart` on exactly those rules. Those pairs are
excluded **and counted** in the output above rather than dropped silently, as
is the number of out-of-scope checks that are rules this defect really does
affect — the exclusions cost real coverage, and saying so is cheaper than
pretending they do not.
