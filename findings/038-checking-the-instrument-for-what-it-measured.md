# 038 — checking the instrument for the defect it had just measured

*2026-09-14.*

## Why this was asked

[Finding 036](036-a-score-that-depends-on-the-host-locale.md) established that
`ical4j` returns different occurrences on differently-configured machines: with
`WKST` omitted it takes the week's first day from `Locale.getDefault()` instead
of RFC 5545's stated default of `MO`. That was found by accident, while
characterising something else. Nothing in this harness looked for the general
shape of it, so the published scores rested on an unexamined assumption: that
an adapter's answers are a function of the rule and the `DTSTART` alone.

This sweep tests that assumption directly. Every adapter is run over the
scored 1721-case corpus in three environments and the raw answers are diffed
case by case. The hostile environments move three things at once — the time
zone and the sign of its offset, the locale's first day of the week, and the
locale's digit shapes:

| name | `TZ` | locale | first day | digits |
|---|---|---|---|---|
| `baseline` | `UTC` | `en_US.UTF-8` | Sunday | Latin |
| `kiritimati_ar` | `Pacific/Kiritimati` (UTC+14) | `ar_EG.UTF-8` | Saturday | Arabic-Indic |
| `honolulu_th` | `Pacific/Honolulu` (UTC−10) | `th_TH.UTF-8` | Sunday | Latin |

The tool is `conformance/ambient_sweep.py`; it exits non-zero if anything moved.

## What it found

**`ical4j` is the only implementation whose answers moved**, and the way they
moved is finding 036 reproducing in a third locale rather than anything new.
36 of 1721 cases change under `ar_EG`, and every one of them is a `FREQ=WEEKLY`
rule whose week boundary has shifted to Saturday. `FREQ=WEEKLY;BYDAY=SA,SU;
BYSETPOS=-1` `DTSTART:20260517T090000` returns the Sundays under `ar_EG` and
the Saturdays under `en_US`; the rule names no `WKST`, so RFC 5545 fixes the
answer and the machine should not be able to change it. Nothing moves under
`honolulu_th`, which shares `en_US`'s Sunday: the axis is the locale's first
day of the week, not the zone.

Six of the others — `dateutil`, `rrule.js`, `libical`, `rust-rrule`,
`sabre/vobject`, `dmfs lib-recur` — returned byte-identical answers in all
three environments, over all 1721 cases.

The seventh, `DateTime::Event::ICal`, was swept over **1430 of the 1721** and
also returned byte-identical answers. The 291 excluded are every case carrying
`BYSETPOS`: the Perl adapter spends its full 20-second alarm on each of those,
which makes three full passes hours of wall clock for one row. The exclusion is
a budget decision, not a measurement, and it is stated here rather than rounded
away — `DateTime::Event::ICal` is unswept on `BYSETPOS`.

## What it found in the instrument

The sweep's first run reported that **`dmfs lib-recur` changed on 1713 of 1721
cases under `ar_EG`**, which would have been a far larger claim than 036. It
was not a claim about `dmfs` at all. The adapter formats each occurrence with

```java
String.format("%04d%02d%02dT%02d%02d%02d", ...)
```

and `String.format` without an explicit `Locale` uses `Locale.getDefault()`,
whose `ar_EG` number format writes Arabic-Indic digits. The library's answers
were identical throughout; my transcription of them was not. The eight
unchanged cases are the ones with no occurrences to format.

This matters beyond the cosmetics. Had anyone run this harness on an
Arabic-locale machine, `dmfs lib-recur` would have scored **0 out of 1721** and
the table would have said so, in the same typeface as every other number in it.
The instrument carried a weaker version of the defect it had just published
about someone else, and it carried it in the one place that is invisible when
the instrument is only ever run in one place.

Fixed by pinning the formatter to `Locale.ROOT`. Both Java adapters also read
and wrote through the JVM's default charset; those are now pinned to UTF-8,
which changes nothing today — the protocol is ASCII — but removes a second
ambient input. `dmfs lib-recur` scores 1637 / 13 / 63 after the fix, identical
to the published row, so no measurement in this repository changes.

## What this does not establish

Three environments are not a proof of independence. The sweep moves the zone,
the first day of the week, and the digit shapes; it does not move the system
clock, the default charset in a way the ASCII protocol could detect, the
calendar system, or the `TZ` database version. "Nothing moved under the three
environments I tried" is the whole of the claim for the other seven.
