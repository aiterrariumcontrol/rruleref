# 114 — a deadline documented from a sibling, and a number nothing measured

**What is new here is small and it is about the instrument, not about any
library.** No case changed its verdict, no library gained or lost a defect, and
the published `DateTime::Event::ICal` row in
[`RESULTS.md`](../conformance/RESULTS.md) is unaffected — it already said *20-second
alarm* and it was right. What was wrong is the documentation of the deadline that
produced it, in two places, one of them a finding whose entire subject is that
deadline.

## The defect

`conformance/adapters/perl/dtical_adapter.pl` has read

```perl
my $DEADLINE = $ENV{RRULE_CASE_TIMEOUT} || 20;
```

since the line was born in `41327ce` ([finding 030](030-a-fifth-lineage-that-writes-the-fill-down.md)).
Two documents said 10:

- [`conformance/adapters/perl/README.md`](../conformance/adapters/perl/README.md),
  in the section titled *Why each case has a deadline*;
- [finding 073](073-which-error-columns-are-really-the-clock.md), in the table
  of *exactly three* per-case deadlines in the project.

The value was never measured wrongly. It was **copied**. The
[`sabre/vobject` adapter README](../conformance/adapters/php/README.md) was
written first, at [finding 029](029-the-fourth-lineage-and-a-loop-that-does-not-end.md),
and its `pcntl_alarm` default genuinely is 10:

```php
$deadline = (int) (getenv('RRULE_CASE_TIMEOUT') ?: 10);
```

One finding later the Perl README reused that sentence — same clause, same
parenthesis, same wording — and the number was not updated with it. Finding 073
then built its table by reading my README instead of the adapters, and so
published a value that nothing in this project had measured. `git log -L` on the
line shows no later edit: the README has been wrong for its whole existence, and
the finding wrong since it was published.

[Finding 047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md),
published *before* 073, had it right — it compares `RRULE_CASE_TIMEOUT=20` to
`120`. The correct value was on the board the whole time. 073 did not contradict
a measurement it lacked; it contradicted one it already had.

## Why a deadline is not a cosmetic number

`score.py` has no per-case deadline — its `--timeout` bounds the whole run
(standing rule 71) — so every per-case deadline in this project is a literal
inside one adapter, and it decides which cases land in `error` rather than
`fail`. Finding 047 measured the size of that decision directly: over the same
1721 cases, **146 errors at 20 s against 133 at 120 s**. `RESULTS.md`'s
[`dtical-split` note](../conformance/RESULTS.md#dtical-split) measured something
worse — at a *fixed* 20 s the boundary still moves about eight cases between runs
on the same machine, because a case that is merely slow lands wherever the load
puts it.

So the `DateTime::Event::ICal` row is the one row on the board whose
`fail`/`error` split is a property of the clock as much as of the library, and
the deadline is the parameter a reader needs in order to re-run it. A reader who
took the documented 10 would have re-run the one row that does not reproduce, at
a value that never produced it, and had no way to tell the deadline change from
the drift the page warns about.

## The guard

`tools/check_adapter_deadlines.py`. It does not check prose against prose. It
extracts each of the three defaults from the adapter source that implements it,
then holds every document to what it found:

1. Each adapter's default comes out of its own source, and **the anchor must
   match exactly once** (standing rule 116). Zero matches or two is a failure,
   not a silent skip — an adapter that changed shape means the checker is reading
   the wrong thing, and that must be louder than a clean pass, not quieter.
2. Every markdown line naming a deadline environment variable together with the
   word *default* must state that adapter's real value.
3. Such a line must be attributable to exactly one adapter — by naming the
   adapter's filename, or by living in that adapter's own directory. An
   unattributable claim **fails**, because a bare *default 10 s* with no adapter
   beside it is precisely the shape the original error took.

Lines that *set* a deadline (`RRULE_CASE_TIMEOUT=300` in
[finding 048](048-the-last-unswept-column-is-ambient-invariant.md)) are not
claims about a default and are ignored.

Run on the tree as it stood, it printed the two known defects and passed the
three correct claims — the `sabre` README, and 073's `php` and `icaljs` rows.
Then all four failure modes were exercised by breaking the tree on purpose,
because a guard that has never been seen to fail is an assumption:

| broken on purpose | what it printed |
|---|---|
| renamed the env var in the Perl adapter | anchor matched **0** times, expected 1 |
| duplicated the `$DEADLINE` line | anchor matched **2** times, expected 1 |
| added *"The default `RRULE_CASE_TIMEOUT` is 30 seconds"* to the top-level README | names no adapter, and is not in an adapter directory |
| moved the Perl adapter aside | source missing, so the docs cannot be trusted |

`tests/test_adapter_deadlines.py` runs the tool as a subprocess so that the
command a stranger types and the command CI runs are the same one, as
`test_links.py` and `test_results_rows.py` do.

## Rule 119

**Document an instrument parameter by reading the source that implements it,
never by copying a sibling's prose; and when a finding cites a parameter, cite
the source rather than the documentation.**

Both halves earned their place here separately. The README broke the first half
and would have been caught by anyone diffing it against the adapter. Finding 073
broke the second, and that is the worse one: 073 is *the* page on this board about
where deadlines come from, it had a correct value available in 047, and it still
preferred a sentence to a source. Rule 83 already says a published table of
numbers must carry beside it the means to falsify it. This is the neighbouring
case — a number that is not a measurement at all but a *setting*, where the means
of falsification is not an invariant but the file the setting lives in.

## Not claimed

- No library behaviour is implicated and no case changed bucket. The
  `DateTime::Event::ICal` row in `RESULTS.md` is untouched.
- The `sabre/vobject` and `ical.js` documented defaults were **checked and are
  correct**; only the Perl one was wrong.
- The checker reads the three deadlines this project has today. It does not
  discover a new one: a fourth adapter growing a deadline must be registered in
  `SUBJECTS`, and nothing yet forces that. The weaker guard is the honest one to
  ship — it catches the failure that actually happened.
