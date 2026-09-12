# 030 — A fifth lineage, and the first one that writes the DTSTART fill down

*2026-09-12.*

## Result

[`DateTime::Event::ICal`](https://metacpan.org/pod/DateTime::Event::ICal) 0.13
(Perl, Flavio Soibelmann Glock, 2003) is the **fifth independent lineage**
measured against this corpus, and the first since `libical` that is competent
enough on `FREQ=YEARLY` to cast a usable vote on the two contested readings of
RFC 5545 §3.3.10.

It votes for the `dtstart_fill` reading — and unlike every other implementation
here, it does not merely *behave* that way. **The fill is written out in its
source, as two explicit lines, in exactly the two branches
[finding 024](024-dtstart-fill-versus-the-table.md) identified.**

| metric | value |
| --- | --- |
| scored | **1176 / 1721** — 386 mismatch, 51 other reading, 108 error |
| guaranteed invariant violations | **0** |
| order-dependent mismatches | **0** |
| `dtstart_fill`, 65 contested cases | corpus 8, **rival 51**, neither 6 |
| `first_period_truncated`, 25 cases | corpus 15, rival 0, neither 10 |

Reproduce: [`repro/030-dtical-dtstart-fill.pl`](repro/030-dtical-dtstart-fill.pl),
output in [`repro/030-output.txt`](repro/030-output.txt). Adapter and build
notes: [`conformance/adapters/perl/`](../conformance/adapters/perl/README.md).

## Why it counts as a lineage

Standing practice here is to read the README before valuing an implementation
as evidence — the rule that disqualified `rrule-go`, `rust-rrule`,
`rlanvin/php-rrule` and `simshaun/recurr` in a minute each
([027](027-a-port-that-did-not-drift.md),
[028](028-two-ports-agree-and-the-third-does-not.md),
[029](029-the-fourth-lineage-and-a-loop-that-does-not-end.md)).

`DateTime::Event::ICal`'s `CREDITS` name only the `datetime@perl.org` mailing
list. Its `SEE ALSO` names only other `DateTime` modules and RFC 2445. Neither
`dateutil` nor `libical` appears anywhere in the module or in its dependency
`DateTime::Event::Recurrence`. The copyright is 2003 — contemporaneous with
`python-dateutil` 1.0, not downstream of it.

It targets **RFC 2445**, whose §4.3.10 carries the same recurrence text as
§3.3.10 of 5545 on every point at issue here. The corpus is built against 5545;
the difference is recorded, not adjusted for.

## The fill, in the source

`_yearly_recurrence` in `DateTime/Event/ICal.pm` dispatches on which BY part is
present. Two of its branches end with a line that takes the missing field from
`DTSTART`:

```perl
elsif ( exists $args{byweekno} )
{
            $by{weeks} =  $args{byweekno};
            $by{days} =   $args{byday} if exists $args{byday};
            $by{days} =   $dtstart->day_of_week unless exists $by{days};
}
...
else
{
            $by{months} = $dtstart->month;
            $by{days} =   $args{bymonthday} if exists $args{bymonthday};
            $by{days} =   $dtstart->day unless exists $by{days};
}
```

`BYWEEKNO` with no `BYDAY` takes the weekday from `DTSTART`. `BYMONTHDAY` with
no `BYMONTH` takes the month from `DTSTART`. Those are the two clusters —
15 cases and 41 cases — on which `libical`, `ical4j` and `dmfs lib-recur` were
observed to return the identical non-corpus answer, and which finding 024
reproduced exactly by rewriting the rule that way.

This matters because of what the three-way agreement in finding 024 could not
settle. Three implementations landing on the same answer is consistent with
three authors independently reading the DTSTART-fill sentence as governing —
and equally consistent with three authors sharing an implementation shortcut
and never reading the table at all. Here the choice is not inferred from
output. It is a deliberate branch, written by someone with RFC 2445 §4.3.10
open, in 2003.

It is evidence about how the text reads to an implementer, not evidence about
what the text means. §3.3.10 still contains both readings and still declines to
say which wins. But the claim "the table is unambiguous and these libraries are
simply buggy" is now harder to hold.

Corroboration that this is the fill and not weakness: the eight contested cases
where it agrees with the corpus instead are all `FREQ=YEARLY` rules that carry
`BYDAY` *and* `BYMONTHDAY`, which take the `elsif ( exists $args{byday} )`
branch above, where `$by{months}` is set to `[ 1 .. 12 ]` and no fill happens.
The fill fires exactly when the field is absent, and not otherwise.

Corroboration that the week arithmetic is sound: `FREQ=YEARLY;BYWEEKNO=-2,-1`
from a Monday `DTSTART` returns 2026-12-21, 2026-12-28, 2027-12-20, 2027-12-27.
ISO 2026 has 53 weeks and ISO 2027 has 52, and both are counted from the end
correctly. That is what
[finding 029](029-the-fourth-lineage-and-a-loop-that-does-not-end.md) could not
say about `sabre/vobject`, whose week handling is wrong in precisely these
branches and whose vote therefore did not count.

## Where the 545 non-passing cases go

They are not spread evenly, and almost none of them are `FREQ=YEARLY`.

| shape | mismatches |
| --- | ---: |
| `FREQ=WEEKLY` with `BYMONTH` | 179 |
| `FREQ=MONTHLY` with `BYMONTH` | 87 |
| `FREQ=DAILY` with `BYMONTHDAY` | 67 |
| all `FREQ=YEARLY` mismatches | 35 |

Every one of its 179 `FREQ=WEEKLY` mismatches carries `BYMONTH`, and those
three rows are 333 of 386. This is a
scope boundary rather than arithmetic: the module reduces each `FREQ` to a
`DateTime::Event::Recurrence` set and intersects, and the weekly path does not
express "weeks restricted to selected months" the way §3.3.10's limit step
does.

`BYSETPOS` is worse than a mismatch. The module's own source carries a
`# TODO: ... bysetpos` comment, and 27 of the 108 errors are `BYSETPOS` cases
that never terminate within a ten-second deadline. `MINUTELY`/`SECONDLY` with
`BYMINUTE`/`BYSECOND` is refused outright with `these arguments are not
implemented` — 12 cases, an honest refusal rather than a wrong answer.

The remaining 65 errors die inside `DateTime::Event::Recurrence` at line 822
with `Can't call method "is_infinite" on an undefined value`. The smallest
reproducer is one line of the fill above: `FREQ=MONTHLY;BYMONTH=11,12` with
`DTSTART` on a 31st fills day-of-month 31, November has no 31st, the
intermediate set is undefined, and the iterator dies. Moving `DTSTART` to the
30th makes it work. **Only 8 of the 65 have that shape**, though; the other 57
reach the same crash site by routes this finding does not claim to have
identified, and saying so is part of the result.

## What it does not change

`0` guaranteed invariant violations and `0` order-dependent mismatches
([`check_invariants.py`](../conformance/check_invariants.py), which never reads
`expect`) put it level with `python-dateutil` and `libical` master on the
corpus-independent axis, against `sabre/vobject`'s 414. When this module answers, it answers self-consistently; it fails by
declining to cover a shape, not by returning instants that violate the rule
they came from.

That is the honest summary of a 1176. It is the second-lowest score in
`RESULTS.md` and it is still the most useful new row since `libical`, because
score and evidentiary weight are different quantities and this finding is the
clearest case of that so far.
