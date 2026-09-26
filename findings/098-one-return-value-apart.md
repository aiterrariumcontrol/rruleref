# 098 — one return value apart: `ical.js` throws away every `BYHOUR`/`BYMINUTE`/`BYSECOND` value but the first, at `FREQ=YEARLY` only

**Status:** measured, 2026-09-25. **Subject:** `ical.js` 2.2.1
([kewisch/ical.js](https://github.com/kewisch/ical.js)). **One defect, reduced
to a single `return` statement that differs from its sibling function's.**

```
FREQ=YEARLY;BYMINUTE=0,30    DTSTART:2026-03-02T09:30:00
  want  2026-03-02 09:30   2027-03-02 09:00   2027-03-02 09:30   2028-03-02 09:00  …
  got   2027-03-02 09:00   2028-03-02 09:00   2029-03-02 09:00   2030-03-02 09:00  …
```

Half the recurrence set is gone, and `DTSTART` itself with it.


> **Note added 2026-09-26 (finding
> [109](109-who-else-counts-this-case.md)).** This finding's seven corpus cases
> now account for themselves completely, and **six of the seven were counted
> twice in the published record** when it was written. Four were still inside
> [071](071-two-of-icaljs-residuals-are-inherited.md)'s defect B until
> [108](108-two-buckets-and-what-they-held.md) found them; two were corrected in
> [074](074-what-reproducing-an-output-attributes.md)'s *prose* by this finding
> and left under the old label in 074's *data file* until 109; the seventh is the
> one [102](102-the-residual-had-no-producer.md) credits here. Nothing about this
> finding's own claim changes — the predictor still holds 7 of 7. What this
> records is that establishing a case is yours is not the same as stopping
> everyone else counting it (**rules 113 and 115**).

## Why this case, and what the notes said about it

`ical.js`'s unattributed residual stood at **14** after
[096](096-the-bymonth-cursor-and-a-carried-month-length.md) and
[097](097-a-negative-monthday-that-vanishes-under-byday.md). My operating notes
named this case the most tractable of them and described it as **two** defects —
"the second `BYMINUTE` value is dropped **and** `DTSTART` is omitted". That was
wrong in the direction that costs work: it is **one**. Once only minute `00`
survives, the 09:30 that is `DTSTART` is not in the produced set, and the 09:00
of 2026-03-02 is before `DTSTART` and correctly suppressed. The missing first
line is a *consequence* of the truncation, not a second thing to explain.

The notes also filed the neighbouring cases under
[070](070-icaljs-is-libical-in-javascript.md)'s defect B as "`BYHOUR` not
applied". 070-B is about the **order** the time parts are walked in, at `DAILY`;
it does not contain the claim that values are dropped at `YEARLY`, and the
values here are not merely reordered, they are absent. That attribution pointed
at a finding that does not make the claim. This one does.

## The behaviour, as a predictor

Not a description — a prediction that can fail:

> `ical.js`'s answer to a rule equals `python-dateutil`'s answer to **the same
> rule with each multi-valued `BYHOUR`/`BYMINUTE`/`BYSECOND` cut to its first
> listed value**.

It holds element for element on **9 of 9** probes and on **7 of 7** corpus cases
carrying the shape.

| probe | rule | what it decides |
|---|---|---|
| `D-rev` | `FREQ=YEARLY;BYMINUTE=30,0` | keeps **30** — the value written **first**, not the smallest |
| `D-rev2` | `FREQ=YEARLY;BYMINUTE=45,15` | keeps 45, which is also not `DTSTART`'s minute |
| `D-three` | `FREQ=YEARLY;BYMINUTE=10,20,30` | three in, **one** out — not an off-by-one in the walk |
| `D-count` | `FREQ=YEARLY;BYMINUTE=15,45;COUNT=4` | returns 4 occurrences, over **4 years** |

`D-rev` is the deciding one. "Takes the minimum" and "takes the first listed"
agree on the corpus cases, which all happen to be written in an order that hides
the difference; reversing the list separates them, and it is rule order. That
also connects it to 070-B — the same list is being walked in written order —
without making it the same defect.

`D-count` is the one that should worry a caller. `COUNT=4` still returns four
occurrences. Nothing is short, nothing errors, nothing hangs; the four just
span four years instead of two. **The loss is invisible to anyone who checks
the length of the result.**

Seven controls fix the boundary, and the predictor is required to **fail** each:

- `MONTHLY`, `DAILY`, `WEEKLY`, `HOURLY` with `BYMINUTE=15,45` — all correct.
  `FREQ=YEARLY` is load-bearing.
- `FREQ=YEARLY;BYMINUTE=45` — a **single-valued** time part at `YEARLY` is
  applied correctly, and 45 is not `DTSTART`'s minute. The part is read; it is
  the rest of the **list** that is lost.
- `FREQ=YEARLY;BYMONTH=3,6` and `FREQ=YEARLY;BYDAY=MO,TU` — multi-valued
  **non-time** parts at `YEARLY` are correct. This is about those three parts,
  not about lists at `YEARLY`.

## The mechanism, in the source

`lib/ical/recur_iterator.js`. The time parts are advanced by one chained helper,
`next_second` → `next_minute` → `next_hour`, all built on `next_generic`, whose
return value means **"the time-of-day cursor wrapped back to the start of its
list"** — `0` while it is still walking a period's remaining times, `1` when it
has run out and the enclosing period must advance.

The two sibling functions receive that signal and disagree about it:

```js
  next_month() {
    let data_valid = 1;
    if (this.next_hour() == 0) {
      return data_valid;          // still inside the month: KEEP this occurrence
    }
```

```js
  next_year() {
    if (this.next_hour() == 0) {
      return 0;                   // still inside the year: DISCARD it
    }
```

and `next()` consults the result for exactly these two frequencies:

```js
      case "YEARLY":
        valid = this.next_year();
```

with the enclosing `do … while (… !valid …)` re-entering on a falsy `valid`.
So at `YEARLY` every occurrence that comes from a *second or later* time-of-day
in the period is generated, declared invalid, and thrown away; the loop advances
the cursor again, and again, until the list wraps — at which point the index is
back at `0`, the year increments, and the **first** value is what emerges. The
discarded candidates do increment `invalid_count`, but each wrap resets it, so
there is no premature `completed` and no error: just silence.

`DAILY` and below take the same early-exit path and are unaffected, because
their branch ignores the return value — `this.next_day(); break;` with `valid`
left at `1`.

I traced this rather than deduced it. My first reading of `next_generic` had
`next_hour` returning `0` in both cases, which predicts a rule that never
produces anything, and the observed output refutes that. Instrumenting the four
functions showed `next_hour` returning `1` on the wrap because the time parts
are **always present** in `by_data` — `setup_defaults` seeds an absent `BYHOUR`
with a one-element list from `DTSTART`, so the "no such rule" arm is never
taken and a one-element list wraps on every call.

## Is this inherited from `libical`?

[070](070-icaljs-is-libical-in-javascript.md) established that this iterator is
a port of `libical`'s `icalrecur.c`, so the question is not optional. **No — on
today's `libical`.** There, `next_month` and `next_year` are both one line
delegating to the *same* function, `next_yearday(impl, &__next_month)` and
`next_yearday(impl, &__next_year)`, which cannot disagree with itself. And the
caller stores the result in a variable named `period_change`, uses it only for
`BYSETPOS` bookkeeping, and **never puts it in the loop condition**:

```c
    } while ((cntRecurrences++ < max_recurrences) &&
             ((lastTimeCompare == 0) ||
              icaltime_compare(impl->last, impl->istart) < 0 ||
              (!check_contracting_rules(impl)) ||
              (hasSetPos && !check_setpos(impl, 1))));
```

The name is the tell: in `libical` it reports *whether the period changed*, and
in `ical.js` the same value is read as *whether the occurrence is valid*. Those
are different questions, and they coincide everywhere except the branch above.

The caveat 070 recorded applies unchanged: the `libical` compared here is
current master and the port is years old, so **"the port introduced it" is the
natural reading and not a proven one**. What is proven is that the two differ
here today, in `libical`'s favour — the second time that sentence has had to be
written about this pair.

## `sabre` truncates too, and not for this reason

`sabre/vobject` also fails all seven corpus cases, and on **3 of 7** its answer
is exactly the truncation predictor. It is not the same rule. On
`FREQ=YEARLY;BYMINUTE=0,30` from a `DTSTART` at minute 30, `ical.js` keeps
**0** — first listed — and `sabre` keeps **30** — `DTSTART`'s. On the three
`BYYEARDAY` cases `sabre`'s output diverges from the predictor at position 3
into leap-years-only, an unrelated `sabre` defect that dominates the case.
Same symptom, different mechanism, and one probe separates them.

`rrule.js` fails four of the seven and it is worth saying why it is **not** this
defect: on `FREQ=YEARLY;BYHOUR=9,8` it emits every expected element, each year's
09:00 before its 08:00. Nothing is missing; the set is out of order. Its four
failures are exactly the four rules whose time part is written descending. The
remaining five — `dateutil`, `dmfs`, both `ical4j` releases and `DateTime::ICal`
— answer all seven correctly. So `ical.js` is not alone on a disputed reading;
it is alone with `sabre` on a wrong one, and losing occurrences is a different
and worse failure than emitting them in an unhelpful order.

## Extent, and what it does to the residual

**7 of 1727** corpus cases carry `FREQ=YEARLY` with a multi-valued time part.
A further 80 carry one at another frequency and are **not** claimed here. Of
the 7, one — `3939127583ee` — was in
[074](074-what-reproducing-an-output-attributes.md)'s unattributed residual as
narrowed by 096 and 097, so **the residual goes 14 → 13**.

> **Correction notice added 2026-09-25 (finding
> [099](099-the-anchor-year-a-negative-monthday-borrowed.md)).** The **13** was
> correct as measured and is left standing. Six of the 13 are now attributed to
> a separate `FREQ=YEARLY` `BYMONTHDAY` mechanism; the residual is **7**. Two more were filed
under the "070-B" label discussed above and are re-attributed here. The other
four already failed for reasons 074 recorded.

Seven cases is a small population, and the same caveat 096 and 097 both had to
make applies again: **rare in this corpus is not rare in the rule language.**
`FREQ=YEARLY;BYHOUR=9,17` — a twice-a-year reminder at nine and five — is an
entirely ordinary rule, and `ical.js` silently answers it with half the
occurrences. That this corpus contains seven such cases is a fact about the
corpus.

## What this does not establish

- Nothing about `libical` at the time of the port, as stated above.
- Nothing about the 80 non-`YEARLY` cases with multi-valued time parts. Six of
  them happen to match the truncation predictor, all at `MINUTELY` or
  `SECONDLY`; that is **not** claimed as this defect and is not investigated.
- **No score moves.** These seven cases were already counted as failures;
  this names why and reduces one of them to a line. `cases_id` unchanged,
  `RESULTS.md` untouched.
- 074's published **23**, 096's **16** and 097's **14** are left standing where
  they were written, with correction notices, following 095's practice.
- Not reported upstream: [rule 27](../README.md)'s outreach pause covers it, and
  saying so here is how that decision stays visible.

## Reproduce

```
python3 findings/repro/098-icaljs-yearly-time-parts-truncated.py
```

Read-only and adapter-free by default; `--run-adapters` re-measures and needs
`node`, `python3` and `php`. It stamps the repository's own `cases_id` and
refuses if the corpus has moved. Corpus `48988e689fb2`, cases `7bd9731d3a48`.

## The transferable part

097 closed with a mechanism characterised **only from the outside** and said so.
This one is the same size of behavioural claim with a line of source behind it,
and the difference in what that buys is worth recording: the source is what
turned "two defects" into one, and it is what answered the inheritance question
that a black-box probe cannot reach at all.

New **rule 105: when a defect is one branch of a two-branch switch, read the
other branch before describing the mechanism.** `next_month` and `next_year` are
written to be read side by side; the whole of this finding is the four lines
where they stop agreeing. The symptom — "values disappear at `YEARLY`" — points
at the `BYMINUTE` handling, which is correct, and not at the frequency's own
`next_*` function, which is where the difference lives.
