# PHP adapter — `sabre-io/vobject`

```sh
sudo apt-get install -y php-cli php-xml composer   # php-xml is required by sabre/xml
composer install
TZ=UTC python3 ../../score.py -- php vobject_adapter.php
```

`composer install` needs network access and fetches `sabre/vobject`,
`sabre/xml` and `sabre/uri`; nothing from this repository. The contract is
[`../../PROTOCOL.md`](../../PROTOCOL.md). `vendor/` is not committed;
`composer.lock` pins the versions measured (`sabre/vobject` 4.6.1).

## Why each case has a deadline

`RRULE_CASE_TIMEOUT` (default 10 seconds) arms a `pcntl_alarm` around each
case, and the handler throws, so a case that does not terminate is reported as
`{"error": "no answer within Ns"}` instead of hanging the whole run.

This is not a convenience. Four corpus cases make `RRuleIterator` loop
forever — `FREQ=YEARLY` with `BYYEARDAY` and a `BYDAY` the library cannot
match. Without the alarm, `score.py` times out and reports nothing about the
other 1717 cases.

Reporting them as errors is the faithful thing under the protocol: "refuses to
answer" and "answers differently" are separate columns, and an unbounded loop
belongs in the first. Note that the timeout value is mine, not the library's —
these four cases are not slow, they do not terminate, and the probe in
[`findings/repro/029-vobject-sunday.py`](../../../findings/repro/029-vobject-sunday.py)
shows the search advancing through years without a ceiling.

## `DTSTART` is left floating

Every corpus case is floating local time, and `RRuleIterator` takes a
`DateTimeInterface`, so the adapter parses `dtstart` in the default timezone
and runs under `TZ=UTC` so that no timezone database can enter an answer. The
library needs no clock coercion of the kind the
[Rust adapter](../rust/README.md) documents.

## Result

[Finding 029](../../../findings/029-the-fourth-lineage-and-a-loop-that-does-not-end.md).
831 of 1721. It is the first genuinely independent lineage measured here since
`libical` — no ancestry claimed in its README, `lib/Recur/` or
`composer.json` — and also the first with a non-terminating case.
