# 021 — The BYSETPOS first-interval question is answered in RFC 5545, by a sentence with a missing full stop

*2026-09-08.*

**Status:** Resolves the open interpretive question in finding 004 and closes the
hole in finding 020. Documentary; no implementation was run for this note.

## The question this closes

Findings 004, 018 and 020 all turn on one unresolved point. When `DTSTART` falls
part-way into the first `FREQ` interval and `BYSETPOS` is present, is the set
that `BYSETPOS` indexes

- **(A) whole-period:** every candidate in the whole interval, with the
  `DTSTART` lower bound applied *after* `BYSETPOS` selects; or
- **(B) first-period cut:** only the candidates at or after `DTSTART`, with the
  bound applied *before* `BYSETPOS` selects?

I had been treating this as genuinely open, and every attempt to settle it went
through implementations — which, by the lesson of findings 018 and 019, is
evidence about implementations and not about the specification. It is not open.
RFC 5545 answers it in §3.3.10:

> The BYSETPOS rule part specifies a COMMA-separated list of values that
> corresponds to the nth occurrence within the set of recurrence instances
> specified by the rule.  BYSETPOS operates on a set of recurrence instances in
> one interval of the recurrence rule.  For example, in a WEEKLY rule, the
> interval would be one week **A set of recurrence instances starts at the
> beginning of the interval defined by the FREQ rule part.**

The emphasised sentence is reading **(A)**. The set `BYSETPOS` indexes begins at
the start of the `FREQ` interval, not at `DTSTART`; so the `DTSTART` bound of
§3.8.5.3 applies to the result of the selection, not to its inputs.

Note the text as published: `one week A set`. There is no full stop between the
two sentences.

## That this was deliberate, not an accident of drafting

The sentence is **absent from RFC 2445** — `grep` for "beginning of the
interval" and for "operates on" in RFC 2445 returns nothing. It entered during
the calsify working group's revision, and the drafts say why. Fetching
`draft-ietf-calsify-rfc2445bis-00` through `-10`, the phrase first appears in
**-08 (2008-02-06)**, and that draft's change log records it as a numbered
working-group issue:

> B.1. Changes in -08
>   b.  Issue 81: BYSETPOS: Clarify that "a set" starts at the beginning
>       of the interval defined by the FREQ rule part.

The same issue had already been touched once, one draft earlier:

> B.2. Changes in -07
>   n.  Issue 81: Clarified the meaning of "the set of events specified
>       by the rule" in the description of the BYSETPOS rule part.

So the working group looked at this exact question twice, and on the second pass
added a sentence whose entire content is the answer to it. The `-07` text was a
clean enumeration — *"For a WEEKLY rule, the interval is one week, for a MONTHLY
rule, one month, and for a YEARLY rule, one year."* The `-08` edit replaced that
with *"For example, in a WEEKLY rule, the interval would be one week"* and
appended the new sentence. **The missing full stop was introduced by that edit**,
survived `-09` and `-10`, and was published in RFC 5545 in September 2009.

## Why the damaged punctuation is not a triviality

Run together, the clause reads as a continuation of the WEEKLY example — as if
the whole thing were an aside about what "interval" means for one `FREQ` value.
Separated, the second sentence is a general statement about where the candidate
set begins for every `FREQ` value, which is the only sentence in §3.3.10 that
decides (A) against (B). The sentence that resolves the ambiguity is the one the
typography hides. I read this section repeatedly across several days of work on
findings 004, 018 and 020 and did not see it, which is the observation that
prompted this note.

No RFC 5545 erratum touches this text (checked against a full errata dump: 39
errata against RFC 5545, none matching `BYSETPOS`, `one week`, or `beginning of
the interval`), and I found no prior report of the missing full stop.

## What this changes here

- **Finding 004.** The `dateutil` behaviour reported there — `BYSETPOS` applied
  to a first period truncated at `DTSTART` — is reading (B), and (B) is not what
  RFC 5545 says. The mechanism is unchanged; its status changes from "one of two
  defensible readings" to non-conformance with an explicit sentence.
- **Finding 020 / standing rule 3b.** The hole was that whether `DTSTART` is
  synchronized could depend on the reading when `BYSETPOS` is present, so the
  synchronization audit could not be applied reading-neutrally. Under (A) the
  reading is fixed, so the dependence disappears: `naive.expand`'s whole-period
  default was already the specified behaviour. The audit is sound as written.
- **Not changed:** finding 018's demonstration that corpus outcomes can be
  reading-dependent stands as a fact about the corpus. What it no longer implies
  is that the reading is a free parameter.

## Limits

This is a documentary argument and rests on the text and the draft history, both
quoted above and reproducible from public sources. I have not found working-group
list traffic for Issue 81 itself; the calsify archive's search endpoint returns
403 to non-browser clients, so "the WG discussed X" is not a claim I am making —
only that the change log attributes the edit to a numbered issue, twice.

The missing full stop is a candidate for an editorial erratum. I am not
proposing one now: REQ-0009 is outstanding, and one upstream item at a time.
