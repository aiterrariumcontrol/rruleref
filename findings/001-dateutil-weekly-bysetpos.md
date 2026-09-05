# Finding 001 — `python-dateutil`: `FREQ=WEEKLY` + `BYSETPOS` mis-numbers the first week

**Status:** confirmed against `python-dateutil` 2.9.0.post0, Python 3.13.5.
**Not yet reported upstream** — see "Reporting" below.

## Summary

For `FREQ=WEEKLY` with `BYSETPOS`, dateutil builds the first period's instance
set from `DTSTART` onward instead of from the start of the week. Positions are
therefore numbered within a truncated set, and the rule emits an instance that
is not at any requested position in the real week.

It does **not** do this for `FREQ=MONTHLY` or `FREQ=YEARLY`, which use the full
period and correctly yield nothing for a first period whose selected position
precedes `DTSTART`. So this is an internal inconsistency, not a deliberate
policy about `DTSTART`.

## Reproduction

```python
from datetime import datetime
from dateutil.rrule import rrulestr

# DTSTART is Wednesday 2027-01-06. Its ISO week is Mon 01-04 .. Sun 01-10.
ds = datetime(2027, 1, 6, 9, 0)
r = rrulestr("RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=1", dtstart=ds)
print([d.strftime("%a %Y-%m-%d") for d in r[:3]])
```

```
actual:   ['Wed 2027-01-06', 'Mon 2027-01-11', 'Mon 2027-01-18']
expected: ['Mon 2027-01-11', 'Mon 2027-01-18', 'Mon 2027-01-25']
```

Position 1 of the week Mon 01-04 .. Sun 01-10 is **Mon 2027-01-04**, which is
before `DTSTART`. That instance is excluded by the bound, and the week
contributes nothing. `Wed 2027-01-06` is position 3, never position 1.

Every subsequent week agrees with the expected output; the defect is confined
to the `DTSTART` week.

## The same shape handled correctly at other frequencies

```python
# MONTHLY: position 1 of Jan 2027 is Mon 01-04, before DTSTART -> January is
# correctly skipped.
rrulestr("RRULE:FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1", dtstart=datetime(2027,1,20,9))[:1]
# -> [Mon 2027-02-01]   correct

# YEARLY: 2nd Thursday of 2026 is 01-08, before DTSTART -> 2026 correctly
# skipped.
rrulestr("RRULE:FREQ=YEARLY;BYDAY=TH;BYSETPOS=2", dtstart=datetime(2026,3,31,9))[:1]
# -> [Thu 2027-01-14]   correct
```

## Why the expected output is the expected output

RFC 5545 §3.3.10 defines `BYSETPOS` over "the set of recurrence instances
specified by the rule" for a period, and §3.8.5.3 generates the recurrence set
and *then* bounds it. `DTSTART` bounds the output; it does not redefine where
the period begins. dateutil's own `MONTHLY`/`YEARLY` behaviour agrees with that
reading, which is the strongest evidence that `WEEKLY` is the odd one out.

The week boundary is `WKST` (default `MO`), not `DTSTART`'s weekday. With
`WKST=SU` and `BYDAY=SA,SU;BYSETPOS=1` from Wed 2027-01-06, dateutil emits
`Sat 01-09` first and only then settles onto `Sun 01-10, 01-17, ...`; the
steady state is right and the first week is wrong in the same way.

## Reporting

Blocked on [REQ-0004], the pending request for scoped authorization to open
Issues on public third-party repositories. Until that is decided I am not
contacting the project. The finding is written up here so that it is ready to
send the moment it is authorized, and is useful as a corpus case regardless.

[REQ-0004]: https://github.com/kaz8096/ai-terrarium-agent-control/issues/5
