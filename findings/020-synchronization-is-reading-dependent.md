# 020 — Whether `DTSTART` is synchronized is itself reading-dependent

*2026-09-08.*

## Why this was checked at all

On 2026-09-08 a stored example in finding 002 turned out to have an
unsynchronized `DTSTART` — `DTSTART:20180101` against `BYWEEKNO=53` — months
after I wrote it. RFC 5545 §3.8.5.3 says the recurrence set generated with an
unsynchronized `DTSTART` is undefined, so an example built on one is evidence of
nothing. That failure was found by hand, which is not a method. So I checked
every example in the finding set mechanically:
[`tools/audit_finding_dtstarts.py`](../tools/audit_finding_dtstarts.py) extracts
each rule + `DTSTART` pair from `findings/*.md` and asks
`naive.expand(rule, dtstart, limit=1)` whether the first occurrence is `DTSTART`.

It prints its unpaired rules rather than dropping them, because a silently
skipped example is exactly the failure the audit exists to catch. Those were
hand-read; one pairing at a 12-line window was spurious (a rule cited without
its own `DTSTART`, matched against a neighbouring example's), which is why the
window is three lines.

## Result on the documents

Six examples expand to something other than their `DTSTART`. Four are fine as
written: finding 007's is a **quotation from RFC 5545's own Example 5** and the
unsynchronized `DTSTART` *is* the defect being reported; finding 004 already
carries an explicit correction saying its reproduction is undefined under
§3.8.5.3; finding 017's is already retracted; finding 015's two are claims about
this corpus's horizon metadata, not about a correct recurrence set.

One document was missing the caveat: finding 014's re-verification of
`dateutil` issue 1398 uses `DTSTART:20241110T000000` (a Sunday) with
`BYDAY=MO,TU,WE` — the same rule shape finding 004 flags, without finding 004's
note. Fixed there.

## The part that is not about the documents

The remaining flag, from finding 018:

```
DTSTART:20260302T090000
RRULE:FREQ=DAILY;BYHOUR=9,8;BYSETPOS=1
  whole period reading : first occurrence 20260303T080000  -> unsynchronized
  first-period cut     : first occurrence 20260302T090000  -> synchronized
```

and finding 017's, which behaves identically:

```
DTSTART:20260705T090000
RRULE:FREQ=WEEKLY;BYDAY=MO,SU,TU;BYSETPOS=1
  whole period reading : 20260706T090000  -> unsynchronized
  first-period cut     : 20260705T090000  -> synchronized
```

**When `BYSETPOS` is present, "is `DTSTART` synchronized" is not a fact about
the rule and the date. It depends on which reading of the first period the
expander uses — [finding 004](004-bysetpos-first-period-truncation.md)'s
unresolved question.** `DTSTART` is a member of the un-truncated candidate set
in both cases; what differs is whether `BYSETPOS` counts positions before it.

So the synchronization test cannot be used to dismiss a `BYSETPOS` example
without first fixing a reading — and fixing that reading is the thing finding
004 says is undecided. The test is only reading-neutral for rules without
`BYSETPOS`. My own verification rule silently assumed the whole-period reading,
which is the reading this project's expander happens to implement. That is
standing rule 9 turned inward: agreement between *my* expander and *my* check is
evidence about my code, not about the specification.

I do not think this makes §3.8.5.3 ill-defined in general. It makes it circular
for the specific rule shapes finding 004 is about, which is a smaller claim and
the only one the evidence supports.

## Not done

The audit covers examples written in the finding documents. Whether every
`rule + DTSTART` pair in `corpus/` is synchronized is a different and larger
question; finding 014 already restricts its property runs to the synchronized
subset, so the corpus is known not to be uniformly synchronized. Left open
deliberately.
