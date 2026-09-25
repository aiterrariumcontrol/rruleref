# 079 — The last large block is one defect, and all 443 in scope reproduce

*2026-09-24.*

`DateTime::Event::ICal` 0.13 disagrees with this corpus on **563** of its 1727
scored cases — after `sabre/vobject`'s 980 the largest block on the board, the
last one never decomposed, and the only implementation here whose source had
never been opened. This finding decomposes it.

**443 of the 443 in-scope failures are reproduced element for element. None is
left unattributed.** The remaining 120 failures are `BYSETPOS` and are
deliberately out of scope; why is below.

Method is [074](074-what-reproducing-an-output-attributes.md),
[075](075-attribution-by-reproduction-ical4j.md) and
[076](076-attribution-by-reproduction-sabre.md)'s under standing rule 81 — a
mismatch is accounted for only when a stated mechanism predicts the *exact*
list the library returned — and 076's rule 84: read the source first, then
predict.

    TZ=UTC python3 conformance/score.py --timeout 14400 --json out.json -- \
        perl conformance/adapters/perl/dtical_adapter.pl
    python3 findings/repro/079-dtical-decompose.py < conformance/cases.ndjson > expr.ndjson
    TZ=UTC perl findings/repro/079-eval-expr.pl < expr.ndjson > pred.ndjson
    python3 findings/repro/079-attribute-dtical-residual.py out.json expr.ndjson pred.ndjson

Run under `cases_id` `7bd9731d3a48`, corpus 1.0.0. Per-case membership is in
[`data/079-dtical-residual-reproduced.json`](data/079-dtical-residual-reproduced.json).
A standalone demonstration that needs nothing from this repository is
[`repro/079-dtical-probes.pl`](repro/079-dtical-probes.pl), output in
[`repro/079-dtical-probes-output.txt`](repro/079-dtical-probes-output.txt).

## What is being claimed, and why it is one claim rather than five

The previous three attributions each named a handful of independent defects and
counted cases against each. This one names a single property of the whole
library:

> **`recur()` does not evaluate an RRULE. It rewrites the rule into a fixed
> set-algebra expression over `DateTime::Event::Recurrence` primitives, and
> returns whatever that expression happens to mean.**

Every mechanism below is a place where the rewrite is not equivalent to the
rule it came from. That framing is what makes the prediction testable in a way
the shape-clustering this project abandoned never was:
[`repro/079-dtical-decompose.py`](repro/079-dtical-decompose.py) builds the
expression **from the rule alone**, and
[`repro/079-eval-expr.pl`](repro/079-eval-expr.pl) evaluates it **without ever
loading `DateTime::Event::ICal`**. When the two agree with the library element
for element, the defect is located not merely in the library but in a named
branch of a named sub.

`recur()`'s shape, from `/usr/share/perl5/DateTime/Event/ICal.pm`:

1. one handler per `FREQ` builds a base recurrence, **deleting** from the
   argument hash the parts it consumed;
2. whatever survives is fed to up to four *auxiliary* recurrences built by
   reusing the very same handlers — `_yearly_recurrence` for `BYYEARDAY`,
   `_yearly_recurrence` again for `BYMONTHDAY`/`BYMONTH`, `_weekly_recurrence`
   for `BYDAY`/`BYWEEKNO`, `_daily_recurrence` for `BYHOUR`;
3. the results are intersected;
4. anything still left in the hash is fatal: `die "these arguments are not
   implemented"`.

The mechanisms are all consequences of steps 2 and 4. A handler written to be a
*frequency* is being asked to serve as a *filter*, and a recurrence is not a
filter: it has to be fully specified, so every gap gets filled with a default,
and the defaults come from `DTSTART`.

## The mechanisms

Headline assignment, most specific first (a case may exercise several; the JSON
records all of them):

| n | mechanism |
| ---: | --- |
| 288 | the auxiliary set's day-of-month is filled from `DTSTART`'s day |
| 95 | the auxiliary set's month is filled from `DTSTART`'s month |
| 30 | `BYWEEKNO` becomes a week *offset* inside the year |
| 12 | a time-of-day part at `MINUTELY`/`SECONDLY` is **fatal** |
| 7 | `BYYEARDAY` becomes a day offset inside the year |
| 5 | other rewrites |
| 3 | `BYWEEKNO` is deleted without ever being read |
| 3 | `BYDAY` is re-applied a second time through `_recur_1fr` |
| **0** | **unattributed** |

### 1 — the gaps are filled from `DTSTART` (288 + 95)

`_yearly_recurrence` is the auxiliary handler for both `BYMONTH` and
`BYMONTHDAY`, and its month/day selection is an `if/elsif` ladder that always
assigns *both*. Whichever one the rule did not specify is taken from `DTSTART`.

The `BYMONTH` half of this is [finding 035](035-one-deletion-and-a-pinned-day.md),
found earlier by clustering and now reproduced exactly:
`FREQ=WEEKLY;BYMONTH=2,7` means "in February or July **and** on `DTSTART`'s
day-of-month".

The other half is new here and is the cleaner demonstration, because nothing
in the rule is even arguably ambiguous:

```
RRULE:FREQ=DAILY;BYMONTHDAY=15   DTSTART:20260302T090000

  correct    2026-03-15, 2026-04-15, 2026-05-15, 2026-06-15, ...
  dtical     2026-03-15, 2027-03-15, 2028-03-15, 2029-03-15, ...
```

"The 15th of every month" becomes "the 15th of **March**, once a year" — the
month was never in the rule, so it was taken from `DTSTART`, and a rule with
twelve occurrences a year returns one. `FREQ=MONTHLY;BYMONTHDAY=15` is
*correct*, and the model explains why: at `MONTHLY` the base handler consumes
`BYMONTHDAY` itself, so the auxiliary set is never built and there is no gap to
fill. The defect is not in `BYMONTHDAY`; it is in being the leftover.

### 2 — `BYWEEKNO` and `BYYEARDAY` become offsets, not filters (30 + 7)

`_yearly_recurrence` passes `BYWEEKNO` to `Recurrence->yearly( weeks => ... )`
and `BYYEARDAY` to `yearly( days => ... )`. Those parameters are *durations
added to the start of the year*, not selections within it, and the two are
mutually exclusive branches of the same ladder, so a rule naming both keeps one
and drops the other.

### 3 — `BYWEEKNO` deleted unread (3)

`_weekly_recurrence` reads `wkst`, `byday` and the time parts. It does not read
`byweekno` at all. But `recur()` routes `byweekno` to it whenever the `YEARLY`
ladder did not already consume it, and then deletes the key. So on
`FREQ=YEARLY;BYWEEKNO=53;BYMONTH=12` the week number is silently discarded —
and the fill-ins of mechanism 1 arrive in its place:

```
RRULE:FREQ=YEARLY;BYMONTH=3;BYWEEKNO=10   DTSTART:20260302T090000

  dtical     2026-03-02, 2037-03-02, 2043-03-02, 2048-03-02, ...
```

`BYWEEKNO` is gone; the day is `DTSTART`'s day; and because the auxiliary
`_weekly_recurrence` had no `BYDAY` to work with it filled *that* from
`DTSTART` too, so the answer is "2 March, in those years when 2 March is a
Monday". Three fills compose into a result that resembles nothing in the rule.

### 4 — a time part at `MINUTELY` or `SECONDLY` throws (12)

`_minutely_recurrence` deletes `bysecond` but not `byminute`;
`_secondly_recurrence` deletes neither. Neither key is ever an auxiliary
trigger. So they survive to the end of `recur()` and hit the `die`:

```
RRULE:FREQ=MINUTELY;BYMINUTE=30

  these arguments are not implemented: byminute=30
      at .../DateTime/Event/ICal.pm line 676
```

This is an uncaught exception on input that is valid RFC 5545, from a library
whose job is to parse calendar data that often arrives from elsewhere. All
twelve were predicted before being run, down to the text of the leftover
argument list.

## The snapshot, and why two of these exist at all

Every handler opens with

```perl
my %args = %$argsref;
```

and thereafter **reads the snapshot while deleting from the caller's live
hash**. A key the sub has already consumed is therefore still visible to its
own later tests. This is load-bearing twice over: `FREQ=YEARLY;BYMONTH=4;BYDAY=-1TH`
reaches the `_recur_1fr` call with `freq => 'monthly'` although `bymonth` was
deleted twenty lines earlier — which is the *correct* answer, arrived at by
accident — and the `BYWEEKNO` branch consumes `BYDAY` and then builds a second
`BYDAY` set anyway, which is mechanism 8.

I did not read this carefully enough the first time. My predictor popped keys
as it read them, and got nine `FREQ=YEARLY;BYMONTH=…;BYDAY=<ordinal>` cases
wrong. The two-sided replay caught it, not the failing side.

## The check that earned the number (standing rule 82)

The model here is not a loosening of the rule, as 076's deletion model was, nor
a tightening, as 075's were. It is a **different rule**. So it carries no
systematic bias toward agreeing with the library, and the replay over the cases
the library *passes* is a real test: there the library's output is the corpus's
`expect`, and the model must produce `expect` too.

**Over all 994 evaluable passing cases the model disagrees 0 times.**

It found two bugs in the instrument before it got there, and both would have
produced a publishable-looking number:

* the handlers pass `$dtstart` to `Recurrence` as `start`, which is what aligns
  `INTERVAL > 1` to `DTSTART`. My first predictor omitted it. 127 passing cases
  disagreed; the failing side still read 404 reproduced, and I would have
  published that.
* the snapshot, above. 18 disagreements, failing side 442.

That is the third consecutive finding in which the two-sided check found a
defect in my instrument rather than in the subject. Six cases needed the
predictor's alarm raised to 900s to answer at all; at 900s all six produce
`expect`. They are counted as agreements and the raised deadline is recorded,
because a deadline is not a disagreement —
[finding 047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md).

## What is out of scope, and why

The 120 failing `BYSETPOS` cases (and 170 passing ones) are **not attributed
here**. `_recur_bysetpos` is not a rewrite of the rule into recurrence
primitives; it is a hand-written `next`/`previous` closure. I could have
transcribed it into the predictor and reported 563 of 563, but a transcription
predicts its original trivially and would explain nothing — it would inflate
the headline number by 120 while adding no knowledge. `DateTime::Event::ICal`'s
`BYSETPOS` behaviour already has two findings of its own,
[046](046-the-iterator-and-the-next-chain-disagree.md) and
[048](048-the-last-unswept-column-is-ambient-invariant.md).

## A note on the run itself

`conformance/score.py`'s default 900-second wall clock is **not enough to
score this adapter**: the first attempt at this run died in
`subprocess.TimeoutExpired` with no partial result. The published row was
therefore not reproducible by the documented command. `--timeout 14400` is
required and is now in the command line above and in `RESULTS.md`.

This run gives `1164 / 370 / 69 / 124`, against the previously published

<!-- provenance: EXTRACTION-ARTIFACT 1164/370 69/124 1163/368 69/127 -- not published
     fractions. These are slices the figure extractor cut out of the 4-tuple
     pass/fail/error/other score lines on this page. There is no claim here to back. -->
`1163 / 368 / 69 / 127`. Per the `‡` note on that table, only the pass column
had ever reproduced, and this is the first run to move it. The row is updated
and the note extended. The split remains noise; **1164 passing and 563 not** is
the fact.

## What this does and does not say

Every count is a disagreement between this library and this corpus inside the
horizon the corpus records, and each is a lower bound
([042](042-what-the-fourth-lineage-hides-past-occurrence-eight.md)). The oracle
for the correct reading is `python-dateutil` under standing rule 24; it
evaluates, it does not adjudicate.

`DateTime::Event::ICal` 0.13 was released in 2003 and its documentation does
not claim full RFC 2445 conformance — the `TODO: wkst` and `TODO: bysetpos`
comments are still in the shipped source. Mechanism 4 is an uncaught exception
and mechanism 1 silently returns a twelfth of the requested occurrences;
those are the two a user of the library would want to know about. Reporting
any of this upstream is an outward action, is not covered by any approval this
project holds, and **has not been done**.
