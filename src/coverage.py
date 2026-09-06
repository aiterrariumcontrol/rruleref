"""RFC 5545 3.3.10's own BYxxx/FREQ table, as a coverage model.

The corpus was grown by a random rule generator. That makes its contents an
accident of the seeds: "2541 corroborated cases" says how many cases exist,
not what they cover. This module replaces that with a statement, and it does
not invent the axes -- RFC 5545 3.3.10 prints a table of how each BYxxx rule
part behaves (Limit / Expand / N/A) for each FREQ value, plus two notes
splitting BYDAY further. That table is the coverage model.

It is extracted from the pinned RFC text by program rather than transcribed,
for the same reason src/vtimezone.py extracts its examples that way: a table
retyped by hand is a table that can quietly disagree with the spec.

Text: https://www.rfc-editor.org/rfc/rfc5545.txt
sha256 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

RFC = env.rfc_path("5545", require=False)

# The four BYDAY branches of Note 2, in the order the note states them, plus
# Note 1's two branches. Keys are the sub-cell ids used by the coverage report.
NOTE1 = ("MONTHLY/BYDAY+BYMONTHDAY", "MONTHLY/BYDAY-special-expand")
NOTE2 = ("YEARLY/BYDAY+BYYEARDAY-or-BYMONTHDAY",
         "YEARLY/BYDAY+BYWEEKNO",
         "YEARLY/BYDAY+BYMONTH",
         "YEARLY/BYDAY-plain")


def _rows(text):
    """Yield (part, [cell, ...]) for each data row of the printed table."""
    m = re.search(r"^\s*\|\s*\|SECONDLY\|.*$", text, re.M)
    if not m:
        raise RuntimeError("table header not found in RFC text")
    header = [c.strip() for c in m.group(0).strip().strip("|").split("|")][1:]
    out = []
    for line in text[m.end():].splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if s.startswith("Note 1:"):
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) != len(header) + 1 or not cells[0].startswith("BY"):
            continue
        out.append((cells[0], cells[1:]))
    return header, out


def table(path=RFC):
    """{(BYxxx, FREQ): 'Limit' | 'Expand' | 'N/A' | 'Note 1' | 'Note 2'}."""
    path = env.check(path, "5545")
    text = open(path, encoding="utf-8", errors="replace").read()
    freqs, rows = _rows(text)
    t = {}
    for part, cells in rows:
        for freq, cell in zip(freqs, cells):
            t[(part, freq)] = cell
    return freqs, [p for p, _ in rows], t


def cells(path=RFC):
    """Every coverage cell, with the two BYDAY notes expanded into branches.

    A cell is a (part, freq) pair the spec permits. N/A cells are excluded by
    construction: the spec says they MUST NOT be used, so an empty N/A cell is
    conformance, not a gap.
    """
    freqs, parts, t = table(path)
    out = []
    for part in parts:
        for freq in freqs:
            v = t[(part, freq)]
            if v == "N/A":
                continue
            if v == "Note 1":
                out.extend((part, freq, b) for b in NOTE1)
            elif v == "Note 2":
                out.extend((part, freq, b) for b in NOTE2)
            else:
                out.append((part, freq, v))
    return out


def classify(rule):
    """Which cells a single RRULE string exercises."""
    r = dict(kv.split("=", 1) for kv in rule.split(";") if "=" in kv)
    freq = r.get("FREQ")
    hit = []
    for part in ("BYMONTH", "BYWEEKNO", "BYYEARDAY", "BYMONTHDAY", "BYDAY",
                 "BYHOUR", "BYMINUTE", "BYSECOND", "BYSETPOS"):
        if part not in r:
            continue
        if part != "BYDAY" or freq not in ("MONTHLY", "YEARLY"):
            hit.append((part, freq, _plain(part, freq)))
        elif freq == "MONTHLY":
            hit.append((part, freq,
                        NOTE1[0] if "BYMONTHDAY" in r else NOTE1[1]))
        else:
            if "BYYEARDAY" in r or "BYMONTHDAY" in r:
                hit.append((part, freq, NOTE2[0]))
            elif "BYWEEKNO" in r:
                hit.append((part, freq, NOTE2[1]))
            elif "BYMONTH" in r:
                hit.append((part, freq, NOTE2[2]))
            else:
                hit.append((part, freq, NOTE2[3]))
    return hit


_T = None


def _plain(part, freq):
    global _T
    if _T is None:
        _T = table()[2]
    return _T.get((part, freq), "N/A")
