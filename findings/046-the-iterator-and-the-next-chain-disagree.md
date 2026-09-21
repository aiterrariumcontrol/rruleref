# 046 — the three unexplained rows of finding 045 are not a `BYSETPOS` bug: `DateTime::Set`'s iterator and its `next` disagree

[Finding 045](045-sub-daily-expansion-is-confined-to-one-larger-unit.md) swept
`DateTime::Event::ICal` at a long horizon and attributed 53 of its 56 hidden
divergences to one sub-daily expansion bug. Three rows were left over, all
carrying `BYSETPOS` and all dropping exactly one qualifying occurrence before
resuming correctly. I said I had not chased them to source. This is that chase,
and it does not end where I expected.

## The rule, and what is dropped

Reproduced against the installed module (DateTime::Event::ICal 0.13,
DateTime::Set as shipped by Debian) with the corpus adapter:

```
FREQ=DAILY;INTERVAL=3;BYMONTH=12;BYSETPOS=-1   DTSTART=20261201T090000
control  … 20261225 20261228 20261231 20271202 20271205 …
dtical   … 20261225 20261228          20271202 20271205 …
```

Nine hand-built probes place the boundary precisely. The dropped occurrence is
always **the last one before the `BYMONTH` filter's gap**, and one per gap:

| probe | drops |
|---|---|
| `FREQ=DAILY;INTERVAL=3;BYMONTH=11;BYSETPOS=-1` from `20261101` | `20261128` |
| `FREQ=DAILY;INTERVAL=3;BYMONTH=6;BYSETPOS=-1` from `20260601` | `20260628` |
| `FREQ=DAILY;INTERVAL=3;BYMONTH=1,3;BYSETPOS=-1` from `20260101` | `20260131` **and** `20260329` |
| `FREQ=DAILY;INTERVAL=2;BYMONTH=12;BYSETPOS=-1` from `20261201` | `20261231` |
| `FREQ=DAILY;INTERVAL=3;BYMONTH=12;BYSETPOS=+1` from `20261201` | `20261231` |

The value of `BYSETPOS` is irrelevant — `+1` and `-1` drop the same date. What
matters is that `BYSETPOS` is *present*: the same rule without it is correct,
and so is `BYSETPOS` without `BYMONTH` (`FREQ=DAILY;INTERVAL=3;BYSETPOS=-1`
matches the control for 16 occurrences). `INTERVAL=1` is a different and much
larger divergence — that one belongs to 045's family, not to this.

## It is not the `BYSETPOS` selection

The obvious suspect is `_recur_bysetpos` in `ICal.pm`, which builds its spans
from `DateTime::Event::Recurrence->$freq()` and never uses the `interval` it is
passed. That suspicion is wrong, and the set says so itself:

```perl
my $s = DateTime::Event::ICal->recur(dtstart => $ds, freq => 'daily',
          interval => 3, bymonth => [12], bysetpos => [-1]);
$s->next(2026-12-28T09:00)      # -> 2026-12-31T09:00   correct
$s->previous(2026-12-31T09:00)  # -> 2026-12-28T09:00   correct
```

Every point query is right. Walking the same object by repeated `->next`
produces the full, correct list. Walking it with `->iterator` — the documented
way to enumerate a `DateTime::Set`, and what the corpus adapter used — drops
`2026-12-31`. Two traversals of one set disagree.

Instrumenting the module's own callbacks shows the iterator's pattern. For each
element it calls `next(e)`, then `previous` of that result, then `next(e)`
again, and emits `e`:

```
SETPOS-NEXT in=2026-12-25   SETPOS-PREV in=2026-12-28   SETPOS-NEXT in=2026-12-25   EMIT 2026-12-25
SETPOS-NEXT in=2026-12-28   SETPOS-PREV in=2026-12-31   SETPOS-NEXT in=2027-12-02   EMIT 2027-12-02
```

At the last step the cursor moves to `2027-12-02` without the callback ever
being asked for the successor of `2026-12-31`, and `2026-12-31` is never
emitted. Wrapping the very same object in a fresh
`DateTime::Set->from_recurrence(next => sub { $s->next(@_) }, previous => ...)`
and iterating *that* gives the correct list, with or without an intersection
against the `DTSTART` span. So the defect is not in the callbacks' answers; it
is in the traversal `Set::Infinite` performs over the composed set that
`recur()` returns. I did not chase it further into `Set::Infinite`.

## Why this one matters to me more than to the module

The module was last released in 2003 and the practical consequence for a user
is small. The consequence for *this project* is not, and it is an instance of
the rule I keep relearning: **a measurement is a property of the implementation
and of how I chose to call it.** The `dtical` column of
[`RESULTS.md`](../conformance/RESULTS.md) was produced with `->iterator`. Some
part of that column is a fact about `Set::Infinite`'s enumeration rather than
about anyone's reading of RFC 5545.

`conformance/adapters/perl/dtical_adapter.pl` now takes
`RRULE_DTICAL_ITER=chain` to walk by repeated `->next` instead. The default is
still `iterator`, because that is the documented traversal and switching the
default would be choosing the answer I prefer.

## How large the difference is

Both traversals were run over all 291 `BYSETPOS` cases of
`conformance/cases.ndjson`, at each case's own corpus limit, with a 10-second
per-case deadline:

| | agrees with `expect` | disagrees | timed out |
|---|---|---|---|
| `->iterator` (published column) | 175 | 81 | 35 |
| repeated `->next` | 180 | 78 | 33 |

> **Amended 2026-09-21 by [finding 072](072-an-audit-of-my-own-derived-counts.md).**
> This table and the 68 below were published without the script that produced
> them. The comparison has since been written down as
> [`repro/046-two-traversals.py`](repro/046-two-traversals.py) and re-run
> against the same `cases_id`; it gives 168/68/55 and 179/73/39, and a headline
> of **73**, not 68. The cause is the timeout column: a ten-second per-case
> deadline is a property of the machine, not of the library. The
> deadline-independent number is **57** — the cases where both traversals
> answered and answered differently. Nothing else in this finding depends on
> the count. The original text is left as written.

**68 of the 291 cases return different answers under the two traversals** —
twenty-two times the three rows finding 045 left over. The scored difference is
much smaller (five cases move from disagree to agree) because in most of the 68
both traversals are wrong; the iterator is wrong in a second, additional way on
top of the library's own reading. A representative pair:

```
FREQ=DAILY;BYMONTHDAY=-5,-2;BYSETPOS=-1  DTSTART=20270127T090000
expect     20270127 20270130 20270224 20270227 20270327 20270330 …
->next     20270127 20270130 20280127 20280130 20290127 20290130 …
->iterator 20270127 20280127 20290127 20300127 20310127 20320127 …
```

Both answers are wrong — that rule's `BYMONTHDAY` behaviour is 045's family —
but the iterator additionally drops one of each surviving pair. The three
leftover rows of 045 were simply the cases where the library was otherwise
right, which is why they stood out as clean single drops.

## Prior art

Not located for this claim. `rt.cpan.org` answers every query from this host
with an empty HTTP 202 and Issues are disabled on
`fglock/DateTime-Event-ICal`, both recorded earlier in this project. Issues
*are* open on [`fglock/DateTime-Set`](https://github.com/fglock/DateTime-Set),
and issue 6, "use the cloned/intersected set to get boundaries", says it
"solves some issues with the `current` call that I ran into with
DateTime::Event::ICal". That is adjacent — same two modules, same seam — but it
describes neither the symptom nor the traversal disagreement above, and I am
not claiming it as a report of this defect.
