# 039 — what `BYSETPOS` selects from

*2026-09-14.*

## Why this was asked

[Finding 037](037-a-limit-that-runs-before-the-thing-it-limits.md) showed that
`ical4j` applies `BYMONTH` at `FREQ=WEEKLY` to the period *seed* rather than to
the expanded week, with two consequences: dates in months the rule excludes are
emitted, and whole weeks whose seed falls outside `BYMONTH` are discarded along
with their valid in-month days.

037 deliberately left `BYSETPOS` out of scope. The scored corpus holds 39 cases
that combine `FREQ=WEEKLY`, `BYMONTH` and `BYSETPOS`, and it was not obvious
which way the interaction would go. `BYSETPOS` keeps one element per week and
throws the rest away, so a plausible guess is that it *masks* the defect most of
the time. This is the measurement.

## Method

39 cases from `conformance/cases.ndjson` matching `FREQ=WEEKLY` + `BYMONTH` +
`BYSETPOS` and not `BYWEEKNO`. `ical4j` 4.1.1 under an explicit `en-GB` JVM
locale, so that the Monday-first week boundary of [036](036-a-score-that-depends-on-the-host-locale.md)
is not part of what is being measured. `python-dateutil`, `libical` and
`rrule.js` are the control, and a case counts only where all three agree —
three implementations, two lineages, so this is agreement evidence and not a
ruling (standing rule 9). Each rule was run to a 200-occurrence horizon and the
lists truncated to a **common endpoint** before comparison, because a spurious
early occurrence pushes a required late one off a fixed-length prefix and
imitates a drop (standing rule 33).

Data: [`data/039-bysetpos-interaction.json`](data/039-bysetpos-interaction.json).

## Result

The controls agree on 34 of the 39. `ical4j` differs from them on **14**.

`BYSETPOS` does not mask the defect, and it does not create one. Running the
same 34 rules with the `BYSETPOS` part removed — a *related* rule, not the same
rule (standing rule 4c) — `ical4j` is wrong on exactly the same 14 cases. The
sets are identical: no case is correct with `BYSETPOS` and wrong without, or
the reverse.

What changes is what a reader sees. `BYSETPOS` selects from the week set
`ical4j` built, and that set is the wrong one, so the wrong day can be the one
that survives.

## The case worth looking at

```
FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1    DTSTART:20260102T090000
```

`DTSTART` is a Friday, so every period seed is a Friday. Take the week of
Monday 2026-12-28. Its seed is Friday **2027-01-01**, which is in `BYMONTH=1`,
so the week survives the month filter. `BYDAY=FR,WE` then expands it to
Wednesday 2026-12-30 and Friday 2027-01-01, and nothing re-applies the month
limit. `BYSETPOS=1` takes the *first* element of that set.

It returns **2026-12-30** — a December date, from a rule that lists only
January and November — and the correct 2027-01-01 is gone. `BYSETPOS` does not
merely fail to hide the spurious date here; it prefers it. Over the 14 failing
cases, four emit out-of-month dates this way, 65 of them within the compared
horizon.

The other direction, from 037's second consequence:

```
FREQ=WEEKLY;BYDAY=MO,TU;BYMONTH=8;BYSETPOS=-1      DTSTART:20260804T090000
```

`DTSTART` is a Tuesday. The week of Monday 2026-08-31 has seed Tuesday
2026-09-01, outside `BYMONTH=8`, so the whole week is discarded — and with it
Monday 2026-08-31, which is what `BYSETPOS=-1` should have returned for August
2026. The rule's last August occurrence in each affected year simply is not
there.

## The corpus's own horizon hides six of them

Only **8** of the 14 are failures on the scored `en`-`GB` row. The other six
agree with `expect` for as long as the corpus case runs, and diverge only past
its `limit`. This is standing rule 33 pointing the other way: a short prefix
does not merely imitate defects that are not there, it also conceals defects
that are. The 176-case `ical4j` figure in
[RESULTS.md](../conformance/RESULTS.md) is a count of disagreements *within the
corpus's horizons*, and for this defect that is an undercount.

(One further case, `c29dd0b92b8f`, is a scored failure but is not counted among
the 14: the three controls do not agree on it, so this measurement has nothing
to say about it.)

## What this does and does not add

It adds nothing to 037's diagnosis; the mechanism is the same code path and the
same defect. It settles the scope question 037 left open: the corpus's `BYSETPOS` cases fail
at the same rate as the rest, and `BYSETPOS` makes the failure harder to notice
rather than rarer, because the output keeps the shape a correct answer would
have had. It also shows that this repository's own published count of `ical4j`
failures is bounded below by the horizons it chose.

Per standing rule 27, external outreach is paused. This is published here and
has not been reported upstream.
