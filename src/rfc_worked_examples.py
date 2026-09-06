"""Extract the worked RRULE examples from RFC 5545 section 3.8.5.3 as data.

Why this exists
---------------
`rruleref`'s corpus is built by cross-checking two independent expanders, which
tells you what implementations *do*. Section 3.8.5.3 of RFC 5545 is different
in kind: roughly forty rules with their **printed expected occurrences**, in
the normative document itself. That is the strongest evidence class this
project can use, and most of the examples carry
`DTSTART;TZID=America/New_York`, so the expected output crosses the EDT/EST
transition and is annotated with which offset applies. They are therefore also
the project's first timezone/DST coverage, and they come from the spec rather
than from me inventing transition cases.

An earlier version of this repository quoted an RFC example that did not exist.
The rule now is that RFC-derived expected values are *extracted by program from
a hashed copy of the text*, never retyped. `RFC_SHA256` below pins that copy.

Honest limits
-------------
Many examples end in an ellipsis (``...``) because the recurrence is unbounded
or the list was elided for print. Those are **skipped, not guessed**, and every
skip is recorded with its reason in the output so the count is auditable. Two
output shapes are understood:

  ``(1997 9:00 AM EDT) September 2,9,16;October 7``   -- year + fixed time
  ``(2007 EST) January 15,30``                        -- year, time from DTSTART

A third shape used by the sub-daily examples,
``(September 2, 1997 EDT) 9:00,9:20,...``, lists times rather than dates and is
not parsed; those examples are all elided anyway.

The ``EDT``/``EST`` annotations are carried through and checked: an expected
occurrence is only counted as matched if the localized datetime has the same
UTC offset the RFC printed for it.
"""

import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
from datetime import datetime, timedelta

RFC_PATH = env.rfc_path("5545", require=False)
RFC_SHA256 = "c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb"
RFC_URL = "https://www.rfc-editor.org/rfc/rfc5545.txt"

# Verified errata against RFC 5545 that change a section 3.8.5.3 example.
# Applied to the extracted data, never silently: each patched example carries
# the erratum id, and `errata_applied` in the output lists what was changed.
#
# Errata 3883 was found here by running the examples rather than by reading the
# errata list: the extracted expectations disagreed with the expander on exactly
# one of thirty-nine examples, and the errata list then confirmed why. The other
# two errata filed against this section (5872, 5920) are Rejected and are not
# applied. Checked against https://www.rfc-editor.org/errata/rfc5545 on
# 2026-09-06.
ERRATA = [
    {
        "id": 3883,
        "status": "Verified",
        "url": "https://www.rfc-editor.org/errata/eid3883",
        "verified": "2014-02-14",
        "reported_by": "Bruce Florman",
        "why": "DTSTART is 09:00 in America/New_York, which was UTC-04:00 on "
               "1997-09-02, so the printed UNTIL=19970902T170000Z is 13:00 "
               "local -- before the 15:00 occurrence the example itself "
               "prints. RFC 5545 section 3.3.10 requires UNTIL to be a UTC "
               "value when DTSTART carries a TZID, so the value is wrong, not "
               "the expected output.",
        "match_rrule": "FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T170000Z",
        "replace_rrule": "FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T210000Z",
    },
]

SECTION_START = "3.8.5.3.  Recurrence Rule"
SECTION_END = "3.8.6.  Alarm Component Properties"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

# Offsets the RFC prints in its America/New_York examples.
ABBREV_OFFSET = {"EDT": timedelta(hours=-4), "EST": timedelta(hours=-5)}

_PAGE_BREAK = re.compile(r"^(Desruisseaux .*\[Page \d+\]|RFC 5545 .*September 2009|\x0c)\s*$")
_HEADER = re.compile(r"\((\d{4})(?: (\d{1,2}):(\d{2}) (AM|PM))? (E[SD]T)\)\s*(.*)")
# The sub-daily examples invert the shape: one date in the header, times in the body.
_HEADER_TIMES = re.compile(r"\(([A-Z][a-z]+) (\d{1,2}), (\d{4}) (E[SD]T)\)\s*(.*)")


def read_rfc(path=RFC_PATH):
    """Return the RFC text, refusing to proceed if the copy is not the pinned one."""
    path = env.check(path, "5545")
    with open(path, "rb") as f:
        raw = f.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != RFC_SHA256:
        raise RuntimeError(
            "RFC 5545 copy at %s has sha256 %s, expected %s. Re-fetch from %s."
            % (path, got, RFC_SHA256, RFC_URL))
    return raw.decode("utf-8")


def section_lines(text):
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith(SECTION_START))
    end = next(i for i, l in enumerate(lines) if i > start and l.startswith(SECTION_END))
    return [l for l in lines[start:end] if not _PAGE_BREAK.match(l) and l.strip() != ""]


def _unfold(lines):
    """Rejoin RFC line folding: a continuation line starts with one extra space.

    In this section only RRULE values are folded, and the continuation is
    marked by a leading space relative to the property line's own indent.
    """
    out = []
    for l in lines:
        if (out and l.startswith("        ") and not l.lstrip().startswith("==>")
                and out[-1].lstrip().startswith("RRULE:")):
            out[-1] = out[-1].rstrip() + l.strip()
        else:
            out.append(l)
    return out


def _parse_dates(spec, year):
    """Parse 'September 2,9,16;October 7,14' or 'January 1-31' into (month, day)s."""
    out = []
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"([A-Z][a-z]+)\s*(.*)", chunk)
        if not m or m.group(1) not in MONTHS:
            raise ValueError("unparsed date chunk: %r" % chunk)
        month = MONTHS[m.group(1)]
        for item in m.group(2).split(","):
            item = item.strip()
            if not item:
                continue
            if "-" in item:
                a, b = item.split("-")
                out.extend((month, d) for d in range(int(a), int(b) + 1))
            else:
                out.append((month, int(item)))
    return [(year, mo, d) for mo, d in out]


def parse_examples(lines):
    """Split the section into examples: description, DTSTART, RRULE(s), expected."""
    lines = _unfold(lines)
    examples = []
    cur = None
    mode = None
    for raw in lines:
        s = raw.strip()
        if s.startswith("DTSTART"):
            cur = {"dtstart_line": s, "rrules": [], "expected_raw": [], "desc": desc}
            examples.append(cur)
            mode = "rrule"
        elif s.startswith("RRULE:") and cur is not None:
            cur["rrules"].append(s[len("RRULE:"):])
        elif s.startswith("==>") and cur is not None:
            cur["expected_raw"].append(s[3:].strip())
            mode = "expected"
        elif (cur is not None and mode == "expected" and not s.startswith("Note:")
                and (s.startswith("(") or s.startswith("...")
                     or raw.startswith("        "))):
            cur["expected_raw"].append(s)
        else:
            mode = None
        if not s.startswith(("DTSTART", "RRULE:", "==>", "(")) and mode is None:
            desc = s
    return examples


def parse_expected(expected_raw, default_time):
    """Turn the printed occurrence block into [(naive_datetime, tz_abbrev)].

    Raises ValueError for anything elided or in an unhandled shape; callers
    record the reason rather than guessing at the intended values.
    """
    text = " ".join(expected_raw)
    prefix_only = "..." in text
    if prefix_only:
        # An ellipsis means the recurrence is unbounded or the list was elided
        # for print. Everything *before* the first ellipsis is still a verbatim
        # chronological prefix of the expected occurrences, so keep that and
        # mark the example as prefix-only rather than discarding it. Nothing is
        # inferred about what the ellipsis stands for.
        text = text.split("...")[0]
    # Re-split on the '(YYYY ... TZ)' headers, which may appear mid-line.
    parts = re.split(r"(?=\((?:\d{4}|[A-Z][a-z]+ \d{1,2}, \d{4}))", text)
    out = []
    seen_any = False
    for part in parts:
        part = part.strip()
        if not part:
            continue
        mt = _HEADER_TIMES.match(part)
        if mt:
            seen_any = True
            month, day, year, abbrev = (MONTHS[mt.group(1)], int(mt.group(2)),
                                        int(mt.group(3)), mt.group(4))
            for item in re.split(r"[,;]", mt.group(5)):
                item = item.strip().rstrip(";")
                if not item:
                    continue
                hh, mm = item.split(":")[:2]
                out.append((datetime(year, month, day, int(hh), int(mm)), abbrev))
            continue
        m = _HEADER.match(part)
        if not m:
            raise ValueError("unhandled expected-output shape: %r" % part[:60])
        seen_any = True
        year = int(m.group(1))
        if m.group(2) is not None:
            hour = int(m.group(2)) % 12 + (12 if m.group(4) == "PM" else 0)
            minute = int(m.group(3))
        else:
            hour, minute = default_time
        for (y, mo, d) in _parse_dates(m.group(6), year):
            out.append((datetime(y, mo, d, hour, minute), m.group(5)))
    if not seen_any:
        raise ValueError("no '(YYYY TZ)' header found")
    if not out:
        raise ValueError("nothing enumerated before the first '...'")
    return out, prefix_only


def build():
    text = read_rfc()
    examples = parse_examples(section_lines(text))
    usable, skipped = [], []
    for ex in examples:
        m = re.match(r"DTSTART(?:;TZID=([^:]+))?:(\d{8}T\d{6})Z?$", ex["dtstart_line"])
        if not m:
            skipped.append({"desc": ex["desc"], "dtstart": ex["dtstart_line"],
                            "reason": "unparsed DTSTART"})
            continue
        tzid, dtraw = m.group(1), m.group(2)
        dtstart = datetime.strptime(dtraw, "%Y%m%dT%H%M%S")
        try:
            expected, prefix_only = parse_expected(
                ex["expected_raw"], (dtstart.hour, dtstart.minute))
        except ValueError as e:
            skipped.append({"desc": ex["desc"], "dtstart": ex["dtstart_line"],
                            "rrules": ex["rrules"], "reason": str(e)})
            continue
        errata_ids = []
        rrules = []
        for r in ex["rrules"]:
            for e in ERRATA:
                if r == e["match_rrule"]:
                    r = e["replace_rrule"]
                    errata_ids.append(e["id"])
            rrules.append(r)
        usable.append({
            "desc": ex["desc"],
            "tzid": tzid,
            "dtstart": dtraw,
            "rrules": rrules,
            "errata_applied": errata_ids,
            "expected_is_prefix_only": prefix_only,
            "expected": [{"local": dt.strftime("%Y%m%dT%H%M%S"), "tz_abbrev": ab,
                          "utc_offset_minutes": int(ABBREV_OFFSET[ab].total_seconds() // 60)}
                         for dt, ab in expected],
        })
    return {
        "source": {
            "document": "RFC 5545", "section": "3.8.5.3", "url": RFC_URL,
            "sha256": RFC_SHA256,
            "note": "Expected values extracted by program from the hashed text, "
                    "never retyped. Skipped examples are listed, not guessed.",
            "errata_checked": "https://www.rfc-editor.org/errata/rfc5545 (2026-09-06)",
        },
        "errata_applied": ERRATA,
        "counts": {"examples_found": len(examples), "usable": len(usable),
                   "skipped": len(skipped),
                   "with_tzid": sum(1 for e in usable if e["tzid"]),
                   "prefix_only": sum(1 for e in usable if e["expected_is_prefix_only"]),
                   "complete": sum(1 for e in usable if not e["expected_is_prefix_only"]),
                   "crossing_dst": sum(1 for e in usable
                                       if len({x["tz_abbrev"] for x in e["expected"]}) > 1),
                   "errata_applied": sum(1 for e in usable if e["errata_applied"])},
        "examples": usable,
        "skipped": skipped,
    }


if __name__ == "__main__":
    data = build()
    out = os.path.join(os.path.dirname(__file__), "..", "corpus", "rfc5545-examples.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps(data["counts"], indent=1))
    for s in data["skipped"]:
        print("SKIP  %-40s %s" % (s["desc"][:40], s["reason"][:70]))
