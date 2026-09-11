# 025 — §3.3.10 contradicts itself about nonexistent local times, and a Verified errata decides it

**Status:** Documentary, and decisive. **Date:** 2026-09-11.
**Not a defect report against any implementation.** It corrects an overstatement
in [finding 006](006-dst-gap-and-repeat-instances.md) and supplies the authority
that 006's conclusion actually rests on.
**Sources:** RFC 5545 §3.3.10 (two passages); RFC 5545 errata ID 4271.

## What 006 claimed, and why the claim was under-justified

Finding 006 quoted one sentence of §3.3.10 —

> If the computed local start time of a recurrence instance does not exist, or
> occurs more than once, for the specified time zone, the time of the
> recurrence instance is interpreted in the same manner as an explicit
> DATE-TIME value describing that date and time, as specified in Section 3.3.5.

— and said it "settles the question completely": a generated instance is
localized by exactly the same two rules as a literal `DATE-TIME` value, so an
instance falling in a spring-forward gap takes the pre-gap offset and therefore
moves *forward* through the gap.

The conclusion is right. The justification was not complete, because **§3.3.10
also contains a sentence that says the opposite**, 110 lines earlier in the same
section:

> Recurrence rules may generate recurrence instances with an invalid date (e.g.,
> February 30) or nonexistent local time (e.g., 1:30 AM on a day where the local
> time is moved forward by an hour at 1:00 AM). Such recurrence instances MUST be
> ignored and MUST NOT be counted as part of the recurrence set.

One passage says a nonexistent local time is shifted forward and kept. The other
says it is dropped and not counted. Both are in §3.3.10 of the published RFC.
006 read the second-best sentence for its purpose and never noticed the first,
so what it presented as a quoted rule was in fact a choice between two quoted
rules — the same error 006 congratulated itself for avoiding.

## The errata settles it, in the direction 006 guessed

**RFC 5545 errata ID 4271**, section 3.3.10, type Technical, status **Verified**.
Submitted 2015-02-12 by Neil Jenkins, verified by Barry Leiba, last updated
2019-09-10. It replaces the "MUST be ignored" paragraph with two paragraphs:

> Recurrence rules may generate recurrence instances with an invalid date (e.g.,
> February 30). Such recurrence instances MUST be ignored and MUST NOT be
> counted as part of the recurrence set.
>
> Recurrence rules may generate recurrence instances with a nonexistent local
> time ((e.g., 1:30 AM on a day where the local time is moved forward by an hour
> at 1:00 AM). Such recurrence instances are handled as specified in Section
> 3.3.5.

The submitter's stated reason is the contradiction above, and the note adds that
shifting forward "is the behaviour implemented by major clients such as
Calendar.app and Google Calendar". (The doubled `((` is in the errata text as
published.)

So the correct reading of finding 006 is: its conclusion is what the RFC means,
but the RFC as printed does not say so unambiguously, and the thing that makes
the reading safe is a Verified technical errata rather than the body text.

## The consequence that is easy to miss

Before the errata, one sentence covered two situations and gave them one fate.
After it, **the two halves of that sentence have opposite fates**, and the split
is observable in `COUNT`:

| generated instance | fate | counts toward `COUNT`? |
|---|---|---|
| invalid date, e.g. 30 February | ignored | **no** |
| nonexistent local time, e.g. 02:30 inside a spring-forward gap | shifted per §3.3.5 | **yes** |

An implementation that treats the two alike — the natural reading of the
uncorrected paragraph, since they were one sentence — gets `COUNT` wrong by one
for any rule that crosses a spring-forward transition at a gap local time. That
is a silent, once-a-year, off-by-one in the *length* of the recurrence set, not
merely in one instance's time.

## What I checked and what came back empty

* Both passages are in the published RFC: `rfc5545.txt` lines 2382–2386 and
  2492–2496 — 110 lines apart, in one section.
* Errata 4271's status is **Verified**, not Reported or Held for Document Update,
  so it is the RFC Editor's adjudicated correction and not a pending suggestion.
  Of 39 recorded RFC 5545 errata, 13 are Verified/Technical; this is one.
* **There is no RFC 5545 revision in progress to check the errata against.** I
  expected to be able to say whether a successor draft had folded 4271 in, and
  there is no successor: the IETF datatracker shows no active iCalendar core
  revision, and the `draft-ietf-calsify-rfc2445bis-10` text held locally is the
  April 2009 *predecessor* that became RFC 5545, six years older than the
  errata. The claim I was about to make would have been backwards.
* This corpus cannot test the behaviour. Every adapter in `conformance/adapters/`
  is floating-time; none accepts a `TZID`. The empirical work on this question is
  `tests/test_dst_recurrence.py` (finding 006), which tests `rruleref` and
  `python-dateutil` only, and both implement the post-errata reading.

## Why this was worth a finding rather than an edit to 006

006's error is not in its test table or its result — 30/30 still pass and the
expected column is still right. It is in the epistemic claim: "the *rule* is
quoted, not argued." That claim needs withdrawing on its own terms, because the
lesson 006 drew from it is one I keep relying on. **Quoting one sentence from a
section is not reading the section.** Errata 4271 existed for eleven years before
I looked for it, and the check that found it was a single grep of a dataset I
already had on disk.
