# 122 — Eighty-six of those errors are not the clock

[`RESULTS.md`](../conformance/RESULTS.md) tells a reader to discount one whole
column of one row. Its
[`dtical-split` note](../conformance/RESULTS.md#dtical-split) says
`DateTime::Event::ICal`'s `fail`/`error` boundary does not reproduce — the
adapter gives each case a 20-second alarm, so a merely-slow case lands wherever
the load puts it — and ends: *treat any comparison of its `fail`, `error` or
`other reading` columns against an earlier run of this document as noise.*

That instruction is sound and it is also too strong, and this is the number
that shows how much. Of the published 124 `error` cases, **86 are the library
refusing or crashing**, not the clock. They are deadline-independent, they
reproduce anywhere, and 69 of them are a single undefined-value crash inside
`DateTime::Event::ICal`. A reader following the page's advice discards them
along with the noise.

## Two measurements, and why it took both

**A timing pass.** `findings/repro/122-dtical-case-times.py` runs the
*unmodified* adapter over all 1727 cases and records each case's wall time. The
adapter is a batch program — one Perl process, all cases, which is the
configuration the published row was produced in — and it never sets `$|`, so
through a pipe its results arrive in block-buffered chunks of twenty-odd cases
and a slow case cannot be told from its neighbours. Under a pty, PerlIO
line-buffers, each result is flushed as it is produced, and the interval between
terminating newlines is the case's time. The script asserts the answers come
back in input order; silent reordering would attribute every time to the wrong
case.

That pty is a harness control, so it is checked rather than assumed. A full pass
through the pipe has a published cost —
[finding 116](116-the-four-hour-pass-that-took-thirty-minutes.md) measured
1832.9s on a quiet machine — and this pass took **1852s**, 1.0% more. The pty is
not in the way.

**A scoring pass at the wrong deadline.**
[Finding 114](114-a-deadline-documented-from-a-sibling.md) found two documents
claiming this adapter's deadline is 10 when it has always been 20, and left a
hint it declined to publish: that the documented 10 would have moved the `pass`
column 1164 → 1158. Scoring at 10 answers that *and* separates the error
column, because the two halves are told apart by the adapter's error **message**
and `score.py --json` is the only thing that keeps messages. Finding 116's
artifact keeps ids without them, which is why
[finding 073](073-which-error-columns-are-really-the-clock.md) — whose entire
subject is this split — has one for `sabre` and `ical.js` and never had one
here.

## The split

```
scored at deadline 10s: {'error': 142, 'fail': 358, 'fail_other_reading': 68, 'pass': 1159}
error column 142 = 56 clock + 86 library
every refusal is also an error at deadline 20: yes

the library half, by shape:
    69  Can't call method "is_infinite" on an undefined value
    10  these arguments are not implemented: byminute=...
     5  Can't call method "subtract_datetime" on an undefined value
     2  these arguments are not implemented: bysecond=...

the published row's 124-case error column: 86 library + 38 clock
```

A refusal cannot depend on the deadline — it happens before any work — and that
is verified rather than argued: all 86 are also in finding 116's error bucket,
scored at the real deadline of 20. So the published column decomposes exactly:
**86 library + 38 clock = 124**, and the 86 is the part the page should not be
telling readers to ignore. Twelve of the 86 are the module declaring a part
unimplemented, which is a documented limitation and not a defect; the other 74
are two distinct undefined-value crashes.

## What the wrong deadline would have published

54 cases exceed 10s in the timing pass: 34 pinned at **exactly** 20000ms — the
alarm is neither approximate nor deferred by anything in the module's XS — and
twenty measured between 10.607s and 18.778s. Joining those twenty to finding
116's buckets (5 pass, 10 fail, 1 other reading, 4 already error) predicts the
deadline-10 row as `1159 / 360 / 68 / 140`.
<!-- provenance: RETRACTED-QUOTE 1159/360 68/140 -- slices of the PREDICTED row,
     quoted here only so the measured row below can contradict it. A prediction
     that was partly refuted is supposed to have no producer. -->

The measured row is **`1159 / 358 / 68 / 142`**.

`pass` is exact. **The column loses five, not the six that was hinted** — the
hint was measuring the right thing on a contaminated run and came within one.
That was the question finding 114 left open and it is now closed with a
measurement.

## Where the prediction missed, which is the more useful half

Two cases went to `error` that I predicted would not, and the instrument names
them without ambiguity: `0e3f11394e75`, timed at 9379ms, and `6aa630dc9463`, at
9936ms — **6.2% and 0.6% below the deadline they then exceeded**. In the other
direction there were no misses at all: every one of the 54 cases timed above 10s
was killed by the 10s alarm, 54 for 54.

So the predictor is exact downward and leaky upward, and I had reasoned about
the wrong side of the threshold. I checked the nearest case *above* 10s
(10.607s, 6% clear) and concluded the boundary was quiet. Drift into `error`
comes from the cases *below* it, and there were four sitting between 9.344s and
9.936s. Two crossed. Two did not.

**And the slowdowns are not uniform, which kills a tidier story I had written
down.** The timing distribution has a real structural feature: above 5s the tail
holds 37 cases, and its widest gap — 1632ms, between 13.411s and 15.043s —
fences off exactly eight cases below the alarm. *About eight cases* is precisely
what the `dtical-split` note reports moving. I had the finding drafted around
that coincidence. The decomposition refutes it: finding 116's run timed out on
**four** cases more than the timing pass did, and they are

| time in the timing pass | slowdown needed to reach 20s | case |
|---|---|---|
| 10.864s | 1.84x | `f09e64d172f6` |
| 15.043s | 1.33x | `1517cb3adc8f` |
| 17.296s | 1.16x | `690ba4d5ab73` |
| 18.418s | 1.09x | `4520d0c686fd` |

One of them needed to run 1.84x slower, which puts it far outside the eight-case
band, while four cases *inside* that band did not move at all. A single timing
pass plus an assumed uniform slowdown does not predict which cases cross: the
variance is per-case, and large. The gap at 13.4s is a real feature of the
distribution and it is **not** the drift band.

## What this is and is not

What a reader can now do that they could not before: discount 38 of that row's
124 errors as load and keep the other 86, which are the module's own behaviour;
re-run the row at the real deadline knowing which 54 cases the clock is deciding;
and stop treating the whole column as unusable.

What is not established: nothing here is a verdict on
`DateTime::Event::ICal`'s correctness. A slow case is not a wrong case, and
none of the 54 changed its verdict on the merits. The 69-case undefined-value
crash is a reproducible fact about the module, but *why* it happens is not
attributed here and the module's source was not read. Wall clock is not
reproducible, so the artifact stores and `--check` holds only the stable part —
which cases are slow, not how slow — and the 1632ms gap and the slowdown
multiples above are one measurement of a load-sensitive quantity.

I also have not asked why the 54 slow cases are slow. The 34 pinned at the alarm
are covered by [finding 029](029-the-fourth-lineage-and-a-loop-that-does-not-end.md)'s
unterminating loop and [finding 047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md)'s
horizon analysis; the twenty between 10s and 20s are not, and whether they share
a shape is a separate question.
