# Finding 001 — WITHDRAWN as a bug: `FREQ=WEEKLY` + `BYSETPOS` with an unsynchronized `DTSTART`

**Status: WITHDRAWN 2026-09-05.** Previously classified "confirmed bug in
`python-dateutil`, ready to report upstream". That classification was wrong and
the report was never sent. What follows is the corrected account; the original
claim is described in full below rather than deleted.

**Current classification:** a behavioral difference in territory RFC 5545
explicitly declares undefined. Not a conformance violation. Not reportable as a
bug on this evidence.

## What was originally claimed

That for `FREQ=WEEKLY` with `BYSETPOS`, `python-dateutil` builds the first
period's instance set from `DTSTART` onward instead of from the start of the
`WKST`-aligned week, numbers positions within that truncated set, and so emits
an instance that sits at no requested position in the real week:

```python
ds = datetime(2027, 1, 6, 9, 0)   # a Wednesday
rrulestr("RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=1", dtstart=ds)[:3]
# -> ['Wed 2027-01-06', 'Mon 2027-01-11', 'Mon 2027-01-18']
```

Position 1 of the week Mon 01-04 .. Sun 01-10 is Mon 01-04, which precedes
`DTSTART`. Wed 01-06 is position 3. The argument was that `DTSTART` bounds the
output but does not redefine where the period begins, and that dateutil's
`MONTHLY`/`YEARLY` paths — which do skip a first period whose selected position
precedes `DTSTART` — showed `WEEKLY` to be the inconsistent one.

## Why that is not a bug

RFC 5545 §3.8.5.3 (Recurrence Rule, Description):

> The "DTSTART" property value SHOULD be synchronized with the recurrence rule,
> if specified. The recurrence set generated with a "DTSTART" property value
> not synchronized with the recurrence rule is undefined.

The reproduction supplies a Wednesday `DTSTART` to a rule that selects the
first weekday of each week, i.e. Mondays. `DTSTART` is not synchronized with
the rule, so the recurrence set is undefined by the spec's own terms. An
implementation cannot violate a requirement the spec declines to make.

The decisive check, which the original writeup did not run: give the same rule
a **synchronized** `DTSTART` and dateutil is correct.

```
DTSTART Mon 2027-01-04 (synchronized)   -> Mon 01-04, 01-11, 01-18, 01-25   correct
DTSTART Wed 2027-01-06 (unsynchronized) -> Wed 01-06, Mon 01-11, 01-18, 01-25
```

The entire discrepancy is confined to the unsynchronized case. Emitting
`DTSTART` itself as the first instance is a defensible reading of "the DTSTART
property defines the first instance in the recurrence set" (§3.8.5.3, same
paragraph) — arguably more defensible than silently dropping the user's start
date.

The internal-inconsistency argument does not rescue the claim either.
Differing across frequencies inside undefined territory is untidy, not
non-conforming. It is at most a consistency question for the maintainers, and
not one worth a maintainer's time on this evidence.

## What went wrong in the reasoning

Three failures, all in the same direction:

1. **Reproduced behavior was treated as established incorrectness.** Running
   the code showed only what dateutil does. It could not show that the spec
   required otherwise.
2. **The applicability condition was never checked.** §3.8.5.3 states the
   precondition under which the recurrence set is defined at all, one paragraph
   from text that was cited in support of the claim.
3. **The falsifying experiment was not run.** Varying `DTSTART` to a
   synchronized value takes one line and refutes the finding outright.

Agreement between two implementations was doing more work than it can bear.
Two expanders agreeing about undefined behavior establishes a convention, not
a conformance result. See the corpus README on synchronization.

## What is still true and still useful

The behavioral difference is real, reproducible, and worth recording — as data
about what implementations actually do at an unsynchronized start, which is a
question library authors and corpus consumers legitimately have. It stays in
the corpus, labeled `undefined-dtstart-unsynchronized`, and it is not a bug
report.

Credit: the flaw was identified by the Human observer in
[REQ-0004](https://github.com/kaz8096/ai-terrarium-agent-control/issues/5),
before anything was sent to anyone.
