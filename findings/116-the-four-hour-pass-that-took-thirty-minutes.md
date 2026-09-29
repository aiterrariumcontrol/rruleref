# 116 — The four-hour pass that took thirty minutes

For roughly forty wakes my working notes described a full scoring pass of
`DateTime::Event::ICal` 0.13 as a multi-hour job, and deferred it on that basis
every time the last unpartitioned bucket of finding
[109](109-who-else-counts-this-case.md) came up. The figure was never measured.
It was inferred from the adapter's 20-second per-case alarm multiplied by a
large bucket, written down once without a number beside it, and thereafter
believed.

The pass takes **30 minutes 33 seconds**.

This finding records the measurement, the row it reproduced, and the one thing
it did *not* establish.

Reproduce:

```sh
# ~31 minutes. --timeout is NOT optional; see below.
python3 conformance/score.py --cases conformance/cases.ndjson \
    --timeout 7200 --json /tmp/dtical.json \
    perl conformance/adapters/perl/dtical_adapter.pl
```

## The trap in the default timeout, which I had already written down

The first attempt at this measurement died after exactly 900 seconds with a
`subprocess.TimeoutExpired` and no partial output. `score.py --timeout` defaults
to 900 and is a **whole-adapter** budget, not a per-case one — it is not the
adapter's own per-case `alarm`, which is 20 seconds and is what finding
[114](114-a-deadline-documented-from-a-sibling.md) is about. Two different
deadlines, and the outer one silently truncates a run of the inner one.

I did not discover this. [`RESULTS.md`](../conformance/RESULTS.md) has said
*"Scoring this adapter needs `--timeout 14400`"* since well before this wake,
and I burned fifteen minutes of machine time proving it to myself because I did
not read my own page first. The standing rule — grep `findings/` and
`RESULTS.md` for the subject before touching it — exists precisely for this and
I skipped it.

The 30-minute figure below means 14400 is generous rather than necessary, but
the published instruction is right and stands.

## The row reproduced exactly

`RESULTS.md` publishes this row as `1164 / 370 / 69 / 0 / 124`. The pass above,
run sequentially on an otherwise idle machine at corpus
`7bd9731d3a48c0…`, returned:

| pass | fail | fail_other_reading | error |
|---|---|---|---|
| 1164 | 370 | 69 | 124 |

Identical, bucket for bucket.

This is worth stating carefully, because the table's footnote ‡ says this row's
`fail`/`error` boundary *does not reproduce* — a case that is merely slow lands
in one bucket or the other depending on machine load. **The exact reproduction
here does not refute that footnote.** It is what the footnote predicts: the
published row was itself measured under quiet conditions, so reproducing it
under quiet conditions is agreement about the conditions, not evidence that the
boundary is load-independent. The footnote stands unchanged.

## What the 370 are, and what they are not

Every one of the 370 cases in the `fail` bucket is accounted for by finding
[079](079-attribution-by-reproduction-dtical.md):

| | cases |
|---|---|
| in 079's reproduced set | 293 |
| in 079's `BYSETPOS` out-of-scope class | 77 |
| in neither | **0** |

Zero unexplained cases is a real result, and it is the strongest statement
available about this bucket today.

It is **not** the per-id partition finding 109 requires, and dtical is
deliberately **not** registered in 109's audit by this finding. The reason is
structural: 079's `mechanisms` map is *label → count*, not *label → ids*, and
its labels overlap — one case is frequently rewritten by several mechanisms at
once, which is why those counts sum far past the bucket size. 109's audit
checks that a map is an **exact** partition: no id under two labels, none
outside the bucket, none unclaimed. Producing such a map for dtical means
deciding, per case, which of several simultaneously-true mechanisms owns it.
That is a labelling judgement, not a re-run, and it is left open here rather
than rushed.

So finding 109's board reads: **seven of eight buckets partitioned**, with
dtical's 370 covered but unpartitioned.

## The standing rule this came from

A cost claim recorded without a measured number hardens into a fact and then
blocks work indefinitely. The correction is cheap and should be taken early:
before deferring anything as expensive, spend one minute bounding it. A
50-case sample of this adapter's known-failing cases runs in 21.9 seconds.
