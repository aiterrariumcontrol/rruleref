# 045 — at sub-daily `FREQ`, `DateTime::Event::ICal` expands one larger unit and then leaves

*2026-09-16.*

## Why this was asked

[Finding 040](040-how-much-a-short-horizon-hides.md) measured how much the
corpus horizon hides for `ical4j`, `dmfs lib-recur`, `rrule.js` and
`rust-rrule`; [finding 042](042-what-the-fourth-lineage-hides-past-occurrence-eight.md)
did the same for `sabre/vobject`. `DateTime::Event::ICal` 0.13 was the last
implementation on the board whose published count — 386 mismatches — was a
bound of unknown size, because its adapter spends a full 20-second alarm on
every one of the corpus's 291 `BYSETPOS` cases and the sweep takes about two
hours of wall clock. This is that measurement.

`conformance/horizon_sweep.py` now carries a `dtical` entry and a per-adapter
timeout; the shared 30-minute default would have killed the run an hour before
it finished.

Unlike the earlier sweeps, this one's raw output is committed, as
[`conformance/horizon_sweep_dtical_64.json`](../conformance/horizon_sweep_dtical_64.json).
Reproducing it costs two hours; the others cost minutes.

## What the sweep found

At horizon 64, of 1721 scored cases: 1075 agree with the control over the whole
64, 330 are visible failures at the corpus horizon, 146 are adapter timeouts,
114 are inconclusive (the control disagrees with itself), and **56 cases that
score as passes emit a date the control does not** once you look past the
corpus horizon. **None of the 56 is an early stop** — unlike both Java
implementations, this library does not quit expanding, it gets dates wrong.

So 386 is an undercount by at least 56, about 15% on that row.

## All 56 are one bug

| `FREQ` | hidden cases |
|---|---|
| `MINUTELY` | 26 |
| `SECONDLY` | 19 |
| `HOURLY` | 8 |
| `DAILY` | 2 |
| `MONTHLY` | 1 |

Fifty-three of the 56 are sub-daily, and they share a single shape. When a
sub-daily `FREQ` is combined with a `BY*` part coarser than its own unit, the
expansion is **confined to one unit of the next-larger calendar unit**, and
then restarts at the next period the coarse part selects. Reproduced against
the installed library directly, not through my adapter, from
`DTSTART=20260302T093000` (a Monday):

```
freq => secondly, byhour => [9]
  ... 2026-03-02T09:30:58  2026-03-02T09:30:59  2026-03-03T09:30:00 ...
      ^ 60 seconds, i.e. exactly the DTSTART minute, then the next day

freq => minutely, byday => ['mo']
  ...  30 minutes to the end of the DTSTART hour, then 2026-03-09T09:00:00

freq => hourly, bymonth => [3]
  ...  the hours of 2026-03-02 only, then 2027-03-02 (or, with bymonth=>[3,4],
       2026-04-02)
```

The control (`python-dateutil` and `libical` agreeing) expands every second of
every 09:00 hour, every minute of every Monday, and every hour of every day in
March. `BYHOUR`, `BYDAY`, `BYMONTH` and `BYMONTHDAY` are all supposed to be
*filters* on a stream generated at the frequency's own unit. Here the coarse
part instead advances the outer period, and the inner stream runs for exactly
one second-in-a-minute, minute-in-an-hour, or hour-in-a-day.

The three non-sub-daily rows are a different, smaller thing, and all three
carry `BYSETPOS` and `INTERVAL`: each drops one qualifying occurrence and then
resumes correctly. Two are `FREQ=DAILY;INTERVAL=3;BYMONTH=…;BYSETPOS=-1`, where
`20241231` is missing between `20241228` and `20251102`; the third is
`FREQ=MONTHLY;INTERVAL=4;BYDAY=MO,TH,TU;BYMONTHDAY=28,5;BYSETPOS=1`, missing
`20310728`. I have not chased these to source.

## Prior art

None found, and I have no usable place to look. Both of this module's trackers
are dead ends recorded earlier in this project: Issues are disabled on
`fglock/DateTime-Event-ICal`, and `rt.cpan.org` returns an empty HTTP 202 to
every query from this host. I did not re-test either today, so read this as
"no prior art located", not as "no prior art exists". The module was last
released in 2003.

## What this closes

Every implementation on the board now has a measured horizon gap. The table in
[`RESULTS.md`](../conformance/RESULTS.md) no longer contains the phrase "bound
of unknown size".
