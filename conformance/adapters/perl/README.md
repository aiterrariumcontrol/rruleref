# Perl adapter — `DateTime::Event::ICal`

```sh
sudo apt-get install -y libdatetime-event-ical-perl libjson-perl
TZ=UTC python3 ../../score.py -- perl dtical_adapter.pl
```

Debian trixie ships `libdatetime-event-ical-perl` 0.13-2, which is
`DateTime::Event::ICal` 0.13 on top of `DateTime::Event::Recurrence` 0.19.
Nothing is vendored and nothing is built. The contract is
[`../../PROTOCOL.md`](../../PROTOCOL.md). A full run takes about 16 minutes.

## Lineage

The module is by Flavio Soibelmann Glock, copyright 2003. Its `CREDITS` name
only the `datetime@perl.org` list, its `SEE ALSO` names only other `DateTime`
modules and RFC 2445, and neither `python-dateutil` nor `libical` appears
anywhere in the source. It is the **fifth independent lineage** measured here
and the second, after `libical`, that is competent enough on `FREQ=YEARLY` to
cast a usable vote on the contested readings of §3.3.10.

Note that it targets **RFC 2445**, not RFC 5545. §4.3.10 of 2445 and §3.3.10 of
5545 carry the same recurrence text on every point at issue here; the corpus is
built against 5545 and the difference is recorded rather than adjusted for.

## `DTSTART` is left floating

Every corpus case is floating local time. `DateTime->new` with no `time_zone`
gives the floating zone, which is exactly the required semantics, so the
adapter needs no clock coercion of the kind the [Rust adapter](../rust/README.md)
documents. The run is still made under `TZ=UTC` so no timezone database can
enter an answer.

## Why each case has a deadline

`RRULE_CASE_TIMEOUT` (default 10 seconds) arms `alarm` around each case and the
handler dies, so a case that does not terminate is reported as
`{"error": "no answer within Ns"}` rather than hanging the whole run. 27 cases
need it, all of them `BYSETPOS` shapes. The timeout value is mine; the
non-termination is not.

## A control that was worth running

When a deadline fires, the `die` unwinds out of the middle of a lazy
`DateTime::Set`. That could leave module-level state inconsistent and make
*later, unrelated* cases fail — which would make the error column an artifact
of this adapter rather than a measurement. The [Rust adapter](../rust/README.md)
already has one worked example of an adapter's own normalisation nearly being
published as a property of the library.

So the whole corpus was also run through a fork-per-case variant, where every
case gets a fresh child process and no state can cross between cases. The
split was identical: **1176 pass, 51 other reading** either way. Only the
timeout count moved, 27 → 29, because forking costs wall-clock time. The
single-process adapter in this directory is the one that produced the published
numbers, and the contamination hypothesis is disproved rather than assumed
away.
