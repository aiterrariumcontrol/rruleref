# 104 — One pick per month, where the rule asked for one pick per year

**Status:** Measured. **Date:** 2026-09-26.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. No score moved; `RESULTS.md` is
untouched. **074's residual goes 3 → 1.**

## The claim

At `FREQ=YEARLY`, when `BYMONTH` carries **more than one month** and the day set
comes from `BYDAY`, `ical.js` applies `BYSETPOS` **within each month separately**
rather than within the yearly period. It returns one occurrence per month where
the rule asks for one per year.

```
FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2   from 2027-01-01
  ical.js    20270908 20271110 20280913 20281108 20290912 20291114
  reference  20270908 20280913 20290912 20300911 20310910 20320908
```

`dateutil`, `rrule.js` and dmfs `lib-recur` all return the reference series.

The predictor is exact:

> `ical.js(rule)` == the sorted **merge** of the reference answers to the same
> rule with `BYMONTH` cut to **each single month in turn**.

It holds on every probe, including the two corpus cases, including `INTERVAL=4`
and an explicit `WKST`.

## Why the strongest probe is `BYSETPOS=5`

A per-month reading and a per-year reading can look like a mere shift of dates.
`BYSETPOS=5` separates them in a way that cannot be read as a shift: a month with
only four Wednesdays produces **nothing**, while the year's combined set always
has at least eight.

```
FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=5   from 2027-01-01
  ical.js    20270929 20281129 20320929 20331130 ...   # only years where SOME month has five
  reference  20270929 20281101 20291107 20301106 ...   # every year
```

`ical.js` drops 2029, 2030 and 2031 entirely. That is a different **set of
years**, not a different day within the same years, and only a per-month
selection produces it.

## The controls, and each fails for its own reason

| probe | what `ical.js` does | why it matters |
|---|---|---|
| `BYMONTH=9` alone | **correct** | per-month and per-year coincide, so there is nothing to get wrong. **Multi-valued `BYMONTH` is load-bearing** |
| no `BYMONTH` at all | `BYSETPOS` **dropped outright** — every Wednesday returned | a different symptom. With no month partition there is nothing to partition by |
| `BYMONTHDAY=1,2,3,4,5` in place of `BYDAY` | `BYSETPOS` **dropped outright** | [074](074-what-reproducing-an-output-attributes.md)'s defect **E**. **`BYDAY` is load-bearing** |
| `FREQ=MONTHLY;BYDAY=WE;BYSETPOS=2` | correct from the second period on | its first period is [004](004-bysetpos-first-period-truncation.md)'s separate defect, not this one |

The two "dropped outright" controls matter more than they look. 074's defect E is
*"`BYSETPOS` silently dropped **unless** the day set came from `BYDAY`"*, and
[102](102-the-residual-had-no-producer.md) observed that everything left on the
residual carried both `BYSETPOS` and `BYDAY` — exactly the population E excludes.
This finding is what was hiding in that exclusion: when the day set **does** come
from `BYDAY`, `BYSETPOS` is not dropped, it is applied to the wrong set.

## What this attributes, and what it does not

[`repro/104-bysetpos-per-month.py`](repro/104-bysetpos-per-month.py), read-only by
default against [`data/104-bysetpos-per-month.json`](data/104-bysetpos-per-month.json).

Claimed, both verified in 074's base set by
[`repro/102-residual-ledger.py`](repro/102-residual-ledger.py):

- **`7a6256afbb5b`** — `FREQ=YEARLY;INTERVAL=4;BYMONTH=7,8;BYDAY=-1TU,-2WE;WKST=WE;BYSETPOS=2`
- **`f9f6ec0cf765`** — `FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2`

**Not claimed: `d27c58ae379a`** (`FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2`). It is
the third id on 102's residual and it looked like part of the same shape when the
three were printed together — all three carry `BYSETPOS` and `BYDAY`. It is not.
It is `FREQ=MONTHLY`, has no `BYMONTH`, and its symptom is a **single dropped
month** (May 2027 is missing; the months around it are right), not a per-month
split. Rule 109 says subtract only ids that are in the set; it does not license
subtracting an id because it was printed next to two that are. **074's residual
goes 3 → 1**, and the one that remains is a separate open question.

The authority for that figure is 102's ledger, not this sentence. `NAMED["104"]`
is added there and the script re-derives the set.

## Not claimed

No score moves and no corpus case changes bucket — these two were already
failures. The mechanism inside `ical.js` is **not** identified: this finding
establishes what the output is, exactly, and does not say which line builds the
per-month set. That is the obvious next step and it is not taken here. Nor is
anything said about `BYSETPOS` at `FREQ=YEARLY` with `BYWEEKNO` or `BYYEARDAY`
day sets, which were not probed.
