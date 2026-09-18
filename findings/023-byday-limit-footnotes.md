# Finding 023 — the two footnotes under §3.3.10's table, as a shipped bug

**Status:** measurement, plus a change to the debugger. Nothing here is
reportable upstream, and the reason why is the interesting part.
**Date:** 2026-09-11

## The report

[`FossifyOrg/Calendar` issue 491](https://github.com/FossifyOrg/Calendar/issues/491),
opened 2025-02-25 and still open, is a user of a shipped Android calendar
describing this and nothing else:

> I have an event with following recurence rule:
> `RRULE:FREQ=MONTHLY;BYMONTHDAY=13;BYDAY=FR`
>
> **Expected behavior**: The event should recur only on every friday the 13th.
>
> **Actual behavior**: The event recurs every month on a friday, for example
> 14. mar, 11. apr and 9. may.

The user is right. RFC 5545 §3.3.10's table gives `BYDAY` as an **expanding**
part, with two footnotes:

> Note 1: Limit if BYMONTHDAY is present; otherwise, special expand for MONTHLY.
>
> Note 2: Limit if BYYEARDAY or BYMONTHDAY is present; otherwise, ...

So `BYMONTHDAY=13` together with `BYDAY=FR` is an **intersection** — Friday the
13th — and reading it as a union turns a rule that fires roughly twice a year
into one that fires fifty times. Nothing on screen says which reading you got.

## All six implementations get it right

The rule and three variants, through every adapter in
[`conformance/adapters/`](../conformance/adapters/):

```
FREQ=MONTHLY;BYMONTHDAY=13;BYDAY=FR   DTSTART:20250613T090000
  dateutil, rrule.js, ical4j, lib-recur, libical, this corpus's expander
    2025-06-13, 2026-02-13, 2026-03-13, 2026-11-13, 2027-08-13, 2028-10-13
```

Six for six, on the `MONTHLY` shape and on `BYMONTHDAY=13,14;BYDAY=FR,SA`. The
footnotes are not a place the libraries fall over.

> **Narrowed, 2026-09-18.** That sentence claims more than the measurement
> earns. Every rule tested here carries a *plain* weekday. Put an ordinal on the
> weekday — `FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO` — and `ical4j` returns an
> empty list while the other lineages agree on an answer, because its limit
> filter compares the whole `1MO` token against an offset-0 `MO`. So the
> footnotes *are* a place one library falls over; this finding could not see it
> because it never wrote an ordinal. See
> [finding 051](051-what-is-left-after-the-negative-limit-fix.md).

**So there is nothing to report upstream, and the failure is somewhere else.**
Fossify's calendar does not use any of these; Android calendar code
conventionally carries its own expander. That is where this bug lives, and it
is the general shape: the footnotes are missed by people writing an expander
from the table, not by the libraries that already did.

Under rule 0b that ends the upstream question. It does not end the useful one.

## What changed instead

`web/src/describe.js` now says the intersection out loud whenever the footnotes
apply. Before, the sentence was a comma list —

> Every month, but only on the 13th, on Friday.

— which is exactly as readable as a union, to anyone who has not memorised the
table. It now adds:

> BYDAY narrows here rather than adding. With BYMONTHDAY present, RFC 5545
> section 3.3.10 makes BYDAY limit rather than expand: it contributes no dates
> of its own, and only removes ones BYMONTHDAY already chose, so a date has to
> satisfy both.

With `BYSETPOS` the wording differs, because there "only removes" would be
false of the output: `BYSETPOS` selects from whatever is left, so deleting
`BYDAY` moves which member is picked rather than only removing members. Six
corpus rules demonstrated this while the property below was being written, and
the note was wrong until they did. The claim that survives either way is about
the candidate set, so the note says which one it is making.

## The property

[`web/test/byday-limit.mjs`](../web/test/byday-limit.mjs), over all 1721 corpus
cases, run by `tests/test_describe.py`:

* **Condition** — the note appears on exactly the rules the two footnotes name,
  restated from the RFC rather than from the code. 75 cases.
* **Truth** — where it appears, the expansion is a subset of the same rule with
  `BYDAY` deleted, inside the window both expansions cover. `BYSETPOS` is
  deleted from both sides first, so the comparison is of candidate sets.

Both hold on all 75. **Seen to be capable of failing:** of the 733 corpus rules
where `BYDAY` expands, 439 do add dates and would fail the subset check.

The window is not decoration. Deleting `BYDAY` makes a rule fire more often, so
its Nth occurrence is earlier; comparing past that point reports dates as
"added by BYDAY" when they are merely past where the other list stopped. The
first version of the check did exactly that and reported six false violations.

## A correction this turned up

Probing `FREQ=YEARLY;BYMONTHDAY=13;BYDAY=FR` showed libical siding with ical4j
and lib-recur, which sent me back to the debugger's `yearly-expand-vs-inherit`
diagnostic. It was telling every reader:

> ical4j 4.1.1 and dmfs lib-recur 0.17.1 — two implementations that share no
> code — both produce the right-hand answer instead.

**Three, not two.** [Finding 017](017-libical-third-lineage.md) counted three
lineages on 2026-09-08 — 41 `BYMONTHDAY` cases where libical, ical4j and
lib-recur agree against the corpus — and the diagnostic text, written before
libical was adapted, was never revisited. Checking the `BYWEEKNO` branch too:
of 42 corpus cases with `FREQ=YEARLY` and `BYWEEKNO` and no `BYDAY`, 15 show
the same three-way agreement against the corpus, with `python-dateutil` on the
corpus side in all 15.

The undercount mattered because weight of evidence is the entire point of that
sentence. It now names all three, says that dateutil and rrule.js are one
lineage rather than two votes, and cites finding 017.

[`README.md`](../README.md)'s honest-limits section carried a stale claim in
the same direction — "only two implementations in the corpus", written before
four were being scored — and has been corrected.
