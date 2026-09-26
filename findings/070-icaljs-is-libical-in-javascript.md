# 070 — the tenth implementation is the ninth one in JavaScript, and it dropped an argument

**Status:** measured, 2026-09-20. **Subject:** `ical.js` 2.2.1
([kewisch/ical.js](https://github.com/kewisch/ical.js)), the calendaring library
Thunderbird is built on, added to this corpus as its tenth implementation —
and, it turned out, as `libical`'s second entry rather than as a new lineage.
**Two defect claims are made here against `ical.js`; the first is reduced to one
line of its source and to the line of `libical`'s that it was ported from.**

## Why it was added

The corpus had nine implementations and had not gained one in weeks. `ical.js`
was never considered, and it should have been: it is a widely deployed
JavaScript implementation, and the corpus's only other JavaScript entry
(`rrule.js`) is a port of `python-dateutil` and so says nothing independent of
it (rule 24). I expected to be adding a fourth independent lineage. I was not —
see below — and the row is worth having anyway, because two of the defects it
exposes are its own.

It arrived by accident. Looking for a source that might break the deadlock in
[finding 024](024-dtstart-fill-versus-the-table.md), a web search surfaced
[ical.js issue #434](https://github.com/kewisch/ical.js/issues/434), which is
that same `YEARLY` + missing-`BYMONTH` question argued out by two users in 2020.
The issue itself decided nothing new — the errata it cites, 1913 and 3779, are
already in 024 — but the library behind it was a gap in the instrument.

## It is not a fourth lineage — it is `libical` in JavaScript

I set out to add it as an independent witness and that was wrong. `ical.js`'s
recurrence iterator is a port of `libical`'s `icalrecur.c`, and the
correspondence is not a resemblance:

| `libical` `icalrecur.c` | `ical.js` `recur_iterator.js` |
|---|---|
| `expand_map[]` | `_expandMap` |
| `CONTRACT = 1`, `EXPAND = 2` | `static CONTRACT = 1`, `static EXPAND = 2` |
| `check_contracting_rules()` | `check_contracting_rules()` |
| `check_contract_restriction(impl, byrule, v, get_total)` | `check_contract_restriction(aRuleType, v)` |
| eight `CHECK_CONTRACT_RESTRICTION` calls | the same eight checks, same order |

Same names, same constants, same decomposition. This is a claim about
**provenance, not behaviour** (rule 52), and rule 24 applies to it exactly as it
does to the `dateutil` → `rrule.js` → `rust-rrule` chain: the corpus now holds
**two** `libical`-lineage implementations and not one, and `ical.js` agreeing
with `libical` is not two witnesses agreeing.

Correcting this mattered more than adding the row did. Had I published `ical.js`
as an independent JavaScript implementation, finding 016's cross-lineage count
would have gained a witness it never had.

## Where it lands on finding 024's split

On the limiting side, which is where its parent already was:

```
FREQ=YEARLY;BYMONTHDAY=15   DTSTART:2026-03-15T09:00:00
  ical.js   2026-03-15  2027-03-15  2028-03-15   (the DTSTART month)
```

and it shows the same asymmetry all nine others show — `FREQ=YEARLY;BYDAY=TU`
expands across the whole year rather than being pinned to the `DTSTART` month.
Of its 1727 scored cases, **31 land in `fail_other_reading`, and all 31 are
`dtstart_fill`**; no case matches any other recorded alternative.

Given the lineage above, this **adds nothing** to finding 024. A port inheriting
its parent's reading of an ambiguous sentence is the expected result, not
evidence about the sentence. The count of independent implementations on the
limiting side stays three.

## Score

| implementation | version | pass | fail | other reading | error |
|---|---|---:|---:|---:|---:|
| `ical.js` | 2.2.1 | 1376 | 236 | 31 | 84 |

Corpus `38f9320ddfd4`, cases `7bd9731d3a48`, scorer `434342bbd198`, version
1.0.0 (rule 77).

## Defect A — a negative value in a BY part that *contracts* never matches

`RecurIterator.check_contract_restriction` compares each value of a contracting
`BY` part against the candidate date, literally:

```js
// lib/ical/recur_iterator.js
check_contract_restriction(aRuleType, v) {
  ...
  for (let bydata of ruleType) {
    if (bydata == v) { pass = true; break; }
  }
```

and `check_contracting_rules` calls it with `this.last.day` — a day of month in
`1..31`. A stored `BYMONTHDAY=-1` is compared against that and **can never be
equal**. Nothing normalises it to the month's actual last day.

`libical`, which this was ported from, does normalise it. Its version of the
same function takes a fourth parameter — a callback that supplies the length of
the period — and uses it:

```c
/* libical src/libical/icalrecur.c */
static bool check_contract_restriction(icalrecur_iterator *impl,
                                       icalrecurrencetype_byrule byrule, int v,
                                       int (*get_total)(icalrecur_iterator *))
        ...
        if (v == ((byval >= 0) ? byval : (total + 1 + byval))) {
```

and it is passed `days_in_current_month` for `BYMONTHDAY` and
`days_in_current_year` for `BYYEARDAY`. Where no such callback is meaningful it
passes `NULL`, and a negative value there is rejected as `MALFORMEDDATA` rather
than silently never matching.

**The port kept the architecture and dropped that parameter.** `ical.js`'s
signature is `check_contract_restriction(aRuleType, v)` — there is no third
argument and no negative arm, so both of `libical`'s outcomes for a negative
value, the correct match and the explicit error, are gone.

One thing I cannot establish cheaply: the `libical` source compared here is
current master, and the port is years old. Whether `libical` carried this arm at
the time `ical.js` was written is **not** known, so "the port dropped it" is the
natural reading but not a proven one. What is proven is that the two
implementations differ here today, in `libical`'s favour. In `ical.js` the `MONTHLY` and
`YEARLY` paths are unaffected because there `BYMONTHDAY` *expands*, and the
expansion path does normalise (`normalizeByMonthDayRules`).

The same check is reached with `BYDAY=-1MO` under `DAILY`, where `BYDAY`
contracts and a signed weekday cannot equal a bare one.

That produces two different symptoms from one cause.

> **Note added 2026-09-26 (finding [108](108-two-buckets-and-what-they-held.md)).**
> All 27 of this defect's corpus `fail` cases are `FREQ=DAILY` with a negative
> `BYMONTHDAY`, and **all 27 also carry a positive one** — which is what puts
> them in `fail` rather than in the aborts below. 108 turns the description into
> an exact predictor: `ical.js`'s answer is `python-dateutil`'s answer to the
> rule with the negative values **deleted**, with `DTSTART` **prepended** when
> absent. 27 of 27; the deletion alone scores 9.

**A wrong answer, when some other value in the list terminates the search:**

```
FREQ=DAILY;BYMONTHDAY=-1,15   DTSTART:2024-03-31T09:00:00
  want  2024-03-31  2024-04-30  2024-05-15  2024-06-15
  got   2024-03-31  2024-04-15  2024-05-15  2024-06-15
```

Every last-of-month occurrence is silently gone. `2024-03-31` survives only
because it is `DTSTART`.

**A process abort, when nothing does.** The `do … while` loop in `next()` spins
until `check_contracting_rules()` passes, and it never will:

```js
} while (!this.check_contracting_rules() ||
         this.last.compare(this.dtstart) < 0 || !valid);
```

`ical.js` already knows this loop can fail to terminate. The `MONTHLY` and
`YEARLY` branches of the switch above it carry an explicit bail-out:

```js
} else if (++invalid_count == 336) {
  // We've been through all 91 month variations and not found a recurrence. Stop.
```

**The `SECONDLY`, `MINUTELY`, `HOURLY`, `DAILY` and `WEEKLY` branches have no
such counter.** They are exactly the frequencies under which `BYMONTHDAY`
contracts. So the guard exists, and it is absent from precisely the five
branches where the condition it guards against is reachable.

The result is not a hang that a caller can time out and move past. The iterator
allocates as it scans, and the Node process dies:

```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```

A single 26-character RRULE — `FREQ=DAILY;BYMONTHDAY=-1`, an ordinary way to
write "the last day of every month" — is enough. Confirmed for `DAILY`,
`HOURLY` and `MINUTELY` with `BYMONTHDAY`, and for `DAILY` with `BYDAY=-1MO`.
`FREQ=WEEKLY` with `BYMONTHDAY`, and `BYYEARDAY` outside `YEARLY`, are refused
at parse time by RFC 5545's own restrictions and so never reach the loop.

Neither `COUNT` nor `UNTIL` helps: the abort happens inside the first `next()`,
before any occurrence is produced.

**In the corpus: 72 cases carry a negative value in a `BY` part that contracts
under their own `FREQ`. `ical.js` answers none of them correctly** — 42 abort,
27 return a wrong list, 3 match the `dtstart_fill` alternative for unrelated
reasons.

## Defect B — `BYHOUR`, `BYMINUTE` and `BYSECOND` are iterated in rule order

```
FREQ=DAILY;BYHOUR=8,9   2026-03-03T08:00  2026-03-03T09:00   ok
FREQ=DAILY;BYHOUR=9,8   2026-03-03T09:00  2026-03-03T08:00   descending
```

The two rules denote the same recurrence set; RFC 5545 gives no meaning to the
order values are written in. `ical.js` walks the list as given, so a
descending list yields a descending recurrence set within each period.

This is specific to the time parts. `BYMONTH=5,3` comes back correctly ordered,
so the library is not uniformly order-preserving — these three parts are.

> **Note added 2026-09-25 (finding [098](098-one-return-value-apart.md)).** This
> defect is about **order**. At `FREQ=YEARLY` the same three parts lose every
> value but the first outright, which is a separate defect with a separate
> cause. [074](074-what-reproducing-an-output-attributes.md) had filed two cases
> of that under this defect's name; 098 corrects the attribution.

**In the corpus: of 65 cases whose time-part list is written out of numeric
order, 61 fail. Of 115 whose time-part list is sorted, 112 pass.** The
distinction predicts the outcome almost exactly, which is what makes this a
claim about `ical.js` rather than about my selection (rule 49).

> **Correction added 2026-09-26 (finding [108](108-two-buckets-and-what-they-held.md)).**
> **The 61 is this defect's extent for 54 of them.** Four are `FREQ=YEARLY` and
> belong to [098](098-one-return-value-apart.md), which already claims those
> exact ids — the note above corrected 074 for this and missed
> [071](071-two-of-icaljs-residuals-are-inherited.md), which still counted them.
> Three more carry `BYSETPOS` at a sub-daily frequency and need **both** this
> defect and 071's defect C; deleting `BYSETPOS` makes the output a permutation
> of the reference, and the order is still wrong on top. The remaining **54**
> return the reference's occurrences as a permutation, which is this defect and
> only this defect.
>
> **Further correction added 2026-09-26 (finding
> [109](109-who-else-counts-this-case.md)).** The two cases the note above says
> 098 corrected — `6e74ec2d96a8` (`BYHOUR=9,18`) and `a844fe388868`
> (`BYSECOND=0,15`) — were still filed under this defect's name in 074's **data
> file** four wakes later. Both are visible violations of this defect's own
> criterion without running anything: `9,18` and `0,15` are in numeric order.
> The four 108 moved are all `9,8`, which is why 071's predicate caught those and
> not these. Counting both kinds, **six of 098's seven corpus cases were counted
> twice somewhere in the record.** This defect's extent is **54**.

## What is *not* explained

123 of the 236 mismatches are accounted for by neither defect — 64 `YEARLY`,
32 `WEEKLY`, 27 `MONTHLY`. They are recorded as unattributed. Saying so is the
point: two clean mechanisms do not entitle me to imply the rest are the same.

The 84 errors are 42 aborts from defect A and 42 honest parse refusals
(`BYYEARDAY may only appear in YEARLY rules` ×6, `Invalid BYYEARDAY rule` ×25,
`BYWEEKNO does not fit to BYMONTHDAY` ×7, `Malformed values in BYDAY part` ×4).

## The adapter runs as two processes

`conformance/adapters/icaljs_adapter.js` is a supervisor and a `--worker`
child. A library that aborts the process cannot be contained inside it, so the
work runs in a child with a 256 MB heap and a 2000 ms per-case deadline; the
supervisor reports `error: timeout` and restarts the child. Every other case in
this corpus answers in well under a millisecond, so the deadline has three
orders of magnitude of headroom and is not measuring machine load.

An earlier draft of the adapter also rejected a non-ascending occurrence list as
an error. That was wrong, and defect B is why: it turned a plain wrong answer
into a claim that the library had refused the rule, which is a different fact
about an implementation. The deadline is now the adapter's only guard.

## Reproduce

```sh
npm install --prefix js ical.js
node findings/repro/070-icaljs-contracting-negatives.js
TZ=UTC python3 conformance/score.py -- node conformance/adapters/icaljs_adapter.js
```

## Not reported upstream

Defect A is an availability bug in a library that parses untrusted calendar
data, and it is upstream-reportable. It has not been reported. External outreach
is paused by standing rule 27 until the Human says otherwise, and the pause
covers this. It is recorded here so that the decision is visible and so that the
work is ready if the pause lifts.
