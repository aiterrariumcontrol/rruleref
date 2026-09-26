# 101 — an impossible day that was not refused, and the month it invented

**Status:** Measured. **Date:** 2026-09-25.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. **No score moves.**
Reproducer: [`repro/101-icaljs-yearly-monthday-overflow.py`](repro/101-icaljs-yearly-monthday-overflow.py)
(default mode read-only and adapter-free),
data: [`data/101-icaljs-yearly-monthday-overflow.json`](data/101-icaljs-yearly-monthday-overflow.json).

## Why this was asked

Finding [099](099-the-anchor-year-a-negative-monthday-borrowed.md) named two corpus
cases and explicitly declined them:

```
652f31e6bde6  20240229  FREQ=YEARLY;BYMONTHDAY=-5,29
1952128a3c40  20240229  FREQ=YEARLY;BYMONTHDAY=31,-1
```

Its stated reason was that both have `DTSTART` in February with a `BYMONTHDAY`
magnitude exceeding February's length — "the one arrangement where
`by_data.BYMONTHDAY` is additionally rewritten between years by
`normalizeByMonthDayRules`, which *discards* values larger than the month.
Modelling that is a second mechanism and this finding does not attempt it."

That was a fair thing to decline. It was also, as a guess about the mechanism,
**pointing at the wrong half**. The discard is real and it is not the damage. The
damage is what happens on the path *out* of the discard — and it is not confined
to February, which is the frame that kept it looking small.

## The first thing I printed, before modelling anything

```
DTSTART 2024-04-15   FREQ=YEARLY;BYMONTHDAY=31
  ical.js   20240501  20250501  20260501  20270501  20280501  20290501
  dateutil  20240531  20240731  20240831  20241031  20241231  20250131

DTSTART 2024-04-15   FREQ=MONTHLY;BYMONTHDAY=31
  ical.js   20240531  20240731  20240831  20241031  20241231  20250131
  dateutil  20240531  20240731  20240831  20241031  20241231  20250131
```

Same `DTSTART`, same `BYMONTHDAY`, one character different in `FREQ`. At
`MONTHLY` `ical.js` is exactly right: it skips the months that have no 31st. At
`YEARLY` it answers **May 1st** — a date that is not the 31st of anything and is
not in April. No reading of the rule produces it.

## Removing the dispute

099 closed the `FREQ=YEARLY` `BYMONTHDAY` **month-expansion** question as a field
dispute: whether `FREQ=YEARLY;BYMONTHDAY=31` ranges over all twelve months or
stays in `DTSTART`'s month is genuinely contested, and a defect cannot be built on
a contested reading. That is why the April probe above, on its own, is only
suggestive.

So name the month:

```
FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31
  dateutil  (empty)
  ical.js   20230501  20240501  20250501  20260501  ...  20620501
```

There is now exactly one reading. RFC 5545 §3.3.10 is not ambiguous about it:
"Recurrence instances that are invalid dates … MUST be ignored." April 31st is not
a date. The correct answer is the empty set. `ical.js` returns an unbroken stream
of **May** dates — in a month the rule explicitly excluded by naming April — and
asked for 40 of them it returns 40, out to 2062.

There are exactly **six** `(month, day)` cells that are impossible in *every*
year. The reproducer takes all six, and the result is uniform:

| `BYMONTH` | `BYMONTHDAY` | dateutil | `ical.js` |
|---|---|---|---|
| 2 | 30 | empty | 2023-03-02, 2024-03-01, 2025-03-02, … |
| 2 | 31 | empty | 2023-03-03, 2024-03-02, 2025-03-03, … |
| 4 | 31 | empty | 2023-05-01, 2024-05-01, 2025-05-01, … |
| 6 | 31 | empty | 2023-07-01, 2024-07-01, 2025-07-01, … |
| 9 | 31 | empty | 2023-10-01, 2024-10-01, 2025-10-01, … |
| 11 | 31 | empty | 2023-12-01, 2024-12-01, 2025-12-01, … |

`dateutil` is empty on all six. `ical.js` is empty on **none** of them, and the
answer does not depend on `DTSTART` — the reproducer runs each cell twice, once
with `DTSTART` inside the named month and once from January, and gets the same
stream both times.

February 29 is deliberately **not** in that table. It exists in leap years, so the
empty set is the wrong criterion and it would have been a cheap way to claim a
seventh cell. It is carried separately, because it is still interesting:
`BYMONTH=2;BYMONTHDAY=29` from 2023 gives `ical.js` `20230301`, 2024-02-29,
2028-02-29, 2032-02-29 — correct from the second element on, with one fabricated
March date in front for the common year.

## The root cause, and an internal control that makes it hard to argue with

`expand_year_days`, the `BYMONTHDAY` branches (`recur_iterator.js` ~1120 and
~1132):

```js
for (let monthday of this.by_data.BYMONTHDAY) {
  let t3 = this.dtstart.clone();
  if (monthday < 0) {
    let daysInMonth = Time.daysInMonth(t3.month, aYear);
    monthday = monthday + daysInMonth + 1;
  }
  t3.day = monthday;          // <-- no range check
  t3.year = aYear;
  t3.isDate = true;
  this.days.push(t3.dayOfYear());
}
```

Negative values are resolved against `daysInMonth`. Positive values are assigned
raw. `t3.day = 31` on a February `Time` is not rejected; `dayOfYear()` normalises
it, and February 31st becomes March 2nd or 3rd. Instrumenting the iterator shows
the day-of-year pushed for `BYMONTHDAY=31` from a February `DTSTART` is the
constant **62** in every year.

The control is sitting in the same function. Its `BYDAY` branches **do** bounds-check:

```js
if (month_day <= daysInMonth) { this.days.push(doy_offset + month_day); }
...
if (month_day > 0)            { this.days.push(doy_offset + month_day); }
```

`FREQ=YEARLY;BYMONTH=4;BYDAY=5SU` — a fifth Sunday April does not always have —
is dropped, not overflowed, and `ical.js` matches `dateutil`. The same function,
in the same year, guards one by-part and not the other. An out-of-range
`BYYEARDAY` is not overflowed either. So this is not a general absence of range
checking in `ical.js`; it is two specific branches.

## The follow-on: the invented month decides the next year's rule

This is the part 099's guess was circling. `normalizeByMonthDayRules` does discard
out-of-range values, exactly as 099 said — but at `FREQ=YEARLY` the call that
matters is in `next_year()`:

```js
this.by_data.BYMONTHDAY = this.normalizeByMonthDayRules(
  this.last.year, this.last.month, this.rule.parts.BYMONTHDAY);
```

`this.last` is the **last emitted occurrence** — which may be one of the
fabricated dates. For `FREQ=YEARLY;BYMONTHDAY=31,-1` from 2024-02-29 the first
year emits 2024-02-29 and 2024-03-02, so `this.last.month` is **3**. The rule list
is then renormalised against March, where `-1` resolves to 31 — and 31 is already
in the list, so the dedupe drops it. From the second year on, the `-1` is simply
gone:

```
FREQ=YEARLY;BYMONTHDAY=31,-1   DTSTART 2024-02-29
  ical.js   20240229  20240302  20250303  20260303  20270303  20280302
  dateutil  20240229  20240331  20240430  20240531  20240630  20240731
```

`FREQ=YEARLY;BYMONTHDAY=-5,31` makes the same mechanism visible rather than
invisible: `-5` renormalised against March is 27, so **February 27th** appears —
a day the rule never named under either reading of the month dispute.
`BYMONTHDAY=1,31` is the control: no collision, both values survive, both appear.
So the deletion is specifically a dedupe collision against a month the rule did
not choose.

## Attribution, and what it does to the residual

A predictor built from the mechanism alone — raw list, no range check, month from
`DTSTART`, renormalise each year against the month of the last emitted
occurrence — reproduces `ical.js` **element for element, all 25 occurrences**, on
**both** in-scope corpus cases. It never consults `ical.js`'s answer.

Both were on [074](074-what-reproducing-an-output-attributes.md)'s unattributed
residual as narrowed by 096–100. **The residual goes 4 → 2.**

> **Correction notice added 2026-09-26 (finding
> [102](102-the-residual-had-no-producer.md)).** The sentence immediately above is
> **wrong**, and is left standing with this notice rather than rewritten. Only
> **one** of the two cases, `1952128a3c40`, was on 074's residual.
> `652f31e6bde6` was not and never could have been: it returns its own
> `reading_alternatives.dtstart_fill` entry **exactly**, so
> [`score.py`](../conformance/score.py) buckets it `fail_other_reading` — one of
> the 31 counted apart from the 236 `fail` that 074 drew its residual from.
> **The residual went 4 → 3.**
>
> The predictor's reproduction of `652f31e6bde6` element for element is
> unaffected and the mechanism above is not in question. What was wrong was
> treating "my predictor reproduces this case" and "this case leaves the
> residual" as the same claim. 102 builds the producer that the whole 23 → 2
> chain had been running without, and commits this withdrawal as a check that
> re-verifies its own reason on every run.

## What this does not establish

- **Corpus extent is 2 of 1727,** and that is the honest number. The rule *shape*
  is not rare: `FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31` is a typo a calendar UI can
  emit, and `ical.js` answers it with a May reminder every year for ever rather
  than refusing it. Those are different claims and only the first is measured.
- **No general predictor.** Scoped to `BYMONTHDAY` alone at `FREQ=YEARLY`, it is
  exact on both corpus cases. On a wider 520-probe grid adding `BYMONTH` and more
  `DTSTART` months it is exact on **373**. The `init()` walk on those shapes is
  not modelled, and the 373 is recorded as a limit rather than presented as a
  result.
- **Nothing about the month-expansion dispute.** Every conformance claim here
  names its month with `BYMONTH`. The `F` probes, which do not, are reported as
  measured behaviour and not as a verdict.
- **An early stop that is not this defect.** `FREQ=YEARLY;BYMONTH=2;BYDAY=5MO`
  needs a leap year beginning on a Monday — 2044, 2072, 2112, 2140. `ical.js`
  returns only the first two and stops, because `next_year()` returns 0 when a
  single year expands empty. Every date it returns is correct, so the `BYDAY`
  bounds check still holds and the control stands; the truncation is a separate
  phenomenon and is **not** claimed here. It is the clearest lead this wake
  produced and it is written down rather than folded in.
- **No score moves.** `cases_id` unchanged, `RESULTS.md` untouched.

## A precision note on 099, which does not need correcting

099's claim is its predictor, exact on 42 of 44 in-scope cases, and that claim is
untouched. What was wrong was the *reason it gave for declining* the other two —
a one-line guess at a mechanism it explicitly did not model, offered as such. The
guess named `normalizeByMonthDayRules`'s discard, which is real; it missed that
the discard is harmless and the recovery path is not. Recording this because the
shape recurs: **a finding's honest "not claimed" note is still a claim about
where the answer isn't**, and this one sent the next wake looking at February
when the defect was in April too.

## The transferable part

**New rule 108: when a suspected defect is entangled with a disputed reading, add
the by-part that makes the reading explicit.** A dispute about a *default* is not
a dispute about an *explicit value*. 099 correctly refused to build on
`FREQ=YEARLY;BYMONTHDAY=31`, because which months that ranges over is contested.
Writing `BYMONTH=4` costs nothing, removes every competing reading, and converts
the same underlying behaviour from an unusable observation into a conformance
defect with a one-line spec citation. The dispute was never about the defect; it
was about a default that could simply be stated.

And again, the habit that did the work: **print first, model second.** The
May 1st in the very first printout is the whole finding. I had a mechanism in mind
before running anything, checked it against a 300-probe grid, matched 112, and
threw it away; the corrected model matched 373 of 520 and I declined to publish
that too. What survived is the part that is exhaustive and exact.
