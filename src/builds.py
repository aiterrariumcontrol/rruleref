"""Canonical display names for the measured builds.

The audit tools key their grids by short build ids (`ical4j430`, `libical_4edd`)
because those are directory and binary names. Anything written into `corpus/`
has to name the build the way `conformance/RESULTS.md` names it, or a reader
cannot line the two up. This module is the single place that mapping lives.

A build id that is not here is an error, not a pass-through: a silent rename is
how a witness list starts crediting the wrong version.
"""

#: short id (as used by the audit tools' grids) -> name as RESULTS.md prints it
DISPLAY = {
    "dateutil":     "python-dateutil 2.9.0.post0",
    "dmfs":         "dmfs lib-recur 0.17.1",
    "dtical":       "DateTime::Event::ICal 0.13",
    "ical4j411":    "ical4j 4.1.1",
    "ical4j430":    "ical4j 4.3.0",
    "icaljs":       "ical.js 2.2.1",
    "libical_3020": "libical 3.0.20",
    "libical_48d5": "libical master 48d52b4b",
    "libical_4edd": "libical master 4edd39a3",
    "rrulego":      "rrule-go 1.8.2",
    "rrulejs":      "rrule.js 2.8.1",
    "rustrrule":    "rust-rrule 0.14.0",
    "sabre":        "sabre/vobject 4.6.1",
}


class UnknownBuild(KeyError):
    pass


def display(build_id):
    """Name `build_id` as RESULTS.md names it. Raises on an unknown id."""
    try:
        return DISPLAY[build_id]
    except KeyError:
        raise UnknownBuild(
            "no display name for build id %r; add it to src/builds.py rather "
            "than letting the id through" % (build_id,))


def display_all(build_ids):
    """Sorted display names for an iterable of build ids."""
    return sorted(display(b) for b in build_ids)
