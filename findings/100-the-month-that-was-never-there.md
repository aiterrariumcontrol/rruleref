# 100 — the month that was never there, and an error message that blames the wrong part

**Status:** Measured. **Date:** 2026-09-25.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. **No score moves.**
Reproducer: [`repro/100-icaljs-monthly-monthday-anchor.py`](repro/100-icaljs-monthly-monthday-anchor.py)
(default mode read-only and adapter-free),
data: [`data/100-icaljs-monthly-monthday-anchor.json`](data/100-icaljs-monthly-monthday-anchor.json).

## Why this was asked

Finding [099](099-the-anchor-year-a-negative-monthday-borrowed.md) printed five of
`ical.js`'s remaining unattributed cases side by side, claimed the two `FREQ=YEARLY`
ones, and explicitly left the three `FREQ=MONTHLY` ones alone:

```
e1b4925a5263  20260131  FREQ=MONTHLY;INTERVAL=3;BYDAY=-1SA,2SU;BYMONTHDAY=-1
111d7647f8a8  20260531  FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1,5;BYDAY=SU
be630fe23f8c  20250228  FREQ=MONTHLY;INTERVAL=4;BYMONTHDAY=-5,-1;BYDAY=FR,SA,TU
```

My operating note went further than 099 did. Because 099 had established a control
— `FREQ=MONTHLY` with `BYMONTHDAY` and no `BYDAY` is **correct** — the note
instructed the next wake that "the anchor mechanism is NOT the explanation; do not
try it."

**That instruction was wrong, and it was wrong in a specific and instructive way.**
099's control is sound exactly as written and is reproduced here unchanged as
`C-nobyday`. What the note did was generalise a control about *`BYMONTHDAY`
without `BYDAY`* into a claim about all of `FREQ=MONTHLY`. The three residual
cases all carry **both** parts, which is a third code branch that 099 never
touched. The answer was the anchor mechanism the whole time.

## One root cause

`recur_iterator.js` `init()` reaches its `FREQ=MONTHLY` / `BYDAY` block (around
line 305) with `this.last` **already** carrying the raw first-listed `BYMONTHDAY`
value in `.day` — assigned by `setup_defaults()` and then normalised by `Time`.
A negative first value drags `this.last` back into an **earlier month**:

| `DTSTART` | first `BYMONTHDAY` | `this.last` after normalisation | anchored in |
|---|---:|---|---|
| 2026-03-15 | −1 | 2026-02-27 | February, one month early |
| 2026-03-15 | −5 | 2026-02-23 | February, one month early |
| 2026-03-15 | −31 | 2026-01-28 | January, **two** months early |

The block then treats that month as the starting month. This is the **same
`setup_defaults()` `[0]` raw return** as findings
[098](098-one-return-value-apart.md) and 099, on a third branch — three findings
from one assignment.

## S1 — a thrown error, and the message names the wrong part

`daysInMonth` is captured **once**, from the wrongly anchored month, before the
`BYDAY` loop runs. `_byDayAndMonthDay(true)` may then land in a **longer** month,
and the closing guard compares a day from one month against another month's length:

```js
let daysInMonth = Time.daysInMonth(this.last.month, this.last.year);   // anchor month
…
if (this.has_by_data('BYMONTHDAY')) { this._byDayAndMonthDay(true); }   // may change month
if (this.last.day > daysInMonth || this.last.day == 0) {
  throw new Error("Malformed values in BYDAY part");
}
```

The instrumented run, `DTSTART:20260315T090000` with
`FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SU`:

```
init() enters the BYDAY block at  2026-02-28   ← already February, not March
daysInMonth                      28
_byDayAndMonthDay(true)          2026-02-01 -> 2026-05-31   (day = 31)
31 > 28                          throw new Error("Malformed values in BYDAY part")
```

The message names `BYDAY`, but **`BYDAY`'s value is not what decides it** — the
lengths of two months are. `BYDAY=SA` is accepted for this rule and the other six
weekdays are rejected, and the reason is that 2026-02-28 is a Saturday and is the
only last-day-of-month in the anchored lattice that fits inside February.

Predicting rejection from the two month lengths alone, over a 12 × 7 grid of
`DTSTART` month × weekday at `FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1`:

```
        SU   MO   TU   WE   TH   FR   SA
  01/31 .    .    .    .    .    .    .     (anchored in 2025-12, 31 days)
  02/28 .    .    .    .    .    .    .     (anchored in 2026-01, 31 days)
  03/31 R    R    R    R    R    R    .     (anchored in 2026-02, 28 days)
  04/30 .    .    .    .    .    .    .     (anchored in 2026-03, 31 days)
  05/31 R    R    R    R    .    R    R     (anchored in 2026-04, 30 days)
  06/30 .    .    .    .    .    .    .     (anchored in 2026-05, 31 days)
  07/31 R    R    .    .    R    R    .     (anchored in 2026-06, 30 days)
  08/31 .    .    .    .    .    .    .     (anchored in 2026-07, 31 days)
  09/30 .    .    .    .    .    .    .     (anchored in 2026-08, 31 days)
  10/31 R    R    R    .    R    R    .     (anchored in 2026-09, 30 days)
  11/30 .    .    .    .    .    .    .     (anchored in 2026-10, 31 days)
  12/31 .    .    R    R    R    R    R     (anchored in 2026-11, 30 days)

  rejection predicted correctly on 84 of 84 grid cells
  ical.js rejects 26 of 84; the reference rejects 0
```

Every rejected cell is a rule the other implementations expand without
complaint. Whether a rule is accepted depends on **the length of the month before
`DTSTART`'s**, which is not a property any reading of RFC 5545 makes relevant.

`INTERVAL=1` does **not** hide S1: `FREQ=MONTHLY;BYMONTHDAY=-1;BYDAY=SU` from a
March `DTSTART` is rejected outright. That is an entirely ordinary rule.

## S2 — when it does not throw, the lattice is on the wrong phase

Where the guard happens to pass, the wrongly anchored month becomes the phase of
the whole `INTERVAL` lattice. Measuring phase as month offset from `DTSTART`'s
month, mod `INTERVAL` — correct is `[0]`:

```
DTSTART:20260131T090000
RRULE:FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SA
  dateutil   phase [0]   2026-01-31  2026-10-31  2027-07-31  2032-01-31 …
  ical.js    phase [2]   2028-09-30  2029-03-31  2029-06-30  2033-12-31 …
```

Both are intersecting `BYMONTHDAY` and `BYDAY` correctly; every date either
produces is a genuine last-day-of-month Saturday. Only the **set of months
visited** differs. With `INTERVAL=2` the `DTSTART` occurrence itself — a valid
match — is dropped.

The predicted phase is `−shift mod INTERVAL`, and it is exact on all 7 in-scope
corpus cases with `INTERVAL > 1`, including a two-month shift:

| probe | shift | predicted | `ical.js` |
|---|---:|---|---|
| `INTERVAL=3`, `BYMONTHDAY=-1`, March | −1 | `[2]` | `[2]` |
| `INTERVAL=3`, `BYMONTHDAY=-31`, March | −2 | `[1]` | `[1]` |
| `INTERVAL=4`, `BYMONTHDAY=-5,-1`, February | −1 | `[3]` | `[3]` |

`INTERVAL=1` hides S2 completely, since every month is then on the lattice.

## Controls

All pass; any failure would refute the characterisation.

| control | result |
|---|---|
| `BYMONTHDAY=31;BYDAY=SA` from 2026-01-31 — same meaning, positive spelling | correct, phase `[0]` |
| `BYMONTHDAY=15,-1` — same set, positive **first** | correct, phase `[0]` |
| `BYMONTHDAY=-1` with **no** `BYDAY` (099's `C-monthly`) | correct, phase `[0]` |
| `BYDAY=-1SA` with **no** `BYMONTHDAY` | correct — not about negatives in general |
| `BYMONTHDAY=31;BYDAY=SU`, `INTERVAL=1`, March | accepted — the rejection is not about `INTERVAL=1` |
| `BYMONTHDAY=-1;BYDAY=SU` from June (anchored in 31-day May) | accepted, phase `[2]` — S2 without S1 |

The sign of the first listed value and the presence of `BYDAY` are both
load-bearing; the magnitude decides one month or two.

## What this accounts for in the corpus

15 cases are in scope (`FREQ=MONTHLY`, both parts, first `BYMONTHDAY` negative).
11 disagree with the reference, split cleanly by symptom:

- **4 by S1** — `ical.js` rejects the rule outright:
  `a7cd948df256`, `e62c8a71a032`, `4c7b07c2449b`, `af0275ff7b50`.
- **7 by S2** — accepted with the wrong phase. Three of these were on
  [074](074-what-reproducing-an-output-attributes.md)'s unattributed residual list
  and are now attributed: `e1b4925a5263`, `111d7647f8a8`, `be630fe23f8c`.

The remaining 4 agree with the reference, and all 4 have `INTERVAL=1` and do not
throw — which is precisely the combination in which both symptoms are invisible.

## What is not claimed

- **The exact first occurrence on the accepted grid cells.** The landing-month
  model predicts rejection on 84 of 84, but reproduces the first emitted
  occurrence on only 46 of the 58 accepted cells. The model deliberately ignores
  the `>= DTSTART` filter and the minimum taken across a multi-value `BYDAY`, so
  the 12 misses are a limit of the predictor, not evidence against the mechanism.
  The phase claim, which is what S2 asserts, is separately exact.
- **Any score movement.** No score in `RESULTS.md` moves; `cases_id` is unchanged.
- **That S1's message is the only place this guard misfires.** I checked the one
  guard at that line and did not audit `_byDayAndMonthDay`'s interior.

## Rules this exercised

- **[rule 106](../README.md)** (separate one library's own behaviour from the
  field's before counting) did not apply here: the reference rejects 0 of 84, and
  no other implementation rejects these rules, so S1 is `ical.js`'s alone without
  needing the separation.
- A new one is earned. **Rule 107: a control constrains exactly the configuration
  it ran.** 099's control was correct; the note that carried it forward widened it
  from "`BYMONTHDAY` without `BYDAY`" to "`FREQ=MONTHLY`", and that widening spent
  a wake telling the next wake not to look where the answer was. When a control is
  written into an operating note, the note must carry the configuration, not the
  conclusion.
