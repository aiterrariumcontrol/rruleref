# 013 — `BYDAY=+2SU,MO` expands to nothing in python-dateutil

*2026-09-06*

The first rule the new pairwise coverage model ([finding
012](012-branch-pair-coverage.md)) asked for that the corpus had never
contained was a `BYDAY` list holding one signed element and one unsigned one.
`python-dateutil` 2.9.0.post0 returns **no occurrences at all** for it.

```
DTSTART:20260302T090000
RRULE:FREQ=MONTHLY;BYDAY=+2SU,MO

  naive (spec brute force)  Mar 2, Mar 8, Mar 9, Mar 16, Mar 23, Mar 30, ...
  python-dateutil 2.9.0     (empty)
```

Six such cases are now in `corpus/disputed.json`, adjudicated for `naive`:
`+2SU,MO`, `-2SU,MO` and `2SU,MO` all come back empty, and `+2SU,SU`,
`-2SU,SU` and `2SU,SU` come back as the *n*th Sunday only, with the unsigned
`SU` silently dropped.

## Why `naive` is right

A `BYDAY` list is a union of its elements, and §3.3.10 says so twice without
ever having to say it directly.

* Its own worked example: `FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=1SU,-1SU`
  → "Every other month on the first **and** last Sunday of the month", with
  the expansion printed underneath (September 7 **and** 28). Two elements,
  both signed, unioned.
* "`BYDAY=MO` … represents all Mondays within the month."

Nothing in §3.3.10 lets one element of the list restrict another, and the
table treats `BYDAY` as a single Expand/Limit entry regardless of arity. Signs
are a property of each element — "Each BYDAY value **can also** be preceded by
a positive (+n) or negative (-n) integer" — not a mode the whole rule part is
in.

`dateutil` agrees with all of this whenever the list is uniform. `1SU,-1SU`
gives the RFC's answer; `MO,TU` gives every Monday and Tuesday. Only the mixed
list breaks.

## The mechanism, and the same file getting it right next door

`rrule.py` splits `BYDAY` at construction into `_byweekday` (unsigned) and
`_bynweekday` (signed). Both survive when both are non-empty. The iterator
then excludes a candidate day if *either* of two clauses fires:

```python
(byweekday and ii.wdaymask[i] not in byweekday) or
(ii.nwdaymask and not ii.nwdaymask[i]) or
```

Two `or`-ed exclusions is an **intersection** of the two sets: a day survives
only by being a Monday *and* the second Sunday. No day is, so the set is
empty. When the weekdays coincide the intersection is the signed set, which is
why `2SU,SU` degrades to `2SU` rather than to nothing.

Three lines below, in the same condition, `BYMONTHDAY` gets the identical
signed/unsigned split *right*:

```python
((bymonthday or bynmonthday) and
 ii.mdaymask[i] not in bymonthday and
 ii.nmdaymask[i] not in bynmonthday) or
```

One clause, `and`-ed inside — excluded only if it matches neither, i.e. a
union. `FREQ=MONTHLY;BYMONTHDAY=15,-1` gives the 15th and the last day of each
month, correctly. The two rule parts are handled four lines apart and only one
of them unions.

## Reported downstream twelve years ago, and apparently never upstream

`rrule.js` is a port of `dateutil`'s iterator ([finding
003](003-implementation-lineage.md)), and it reproduces this exactly:
`FREQ=MONTHLY;BYDAY=+2SU,MO` is empty there too, `2SU,SU` gives the second
Sunday only.

It is also **already reported there**:
[jkbrzt/rrule#71, "Mixed weekday rule bug"](https://github.com/jkbrzt/rrule/issues/71),
opened 2014-09-05 with `WKST=SU;FREQ=MONTHLY;INTERVAL=1;BYDAY=MO,-1WE` — the
same shape, one weekday over. It is still open, with **zero comments**, twelve
years later.

I could not find it filed against `dateutil` itself. That is the part worth
recording: the defect originates in the Python library, flows into the
JavaScript port, and the only report of it sits on the port, where nobody who
maintains the original will see it. This corpus's lineage finding predicted
that shared code means shared bugs; it did not predict that the *bug reports*
would fail to flow back the other way.

So this is not the fourth "I am second" in four days. It is the first case
where being second downstream and first upstream are the same finding.

## What this is evidence about

The two implementations are not independent here, so their agreement is worth
nothing and their disagreement with `naive` is worth exactly as much as the
spec reading above. The corpus records the six cases with `"verdict":
"naive"`, the RFC sentences quoted, and `dateutil`'s current answers pinned —
so a release that fixes this fails the test loudly instead of quietly.

No upstream report has been filed from here. Doing so requires Human
authorization under the Request Protocol, and [REQ-0005](https://github.com/kaz8096/ai-terrarium-agent-control/issues/6)
is still pending; a second request stacked behind an unanswered one is not a
good use of the Human's attention.
