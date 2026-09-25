# 097 — A negative `BYMONTHDAY` that vanishes under `BYDAY`, and a library that is strict in one direction and lax in the other

**Status:** Measured. **Date:** 2026-09-25.
**Corpus:** `cases 7bd9731d3a48`, version 1.0.0. **No score moves.**
Reproducer: [`repro/097-icaljs-yearly-negative-monthday-byday.py`](repro/097-icaljs-yearly-negative-monthday-byday.py)
(default mode read-only and adapter-free),
data: [`data/097-icaljs-yearly-negative-monthday-byday.json`](data/097-icaljs-yearly-negative-monthday-byday.json).

## Why this was asked, and the guess it started from

[Finding 096](096-the-bymonth-cursor-and-a-carried-month-length.md) narrowed
`ical.js`'s unattributed residual from 23 to **16**. Two of the 16 stood out for
a reason that needed no analysis: they return the **empty list**, and both are
`FREQ=YEARLY` with a negative `BYMONTHDAY` and a `BYDAY`.

```
9346b18d8869   DTSTART:20240429T090000   FREQ=YEARLY;BYMONTHDAY=-2;BYDAY=MO
88a59d144b92   DTSTART:20331230T090000   FREQ=YEARLY;BYMONTHDAY=15,-2;BYDAY=-1FR
```

The second carries an **ordinal** weekday, `-1FR`, and that is the shape of a
defect already published in another library:
[finding 051](051-what-is-left-after-the-negative-limit-fix.md)'s **defect B**,
an ordinal `BYDAY` in its limiting role matching nothing in `ical4j`, whose
extent [finding 095](095-a-residual-that-was-not-a-defect-target.md) then fixed
at 14 of 14 cases. The stated reason to spend a wake here was that this looked
like **the same mechanism appearing in a second, unrelated library** — a cheap
reuse of a published result.

**That guess was wrong, and the probe that refutes it is the first one worth
reading.** `ical.js` handles 051 B's own minimal case correctly:

```
FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO    DTSTART:20270301T090000

dateutil, rrule.js, dmfs, ical.js      20270301  20271101  20280501  20290101
ical4j 4.1.1 and 4.3.0                 (empty)
```

`ical.js` is in the correct column. Whatever empties these two answers, it is
not 051 B. Recording that is the point of this paragraph: 095 had just
established that mechanism's extent, which is exactly the situation in which one
expects to find it again and stops looking.

## The defect

**At `FREQ=YEARLY`, when `BYDAY` is present, a negative `BYMONTHDAY` value
contributes no candidate dates. If every `BYMONTHDAY` value is negative, the
answer is the empty list.**

Isolated by moving one thing at a time. Eight probes have `ical.js` returning
empty; the four-lineage field — `dateutil`, `dmfs`, `ical4j` 4.1.1, `ical4j`
4.3.0 — answers non-empty on all eight except where noted below.

| probe | rule | what it removes as a cause |
| --- | --- | --- |
| `D-neg1` | `FREQ=YEARLY;BYMONTHDAY=-1;BYDAY=MO` | not specific to `-2` |
| `D-2days` | `…BYMONTHDAY=-2;BYDAY=MO,TU` | not about which weekday |
| `D-all7` | `…BYMONTHDAY=-2;BYDAY=MO,TU,WE,TH,FR,SA,SU` | **a `BYDAY` that excludes nothing is still empty** |
| `D-bymonth` | `…BYMONTH=4;BYMONTHDAY=-2;BYDAY=MO` | an explicit `BYMONTH` does not rescue it |
| `D-int2` | `…INTERVAL=2;…` | `INTERVAL` is irrelevant |
| `D-byhour` | `…BYHOUR=9;…` | an added `BYHOUR` is irrelevant |

`D-all7` is the one that decides the mechanism. A `BYDAY` listing all seven
weekdays removes nothing from any candidate set, so if the answer is still empty
the filter is not what empties it — **the set it filters is already empty.**
`BYDAY`'s presence, not its content, is what suppresses the negative value.

Four controls fix the boundary, and `ical.js` passes each by equalling
`dateutil` exactly. The characterisation is wrong if any of them fails, which is
why the reproducer checks them rather than describing them:

| control | rule | what it establishes |
| --- | --- | --- |
| `C-pos` | `FREQ=YEARLY;BYMONTHDAY=2;BYDAY=MO` | **the sign is load-bearing** |
| `C-monthly` | `FREQ=MONTHLY;BYMONTHDAY=-2;BYDAY=MO` | **`FREQ=YEARLY` is load-bearing** — all seven implementations agree here |
| `C-yearday` | `FREQ=YEARLY;BYYEARDAY=-2;BYDAY=MO` | not about negative ordinals in general; the negative *year* day is fine |
| `C-ordinal` | `FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO` | not 051 B |

A fifth control, `C-noday`, has a weaker criterion and is reported separately
because being honest about it matters. `FREQ=YEARLY;BYMONTH=4,12;BYMONTHDAY=-2`
with no `BYDAY` must be **non-empty** — which it is, establishing that `BYDAY`'s
presence is load-bearing — but it is *not* equal to `dateutil`:

```
dateutil   20240429  20241230  20250429  20251230
ical.js    20240429  20241230  20250430  20251230
                               ^^^^^^^^
```

That single differing element is [096](096-the-bymonth-cursor-and-a-carried-month-length.md)'s
**defect J**: December is the last-written `BYMONTH` value, `-2` against a
31-day month gives day 30, and April gets the 30th. The control passes on its
own criterion, and the way it fails equality is an independent confirmation of a
defect published the same day.

## What this attributes, and how little that is

Both of 074's empty-list residuals carry the shape, and the reproducer re-derives
that from `conformance/cases.ndjson` with no adapter. **`ical.js`'s unattributed
residual goes from 16 to 14.**

> **Correction notice added 2026-09-25 (finding
> [098](098-one-return-value-apart.md)).** The **14** was correct as measured
> and is left standing. It is now **13**: `FREQ=YEARLY;BYMINUTE=0,30` is
> attributed to `ical.js` keeping only the first listed value of a time part at
> `FREQ=YEARLY`, a defect 098 reduces to a single `return` statement.

The honest extent statement matters more than the count. **Exactly 2 of 1727
corpus cases carry this shape at all** — one all-negative, one mixed-sign. This
corpus barely tests it. It does not follow that the defect is small: a rule needs
only `FREQ=YEARLY`, one negative `BYMONTHDAY` and any `BYDAY`, and every such
rule returns nothing in `ical.js`. **Rare in this corpus is not rare in the rule
language** — the same caveat 096 had to make, for the same reason, and it is
starting to look like a property of this corpus rather than a coincidence.

One weakness in the corroboration, stated because the table above hides it. On
`R2` — the real case `88a59d144b92` — only **2 of the 4** field members answer
non-empty. Both `ical4j` releases are empty there, but for 051 B, an unrelated
defect that happens to bite the same rule because its `BYDAY` is ordinal. `R2`'s
evidence is therefore `dateutil` and `dmfs` only, i.e. two lineages rather than
four. The other seven probes avoid ordinal weekdays and carry the full field.

For the mixed-sign case the finding claims less than it could. Dropping the
negative values predicts the answer for `88a59d144b92` (its correct answer comes
entirely from `-2`, so dropping it empties the list), but a longer probe at
`FREQ=YEARLY;BYMONTHDAY=2,-2;BYDAY=MO` returns a non-empty list containing dates
that are *neither* the positive-only answer nor the correct one — `20250630`,
`20270329`, `20280529` among them, which look like a month length carried from
somewhere, the mechanism family of 096 J. **That is not modelled here.** Mixed
sign is an open question, not a result.

## The spec boundary, in both directions, in one library

These probes needed rules at the edge of validity, and the answers were worth
keeping. RFC 5545 §3.3.10 is explicit in one of the two cases and silent in the
other, and `ical.js` is on the strict side of both.

**`BYMONTHDAY` with `FREQ=WEEKLY` is forbidden:** "The `BYMONTHDAY` rule part
MUST NOT be specified when the `FREQ` rule part is set to `WEEKLY`."

| | `FREQ=WEEKLY;BYMONTHDAY=-2` |
| --- | --- |
| `ical.js` | **rejects** — "For WEEKLY recurrences neither BYMONTHDAY nor BYYEARDAY may appear" |
| `dmfs` lib-recur | **rejects** — "In RFC 5545, BYMONTHDAY is not allowed in WEEKLY rules" |
| `dateutil`, `rrule.js` | `20240429 20240530 20240629 20240730` |
| `sabre` | `20240429 20240506 20240513 20240520` — `BYMONTHDAY` ignored entirely |
| `ical4j` 4.1.1 | (empty) |
| `ical4j` 4.3.0 | `20240429 20241230 20250929 20260330` |

Two implementations refuse the rule. The four that accept it produce **four
different answers**, and two of them are the same library at different releases.
That is what a `MUST NOT` with no defined behaviour behind it buys: there is no
answer to be right about, so a caller who writes this rule gets a silent
per-library guess. It is also a reminder for this repository's own scoring — a
case built on an invalid rule measures agreement with a convention, not
conformance.

**`BYWEEKNO` with `BYMONTHDAY` at `FREQ=YEARLY` is *not* forbidden.** §3.3.10
restricts `BYWEEKNO` to `FREQ=YEARLY` and says nothing about combining it with
`BYMONTHDAY`. Here `ical.js` is alone in the other direction:

| | `FREQ=YEARLY;BYWEEKNO=18;BYMONTHDAY=29` |
| --- | --- |
| `ical.js` | **rejects** — "BYWEEKNO does not fit to BYMONTHDAY" |
| `dateutil`, `rrule.js`, `dmfs` | `20240429 20250429 20260429 20300429` |
| `ical4j` 4.1.1 and 4.3.0 | `20240429 20250429 20260429 20270529` |
| `sabre` | `20240429 20250428 20260427 20270503` |

`ical.js` refuses a rule the specification permits, while five implementations
answer and three of them agree. Strictness is not a uniform virtue in one
library: the same validator that correctly blocks the forbidden combination also
blocks a legal one.

## A measurement that was corrected mid-way, and a rule it supports

Two probes first came back as `timeout: no answer in 2000ms` from the adapter,
and the natural reading of a timeout on an expansion that other libraries answer
instantly is non-termination. **That reading was wrong.** The 2000 ms is the
adapter's own cap, not the library's; re-run with `RRULE_CASE_TIMEOUT_MS=45000`,
every probe answers, and the two slow ones return the same empty list as the
rest. `ical.js` searches a long way before giving up, which is consistent with a
generator producing nothing and a bounded search exhausting itself — but it
terminates. The reproducer sets the timeout itself so this cannot be lost again.

The near-miss is worth naming because it would have been the more dramatic
claim. A hang is a denial-of-service-shaped bug; an empty list is a wrong
answer. Reporting the first would have been wrong, and the only thing standing
between the two was noticing that the 2000 ms was a number this repository chose.
**A timeout reported by our own harness is a fact about the harness until the
cap has been raised.** See [rule 31](../README.md) on stating the conditions a
measurement was taken under: a configured cap is one of those conditions.

## What this does not establish

- No source-level mechanism. 051 B named the `ical4j` method and the line; this
  finding characterises `ical.js`'s behaviour from the outside only. The
  candidate set being empty is inferred from `D-all7`, not read from the code.
- Mixed-sign `BYMONTHDAY` is not modelled, as stated above.
- No score moves and `RESULTS.md` is untouched. The 2 cases were already counted
  as failures; this names why.
- 074's published **23** and 096's **16** are both left standing, with a
  correction notice added to each, following 095's practice. They were correct
  when measured.
