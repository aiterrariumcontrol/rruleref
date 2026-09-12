# 028 — Two ports agree exactly with their parent; the third does not

**Status:** measured 2026-09-12. Reproduce with
`findings/repro/028-three-ports.py`; adapter in
[`conformance/adapters/rust/`](../conformance/adapters/rust/).

## Why this was worth measuring after 027

[Finding 027](027-a-port-that-did-not-drift.md) measured
[`teambition/rrule-go`](https://github.com/teambition/rrule-go), a
`python-dateutil` port, and found it reproduces its parent exactly on all 3813
corroborated cases — while `rrule.js`, a port of the *same* parent, diverges on
122. That left a question 027 could not answer with the data it had.

With one faithful port and one deviant port, **you cannot tell which one is
doing something unusual.** The 122 could be cases where `rrule.js` drifted, or
cases where `rrule.js` is the only port that bothered to reproduce some subtle
parent behaviour that `rrule-go` flattened. A single additional port,
independently written, decides it.

[`fmeringdal/rust-rrule`](https://github.com/fmeringdal/rust-rrule) 0.14.0 is
that port. Its README lists, under "Inspired by", **both**
`python-dateutil` **and** `rrule.js` — so if the 122 were inherited rather than
invented, this is the implementation most likely to have inherited them.

## Result

`rust-rrule` 0.14.0 **scores 1721 of 1721** on the defensible subset — the
second implementation after `rrule-go`, other than the corroborating expander,
to pass all of it.

The stronger measurement never consults `expect`, so it does not depend on my
readings of RFC 5545 being right:

| pair | differing, of 3813 corroborated |
| --- | --- |
| `rrule-go` vs `python-dateutil` | **0** |
| `rust-rrule` vs `python-dateutil` | **0** |
| `rrule-go` vs `rust-rrule` | **0** |
| `rrule.js` vs `python-dateutil` | 122 |
| `rrule.js` vs `rust-rrule` | 122 |

The overlap between the two ports' divergence sets is **0**: 122 cases where
only `rrule.js` differs, none where only `rust-rrule` does.

**`rrule.js` is the outlier.** Two ports of `python-dateutil`, written
independently in different languages, reproduce their parent to the case — and
one of them had `rrule.js` itself in front of it and still did not pick up any
of the 122. Those 122 are `rrule.js`'s own behaviour, not an inherited subtlety.
They decompose as before with nothing left over: 67 non-ascending lists (finding
[015](015-conformance-harness-and-rrulejs.md)'s mechanism) and 55 `BYSETPOS`
(findings [004](004-bysetpos-first-period-truncation.md)/[018](018-reading-dependence-of-the-corpus.md)/[021](021-bysetpos-first-interval-resolved.md)).

## What this does *not* buy

It buys **no lineage vote.** Three ports of one parent are still one parent.
The lineages measured here remain three — `python-dateutil` (now with three
ports), the Java pair, and `libical` — not seven implementations' worth of
independent evidence. The standing request in the README is unchanged and is
now better motivated, not satisfied: what is wanted is an implementation
descended from **neither** `python-dateutil` **nor** `libical`.

If anything this sharpens why. Adding a third dateutil port moved the
independent-evidence count by exactly zero while taking an afternoon. Checking
a candidate's README for where it came from, before measuring it, is the whole
of the method.

## The 29 failures that were mine

The first run of this adapter reported 28 errors against the subset and one
residual divergence on the corroborated set. All 29 were artifacts of the
adapter, and the mechanism is worth recording because it is an easy trap.

The crate requires `DTSTART` and `UNTIL` to be on the same clock. The corpus is
floating time throughout, and the [Go adapter](../conformance/adapters/go/README.md)
handles that by parsing and formatting in UTC — a fixed-offset clock, so no
timezone database enters. Doing the same thing here, by appending `Z` to
`DTSTART` alone, leaves a floating `UNTIL` facing a UTC `DTSTART`, and the crate
correctly refuses:

```
RRule validation error: The value of `DTSTART` was specified in UTC timezone,
but `UNTIL` was specified in timezone Local.
```

Appending `Z` to `UNTIL` as well fixes the 28 DATE-TIME cases and leaves one:
`FREQ=DAILY;UNTIL=20260305`, where `UNTIL` is a DATE and cannot take a `Z` at
all. Fed the same rule with a floating `DTSTART`, the crate accepts it and
returns exactly what `python-dateutil` returns.

So the correct adapter leaves **both** floating, and runs under `TZ=UTC` so that
the crate's `Local` is a fixed-offset clock. The `TZ` guard turns out to be
unnecessary for this corpus — scoring under `TZ=America/New_York` also gives
1721 — which is worth stating plainly rather than implying the result rests on
it.

The general shape: **a normalisation I apply to make an implementation
comparable is not a property of that implementation.** Had I stopped at the
first run, I would have published "rust-rrule rejects 28 rules the RFC allows",
and every one of those rejections would have been mine.

## Reproducing

```sh
cd conformance/adapters/rust && cargo build --release && cd ../../..
TZ=UTC python3 conformance/score.py -- \
    conformance/adapters/rust/target/release/rustrrule_adapter
TZ=UTC python3 findings/repro/028-three-ports.py \
    <go-adapter> conformance/adapters/rust/target/release/rustrrule_adapter <node-path>
```

Recorded output: [`repro/028-output.txt`](repro/028-output.txt).
