"""Systematic cases for a DATE-valued DTSTART, and what implementations do.

Writes `corpus/date-value-type.json`. Every case carries:

* `expect` -- the conformant expansion, as dates. Produced by `datevalue.expand`,
  which is `naive` plus the sec. 3.3.10 reduction (see `src/datevalue.py`).
* `reduced_rrule` -- the rule after the parts the RFC says MUST be ignored are
  dropped. Corroboration is done on *this* rule, at midnight, by
  `python-dateutil` exactly as for the rest of the corpus, so the expected
  values still do not come from a single expander. `corroborated_by` records it.
* `observed` -- what `python-dateutil` 2.9.0 and `rrule.js` 2.8.1 actually do
  when handed the DATE-valued start, and whether that matches `expect`.

The point of the file is the gap between the last two.
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")

import datevalue
import grammar
import naive
import validity
from dateutil.rrule import rrulestr

N = 8
NODE_DIR = "/home/agent/terrarium/scratch/rrulejs"
BASE = date(2026, 1, 5)          # a Monday
LEAP = date(2024, 2, 26)

#: (rrule, dtstart, why this case is here)
CASES = [
    # The MUST-ignore, one part at a time and all together.
    ("FREQ=DAILY;BYHOUR=9,17", BASE, "BYHOUR must be ignored"),
    ("FREQ=DAILY;BYMINUTE=30", BASE, "BYMINUTE must be ignored"),
    ("FREQ=DAILY;BYSECOND=15", BASE, "BYSECOND must be ignored"),
    ("FREQ=DAILY;BYHOUR=9,17;BYMINUTE=0,30;BYSECOND=15", BASE,
     "all three must be ignored; as written this is 12 instances a day"),
    ("FREQ=WEEKLY;BYDAY=MO,WE;BYHOUR=8", BASE,
     "the ignored part interacting with an expanding part"),
    ("FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1;BYHOUR=9", BASE,
     "BYSETPOS selects from the reduced set, not the expanded one"),
    # Conformant DATE rules across the frequencies a date can carry.
    ("FREQ=DAILY", BASE, "the plain case"),
    ("FREQ=DAILY;INTERVAL=3", BASE, "INTERVAL"),
    ("FREQ=WEEKLY;BYDAY=TU,TH", BASE, "WEEKLY expansion"),
    ("FREQ=WEEKLY;INTERVAL=2;WKST=SU;BYDAY=SU,SA", BASE, "WKST matters"),
    ("FREQ=MONTHLY;BYMONTHDAY=1,-1", BASE, "first and last of the month"),
    ("FREQ=MONTHLY;BYDAY=-1FR", BASE, "last Friday"),
    ("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29", LEAP, "leap day, skips years"),
    ("FREQ=YEARLY;BYYEARDAY=1,-1", BASE, "BYYEARDAY"),
    ("FREQ=YEARLY;BYWEEKNO=1,53;BYDAY=MO", BASE, "BYWEEKNO"),
    # COUNT and UNTIL. The DATE form of UNTIL is the grammar branch that no
    # DATE-TIME DTSTART can cover conformantly (src/enumerate_branches.py).
    ("FREQ=DAILY;COUNT=3", BASE, "COUNT"),
    ("FREQ=DAILY;UNTIL=20260108", BASE,
     "UNTIL as a DATE -- required here, prohibited with a DATE-TIME DTSTART"),
    ("FREQ=WEEKLY;BYDAY=MO;UNTIL=20260202", BASE, "DATE UNTIL, weekly"),
]

#: Combinations RFC 5545 does not define for a DATE-valued DTSTART. Recorded
#: with no expected value; see `datevalue.UndefinedForDateValue`.
UNDEFINED = [
    ("FREQ=HOURLY", BASE, "sub-daily FREQ: the RFC never connects FREQ to the "
                          "DTSTART value type"),
    ("FREQ=MINUTELY", BASE, "sub-daily FREQ"),
    ("FREQ=SECONDLY", BASE, "sub-daily FREQ"),
    ("FREQ=DAILY;UNTIL=20260108T000000Z", BASE,
     "UNTIL's value type differs from DTSTART's, which 3.3.10 forbids and "
     "gives no remedy for"),
]


def dateutil_observed(rrule, dtstart):
    """What python-dateutil does when handed the DATE-valued start itself."""
    try:
        it = rrulestr(rrule, dtstart=dtstart)
        out = []
        for i, x in enumerate(it):
            if i >= N:
                break
            out.append(x.strftime("%Y%m%dT%H%M%S"))
        return out
    except Exception as exc:                      # noqa: BLE001 - recorded, not raised
        return ["ERROR:%s" % exc]


def rrulejs_observed(cases):
    """rrule.js, in both spellings of a DATE-valued DTSTART.

    `DTSTART;VALUE=DATE:` is the spelling an iCalendar all-day event actually
    uses; `DTSTART:` with a date-shaped value is what survives if a caller
    strips the parameter.
    """
    payload = [{"rrule": r, "dtstart": datevalue.fmt(d)} for r, d, _ in cases]
    with open(os.path.join(NODE_DIR, "datecases.json"), "w") as f:
        json.dump(payload, f)
    script = """
const {rrulestr} = require('rrule');
const cases = require('./datecases.json');
const N = %d;
const fmt = d => d.toISOString().replace(/[-:]/g,'').replace(/\\.\\d+Z$/,'');
const run = (text) => { try {
    const r = rrulestr(text, {forceset:false});
    return r.all((d,i)=>i<N).map(fmt);
  } catch(e) { return ['ERROR:'+e.message]; } };
console.log(JSON.stringify(cases.map(c => ({
  with_param: run(`DTSTART;VALUE=DATE:${c.dtstart}\\nRRULE:${c.rrule}`),
  bare: run(`DTSTART:${c.dtstart}\\nRRULE:${c.rrule}`),
}))));
""" % N
    path = os.path.join(NODE_DIR, "datecases.js")
    with open(path, "w") as f:
        f.write(script)
    out = subprocess.run(["node", path], cwd=NODE_DIR, capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


def _days(out):
    """The distinct calendar dates of an observed DATE-TIME sequence, in order."""
    seen, days = set(), []
    for s in out:
        if s.startswith("ERROR:"):
            return out
        d = s[:8]
        if d not in seen:
            seen.add(d)
            days.append(d)
    return days


def _midnight_only(out):
    # An empty or failed result is not "conformant on the time parts"; without
    # this, a library that returns nothing scores a pass here.
    return bool(out) and all(not s.startswith("ERROR:") and s[9:] == "000000"
                             for s in out)


def corroborate(reduced, dtstart):
    """dateutil on the reduced rule at midnight -- the usual adjudication."""
    start = datetime.combine(dtstart, time(0, 0, 0))
    it = rrulestr(reduced, dtstart=start)
    out = []
    for i, x in enumerate(it):
        if i >= N:
            break
        out.append(x)
    return out


def build():
    cases, undefined = [], []
    js = rrulejs_observed(CASES)
    for (rule, ds, why), jsout in zip(CASES, js):
        reduced = datevalue.reduce_rule(rule)
        occ = datevalue.expand(rule, ds, limit=N)[:N]
        theirs = corroborate(reduced, ds)
        agree = [x.date() for x in theirs] == occ and all(
            x.time() == time(0, 0, 0) for x in theirs)
        expect = [datevalue.fmt(x) for x in occ]
        du = dateutil_observed(rule, ds)
        observed = {
            "python-dateutil-2.9.0": du,
            "rrule.js-2.8.1;VALUE=DATE": jsout["with_param"],
            "rrule.js-2.8.1 bare": jsout["bare"],
        }
        cases.append({
            "rrule": rule,
            "dtstart": datevalue.fmt(ds),
            "dtstart_value_type": "DATE",
            "why": why,
            "expect": expect,
            "ignored_parts": datevalue.ignored_parts(rule),
            "conformant_as_written": not datevalue.ignored_parts(rule),
            "reduced_rrule": reduced,
            "reduction": ("RFC 5545 3.3.10: BYSECOND, BYMINUTE and BYHOUR "
                          "MUST be ignored when DTSTART has a DATE value type"),
            "rule_valid": validity.is_valid(rule),
            "branches": sorted(grammar.classify(rule)),
            "corroborated_by": (["naive-bruteforce",
                                 "python-dateutil-2.9.0 (on reduced_rrule, "
                                 "at 00:00:00)"] if agree else []),
            "observed": observed,
            # Two separate questions, kept separate on purpose. Every
            # implementation here returns DATE-TIMEs, because none of them
            # models the DATE value type at all -- comparing their output to
            # `expect` verbatim would only be measuring that. `same_days` asks
            # whether the recurrence *set* is right; `midnight_only` asks
            # whether the time parts were ignored as 3.3.10 requires. A case is
            # expanded conformantly only if both hold.
            "observed_same_days": {k: _days(v) == expect
                                   for k, v in observed.items()},
            "observed_midnight_only": {k: _midnight_only(v)
                                       for k, v in observed.items()},
        })
    for rule, ds, why in UNDEFINED:
        try:
            datevalue.expand(rule, ds, limit=N)
            raise AssertionError("expected UndefinedForDateValue: %s" % rule)
        except datevalue.UndefinedForDateValue as exc:
            undefined.append({"rrule": rule, "dtstart": datevalue.fmt(ds),
                              "dtstart_value_type": "DATE", "why": why,
                              "refused": str(exc),
                              "observed": {"python-dateutil-2.9.0":
                                           dateutil_observed(rule, ds)}})
    return cases, undefined


def main():
    cases, undefined = build()
    branches = sorted({b for c in cases for b in c["branches"]})
    doc = {
        "meta": {
            "about": "RFC 5545 recurrence with a DATE-valued DTSTART.",
            "cases": len(cases),
            "undefined": len(undefined),
            "occurrences_per_case": N,
            "reduction": ("Expected values are the DATE-TIME expansion of "
                          "reduced_rrule at 00:00:00, projected onto dates. "
                          "The reduction is RFC 5545 3.3.10's own remedy for "
                          "BYSECOND/BYMINUTE/BYHOUR under a DATE-valued "
                          "DTSTART; it does not exist in RFC 2445."),
        },
        "branches": branches,
        "cases": cases,
        "undefined": undefined,
    }
    with open("corpus/date-value-type.json", "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    bad = {k: (sum(1 for c in cases if not c["observed_same_days"][k]),
               sum(1 for c in cases if not c["observed_midnight_only"][k]))
           for k in cases[0]["observed_same_days"]}
    print("cases=%d undefined=%d branches=%d" % (len(cases), len(undefined),
                                                 len(branches)))
    print("uncorroborated=%d" % sum(1 for c in cases if not c["corroborated_by"]))
    for k, (d, m) in sorted(bad.items()):
        print("  %-28s wrong days %d/%d, time parts not ignored %d/%d"
              % (k, d, len(cases), m, len(cases)))


if __name__ == "__main__":
    main()
