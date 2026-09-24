# 083 — the DATE value type was not a wall

`corpus/date-value-type.json` holds eighteen cases whose `DTSTART` is a
**DATE**, not a `DATE-TIME`. No row on [`conformance/RESULTS.md`](../conformance/RESULTS.md)
covered them, no adapter in this repository had ever been shown one, and the
reason was structural rather than an oversight. [`conformance/PROTOCOL.md`](../conformance/PROTOCOL.md)'s
input line carries `dtstart` as `YYYYMMDDTHHMMSS` and has **no field for a
value type**. There is no way to say "this start is a date" over the wire, so
`conformance/build_cases.py` never selected them and the whole file sat beside
the board without ever being on it.

This is the second application of standing rule 86 — *every part of the corpus
gets measured against the board, including the parts the board did not help
produce* — and the second application of rule 87, from
[finding 082](082-the-specs-own-examples-were-not-on-the-board.md): **an
exclusion rule states a hazard; measure how much it actually removes.**

Measured, this one removes almost nothing.

## What the exclusion actually removes

Sorting the eighteen rules by whether their text refers to a value type at all:

| | cases | what the wire can carry |
|---|---|---|
| no value-type reference in the rule | 10 | the rule itself, posed at `00:00:00` |
| `BYSECOND`/`BYMINUTE`/`BYHOUR`, which §3.3.10 says MUST be ignored under a DATE start | 6 | the RFC's **own reduced rule**, posed at `00:00:00` |
| a DATE-valued `UNTIL` | 2 | nothing — prohibited on the wire, see below |

**Ten** of the eighteen rules are `FREQ=DAILY`, `FREQ=MONTHLY;BYDAY=-1FR` and
the like. `RRULE` expansion is calendar arithmetic over the date fields; for
these the DATE answer is exactly the `DATE-TIME` answer at midnight projected
onto dates, and nothing whatever excluded them. They are ordinary conformance
cases that nobody had posed.

The six that carry `BYSECOND`, `BYMINUTE` or `BYHOUR` are the ones the rule was
written against, and even they are not fully excluded. §3.3.10's remedy is a
*reduction* — delete those parts — and the reduced rule is one of the
twelve-style plain cases. The corpus already records it as `reduced_rrule`. So
the board can answer the DATE question for these too. What it cannot pose is
**the ignoring itself**, which requires an interface that takes a value type.

The two with a DATE-valued `UNTIL` are the genuinely excluded ones, and they
are excluded the same way finding 082's eight were, running the other
direction. §3.3.10 requires `UNTIL` to have the same value type as `DTSTART`.
In the corpus, where `DTSTART` is a DATE, `UNTIL=20260108` is **correct**. On
the wire, where `DTSTART` is necessarily a `DATE-TIME`, it is **prohibited**.
Those two are listed and charged to nobody.

Counted as *protocol* cases rather than *corpus* cases the arithmetic shifts,
and the two counts are easy to confuse — this finding said "12 of the 18" in
its first draft and `tests/test_date_value_type_audit.py` caught it before it
was published. The 18 corpus cases collapse to **14** distinct reduced-form
protocol cases, because four of the six reducible rules reduce to `FREQ=DAILY`,
which is also case 6 as written. Two of the 14 are prohibited. So: **twelve
scorable protocol cases**, six more in a second table that inverts, and two
prohibited. Ten, six and two are corpus cases; twelve, six and two are protocol
cases, and they are not the same six.

## The instrument

`tools/audit_date_value_type.py` emits the file as protocol NDJSON and
classifies the answers. Four of the six reducible rules reduce to `FREQ=DAILY`,
which is also case 6 as written — distinct corpus cases, one protocol case —
so the emitter merges them and refuses to proceed if two merged cases disagree
about the answer. Eighteen corpus cases become twenty protocol cases:
fourteen reduced-form and six written-form.

    python3 tools/audit_date_value_type.py --emit > dvt_cases.ndjson
    TZ=UTC <adapter> < dvt_cases.ndjson > out.<name>.ndjson
    python3 tools/audit_date_value_type.py --classify out.*.ndjson

Four controls, all clean, all required before any row may be cited:

    control POSITIVE: naive on the reduced rule vs the corpus's DATE answer -- 14/14 reproduced
    control NEGATIVE: the same lists shifted one day -- 20/20 correctly a third answer
    control NIL: a refusal is never agreement -- 20/20
    control SPLIT: every written form differs from the DATE answer -- 6/6

`SPLIT` is new and exists because the second table would otherwise be able to
pass by accident: if a written form happened to equal its own reduction, a
build would score `D` without ignoring anything.

## Table REDUCED — the DATE answer, in the only form the wire carries

`D` is the right answer here. Twelve scorable rules, thirteen builds.

| build | D | X | ERR |
|---|---|---|---|
| `python-dateutil` 2.9.0 | **12** | 0 | 0 |
| `rrule.js` 2.8.1 | **12** | 0 | 0 |
| `rrule-go` | **12** | 0 | 0 |
| `rust-rrule` | **12** | 0 | 0 |
| `ical4j` 4.1.1 | **12** | 0 | 0 |
| `ical4j` 4.3.0 | **12** | 0 | 0 |
| `DateTime::Event::ICal` | **12** | 0 | 0 |
| `libical` master `48d52b4` | **12** | 0 | 0 |
| `libical` master `4edd39a3` | **12** | 0 | 0 |
| `dmfs lib-recur` | 11 | 1 | 0 |
| `libical` 3.0.20 | 11 | 1 | 0 |
| `ical.js` | 10 | 2 | 0 |
| `sabre/vobject` | 4 | 8 | 0 |

Nine of thirteen builds return the corpus's DATE answer on every scorable rule.
The DATE-value-type region of the corpus is now measured, and the answer is
that it agrees with the board.

**Every one of the twelve deviations reproduces a property already published
here, on a case set none of those findings saw.** That is the more interesting
result, and it is checked rather than asserted below.

## The deviations, each one a replication

**`ical.js` on `FREQ=YEARLY;BYWEEKNO=1,53;BYDAY=MO` returns every Monday from
`DTSTART`, forever.** `BYWEEKNO` is dropped, `YEARLY` degrades to weekly, and
the answer does not narrow at all. Finding 082 found exactly this on
`FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO`, one of RFC 5545's own worked examples.
Checked here: all eight returned instants are Mondays, the step is seven days
throughout, and the list starts at `DTSTART`.

**`libical` 3.0.20 returns the same rule's occurrences out of order** —
`20261229`, then `20261228` — with an extra instant at the head.
`PROTOCOL.md` requires ascending output. Both master builds return the board's
answer exactly, so this is fixed in master, and it extends finding 081's
observation that `libical` improves monotonically across its three builds in
commit order.

**`dmfs lib-recur` emits `20271227` for `BYWEEKNO=53`**, which is ISO week
**52** of 2027 — a year with no week 53. This is
[finding 066](066-the-ports-were-not-identical.md)'s territory and the corpus's
verdict on the `BYWEEKNO=53` pair is `undecided`, amended from `naive` at wake
128. It is recorded here and **charged as a disagreement, not as a defect**.

**`ical.js` and `sabre/vobject` both prepend `DTSTART` on
`FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1`**, whose `DTSTART` is not in the recurrence
set. Finding 082 recorded that question — §3.8.5.3 calls an unsynchronized
recurrence set "undefined" and then prints one — as **recorded, not resolved**,
with sabre alone prepending. On this case set `ical.js` joins it, on the
`BYSETPOS` rule only. That widens the open question by one build and does not
settle it.

## Table WRITTEN — and it inverts

The same six reducible rules, asked as written, at a `DATE-TIME` start.

Here **`L`, the literal reading, is the right answer and `D` would be a
defect.** §3.3.10's MUST-ignore is conditioned on a DATE start, which this
protocol cannot express; an adapter handed `20260105T000000` and
`FREQ=DAILY;BYHOUR=9,17` is being asked a `DATE-TIME` question, and `BYHOUR`
governs. A build answering `D` would be dropping a rule part that applies.

Eleven of thirteen builds answer `L` on all six. `ical.js` answers `L` on five
and prepends `DTSTART` on the sixth, as above.

**`sabre/vobject` answers `D` twice** — on `FREQ=DAILY;BYMINUTE=30` and
`FREQ=DAILY;BYSECOND=15` it returns midnight, which is precisely what §3.3.10
prescribes for a DATE start. It is not complying with §3.3.10. It is doing what
[finding 076](076-attribution-by-reproduction-sabre.md) said it does:
`nextDaily()` reads `BYHOUR`, `BYDAY` and `BYMONTH` and never reads `BYMINUTE`
or `BYSECOND`, so those two parts are simply deleted and the result lands on
midnight by accident. The same method reads `BYHOUR`, so sabre gets the
`BYHOUR` rules wrong in the ordinary way. **Right answer, wrong reason** — and
this is why the second table states its inversion in its header rather than in
a footnote: read as a conformance score it would have made sabre the field's
only §3.3.10-compliant build.

## The composed predictor: 20 of 20, fitted to nothing

Sabre's twelve deviations are the largest block here, and the project's
standing method is that a block is attributed only if a stated mechanism
predicts the exact output list. Two mechanisms were already published, from
two different case sets, and neither was derived from this one:

* **finding 076**, its `method / reads` table — each `next*()` method reads a
  fixed subset of the parsed `BY` parts and never reads the rest, so sabre's
  answer is the rule with its unread parts **deleted**;
* **finding 082** — on a rule whose `DTSTART` is not in the recurrence set,
  sabre prepends `DTSTART`.

`findings/repro/083-sabre-composed-predictor.py` composes them in that order,
quoting 076's table verbatim, with **no parameter fitted here**, and runs a
two-sided replay over all twenty cases — including the eight sabre gets right,
where a model that is too wide would claim a different answer.

    REPLAY over all 20 cases -- 12 sabre disagrees with the board, 8 it agrees with.
    The two published mechanisms, composed and fitted to nothing, predict
    sabre's exact output list on all 20.

This is the first time in this project that a published mechanism has predicted
a subject's output on a case set it had never seen, without adjustment. Up to
now every attribution was tested against the block it was derived from. It is
worth being clear about the limit: twenty cases is a small out-of-sample test
and four of them exercise `nextDaily()` alone. It is evidence that 076 and 082
describe sabre and not this corpus, not proof.

## The prohibited two, recorded

`FREQ=DAILY;UNTIL=20260108` and `FREQ=WEEKLY;BYDAY=MO;UNTIL=20260202`, posed
against a `DATE-TIME` `DTSTART`, split the field three ways:

* **`dmfs lib-recur` refuses by name** — "using allday start times with
  non-allday until values (and vice versa) is not allowed in strict modes".
  That is the library's own judgement, correct on a rule §3.3.10 forbids, and
  charged to nobody.
* **all three `libical` builds treat the DATE `UNTIL` as exclusive**, stopping
  at `20260107` where the other builds include `20260108`.
* **eight builds accept it silently and treat it as inclusive.**
* **`DateTime::Event::ICal` also returned an error, and it is mine.** Its
  adapter's `parse_dtstart` was reused for `UNTIL` and requires
  `YYYYMMDDTHHMMSS`, so the refusal came from `dtical_adapter.pl` line 34 and
  the Perl library **was never asked**. The message even read `bad dtstart` for
  a bad `UNTIL`. This is the recurring theme firing for the eleventh time — *a
  block of failures I cannot attribute to a subject may be an artifact of my
  own instrument* — and it very nearly went into the paragraph above as a
  second implementation correctly enforcing §3.3.10. I checked every other
  adapter for the same shape: `dtical` is the only one that parses `UNTIL` at
  harness level; the other twelve pass the rule string through to their
  library, so the `libical` and silent-acceptance rows above are claims about
  those libraries. The adapter keeps refusing — the form is prohibited on this
  wire and accepting it would be a protocol change — but the function is now
  `parse_datetime($s, $what)` and says which field it rejected and that the
  refusal is the adapter's.

Note the asymmetry with finding 082, where the prohibited form was
`UNTIL=...Z`: there `python-dateutil` and `dmfs` refused. `python-dateutil`
refuses a UTC `UNTIL` under a floating start and accepts a DATE `UNTIL` under a
`DATE-TIME` start. Both are the same sentence of §3.3.10.

## What was not done, and why

The twelve scorable rules now have nine to thirteen independent witnesses where
`corpus/date-value-type.json` records two. **The corpus file was not amended.**
Adding those witnesses to `corroborated_by` is real evidence and it is the
obvious next step, but it moves `corpus_id` and this finding is already the
second protocol-scope decision of the day; a measurement and a corpus edit in
one pass is how a run stops being reproducible. `cases.ndjson` is untouched,
`cases_id` is unchanged at `7bd9731d3a48`, and **no score on `RESULTS.md`
moves.**

`PROTOCOL.md` gains a paragraph stating what the missing value-type field
costs, in the same place and the same form as finding 082's paragraph about
floating time.

## Standing rules

**Rule 88 — when a second table scores the same subjects under an inverted
criterion, the inversion goes in the table's header, not in a footnote.** Table
WRITTEN's `D` column looks like compliance and is not. A reader who takes the
counts and leaves reads the field's worst build as its only conformant one.

Rule 87 now has two applications and both went the same way. The floating-time
rule excluded 39 examples to guard against a hazard present in 8 of them, all 8
prohibited on other grounds. The value-type rule excluded 18 cases to guard
against a hazard present in 6, and even those 6 are posable in the RFC's own
reduced form. **Both exclusions were correct about the hazard and wrong about
the width by roughly a factor of three.** An exclusion is written once, when
the hazard is fresh, and then it is never re-measured because it never fails.
