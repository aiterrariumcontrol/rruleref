#!/usr/bin/env python3
"""Finding 105 -- reproducer.

ical.js, FREQ=MONTHLY with a BYDAY-derived day set and a NEGATIVE BYSETPOS:
when the selected occurrence is day 1 of the month, the whole month is dropped.

MECHANISM (recur_iterator.js, next_month(), the BYDAY branch).
The in-month scan tests BOTH set-position spellings:

    if (!this.has_by_data("BYSETPOS") ||
        this.check_set_position(++setpos) ||
        this.check_set_position(setpos - setpos_total - 1)) {

The month-rollover path that follows tests only the POSITIVE one:

    if (day > daysInMonth) {
      this.last.day = 1;
      this.increment_month();
      if (this.is_day_in_byday(this.last)) {
        if (!this.has_by_data("BYSETPOS") || this.check_set_position(1)) {

Day 1 of a month, when it is in the BYDAY set, is always set position 1, whose
negative spelling is -n for a set of size n. The rollover path never computes
setpos_total for the new month and never tests -n, so a rule that names day 1
only negatively is rejected and the month is skipped entirely.

PREDICTOR (exact, over every probe below): ical.js omits month M iff
  * M is not the DTSTART month (the rollover path is unreachable there), and
  * day 1 of M is in the BYDAY-derived set S(M), and
  * BYSETPOS contains -|S(M)| and does not contain 1.

The second clause is why an ordinal token such as 2SA is immune and 1SA is not;
the third is why BYSETPOS=1,-2 is correct where BYSETPOS=-2 is not, selecting
the same dates.

Read-only. Runs the icaljs and dateutil adapters; writes nothing.
"""
import calendar
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTERS = {
    "dateutil": ["python3", os.path.join(ROOT, "conformance/adapters/dateutil_adapter.py")],
    "icaljs": ["node", os.path.join(ROOT, "conformance/adapters/icaljs_adapter.js")],
}
WD = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

# The corpus case this finding closes: the last id on finding 074's residual.
CORPUS_ID = "d27c58ae379a"
DTSTART = "20270102T090000"


def ask(adapter, rule, dtstart=DTSTART, limit=60):
    payload = json.dumps({"id": "x", "dtstart": dtstart, "rrule": rule, "limit": limit})
    proc = subprocess.run(ADAPTERS[adapter], input=payload + "\n",
                          capture_output=True, text=True, cwd=ROOT)
    out = proc.stdout.strip().splitlines()
    if not out:
        raise SystemExit(f"{adapter} produced no output for {rule}: {proc.stderr[:400]}")
    r = json.loads(out[-1])
    if r.get("error"):
        raise SystemExit(f"{adapter} errored on {rule}: {r['error']}")
    return r.get("occurrences") or []


def day_set(year, month, byday):
    """The BYDAY-derived day-of-month set for one month, as ical.js builds it."""
    n = calendar.monthrange(year, month)[1]
    days = set()
    for tok in byday.split(","):
        weekday = WD[tok[-2:]]
        matching = [d for d in range(1, n + 1)
                    if datetime.date(year, month, d).weekday() == weekday]
        if len(tok) > 2:
            i = int(tok[:-2])
            days.add(matching[i - 1] if i > 0 else matching[i])
        else:
            days.update(matching)
    return sorted(days)


def predict_dropped(byday, setpos, start, n_months):
    """Months the predictor says ical.js will omit, as YYYYMM01 strings."""
    year, month = start
    dropped = []
    for k in range(n_months):
        if k > 0:  # the DTSTART month never goes through the rollover path
            s = day_set(year, month, byday)
            if s and s[0] == 1 and (-len(s)) in setpos and 1 not in setpos:
                dropped.append(f"{year}{month:02d}01")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return dropped


# (byday, bysetpos, why this probe is here)
PROBES = [
    ("3FR,1SA", [-2],
     "the corpus case d27c58ae379a: 1SA is day 1 whenever the month starts Saturday"),
    ("3FR,1WE", [-2],
     "same shape, different weekday -- the trigger is day 1, not Saturday"),
    ("2FR,1SA", [-2],
     "moving the OTHER token changes nothing; 1SA is what matters"),
    ("MO,TU", [-9],
     "unprefixed BYDAY, set size varies: only the 9-member months drop"),
    ("MO,TU", [-8],
     "same rule at -8: a different, disjoint set of months drops"),
    ("MO,WE,FR", [-13],
     "three-token set, size 12-14: only the 13-member months drop"),
    # Controls that must come out CLEAN.
    ("3FR,2SA", [-2],
     "CONTROL: 2SA is never day 1, so nothing is dropped"),
    ("3FR,1SA", [1],
     "CONTROL: the positive spelling of the same selection is handled"),
    ("1SA,3FR", [1, -2],
     "CONTROL: adding the positive spelling to the failing rule repairs it"),
    ("MO,TU", [-1],
     "CONTROL: -1 is never position 1 in a ~9-member set, so no month drops"),
]


def main():
    print(f"finding 105 -- ical.js FREQ=MONTHLY negative BYSETPOS on day 1 of the month")
    print(f"corpus case: {CORPUS_ID}  DTSTART={DTSTART}\n")
    failures = []
    for byday, setpos, why in PROBES:
        rule = f"FREQ=MONTHLY;BYDAY={byday};BYSETPOS={','.join(map(str, setpos))}"
        ref = ask("dateutil", rule)
        got = ask("icaljs", rule)
        # Compare only inside the span both sides reached, so that ical.js's
        # separate first-period defect (finding 004) cannot masquerade as a
        # dropped month by sliding the limit window.
        span = min(ref[-1], got[-1]) if ref and got else ""
        actual = [x[:8] for x in ref if x not in got and x <= span]
        predicted = [p for p in predict_dropped(byday, setpos, (2027, 1), 130) if p <= span[:8]]
        ok = predicted == actual
        if not ok:
            failures.append(rule)
        print(f"{'ok  ' if ok else 'FAIL'} {rule}")
        print(f"       {why}")
        print(f"       predicted {len(predicted)} dropped: {predicted[:6]}"
              f"{' ...' if len(predicted) > 6 else ''}")
        print(f"       actual    {len(actual)} dropped: {actual[:6]}"
              f"{' ...' if len(actual) > 6 else ''}")

    print("\nfield agreement on the corpus rule "
          "(FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2):")
    print("  4 of 4 other adapters that build here -- dateutil, rrule.js, sabre,")
    print("  dmfs -- agree with each other and disagree with ical.js. Verified at")
    print("  wake 153; re-run with --field to check again.")
    if "--field" in sys.argv:
        base = "FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2"
        others = {
            "rrulejs": ["node", os.path.join(ROOT, "conformance/adapters/rrulejs_adapter.js")],
            "sabre": ["php", os.path.join(ROOT, "conformance/adapters/php/vobject_adapter.php")],
            "dmfs": ["java", "-cp",
                     os.path.join(ROOT, "conformance/adapters/java/classes") + ":"
                     + os.path.join(ROOT, "conformance/adapters/java/libs/*"), "DmfsAdapter"],
        }
        ADAPTERS.update(others)
        ref = ask("dateutil", base, limit=25)
        for name in ["rrulejs", "sabre", "dmfs"]:
            print(f"  {name:9s} == dateutil? {ask(name, base, limit=25) == ref}")

    if failures:
        print(f"\nFAIL -- predictor missed {len(failures)} probe(s)")
        return 1
    print(f"\nok -- predictor exact on all {len(PROBES)} probes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
