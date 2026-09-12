#!/usr/bin/env python3
"""026 — iCalendar UNTIL -> JSCalendar "until" -> iCalendar UNTIL is not the identity.

Derivation only: no calendar library is used, and no implementation is under test.
The two conversion steps are the ones the specifications mandate:

  iCalendar -> JSCalendar   draft-ietf-calext-jscalendar-icalendar-26 section 2.3.36:
        "The UNTIL part in a VEVENT or VTODO converts to a LocalDateTime value
         relative to the timezone of the Event or Task object."
  JSCalendar -> iCalendar   RFC 5545 section 3.3.10: with a TZID-form DTSTART the
        UNTIL part MUST be a date with UTC time, so the LocalDateTime must be
        resolved against the event timezone.  draft-ietf-calext-jscalendarbis-19
        section 1.5.5 (== RFC 8984 section 1.4.5) and RFC 5545 section 3.3.5 both
        resolve a repeated local time to the offset BEFORE the transition (the
        "first occurrence").

Requires only the standard library and a tz database (zoneinfo).
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
UTC = timezone.utc


def ical_to_jscalendar(until_utc):
    """UNTIL (a UTC instant) -> JSCalendar LocalDateTime in the event timezone."""
    return until_utc.astimezone(TZ).replace(tzinfo=None)


def jscalendar_to_ical(until_local):
    """JSCalendar LocalDateTime -> UNTIL, resolving a repeated local time to the
    offset before the transition (RFC 8984 1.4.5 == RFC 5545 3.3.5 first occurrence)."""
    return until_local.replace(tzinfo=TZ, fold=0).astimezone(UTC)


def instances(dtstart_local, count):
    """FREQ=DAILY from a TZID-form DTSTART, as instants, resolving each generated
    local time per RFC 5545 3.3.5 (first occurrence when repeated)."""
    out = []
    for i in range(count):
        local = dtstart_local + timedelta(days=i)
        out.append((local, local.replace(tzinfo=TZ, fold=0).astimezone(UTC)))
    return out


def fmt_utc(d):
    return d.strftime("%Y%m%dT%H%M%SZ")


def main():
    dtstart = datetime(2024, 10, 26, 2, 45)
    until = datetime(2024, 10, 27, 1, 30, tzinfo=UTC)

    print("DTSTART;TZID=Europe/Berlin:%s" % dtstart.strftime("%Y%m%dT%H%M%S"))
    print("RRULE:FREQ=DAILY;UNTIL=%s" % fmt_utc(until))
    print()

    inst = instances(dtstart, 2)
    print("generated instances (local -> instant):")
    for local, utc in inst:
        print("  %s %-5s -> %s" % (local.isoformat(), local.replace(tzinfo=TZ, fold=0).tzname(), utc.isoformat()))
    print()

    kept_before = [u for _, u in inst if u <= until]
    print("UNTIL is inclusive, so before conversion the recurrence set has %d instance(s)."
          % len(kept_before))
    print()

    local_until = ical_to_jscalendar(until)
    print('iCalendar -> JSCalendar:  "until": "%s"' % local_until.isoformat())
    back = jscalendar_to_ical(local_until)
    print("JSCalendar -> iCalendar:  UNTIL=%s" % fmt_utc(back))
    print()

    kept_after = [u for _, u in inst if u <= back]
    print("after the round trip the recurrence set has %d instance(s)." % len(kept_after))
    print()

    assert back != until, "round trip was the identity; the example is wrong"
    print("UNTIL moved %s earlier." % (until - back))
    lost = [u for u in kept_before if u not in kept_after]
    print("instances lost: %s" % ", ".join(u.isoformat() for u in lost))

    # The two instants that collide on one LocalDateTime.
    a = datetime(2024, 10, 27, 0, 30, tzinfo=UTC)
    b = datetime(2024, 10, 27, 1, 30, tzinfo=UTC)
    assert ical_to_jscalendar(a) == ical_to_jscalendar(b)
    print()
    print("cause: %s and %s are distinct instants one hour apart that both convert to"
          % (fmt_utc(a), fmt_utc(b)))
    print("       the single LocalDateTime %s; the map is not injective on the"
          % ical_to_jscalendar(a).isoformat())
    print("       repeated local hour, and the inverse mandated by both RFCs picks the first.")


if __name__ == "__main__":
    main()
