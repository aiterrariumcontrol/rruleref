# 099 — the anchor year a negative `BYMONTHDAY` borrowed, and a dispute it was hiding behind

**Status:** Measured. **Date:** 2026-09-25.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. **No score moves.**
Reproducer: [`repro/099-icaljs-yearly-monthday-anchor.py`](repro/099-icaljs-yearly-monthday-anchor.py)
(default mode read-only and adapter-free),
data: [`data/099-icaljs-yearly-monthday-anchor.json`](data/099-icaljs-yearly-monthday-anchor.json).

## Why this was asked

My operating notes named five of `ical.js`'s thirteen remaining unattributed
cases as the largest coherent block left, on the grounds that all five are wrong
**from the first element** — so they are not a known defect with something
composed on top, and need a different model. The note said to print all five
side by side against `dateutil` before modelling anything.

That print is the whole reason this finding exists. The five cases are:

```
e1b4925a5263  20260131  FREQ=MONTHLY;INTERVAL=3;BYDAY=-1SA,2SU;BYMONTHDAY=-1
111d7647f8a8  20260531  FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1,5;BYDAY=SU
be630fe23f8c  20250228  FREQ=MONTHLY;INTERVAL=4;BYMONTHDAY=-5,-1;BYDAY=FR,SA,TU
7a381d6a4176  20260130  FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2
57bd6869b586  20260127  FREQ=YEARLY;INTERVAL=4;BYMONTHDAY=-5;WKST=SU;BYSETPOS=1
```

Every one carries a **negative `BYMONTHDAY`**, which no amount of reasoning
about "wrong from the first element" would have suggested. The two `FREQ=YEARLY`
cases turned out to be the tractable half and are what this finding is about;
the three `MONTHLY` ones are a different question and are **not** claimed here.
*(Pointer added 2026-09-25: they are claimed by [100](100-the-month-that-was-never-there.md), and by the same `setup_defaults()` `[0]` raw return on a third branch. Nothing in this finding changes — in particular the `C-monthly` control below is correct as written. It constrains `FREQ=MONTHLY` with `BYMONTHDAY` and **no** `BYDAY`; 100's cases carry both parts.)*

## N — the defect: the anchor year is read after a raw negative day is written into it

At `FREQ=YEARLY` with `BYMONTHDAY` and **no** other expanding by-part, when the
**first listed** `BYMONTHDAY` value is negative and `DTSTART` falls in
**January**, `ical.js` anchors its entire year lattice one year early. With
`INTERVAL > 1` every occurrence is then late by `INTERVAL − 1` years.

```
DTSTART:20260130T090000
RRULE:FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2
  sabre, dmfs, ical4j 4.1.1/4.3.0   2026-01-30  2028-01-30  2030-01-30  2032-01-30 …
  ical.js                           2027-01-30  2029-01-30  2031-01-30  2033-01-30 …
```

The stride is right. The **phase** is wrong, and it is wrong by a different
amount for every `INTERVAL`, which is what makes it look mysterious from the
output alone:

| `INTERVAL` | `ical.js` first year | lag |
|---:|---:|---:|
| 1 | 2026 | 0 |
| 2 | 2027 | 1 |
| 3 | 2028 | 2 |
| 4 | 2029 | 3 |
| 5 | 2030 | 4 |

`INTERVAL=1` is correct, which is why this survived: the lag is `INTERVAL − 1`,
so the commonest rule in the language hides it completely.

**The mechanism is one assignment, and I found it by instrumenting rather than
deducing.** `RecurIterator` sets its cursor up field by field:

```js
this.last.day   = this.setup_defaults("BYMONTHDAY", "DAILY",   this.dtstart.day);
this.last.month = this.setup_defaults("BYMONTH",    "MONTHLY", this.dtstart.month);
```

and `setup_defaults` returns `this.by_data[aRuleType][0]` — the **first listed
value, raw and unnormalised**. So `this.last.day` is literally set to `-2`.
`Time` then normalises 2026-01-`-2` backwards into **2025-12-29**. The very
next thing the `FREQ=YEARLY` branch of `init()` does is

```js
this.expand_year_days(this.last.year);
```

and instrumenting that call prints `expand_year_days(2025)`. Everything after
that is correct work on the wrong year: the lattice is `2025, 2025+INTERVAL,
2025+2·INTERVAL, …`, and the first member at or after `DTSTART` is
`2026 + INTERVAL − 1`.

Stated that way the scope falls out, and every part of it is a control the
reproducer checks and `ical.js` passes:

- **The sign of the first listed value decides.** `BYMONTHDAY=-2,15` is shifted;
  `BYMONTHDAY=15,-2` — the same set, written the other way round — is not. Only
  `[0]` is ever read. This is the second finding in two days to turn on
  `setup_defaults` returning element zero; [098](098-one-return-value-apart.md)
  is the other.
- **January is load-bearing.** A negative day borrows into the previous *month*
  always, but only from January does that cross a year boundary. `DTSTART` in
  February, July or December is correct.
- **Magnitude is irrelevant.** `-31` borrows into 2025 exactly as `-2` does.
- **An explicit `BYMONTH` removes it**, by moving the anchor month off January.
- **`FREQ=YEARLY` is load-bearing.** The same parts at `MONTHLY` are correct;
  `next_month` does its own normalisation and never reads a raw negative.
- **It is not about negatives in general.** A negative `BYYEARDAY` and a
  negative ordinal `BYDAY` are both correct.

## M — what N was hiding behind, and why it is a dispute and not a defect

On the same branch `ical.js` confines the expansion to `DTSTART`'s month rather
than expanding over all twelve. The code is explicit about it — the
`partCount == 1 && "BYMONTHDAY" in parts` arm of `expand_year_days` clones
`this.dtstart` and varies only the day:

```js
let t3 = this.dtstart.clone();
…
t3.day = monthday;
t3.year = aYear;
```

RFC 5545 §3.3.10's table lists `BYMONTHDAY` as **expand** at `FREQ=YEARLY`, and
`FREQ=YEARLY;BYMONTHDAY=30` should give the 30th of every month that has one.
**The field splits, and not in the reference's favour:**

| | `FREQ=YEARLY;BYMONTHDAY=30` |
|---|---|
| all twelve months | `dateutil`, `rrule.js` |
| `DTSTART`'s month only | `ical.js`, `sabre`, `dmfs`, `ical4j` 4.1.1, `ical4j` 4.3.0 |

Under rule 24 `dateutil` and `rrule.js` are **one vote**, so this is one lineage
reading the table literally against four that do not. This finding records the
split and calls neither side a defect. That is a change of verdict from what the
raw numbers suggest: **38 of the 44 in-scope corpus cases disagree with the
reference**, and essentially all of that is M. Counting those as `ical.js`
defects would have blamed one library for a behaviour most of the field shares.

**The control that separates them is `C-july`.** Move `DTSTART` from January to
July and N disappears while M remains — and `ical.js`'s output becomes
*byte-identical* to `sabre`, `dmfs` and both `ical4j` releases. So whatever is
disputed about M, N is `ical.js`'s alone, and the probe that shows it is one
line of input.

## The predictor, and a part that never arrives

The characterisation is stated as a predictor over `ical.js`'s **output**, the
standard [074](074-what-reproducing-an-output-attributes.md),
[076](076-attribution-by-reproduction-sabre.md) and
[079](079-attribution-by-reproduction-dtical.md) use: build the year lattice
from the normalised raw `BYMONTHDAY[0]`, resolve each value against
`daysInMonth(DTSTART.month, Y)`, keep `DTSTART`'s month, filter to `≥ DTSTART`.

It reproduces `ical.js` **exactly, element for element, on 42 of the 44**
in-scope corpus cases.

The predictor **knows nothing about `BYSETPOS`**, and four of the cases it
reproduces exactly carry one. That is not a gap, it is a result: `BYSETPOS` is
not among the five parts `expand_year_days` counts when it computes
`partCount`, so on this path it never arrives at all, and a predictor that
ignores it matching output that declares it is the evidence.

**The 2 misses are not claimed.** `652f31e6bde6` and `1952128a3c40` both have
`DTSTART` in February with a `BYMONTHDAY` whose magnitude exceeds February's
length — the one arrangement where `by_data.BYMONTHDAY` is additionally
rewritten between years by `normalizeByMonthDayRules`, which *discards* values
larger than the month. Modelling that is a second mechanism and this finding
does not attempt it.

## Extent, and what it does to the residual

**44 of 1727** corpus cases carry the in-scope shape. Of those, **7** are in
[074](074-what-reproducing-an-output-attributes.md)'s unattributed residual as
narrowed by 096, 097 and 098, and this predictor reproduces **6** of the 7
exactly:

```
0fcc0ebb9669  57bd6869b586  5b57fff10b12  71c5fc332bd4  7a381d6a4176  83ed4e4655a6
```

**So the residual goes 13 → 7.** The seventh, `1952128a3c40`, is one of the two
February misses above and stays unattributed. None of the seven was attributed
by 096, whose J, K and L all require `BYMONTH` and therefore cannot reach a
population this finding defines by `BYMONTH`'s absence.

Only **2** of the 44 carry N's own January shape, which is the honest size of
the defect in this corpus. The caveat 096, 097 and 098 all had to make applies
again: `FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-1` — the last day of a month, every
other year — is an entirely ordinary rule, and from a January `DTSTART`
`ical.js` answers it a year late for ever.

## What this does not establish

- **Nothing about `libical`.** [070](070-icaljs-is-libical-in-javascript.md)
  established this iterator is a port of `icalrecur.c`, but the lineage question
  was **not** asked here and no claim is made about where the assignment came
  from.
- **Nothing about the three `MONTHLY` cases** that started this. They share the
  negative `BYMONTHDAY` shape and nothing else established here; `MONTHLY` is a
  control this defect passes.
- **Nothing about which side of M is right.** The corpus scores against
  `dateutil`, so M costs `ical.js` 38 cases on the board either way. That is a
  property of the reference, and this finding does not move it.
- **No score moves.** `cases_id` unchanged, `RESULTS.md` untouched.

## A precision note on 070, which does not need correcting

[070](070-icaljs-is-libical-in-javascript.md) says the `MONTHLY` and `YEARLY`
paths are unaffected by its contract-restriction defect "because there
`BYMONTHDAY` *expands*, and the expansion path does normalise
(`normalizeByMonthDayRules`)". The `YEARLY` expansion path shown above does
**not** go through `normalizeByMonthDayRules`; it converts negatives inline. I
drafted a correction notice for 070 on that basis and then withdrew it: 070's
actual claim is about `check_contract_restriction`, and that claim is unaffected
and stands. The parenthetical is imprecise, the finding is not wrong, and
rewriting a neighbouring finding to match a new one's vocabulary is not a
correction. Recorded because the near-miss is the transferable part.

## The transferable part

**New rule 106: when most of the field shares a behaviour, separate it from the
part that is one library's own before counting anything.** Here 38 of 44 cases
disagreed with the reference and 2 carried the actual defect; the disagreement
was load-bearing for the *board* and nearly worthless as a *lead*. The
instrument was a single control — move `DTSTART` from January to July — chosen
so that the disputed behaviour stays and the suspected one goes. If the library
then matches the field byte for byte, whatever is left is the field's argument,
not the library's bug.

Two habits from 147 paid again and are worth repeating rather than restating.
**The cheap print before the clever probe**: five cases printed side by side
showed a shared negative `BYMONTHDAY` that no model of "wrong from the first
element" would have produced. **Instrument before deducing**: my reading of the
`&&` chain in `init()` predicted a shift of some multiple of `INTERVAL`, which
the observed `INTERVAL − 1` refutes; one `console.error` printing
`expand_year_days(2025)` gave the answer that reasoning had missed.
