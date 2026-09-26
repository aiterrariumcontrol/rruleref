# Finding 107 — the week that was listed first

**Status:** defect in `ical.js` 2.2.1. Reproduced. Corrects
[finding 071](071-two-of-icaljs-residuals-are-inherited.md)'s defect D.

## Claim

In `ical.js` 2.2.1, `lib/ical/recur_iterator.js`, `expand_year_days()` dispatches
on which `BY` parts are present. The arm for `partCount == 2 && "BYDAY" in parts
&& "BYWEEKNO" in parts` filters the expanded days like this:

```js
let weekno = tt.weekNumber(this.rule.wkst);

if (this.by_data.BYWEEKNO.indexOf(weekno)) {
  this.days.push(day);
}
```

There is no `>= 0`. `Array.prototype.indexOf` returns `-1` when the value is
absent — truthy — and `0` when the value is the **first element** — falsy. So the
test does not ask "is this week listed". It asks "is this week listed anywhere
other than position 0", and answers yes for every week that is not listed at all.

The consequence is that `BYWEEKNO` on this arm does not select weeks. It
**excludes at most one**: whichever week number the caller happened to write
first. The two arms immediately above this one in the same function both write
`.indexOf(...) >= 0`.

## The observable that needs no semantic argument

`BYWEEKNO` at `FREQ=YEARLY` has a genuinely contested corner — which year owns a
straddling week — and this repository has three findings that decline to call it a
bug ([002](002-byweekno-year-boundary.md),
[008](008-byweekno-previous-year-last-week.md),
[059](059-which-year-owns-a-straddling-week.md)). This finding does not depend on
any of that being settled, because the defect is visible in a form the RFC
forecloses outright.

RFC 5545 section 3.3.10 defines each `BY` part as a comma-separated **list** of
values. Nothing gives the order of that list a meaning. So two spellings of the
same set must produce the same occurrences, and here they do not:

With `DTSTART=20270101T090000` and `UNTIL=20271231T000000` — 2027 has 52 ISO
weeks, and the rule asks for Mondays:

| rule | `ical.js` |
|---|---|
| `FREQ=YEARLY;BYDAY=MO` | 52 days — every Monday |
| `FREQ=YEARLY;BYDAY=MO;BYWEEKNO=10,20` | 51 days — every Monday **except** week 10's |
| `FREQ=YEARLY;BYDAY=MO;BYWEEKNO=20,10` | 51 days — every Monday **except** week 20's |

Reordering the list changes which day is missing. Both answers are also wrong in
the obvious way: the reference answer is two days, `20270308` and `20270517`.

## The probe that pins it to an index

"`ical.js` honours only the first `BYWEEKNO` value" is a tempting summary and it
is wrong. The deciding probe is a **negative value in first position**:

| rule | `ical.js` |
|---|---|
| `...;BYWEEKNO=-2,10` | **52 days — nothing excluded at all** |
| `...;BYWEEKNO=10` | 51 days — week 10's Monday excluded |
| `...;BYWEEKNO=-2` | 52 days — nothing excluded |

Week 10 *is* listed in the first rule, and it survives. `-2` is never equal to a
computed week number, so index 0 simply never matches, and with index 0 unable to
match, nothing can be excluded. A "first value wins" model has to predict that
week 10 is dropped. The `indexOf` model predicts this result exactly, and it is
the kind of prediction only the code reading could have made.

This also explains why the corpus cases carrying a negative `BYWEEKNO` return
`ical.js`'s unfiltered expansion rather than anything selective.

## Controls

Each fails for a reason of its own, which is what shows the defect belongs to
this arm rather than to `BYWEEKNO` generally.

| control | result | why it fails |
|---|---|---|
| `BYWEEKNO` with no `BYDAY` | empty | arm 5's body is empty — genuinely unimplemented |
| `BYWEEKNO` with `BYMONTHDAY` | `init()` throws `BYWEEKNO does not fit to BYMONTHDAY` | refused before any arm is chosen |
| `BYWEEKNO` with `BYMONTH` | identical to the same rule with no `BYWEEKNO` | the `BYMONTH`+`BYWEEKNO` pre-pass deletes `BYWEEKNO` |
| `BYWEEKNO` with `BYSETPOS` | `BYSETPOS` dropped; still 51 days | this arm never calls `check_set_position()` |

The last one is [finding 106](106-one-branch-of-fourteen.md)'s widened defect E
and the first is [finding 103](103-the-year-the-iterator-gave-up.md)'s unbounded
first-occurrence search. Both are **cited, not re-claimed**: reaching a published
defect from a new direction is not a new defect.

Note that `BYSETPOS` does **not** count toward `partCount`. `expand_year_days()`
copies five names into its local `parts` — `BYDAY`, `BYWEEKNO`, `BYMONTHDAY`,
`BYMONTH`, `BYYEARDAY` — so a rule carrying `BYSETPOS` alongside `BYDAY` and
`BYWEEKNO` still has `partCount == 2` and still lands here.

## What the field does

`DTSTART=20270101T090000`, `FREQ=YEARLY;BYDAY=MO;BYWEEKNO=10,20`, first 8:

| implementation | answer |
|---|---|
| `dateutil` | `20270308, 20270517, 20280306, 20280515, …` |
| `rrule.js` | identical |
| `dmfs` | identical |
| `ical4j` 4.1.1 | identical |
| `sabre/vobject` | identical, plus `DTSTART` seeded in front |
| `ical.js` | every Monday from `20270104`, less week 10's |

Four implementations agree character for character; the fifth differs only by the
`DTSTART` fill this repository already tracks separately. `ical.js` is alone, and
it is not alone in a contested corner — it is alone on a rule the rest of the
field answers identically.

## What this corrects in finding 071

[Finding 071](071-two-of-icaljs-residuals-are-inherited.md) grouped 31 corpus
failures under **defect D**, "`BYWEEKNO` at `FREQ=YEARLY` is unimplemented", and
supported the word *unimplemented* by pointing at branch bodies that are
literally empty. Recomputed from the corpus by this finding's reproducer, the 31
split three ways:

| branch reached | cases | is "unimplemented" the right word? |
|---|---|---|
| arm 5 — body is empty | **20** | yes |
| arm 11 — body runs, `indexOf` without `>= 0` | **8** | **no** |
| `BYMONTH`+`BYWEEKNO` pre-pass — `BYWEEKNO` deleted | **3** | no |

So *unimplemented* is an accurate account of 20 of the 31, not of all 31. The
distinction is not cosmetic. An unimplemented branch returns nothing and is
indistinguishable from a rule with no occurrences; a branch with an inverted
membership test returns a **large, plausible-looking, order-dependent** answer,
which is the harder failure to notice and a different fix. The eight ids:

```
1087a3bfe5b6  FREQ=YEARLY;BYWEEKNO=-2;BYDAY=MO;BYSETPOS=-1            (BYSETPOS)
1b491afa4ef0  FREQ=YEARLY;BYDAY=FR;BYWEEKNO=-2,1;WKST=WE;BYSETPOS=2   (BYSETPOS)
2265a310aa9a  FREQ=YEARLY;BYWEEKNO=1;BYDAY=MO,TU
36fa68873abe  FREQ=YEARLY;INTERVAL=2;BYWEEKNO=53,20;BYDAY=SA,WE
52cb89bd1169  FREQ=YEARLY;BYDAY=SA,WE;BYWEEKNO=52
76656eaa6952  FREQ=YEARLY;BYDAY=MO,SU;BYWEEKNO=-2
a11bc9303af3  FREQ=YEARLY;BYDAY=FR,SA;BYWEEKNO=2,52
c17aa9fd3b11  FREQ=YEARLY;BYDAY=FR,MO,SU;BYWEEKNO=1;WKST=MO
```

Two of them — `a11bc9303af3` and `36fa68873abe` — carry a multi-valued
`BYWEEKNO`, so the order dependence above is live in the corpus and not only in
constructed probes.

**No score moves and no residual moves.** All eight sat inside 071's defect-D
bucket, which was never part of the 85-case base set
[finding 074](074-what-reproducing-an-output-attributes.md) drew its residual
from; that residual remains 0 and is untouched here. 071's *count* of 31 was
right. What was wrong was the single mechanism it offered for all of them.

## Reproduce

```
python3 findings/repro/107-icaljs-byweekno-indexof.py
```

Read-only; runs the `icaljs` and `dateutil` adapters and writes nothing. In the
drift manifest.

## Rule 112

**A bucket named after a shape is not an explanation, and it will absorb a
second defect silently.** 071's defect D was keyed on "`FREQ=YEARLY` and
`BYWEEKNO` present" — a *shape* — and then given one mechanism. Every case that
matched the shape inherited the mechanism without anyone checking that the code
path was the same, and a branch that runs got filed next to a branch that is
empty. When a bucket is defined by the input's shape rather than by the path the
input takes, count the paths before naming the cause.
