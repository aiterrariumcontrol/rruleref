# 026 — Converting `UNTIL` through JSCalendar loses an hour, and can drop an instance

**Status:** Documentary, and about a live document. **Date:** 2026-09-12.
**Not a defect report against any implementation.** Nothing here is an
implementation bug: both conversion steps are mandated, and an implementation
that follows the specifications exactly is the one that loses the instance.
**Sources:** `draft-ietf-calext-jscalendar-icalendar-26` §1.4 and §2.3.36
(revision 26, dated 2026-09-02, **in WG Last Call** as of 2026-09-12);
RFC 5545 §3.3.5 and §3.3.10; `draft-ietf-calext-jscalendarbis-19` §1.5.5 and
§3.3.3, which is what the conversion draft normatively references (published
RFC 8984 §1.4.5 and §4.3.3 say the same thing in the same words).
**Reproducer:** [`repro/026-until-roundtrip.py`](repro/026-until-roundtrip.py) —
standard library only.

## The two rules that meet

`draft-ietf-calext-jscalendar-icalendar` defines how calendar data is converted
between iCalendar and JSCalendar. It updates RFC 5545. Its entire remark on
`UNTIL`, in §2.3.36, is one sentence:

> The UNTIL part in a VEVENT or VTODO converts to a LocalDateTime value relative
> to the timezone of the Event or Task object.

On the iCalendar side, RFC 5545 §3.3.10 says that when `DTSTART` is a date with
local time and time zone reference — the ordinary TZID form — the `UNTIL` rule
part **MUST** be a date with UTC time. So on one side `UNTIL` is an *instant*.

On the JSCalendar side, `jscalendarbis` §3.3.3 gives `until` the type
`LocalDateTime`, and §1.5.5 says the zone to associate with it comes from the
object's `timeZone`.
So on the other side `until` is a *wall-clock time in the event's zone*.

Converting an instant to a wall-clock time in a zone is not injective. In the
hour that a zone repeats at the end of daylight saving, two instants one hour
apart carry the same wall-clock label. Both specifications then resolve that
label the same way, and both resolve it to the earlier of the two:

- RFC 5545 §3.3.5: "If ... the local time described occurs more than once ... the
  DATE-TIME value refers to the first occurrence of the referenced time."
- `jscalendarbis` §1.5.5: "When converting local date-times that fall in the
  discontinuity to UTC, the offset before the transition MUST be used." (RFC 8984
  §1.4.5 is word for word the same.)

They agree, which is normally the good case. Here the agreement is what makes the
loss deterministic rather than implementation-dependent: **the round trip
`UNTIL` → `until` → `UNTIL` is a total function that moves the later of the two
instants one hour earlier, every time, in every conforming implementation.**

## A worked example

`Europe/Berlin` leaves daylight saving on 2024-10-27 at 01:00 UTC: local 03:00
CEST becomes local 02:00 CET, so local 02:00–02:59 happens twice.

```
DTSTART;TZID=Europe/Berlin:20241026T024500
RRULE:FREQ=DAILY;UNTIL=20241027T013000Z
```

The two generated instances are local 02:45 on the 26th and on the 27th. The
second is inside the repeated hour, so by §3.3.5 it is the first occurrence,
`2024-10-27T00:45:00Z`. `UNTIL` is inclusive and is `01:30Z`, so both instances
are in the recurrence set.

Now convert. `01:30Z` is after the transition, so in Berlin it is 02:30 CET, and
the JSCalendar event carries `"until": "2024-10-27T02:30:00"`. Convert back: the
local time 02:30 on that date occurs twice, the mandated resolution is the first
occurrence, and that is `00:30Z`. The rule is now

```
RRULE:FREQ=DAILY;UNTIL=20241027T003000Z
```

and the instance at `00:45Z` is past the end. **The recurrence set went from two
instances to one, and no property was dropped, unrecognised, or unconverted.**

Checked two ways. The reproducer derives every number from `zoneinfo` and the
quoted rules. Independently, `python-dateutil` 2.9.0.post0 expanding the two
rules against the same TZID-form `DTSTART` returns two instances for the original
`UNTIL` and one for the round-tripped one.

## Why this is worth saying now rather than filing as a bug

Three things make it specific to this document rather than to anybody's code.

**It is invisible to the document's own notion of losslessness.** §1.4, "Lossy
versus Lossless Conversion", is entirely about *element coverage*: whether an
element has a standard counterpart in the target format, and what to do when it
does not. `UNTIL` has a counterpart, the counterpart is used, and the conversion
is lossy anyway — because the two counterparts have different *value spaces*. The
word "ambiguous" does not appear in the draft outside a reference title, and
§2.3.36 says nothing about the repeated hour.

**The loss falls in the direction the document offers as the lossless use case.**
§1.4's example of lossless conversion is "an implementation that internally stores
calendar data in iCalendar format might want to convert without loss to
JSCalendar when updating calendar events with JMAP". That is exactly the
iCalendar-first direction. The reverse direction is safe: a JSCalendar `until`
already in the repeated hour converts to the first occurrence and converts back
to the same label, so it is the identity.

**The document already has the machinery to fix it.** For `DTEND`, where the same
shape of problem arises (a `DTEND` and a `duration` that are not distinguishable
after conversion), §2.3.14 has implementations record the original property under
`iCalendar`/`convertedProperties`. The same mechanism would preserve the original
`RRULE`. A normative note in §2.3.36 would also be enough for an implementer to
know the case exists.

## How rare

Narrow, and worth stating honestly. The `UNTIL` instant must land in the one
repeated hour per year per zone — about 0.011% of instants for a zone that
observes daylight saving, and never for a zone that does not — *and* the rule
must generate an instance in the hour between the original `UNTIL` and the
round-tripped one. Machine-generated `UNTIL` values are often synchronized with
the recurrence, which makes the second condition likelier than chance when the
first one holds, because a synchronized `UNTIL` sits exactly on an instance.

The reason to write it down anyway is that it is silent. Nothing rejects the
data, nothing warns, and the event simply ends one occurrence earlier.

## Relation to other findings

This is the third consequence of the same root that
[finding 006](006-dst-gap-and-repeat-instances.md) identified and
[finding 025](025-nonexistent-local-time-errata.md) supplied the authority for:
a local wall-clock label is not a name for an instant. 006 showed the RFC never
defines when two `DATE-TIME` values are duplicates; 025 showed that §3.3.10
contradicts itself about the gap and that a Verified errata decides it; this
finding shows that the *fold*, not the gap, is where an otherwise conforming
round trip quietly changes the recurrence set.
