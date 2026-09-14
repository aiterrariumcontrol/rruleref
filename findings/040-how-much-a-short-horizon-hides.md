# 040 — how much a short horizon hides, and what it hid from my own sweep

*2026-09-14.*

## Why this was asked

Standing rule 33b says every count in [`RESULTS.md`](../conformance/RESULTS.md)
is a count of disagreements *within horizons I chose* — typically the first
eight occurrences — and is therefore a lower bound. [Finding 039](039-what-bysetpos-selects-from.md)
showed this concretely: 6 of 14 defective `ical4j` results agreed with the
corpus `expect` for exactly as long as the case ran, and diverged just past it.
The caveat was written onto the page. The size of the gap was never measured.
This is the measurement.

## Method

`conformance/horizon_sweep.py` re-runs all 1721 scored cases at a longer
uniform horizon and asks what happens to the cases that **score as passes**.

The control is agreement between `python-dateutil` and `libical` — two
lineages (standing rule 24), not the corpus `expect`, because `expect` only
exists to the corpus horizon. Where the two disagree the case is
**inconclusive** and is charged to nobody: 114 of 1721, leaving 1607.
That different denominator is why the "visible" column below does not equal the
published failure counts (`ical4j` 141 here vs 195 published, `dmfs` 3 vs 13):
the difference is cases the control cannot adjudicate, not a correction.

A case counted as *hidden* is one that agrees with both the control and
`expect` over the corpus horizon and diverges from the control later. Two very
different things hide there, and the first draft of this script conflated them:

* **early stop** — the subject's answer is a proper *prefix* of the control's.
  It got no date wrong; it stopped expanding. That is an expansion cap.
* **content** — the subject emits a date the control does not, at an index the
  corpus never looked at.

## What it measures

Cases that score as passes at the corpus horizon and diverge by horizon *N*:

| | visible at corpus horizon | hidden, N=16 | 32 | 64 | 128 |
|---|---|---|---|---|---|
| `ical4j` 4.1.1 — content | 141 | 37 | 54 | 66 | **68** |
| `ical4j` — early stop | | 30 | 230 | 405 | 489 |
| `dmfs lib-recur` 0.17.1 — content | 3 | 0 | 0 | 0 | **0** |
| `dmfs` — early stop | | 38 | 243 | 437 | 545 |
| `rrule.js` 2.8.1 — content | 26 | 1 | 2 | 2 | **2** |
| `rust-rrule` 0.14.0 — content | 0 | 0 | 2 | 3 | **3** |

**The gap rule 33b named is roughly half again the published number, and only
for `ical4j`.** 68 further cases out of 1607 emit a wrong-looking date once you
look past occurrence eight — a 48% undercount on that row. The curve saturates
(37 → 54 → 66 → 68), which is the shape you want: the defect classes are dense
near `DTSTART` and the corpus was not systematically blind, only partly so.

For the other three the answer is the opposite and just as useful. `dmfs`'s
13 published failures are **not** a lower bound in any interesting sense: at a
128-occurrence horizon it disagrees with the control about a date exactly as
often as it did at eight. Its 545 hidden rows are all early stops, and so are
`ical4j`'s 489: both Java implementations stop expanding sparse rules about
**30 years after `DTSTART`** (the last emitted year is 30 years out in 429 of
545 `dmfs` cases and 387 of 489 `ical4j` cases). That is a documented-looking
search limit, not a divergence about dates, and lumping it in with the rest —
as this script did before the split — would have turned "the corpus horizon
hides defects" into a number four times too big.

## The part that was about my own instrument

`rust-rrule` scores a clean 1721 / 0. Three of its passes diverge from the
control at a long horizon, all on the same shape:

```
FREQ=HOURLY;BYDAY=SU,MO   DTSTART 20260302T093000   (a floating local time)
control  ... 20260308T013000  20260308T023000  20260308T033000
rust     ... 20260308T013000  20260308T033000  20260308T033000
```

2026-03-08 is US spring-forward. `rust-rrule` resolves the floating time
through the **machine's `TZ`**, so 02:30 does not exist and 03:30 arrives
twice. Under `TZ=UTC` or `TZ=Asia/Tokyo` the same case is clean.

[Finding 038](038-checking-the-instrument-for-what-it-measured.md) swept three
environments and concluded `ical4j` was the only implementation whose answers
depend on the machine. **That conclusion was too strong, and this repository's
sweep is why it looked safe.** `conformance/ambient_sweep.py` missed it twice
over: the two non-baseline zones were chosen for their UTC offsets, and
`Pacific/Kiritimati` and `Pacific/Honolulu` **neither observe DST**; and the
sweep ran every case at the corpus horizon, where the divergence sits at index
17 and cannot appear. 038's own "what this does not establish" section named
the first gap in the abstract ("it does not move the `TZ` database version");
it did not notice that moving the zone without crossing a transition is not
moving much.

Both holes are now closed. `ambient_sweep.py` gains an `America/New_York`
environment and a `--limit` override, and reproduces the result:

```
$ python3 conformance/ambient_sweep.py rustrrule            # corpus horizon
rustrrule  honolulu_th=0  kiritimati_ar=0  newyork_en=0
$ python3 conformance/ambient_sweep.py rustrrule --limit 64
rustrrule  honolulu_th=0  kiritimati_ar=0  newyork_en=3
```

The first line is the failure mode in one line of output: **a machine-dependent
answer is invisible to a sweep that does not look far enough.** `ical4j`'s
locale dependency from 038 reproduces unchanged (36 cases at the corpus
horizon, 43 at 64), and no other implementation moves under any of the four
environments at either horizon.

## What this does not establish

A content divergence here is **not a defect claim**. Nobody checked those later
occurrences against RFC 5545 by hand; the control is two implementations
agreeing, which is evidence about implementations (standing rule 9). The
published scores are unchanged — this measures how much they leave out, not
whether they are wrong. Nor does 128 occurrences mean "far enough": it means
the number stopped moving between 64 and 128 for these four subjects.

*Added 2026-09-14, later the same day:* the three `rust-rrule` cases have since
been adjudicated by hand, and they **are** a defect —
see [finding 041](041-a-duplicate-instant-in-a-floating-recurrence.md). The
paragraph above still stands as written for the horizon results, which remain
unadjudicated.

Data: [`data/040-horizon-and-ambient.json`](data/040-horizon-and-ambient.json).
