# 082 — The spec's own examples were never on the board

**Status:** the 39 worked examples of RFC 5545 §3.8.5.3 (42 `RRULE`s) measured
against thirteen builds for the first time. Two defect claims filed, against
`ical.js` and `sabre/vobject`. One exclusion rule in `PROTOCOL.md` corrected.
One unresolved tension inside §3.8.5.3 recorded, not resolved.
**Date:** 2026-09-24. **Tool:** `tools/audit_rfc_examples.py`.
**Data:** [`data/082-rfc-examples-audit.json`](data/082-rfc-examples-audit.json).

## The blind spot

[Finding 081](081-what-the-board-says-about-the-disputed-cases.md) established
standing rule 86: every part of the corpus gets measured against the board,
including the parts the board did not help produce. Applying it a second time
finds a worse case than the one that produced it.

`corpus/rfc5545-examples.json` holds the examples RFC 5545 prints for itself,
extracted by program from the hashed RFC text and never retyped. They are the
most authoritative cases about `RRULE` that exist — not two expanders agreeing,
not a judgement of mine, but the specification showing its own answer. Not one
of them had ever been shown to an implementation in this repository.

`conformance/build_cases.py` reads `corroborated.json` only, so they were out of
the corpus selection to begin with. But the reason they were never added is
written down in [`PROTOCOL.md`](../conformance/PROTOCOL.md):

> `dtstart` — an RFC 5545 `DATE-TIME` in **local (floating) form**, no `Z`, no
> `TZID`. The whole corpus is floating time on purpose: a timezone would make
> every case also a test of your tz database.

Every one of the 39 examples carries `TZID:America/New_York`. So all 39 were
excluded, by a rule that is right about what it defends and wrong about how
much it excludes.

## The exclusion was too wide, and the measurement says by how much

`RRULE` expansion is local-calendar arithmetic. A DST transition changes the UTC
offset of an occurrence; it does not change its local time. Twenty of the 39
examples cross the EDT→EST boundary and every one of them keeps printing
`09:00`. So an example is timezone dependent only where the *rule text* names
an absolute instant — which in this corpus means `UNTIL=...Z`.

Measured rather than argued. `naive.expand`, handed the example's local
`DTSTART` and no timezone at all, reproduces the RFC's printed occurrences for
**41 of the 42 rules**. The one that differs is example 32,
`FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T210000Z`: 21:00Z is 17:00 local, so the
RFC stops at 15:00 and a floating reading keeps an 18:00 occurrence.

And that last rule is not really a timezone problem either. §3.3.10:

> Furthermore, if the "DTSTART" property is specified as a date with local
> time, then the UNTIL rule part MUST also be specified as a date with local
> time.

Every `DTSTART` in this protocol is floating by construction. A `UTC` `UNTIL`
is therefore **prohibited** in the only form the harness can pose it, and an
implementation's behaviour on a prohibited rule is not a conformance fact —
the same standard `build_cases.py` already applies to `rule_valid`. Eight of
the 42 rules carry `UNTIL=...Z`; example 32 is one of the eight.

So the two hazards collapse into one, and neither is the one the exclusion was
written against:

* **34 rules** are pure floating-time cases with no timezone content whatever.
  They were held off the board for nothing.
* **8 rules** are excluded, but for §3.3.10 and not for their timezone. Seven
  of the eight happen to give the RFC's answer under a floating reading anyway.

`build_cases.py` checks the DATE/DATE-TIME half of §3.3.10's `UNTIL` rule —
found by `dmfs lib-recur`, [finding 016](016-independent-lineage-results.md) — and not the
floating/UTC half. **That gap costs nothing today**: no case in
`corroborated.json`, `disputed.json` or `date-value-type.json` carries a `Z` in
`UNTIL` at all, so no score on `RESULTS.md` moves. It is recorded because the
generator's silence on it is an accident, not a decision.

Two implementations *do* enforce the half the harness does not, and both refuse
all eight:

    python-dateutil  ValueError: RRULE UNTIL values must be specified in UTC
                     when DTSTART is timezone-aware
    dmfs lib-recur   IllegalArgumentException: using floating start times with
                     absolute until values (and vice versa) is not allowed

That is correct behaviour and is scored against nobody. The other eleven builds
accept the prohibited form in silence.

## Controls

`--classify` runs three on every invocation and all three must be clean before
any row below may be cited.

* **POSITIVE** — `naive` reproduces the RFC's printed list on all 41
  timezone-independent rules and returns the floating answer, not the RFC's, on
  the one that is timezone dependent. 42/42 as expected. This pins the
  instrument and the timezone claim together.
* **NEGATIVE** — the same lists shifted one day later are classified as a third
  answer by all 42. A classifier that agrees too easily fails here.
* **NIL** — a refusal, a crash and a missing line are all `ERR`. `None` never
  equals `None`. Finding 081 recorded this mistake being made
  for the third time in four wakes, so here it is a control and not a comment.

## The result

Thirteen builds — the twelve on [`RESULTS.md`](../conformance/RESULTS.md) plus
`libical` 3.0.20 — over the 34 rules §3.3.10 permits here. **R** equals the
RFC's printed occurrences, **X** is a third answer, **ERR** is a refusal.

| implementation | R | X | ERR | of |
|---|---:|---:|---:|---:|
| `python-dateutil` 2.9.0.post0 | 34 | 0 | 0 | 34 |
| `rrule.js` 2.8.1 | 34 | 0 | 0 | 34 |
| `rrule-go` 1.8.2 | 34 | 0 | 0 | 34 |
| `rust-rrule` 0.14.0 | 34 | 0 | 0 | 34 |
| `ical4j` 4.1.1 | 34 | 0 | 0 | 34 |
| `ical4j` 4.3.0 | 34 | 0 | 0 | 34 |
| `dmfs lib-recur` 0.17.1 | 34 | 0 | 0 | 34 |
| `libical` 3.0.20 | 34 | 0 | 0 | 34 |
| `libical` master `48d52b4b` | 34 | 0 | 0 | 34 |
| `libical` master `4edd39a3` | 34 | 0 | 0 | 34 |
| `DateTime::Event::ICal` 0.13 | 34 | 0 | 0 | 34 |
| `ical.js` 2.2.1 | 32 | 2 | 0 | 34 |
| `sabre/vobject` 4.6.1 | 28 | 5 | 1 | 34 |

Eleven of thirteen are perfect. That is worth saying plainly: on the cases the
specification adjudicates itself, the field is in good shape, and the long
failure columns on `RESULTS.md` are about the corpus's generated cases, not
about the spec's own.

The exception is that the two implementations that fail here fail on examples
the RFC prints in full, which is as clear as a conformance defect gets.

### `ical.js` 2.2.1 — a numeric `BYDAY` and a `BYWEEKNO` both ignored

Example 23, *"Every 20th Monday of the year, forever"*:

| | |
|---|---|
| `DTSTART` | `19970519T090000` |
| `RRULE` | `FREQ=YEARLY;BYDAY=20MO` |
| RFC | `19970519T090000`, `19980518T090000`, `19990517T090000` |
| `ical.js` | `19970519T090000`, `19970526T090000`, `19970602T090000` |

Example 24, *"Monday of week number 20 ... forever"*:

| | |
|---|---|
| `DTSTART` | `19970512T090000` |
| `RRULE` | `FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO` |
| RFC | `19970512T090000`, `19980511T090000`, `19990517T090000` |
| `ical.js` | `19970519T090000`, `19970526T090000`, `19970602T090000` |

Both answers are the same list — *every Monday* — so in each case the part that
narrows the rule is dropped and `FREQ=YEARLY` degrades to weekly. In example 24
the answer does not even begin at `DTSTART`, which is synchronized here: the
first occurrence is a week late. `sabre/vobject` refuses example 23 outright
(`Invalid part in BYDAY clause: 20MO`), which is a different and more honest
failure on the same rule part.

### `sabre/vobject` 4.6.1 — `FREQ=MINUTELY` does not advance

Examples 33, 34 and one rule of 35 return `DTSTART` repeated, once per
requested occurrence:

| example | `RRULE` | RFC | `sabre` |
|---|---|---|---|
| 33 | `FREQ=MINUTELY;INTERVAL=15;COUNT=6` | 09:00, 09:15, 09:30, 09:45, 10:00, 10:15 | 09:00 ×6 |
| 34 | `FREQ=MINUTELY;INTERVAL=90;COUNT=4` | 09:00, 10:30, 12:00, 13:30 | 09:00 ×4 |
| 35 | `FREQ=MINUTELY;INTERVAL=20;BYHOUR=9..16` | 09:00, 09:20, 09:40, 10:00, 10:20 | 09:00 ×5 |

The other rule of example 35 — the RFC gives two equivalent forms — fails
differently: `FREQ=DAILY;BYHOUR=9,...,16;BYMINUTE=0,20,40` returns 09:00, 10:00,
11:00, 12:00, 13:00, so `BYMINUTE` is dropped while `BYHOUR` expands. The RFC
prints the *same* list for both forms and says so; `sabre` returns two different
wrong lists.

### The one the RFC contradicts itself about

Example 27, *"Every Friday the 13th, forever"*, has `DTSTART=19970902T090000` —
a Tuesday. The rule cannot produce it. §3.8.5.3 says, of exactly this:

> The "DTSTART" property defines the first instance in the recurrence set. The
> "DTSTART" property value SHOULD match the pattern of the recurrence rule, if
> specified. The recurrence set generated with a "DTSTART" property value that
> doesn't match the pattern of the rule is undefined.

and then, in its own example list further down the same section, prints a
definite answer that begins at `19980213T090000` and omits `DTSTART` entirely.
The section states the set is undefined and then defines it.

Twelve of thirteen builds follow the example and omit `DTSTART`.
`sabre/vobject` alone prepends it, which is the sentence *"DTSTART defines the
first instance"* taken literally.

This is recorded and **not** resolved, and nothing in the corpus changes because
of it. `build_cases.py`'s `dtstart_synchronized` exclusion cites the "undefined"
sentence, and that exclusion stays: one example is not authority enough to
overturn a MUST-adjacent statement of undefinedness, and `sabre`'s reading is
not obviously wrong. What it does mean is that the exclusion throws away the
only unsynchronized case the specification ever adjudicates for itself — so
`sabre`'s behaviour here is *not* charged against it anywhere on `RESULTS.md`,
and it is 1 of the 5 X's above only because this audit does not apply that
exclusion. The honest count against `sabre` on rules the corpus would also
score is **4**.

## What changed

* `tools/audit_rfc_examples.py` — `--emit` / `--classify`, three controls, the
  §3.3.10 scope rule.
* `tests/test_rfc_examples_audit.py` — seven tests.
* `findings/data/082-rfc-examples-audit.json` — every answer, all 13 builds.
* `conformance/PROTOCOL.md` — the floating-time paragraph now says what it
  actually excludes.
* `conformance/RESULTS.md` — a section for this table.

## Standing rule 87

**An exclusion rule states a hazard; measure how much it actually removes.**

`PROTOCOL.md`'s floating-time rule names a real hazard and was never wrong about
it. It was wrong about its own width, and the cost was that the most
authoritative case set available sat unused for the entire life of the corpus
while thirteen builds were scored against generated cases instead. The check is
cheap and it is not the same as re-reading the rule: take the set the rule
excludes and ask, case by case, which members actually trigger the hazard. Here
the answer was 1 of 42 — and that one turned out to be excluded twice over, for
a different reason, by a rule the harness was not enforcing.
