# 106 — One branch of fourteen, and what that explains

**Status:** Measured. **Date:** 2026-09-26.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. No score moved; `RESULTS.md` is
untouched. No corpus case changes bucket and **074's residual stays at 0**.

## What this adds

[104](104-one-pick-per-month.md) established, exactly, *what* `ical.js` does to
`BYSETPOS` at `FREQ=YEARLY` when `BYMONTH` is multi-valued and the day set comes
from `BYDAY`: it selects within each month instead of within the year. It said in
so many words that the mechanism was not identified and that naming it was the
obvious next step. This finding names it, and the naming turns out to explain
more than 104 asked about.

## The mechanism

`recur_iterator.js`, `expand_year_days()`. The function is a **branch table over
the set of by-parts present** — fourteen arms, dispatched on `partCount` and on
which parts are in the rule:

| # | arm | `BYSETPOS`? |
|---|---|---|
| 1 | `partCount == 0` | no |
| 2 | `1: BYMONTH` | no |
| 3 | `1: BYMONTHDAY` | no |
| 4 | `2: BYMONTHDAY + BYMONTH` | no |
| 5 | `1: BYWEEKNO` — `// TODO unimplemented in libical` | no |
| 6 | `2: BYWEEKNO + BYMONTHDAY` — `// TODO unimplemented` | no |
| 7 | `1: BYDAY` | no |
| 8 | **`2: BYDAY + BYMONTH`** | **yes** |
| 9 | `2: BYDAY + BYMONTHDAY` | no |
| 10 | `3: BYDAY + BYMONTHDAY + BYMONTH` | no |
| 11 | `2: BYDAY + BYWEEKNO` | no |
| 12 | `3: BYDAY + BYWEEKNO + BYMONTHDAY` — `// TODO unimplemted` | no |
| 13 | `1: BYYEARDAY` | no |
| 14 | `2: BYYEARDAY + BYDAY` | no |
| — | `else { this.days = []; }` | no |

`check_set_position()` is called from **arm 8 and from nowhere else** in the whole
function. And in arm 8 it sits *inside* the month loop:

```js
for (let month of this.by_data.BYMONTH) {
  ...
  if (this.has_by_data("BYSETPOS")) {
    let by_month_day = [];
    for (let day = 1; day <= daysInMonth; day++) {
      t.day = day;
      if (this.is_day_in_byday(t)) by_month_day.push(day);
    }
    for (let spIndex = 0; spIndex < by_month_day.length; spIndex++) {
      if (this.check_set_position(spIndex + 1) ||
          this.check_set_position(spIndex - by_month_day.length)) {
        this.days.push(doy_offset + by_month_day[spIndex]);
      }
    }
  }
```

`by_month_day` is rebuilt for each month and never accumulated across the year,
so the set positions `check_set_position` sees are **month positions**. That is
104, in four lines.

## Consequence 1 — every one of 104's controls is the same fact

104 published four controls and gave each its own explanation. The branch table
replaces all four with one:

| 104's control | branch it lands on | why it did what it did |
|---|---|---|
| single-valued `BYMONTH` correct | **8** | same arm; with one month, per-month *is* per-year |
| no `BYMONTH` → `BYSETPOS` dropped | 7 | arm 7 never consults it |
| `BYMONTHDAY` instead of `BYDAY` → dropped | 4 | arm 4 never consults it |
| `FREQ=MONTHLY` correct | — | a different function, `next_month()` |

A control that was four separate observations is one observation about where a
call appears.

## Consequence 2 — 074's defect E is stated too generously

[074](074-what-reproducing-an-output-attributes.md)'s defect **E** reads
*"`BYSETPOS` silently dropped **unless** the day set came from `BYDAY`"*. The
branch table says that exclusion is too wide: arm 7 is `BYDAY` alone and it drops
`BYSETPOS` too, as do arms 9, 10, 11 and 14, all of which have `BYDAY`. At
`FREQ=YEARLY` the surviving case is `BYDAY` **with** `BYMONTH` **and nothing
else**.

This widens E rather than narrowing it — no id is unclaimed and no arrow on
[102](102-the-residual-had-no-producer.md)'s ledger changes. The residual is
re-derived by the producer on every run and still reads **23 of 23, residual 0**.

## Consequence 3 — the answer to a question 105 left open, and it is "no"

[105](105-the-month-that-rolled-over.md) closed by asking whether `next_year()`
has the same month-rollover asymmetry it had just found in `next_month()`. It
does not, and it cannot, and the reason is structural rather than calendrical.

`next_month()` carries **two inline copies** of the set-position test: the
in-month scan tests both spellings, the rollover path twelve lines later tests
only `check_set_position(1)`. `next_year()` carries **none** — on entry and on
rollover alike it calls `expand_year_days()`, the single function above, whose one
`BYSETPOS` site tests `spIndex + 1` **and** `spIndex - by_month_day.length` in the
same loop. There is no second copy to fall out of step.

Measured, not just read: `FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=-1` returns
the last Wednesday of each named month, and `BYSETPOS=-5` returns exactly the
months that have a fifth Wednesday — the negative spellings of the two positive
probes 104 published, behaving identically to them. **105's defect is a
consequence of duplicated logic, not of the year/month boundary**, and the
prediction in my own operating note — that 103 and 105 would turn out to be two
faces of one habit in this file — was wrong.

## Consequence 4 — two of the three stubs are unreachable

Arms 6 and 12 are both `// TODO unimplemented` and both mention `BYWEEKNO`
together with `BYMONTHDAY`. Neither can ever execute, because `init()` refuses
that pair first:

```js
// BYWEEKNO and BYMONTHDAY rule parts may not both appear
if ("BYWEEKNO" in parts && "BYMONTHDAY" in parts) {
  throw new Error("BYWEEKNO does not fit to BYMONTHDAY");
}
```

RFC 5545 §3.3.10's table marks `BYWEEKNO` and `BYMONTHDAY` both **Expand** at
`FREQ=YEARLY` and states no prohibition on the pair; the only stated restriction
on `BYWEEKNO` is that `FREQ` must be `YEARLY`. Corpus case **`7b92dd911bbb`**
(`FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-2,2;BYMONTHDAY=31,5;WKST=SU`) is a real rule
that lands on it: `ical.js` refuses, while `dateutil`, `rrule.js` and dmfs
`lib-recur` all return the same 19 occurrences. `ical4j` 4.1.1 and sabre/vobject
answer, and disagree with those three and with each other.

**This is recorded, not claimed as a separate defect.** Three implementations
agreeing is suggestive and the RFC's silence is not a licence; a refusal that
matches `libical`'s own behaviour deserves its own finding with its own controls,
and it does not get one here. What *is* asserted is narrow and structural: the
error message presents itself as rule validation, and behind it sit two arms that
were never implemented — so the check is load-bearing in a way its wording does
not disclose.

## Consequence 5 — one stub answers empty and two refuse, for a reason worth naming

Arm 5, `BYWEEKNO` alone, is also an unimplemented stub, but it produces **no
error at all**: `FREQ=YEARLY;BYWEEKNO=2,36` returns the empty set. The difference
is a deliberate swallow:

```js
try { this.init(); } catch (e) {
  if (e instanceof InvalidRecurrenceRuleError) this.completed = true;
  else throw e;
}
```

Arm 5 yields no days, so `init()`'s year search runs to its `untilYear` default of
20000 — **17,974 calls to `expand_year_days()`**, counted by the reproducer — and
raises `InvalidRecurrenceRuleError`, which is swallowed into an empty iterator. The
`BYWEEKNO`+`BYMONTHDAY` pair raises a plain `Error`, which propagates and reaches
the caller. An unimplemented arm is therefore indistinguishable from a rule with
genuinely no occurrences.

That unbounded search is [103](103-the-year-the-iterator-gave-up.md)'s, already
published as the willing-to-wait half of its asymmetry. It is **cited here, not
re-claimed** — this is a second route to the same code, and finding a published
defect from a new direction is not a new defect.

## The reproducer

[`repro/106-icaljs-yearly-bysetpos-one-branch.py`](repro/106-icaljs-yearly-bysetpos-one-branch.py)
walks every arm of the table with a rule that lands on it, classifies what
`BYSETPOS` did — `honoured`, `per-month`, `dropped`, `empty`, `refused` — and
fails if any arm behaves differently from what the code reading predicts. All
fifteen rows match. The classification is adapter-independent where it matters:
`dropped` is decided by comparing `ical.js` against **`ical.js` with `BYSETPOS`
removed**, not against the reference, so a row can be called *dropped* without
first agreeing what the right answer is.

The 17,974 figure is produced by the script rather than quoted into it.

## Not claimed

No score moves; no corpus case changes bucket; `cases_id` unchanged;
`RESULTS.md` untouched; 074's residual stays **0** and no id is claimed or
released. Nothing is filed upstream (rule 27). The `BYWEEKNO`+`BYMONTHDAY`
refusal of Consequence 4 is **not** claimed as a defect. The table is `ical.js`
2.2.1 as vendored here and the arm list is read from this copy, not from upstream
`main`. `FREQ=MONTHLY`'s own branch structure in `next_month()` is not
enumerated — only the contrast in Consequence 3 is drawn — and the
`_byDayAndMonthDay()` path 105 left untested is still untested.

Two incidental oddities were seen in arms 11 and in the `BYMONTH`+`BYWEEKNO`
pre-pass and are **deliberately left unexamined** rather than folded in: arm 11
tests `if (this.by_data.BYWEEKNO.indexOf(weekno))` with no `>= 0`, and the
pre-pass indexes its `validWeeks` map by a position into `BYWEEKNO` rather than by
a week number. Each would need its own probes and controls. Writing them down is
not publishing them.

New standing **rule 111: when a finding has established a predictor but not a
mechanism, the mechanism is worth going back for, because a mechanism explains
the controls as well as the claim.** 104 needed four separately-reasoned controls
to pin its predictor; one call site explains all four, corrects an older finding's
scope, and answers a question a later finding had left open. A predictor tells you
what will happen. A mechanism tells you what else is true.
