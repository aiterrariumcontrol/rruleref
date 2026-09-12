# Rust adapter — `fmeringdal/rust-rrule`

```sh
cargo build --release
python3 ../../score.py -- ./target/release/rustrrule_adapter
```

Needs a Rust toolchain (`cargo` 1.85 is enough) and network access for the
crate's dependencies; nothing from this repository. The contract is
[`../../PROTOCOL.md`](../../PROTOCOL.md).

## Why DTSTART is left floating

Every case in the corpus is floating local time. The crate requires `DTSTART`
and `UNTIL` to share a clock, so **both** are left floating — the crate's
`Local` — rather than coercing `DTSTART` to UTC the way the
[Go adapter](../go/README.md) does.

Coercing only `DTSTART` to UTC is the obvious move and it is wrong here: it
makes the crate reject every rule whose `UNTIL` is floating, with
`the value of DTSTART was specified in UTC timezone, but UNTIL was specified in
timezone Local`. That produced 28 errors on the first run of this adapter and
one residual divergence from `python-dateutil` on the corroborated set. All 29
were **the adapter's**, not the library's.

Running under `TZ=UTC` makes `Local` a fixed-offset clock, so no timezone
database can enter the answer. This turns out not to matter for the present
corpus — scoring under `TZ=America/New_York` gives the same 1721 — but the
guarantee is cheap and the corpus may grow DST-adjacent cases later.

The result this produced is
[finding 028](../../../findings/028-two-ports-agree-and-the-third-does-not.md):
`rust-rrule` 0.14.0 scores 1721/1721 and returns exactly what
`python-dateutil` 2.9.0.post0 returns on all 3813 corroborated cases. Like
`rrule-go` it is a dateutil descendant by its own README's account, so it is
**not** an independent lineage and its score is not independent evidence.
