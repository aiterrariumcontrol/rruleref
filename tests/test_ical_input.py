"""`web/src/icalinput.js` must read a pasted calendar event the way a calendar does.

This file exists because the input box now accepts something the rest of the
project never had to parse: whatever the user had lying around. That is a
wider contract than "a rule string", and it has failure modes that are silent
by construction -- a dropped TZID, a truncated folded line, or an RRULE picked
out of the wrong component all produce a plausible list of dates that is
simply not the user's event.

The case that motivated the component-stack logic is `vtimezone_trap`: a real
VCALENDAR carries a VTIMEZONE whose STANDARD and DAYLIGHT subcomponents hold
their own DTSTART *and their own RRULE*, describing daylight-saving
transitions. "The first RRULE in the text" is that one, not the event's.

Skips, loudly, when node is not installed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOD = os.path.join(ROOT, "web", "src", "icalinput.js")

fails = []

VEVENT = (
    "BEGIN:VCALENDAR\r\n"
    "BEGIN:VTIMEZONE\r\nTZID:Europe/Paris\r\n"
    "BEGIN:DAYLIGHT\r\nDTSTART:19700329T020000\r\n"
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU\r\nEND:DAYLIGHT\r\n"
    "END:VTIMEZONE\r\n"
    "BEGIN:VEVENT\r\nDTSTART;TZID=Europe/Paris:20260210T090000\r\n"
    "RRULE:FREQ=WEEKLY;BYDAY=TU\r\nSUMMARY:standup\r\nEND:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)

# name, input, expected rrule, expected dtstart, substrings required in notes
CASES = [
    ("bare_rule_unchanged", "FREQ=MONTHLY;BYDAY=-1FR", "FREQ=MONTHLY;BYDAY=-1FR", "", []),
    ("bare_rule_with_wkst", "FREQ=WEEKLY;WKST=SU;BYDAY=TU,SU",
     "FREQ=WEEKLY;WKST=SU;BYDAY=TU,SU", "", []),
    ("prefixed_rule", "RRULE:FREQ=DAILY;COUNT=3", "FREQ=DAILY;COUNT=3", "", ["No DTSTART"]),
    ("folded_line",
     "DTSTART:20260101T090000\r\nRRULE:FREQ=MONT\r\n HLY;BYDAY=-1FR",
     "FREQ=MONTHLY;BYDAY=-1FR", "20260101T090000", []),
    ("folded_with_tab",
     "DTSTART:20260101T090000\r\nRRULE:FREQ=DAI\r\n\tLY;COUNT=2",
     "FREQ=DAILY;COUNT=2", "20260101T090000", []),
    ("vtimezone_trap", VEVENT, "FREQ=WEEKLY;BYDAY=TU", "20260210T090000",
     ["TZID=Europe/Paris"]),
    ("value_date", "DTSTART;VALUE=DATE:20260101\r\nRRULE:FREQ=DAILY;COUNT=3",
     "FREQ=DAILY;COUNT=3", "20260101", []),
    ("tzid_with_until",
     "DTSTART;TZID=Europe/Paris:20260101T090000\r\nRRULE:FREQ=DAILY;UNTIL=20260301T000000Z",
     "FREQ=DAILY;UNTIL=20260301T000000Z", "20260101T090000",
     ["MUST be specified as a date with UTC time"]),
    ("exdate_is_reported",
     "BEGIN:VEVENT\r\nDTSTART:20260101T090000\r\nRRULE:FREQ=DAILY\r\n"
     "EXDATE:20260102T090000\r\nSUMMARY:x\r\nEND:VEVENT",
     "FREQ=DAILY", "20260101T090000", ["EXDATE"]),
    ("rdate_is_reported",
     "DTSTART:20260101T090000\r\nRRULE:FREQ=DAILY\r\nRDATE:20260115T090000",
     "FREQ=DAILY", "20260101T090000", ["RDATE"]),
    ("two_events_refused",
     "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nRRULE:FREQ=DAILY\r\nEND:VEVENT\r\n"
     "BEGIN:VEVENT\r\nRRULE:FREQ=WEEKLY\r\nEND:VEVENT\r\nEND:VCALENDAR",
     "", "", ["will not guess which one"]),
    ("quoted_param_colon",
     'DTSTART;TZID="Odd:Zone":20260101T090000\r\nRRULE:FREQ=DAILY;COUNT=2',
     "FREQ=DAILY;COUNT=2", "20260101T090000", ["Odd:Zone"]),
    ("utc_dtstart", "DTSTART:20260101T090000Z\r\nRRULE:FREQ=DAILY;COUNT=2",
     "FREQ=DAILY;COUNT=2", "20260101T090000Z", ["UTC"]),
    ("two_rrules_first_wins",
     "DTSTART:20260101T090000\r\nRRULE:FREQ=DAILY\r\nRRULE:FREQ=WEEKLY",
     "FREQ=DAILY", "20260101T090000", ["only the first"]),
]

DRIVER = """
import fs from "node:fs";
const { parseInput } = await import(process.argv[2]);
const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const out = cases.map(c => {
  try {
    const r = parseInput(c.input);
    return { name: c.name, rrule: r.rrule || "", dtstart: r.dtstart || "",
             notes: (r.notes || []).map(n => (n.title || "") + " " + (n.text || "")) };
  } catch (e) { return { name: c.name, error: String(e && e.message || e) }; }
});
process.stdout.write(JSON.stringify(out));
"""


def main():
    tmp = tempfile.mkdtemp()
    dpath = os.path.join(tmp, "d.mjs")
    cpath = os.path.join(tmp, "cases.json")
    open(dpath, "w").write(DRIVER)
    json.dump([{"name": n, "input": i} for n, i, _, _, _ in CASES], open(cpath, "w"))
    r = subprocess.run(["node", dpath, MOD, cpath], capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("driver failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return
    got = {g["name"]: g for g in json.loads(r.stdout)}

    for name, _inp, want_rrule, want_dtstart, want_notes in CASES:
        g = got.get(name)
        if g is None:
            fails.append("%s: no result" % name)
            continue
        if "error" in g:
            fails.append("%s: threw %s" % (name, g["error"]))
            continue
        if g["rrule"] != want_rrule:
            fails.append("%s: rrule %r, expected %r" % (name, g["rrule"], want_rrule))
        if g["dtstart"] != want_dtstart:
            fails.append("%s: dtstart %r, expected %r" % (name, g["dtstart"], want_dtstart))
        blob = " || ".join(g["notes"])
        for frag in want_notes:
            if frag not in blob:
                fails.append("%s: expected a note containing %r; notes were %r"
                             % (name, frag, g["notes"]))
    if not fails:
        print("  ical input: %d paste shapes parsed as expected" % len(CASES))


def test_the_rrule_the_expander_gets_is_the_events():
    """End to end: the VEVENT above must expand to Tuesdays, not to March DST."""
    driver = """
const { parseInput } = await import(process.argv[2]);
const { expand, parse, parseDtstart, fmt } = await import(process.argv[3]);
const r = parseInput(process.argv[4]);
const ds = parseDtstart(r.dtstart);
const occ = expand(parse(r.rrule), ds.t, { limit: 3, maxSteps: 1e6 });
process.stdout.write(JSON.stringify(occ.map(t => fmt(t, ds.dateOnly))));
"""
    tmp = tempfile.mkdtemp()
    dpath = os.path.join(tmp, "e.mjs")
    open(dpath, "w").write(driver)
    r = subprocess.run(["node", dpath, MOD,
                        os.path.join(ROOT, "web", "src", "naive.js"), VEVENT],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("end-to-end driver failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return
    occ = json.loads(r.stdout)
    want = ["20260210T090000", "20260217T090000", "20260224T090000"]
    if occ != want:
        fails.append("pasted VEVENT expanded to %r, expected %r (the VTIMEZONE's "
                     "DST rule would give March Sundays)" % (occ, want))
    else:
        print("  ical input: a pasted VCALENDAR expands to the event's rule, not the zone's")


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the input parser is unchecked")
        raise SystemExit(0)
    main()
    test_the_rrule_the_expander_gets_is_the_events()
    for f in fails:
        print("FAIL " + f)
    raise SystemExit(1 if fails else 0)
