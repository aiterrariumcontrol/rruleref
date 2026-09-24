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
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
env.add_dateutil_to_path()

import builds
import datevalue
import grammar
import naive
import validity
from dateutil.rrule import rrulestr

N = 8
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
    NODE_DIR = env.node_dir(required=True)
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
console.log(JSON.stringify({
  now: fmt(new Date()),
  cases: cases.map(c => ({
    with_param: run(`DTSTART;VALUE=DATE:${c.dtstart}\\nRRULE:${c.rrule}`),
    bare: run(`DTSTART:${c.dtstart}\\nRRULE:${c.rrule}`),
  })),
}));
""" % N
    path = os.path.join(NODE_DIR, "datecases.js")
    with open(path, "w") as f:
        f.write(script)
    out = subprocess.run(["node", path], cwd=NODE_DIR, capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    got = json.loads(out.stdout)
    assert_clock_is_ahead(got["now"])
    for o in got["cases"]:
        o["clock_seeded"] = is_clock_seeded(o["with_param"], got["now"])
    return got["cases"]


CLOCK_SEEDED = {
    "clock_seeded": True,
    "note": ("rrule.js 2.8.1 accepts `DTSTART;VALUE=DATE:` without parsing the "
             "value and expands from the instant of the run instead. The "
             "occurrence list is therefore a function of the wall clock -- "
             "every field of it, down to the seconds -- so it is a property "
             "and not a value, and recording a sample of it made this file "
             "rebuild differently every day for no change in meaning. Rerun "
             "src/datevalue_cases.py to see the substitution happen."),
}


def is_clock_seeded(got, now):
    """Did rrule.js expand from the run instant instead of the case's DTSTART?

    Detected, not assumed. Every `DTSTART` in this file is a fixed constant
    (`BASE`, `LEAP`) and every honest expansion of one lands within a couple of
    years of it, so an occurrence dated on or after the run itself cannot have
    come from the case. The first attempt at this detector compared against the
    run's *date* and missed: the substituted start was 20:55 UTC and the rule's
    own `BYHOUR=9,17` pushed the first occurrence to 09:00 the next morning.
    `assert_clock_is_ahead` keeps the inequality from silently inverting.
    """
    return bool(got) and not got[0].startswith("ERROR:") and got[0][:8] >= now[:8]


def assert_clock_is_ahead(now):
    """The detector reads `>= now` as "not from the case". Check that holds."""
    latest = max(BASE, LEAP).strftime("%Y%m%d")
    if now[:8] <= latest:
        raise RuntimeError(
            "the run clock (%s) is not clearly after every DTSTART in this "
            "file (latest %s); _despatch_clock cannot tell a substituted start "
            "from a real occurrence and would mislabel one" % (now[:8], latest))


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


WITNESS_FILE = "findings/data/083-date-value-type-table.json"


def witnesses(path=WITNESS_FILE):
    """Which measured builds returned this file's own answer, per case index.

    `corroborated_by` is *provenance*: the two expanders that produced `expect`.
    The thirteen builds in `conformance/RESULTS.md` are the *subjects*, and
    putting a subject into the provenance field would make the corpus look as
    though it were built from the implementations it scores. So finding 083's
    measurement is attached under its own name, `reproduced_by`, and the two
    fields never mix.

    Returns {case index: [display name, ...]}, or {case index: None} where the
    case's rule cannot be posed on the conformance wire at all. That last part
    is a property of `conformance/PROTOCOL.md`, whose input line has no
    value-type field, and not of the case: a DATE-valued `UNTIL` beside a
    DATE-valued `DTSTART` is perfectly ordinary iCalendar.
    """
    if not os.path.exists(path):
        return {}
    table = json.load(open(path))
    out = {}
    for key, entry in table["detail"].items():
        if entry["form"] != "reduced":
            continue
        if entry["prohibited"]:
            names = None
        else:
            names = builds.display_all(b for b, status
                                       in table["grid"][key].items()
                                       if status == "D")
        for idx in entry["cases"]:
            assert idx not in out, "case %d reduced by two entries" % idx
            out[idx] = names
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
        # Score the raw output, then publish the property in place of it. The
        # sample drifts; the two questions asked of it do not. rrule.js gets
        # the *days* right on the two YEARLY rules even from a substituted
        # start, because BYYEARDAY and BYWEEKNO determine them without it --
        # dropping the sample before scoring would have silently thrown that
        # measurement away, and did, until this was caught.
        raw = {
            "python-dateutil-2.9.0": du,
            "rrule.js-2.8.1;VALUE=DATE": jsout["with_param"],
            "rrule.js-2.8.1 bare": jsout["bare"],
        }
        same_days = {k: _days(v) == expect for k, v in raw.items()}
        midnight_only = {k: _midnight_only(v) for k, v in raw.items()}
        observed = dict(raw)
        if jsout["clock_seeded"]:
            observed["rrule.js-2.8.1;VALUE=DATE"] = dict(CLOCK_SEEDED)
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
            "observed_same_days": same_days,
            "observed_midnight_only": midnight_only,
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
    seen = witnesses()
    for i, case in enumerate(cases):
        if i in seen:
            case["reproduced_by"] = seen[i]
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
            "reproduced_by": (
                "Measured builds that returned this case's `expect` when the "
                "reduced rule was posed on the conformance wire, from finding "
                "083. Evidence, NOT provenance: `corroborated_by` names the "
                "two expanders that produced `expect`, and these are the "
                "subjects `conformance/RESULTS.md` scores. Never merge the "
                "two fields. `null` means the case cannot be posed on that "
                "wire at all, because PROTOCOL.md's input line carries no "
                "value type -- a property of the harness, not of the case."),
            "reproduced_by_source": WITNESS_FILE,
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
    rep = [c.get("reproduced_by") for c in cases]
    print("reproduced_by: %d cases witnessed (%d..%d builds), %d not posable, "
          "%d absent"
          % (sum(1 for r in rep if r),
             min([len(r) for r in rep if r] or [0]),
             max([len(r) for r in rep if r] or [0]),
             sum(1 for r in rep if r is None),
             sum(1 for c in cases if "reproduced_by" not in c)))
    for k, (d, m) in sorted(bad.items()):
        print("  %-28s wrong days %d/%d, time parts not ignored %d/%d"
              % (k, d, len(cases), m, len(cases)))


if __name__ == "__main__":
    main()
