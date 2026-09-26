#!/usr/bin/env python3
"""Finding 106 -- reproducer.

WHY: finding 104 established, exactly, WHAT ical.js does to BYSETPOS at
FREQ=YEARLY when BYMONTH is multi-valued and the day set comes from BYDAY -- it
applies the selection within each month instead of within the year. It explicitly
did not say which line does it. This reproducer names the line and shows that the
same structural fact also explains 104's four controls and finding 074's defect E.

MECHANISM (recur_iterator.js, expand_year_days()).
expand_year_days() is a branch table over the SET of by-parts present:

    if (partCount == 0) { ... }
    else if (partCount == 1 && "BYMONTH" in parts) { ... }
    else if (partCount == 1 && "BYMONTHDAY" in parts) { ... }
    else if (partCount == 2 && "BYMONTHDAY" && "BYMONTH") { ... }
    else if (partCount == 1 && "BYWEEKNO") { /* TODO unimplemented */ }
    else if (partCount == 2 && "BYWEEKNO" && "BYMONTHDAY") { /* TODO */ }
    else if (partCount == 1 && "BYDAY") { ... }
    else if (partCount == 2 && "BYDAY" && "BYMONTH") { ...  <-- HERE, AND ONLY HERE }
    else if (partCount == 2 && "BYDAY" && "BYMONTHDAY") { ... }
    else if (partCount == 3 && "BYDAY" && "BYMONTHDAY" && "BYMONTH") { ... }
    else if (partCount == 2 && "BYDAY" && "BYWEEKNO") { ... }
    else if (partCount == 3 && "BYDAY" && "BYWEEKNO" && "BYMONTHDAY") { /* TODO */ }
    else if (partCount == 1 && "BYYEARDAY") { ... }
    else if (partCount == 2 && "BYYEARDAY" && "BYDAY") { ... }
    else { this.days = []; }

check_set_position() is called from exactly ONE of those fourteen branches --
`partCount == 2 && BYDAY && BYMONTH` -- and there it sits INSIDE the month loop:

    for (let month of this.by_data.BYMONTH) {
      ...
      if (this.has_by_data("BYSETPOS")) {
        let by_month_day = [];
        for (let day = 1; day <= daysInMonth; day++) {
          t.day = day;
          if (this.is_day_in_byday(t)) by_month_day.push(day);
        }
        for (let spIndex = 0; spIndex < by_month_day.length; spIndex++) {
          if (this.check_set_position(spIndex + 1) ||
              this.check_set_position(spIndex - by_month_day.length)) {
            this.days.push(doy_offset + by_month_day[spIndex]);
          }
        }
      }

`by_month_day` is rebuilt per month and never accumulated across the year, so the
set positions are month positions. That is finding 104.

TWO CONSEQUENCES THIS SCRIPT MEASURES RATHER THAN ASSERTS:

1. At FREQ=YEARLY, BYSETPOS has an effect in that one branch and NOWHERE ELSE.
   Every other reachable branch ignores it, so ical.js answers the rule as if
   BYSETPOS were absent. Finding 074's defect E is stated as "BYSETPOS silently
   dropped UNLESS the day set came from BYDAY". That exclusion is too generous:
   BYDAY alone drops it too. The surviving case is BYDAY *with* BYMONTH *and
   nothing else*.

2. The branch is the only BYSETPOS site in expand_year_days, and it tests BOTH
   set-position spellings in one loop. So finding 105's month-rollover asymmetry
   has NO counterpart here, and next_year() cannot grow one: where next_month()
   carries two inline copies of the selection logic, next_year() calls this one
   function both on entry and on rollover. The asymmetry in 105 is a consequence
   of the duplication, not of the year/month boundary.

Read-only. Runs the icaljs and dateutil adapters; writes nothing.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTERS = {
    "dateutil": ["python3", os.path.join(ROOT, "conformance/adapters/dateutil_adapter.py")],
    "icaljs": ["node", os.path.join(ROOT, "conformance/adapters/icaljs_adapter.js")],
}
DTSTART = "20270101T090000"
LIMIT = 8

# The corpus case that reaches the init() refusal discussed at the end.
REFUSED_ID = "7b92dd911bbb"
REFUSED_RULE = "FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-2,2;BYMONTHDAY=31,5;WKST=SU"
REFUSED_DTSTART = "20530105T090000"


def ask(adapter, rule, dtstart=DTSTART, limit=LIMIT, timeout_ms=8000):
    """Return (occurrences, error_string). Neither raises; a refusal is data here."""
    payload = json.dumps({"id": "x", "dtstart": dtstart, "rrule": rule, "limit": limit})
    env = dict(os.environ, RRULE_CASE_TIMEOUT_MS=str(timeout_ms))
    proc = subprocess.run(ADAPTERS[adapter], input=payload + "\n",
                          capture_output=True, text=True, cwd=ROOT, env=env)
    out = proc.stdout.strip().splitlines()
    if not out:
        return [], f"no output: {proc.stderr[:200]}"
    r = json.loads(out[-1])
    if r.get("error"):
        return [], r["error"]
    return [x[:8] for x in (r.get("occurrences") or [])], None


def count_year_expansions(rule, dtstart=DTSTART):
    """How many times init()'s year search calls expand_year_days() before giving
    up. Produced here rather than quoted, so the figure has a producer."""
    js = """
import ICAL from '%s';
const P = ICAL.RecurIterator.prototype, orig = P.expand_year_days;
let n = 0;
P.expand_year_days = function (y) { n++; return orig.call(this, y); };
const dt = ICAL.Time.fromDateTimeString('%s');
try { const it = ICAL.Recur.fromString('%s').iterator(dt); it.next(); } catch (e) {}
console.log(n);
""" % (os.path.join(ROOT, "js/node_modules/ical.js/lib/ical/module.js"),
       dtstart[:4] + "-" + dtstart[4:6] + "-" + dtstart[6:8] + "T"
       + dtstart[9:11] + ":" + dtstart[11:13] + ":" + dtstart[13:15],
       rule)
    proc = subprocess.run(["node", "--input-type=module", "-e", js],
                          capture_output=True, text=True, cwd=ROOT)
    return proc.stdout.strip() or f"(node failed: {proc.stderr[:120]})"


def strip_setpos(rule):
    return ";".join(p for p in rule.split(";") if not p.startswith("BYSETPOS="))


def single_month_merge(rule):
    """104's predictor: merge of the reference answers with BYMONTH cut to each
    single month in turn. None when the rule has no BYMONTH to cut."""
    months = None
    for p in rule.split(";"):
        if p.startswith("BYMONTH="):
            months = p[len("BYMONTH="):].split(",")
    if not months or len(months) < 2:
        return None
    merged = set()
    for m in months:
        one = ";".join(f"BYMONTH={m}" if p.startswith("BYMONTH=") else p
                       for p in rule.split(";"))
        got, err = ask("dateutil", one, limit=LIMIT * 2)
        if err:
            return None
        merged.update(got)
    return sorted(merged)[:LIMIT]


# (branch label, rule, what the code reading predicts)
#   honoured     -- BYSETPOS changes the answer and the answer is the reference's
#   per-month    -- BYSETPOS changes the answer to the per-month merge (104)
#   dropped      -- BYSETPOS changes nothing; ical.js answers as if it were absent
#   empty        -- the branch is an unimplemented stub, so no day is ever produced
#                   and BYSETPOS is vacuously irrelevant, not dropped
#   refused      -- init() throws a plain Error before any expansion happens
PROBES = [
    ("partCount 0",                    "FREQ=YEARLY;BYSETPOS=2", "dropped"),
    ("1: BYMONTH",                     "FREQ=YEARLY;BYMONTH=9,11;BYSETPOS=2", "dropped"),
    ("1: BYMONTHDAY",                  "FREQ=YEARLY;BYMONTHDAY=5,10,15;BYSETPOS=2", "dropped"),
    ("2: BYMONTHDAY+BYMONTH",          "FREQ=YEARLY;BYMONTH=9,11;BYMONTHDAY=5,10,15;BYSETPOS=2", "dropped"),
    ("1: BYWEEKNO (TODO stub)",        "FREQ=YEARLY;BYWEEKNO=2,36;BYSETPOS=2", "empty"),
    ("2: BYWEEKNO+BYMONTHDAY (stub)",  "FREQ=YEARLY;BYWEEKNO=2,36;BYMONTHDAY=5,10;BYSETPOS=2", "refused"),
    ("1: BYDAY",                       "FREQ=YEARLY;BYDAY=WE;BYSETPOS=2", "dropped"),
    ("2: BYDAY+BYMONTH  <-- 104",      "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2", "per-month"),
    ("2: BYDAY+BYMONTHDAY",            "FREQ=YEARLY;BYDAY=WE;BYMONTHDAY=5,10,15,20,25;BYSETPOS=2", "dropped"),
    ("3: BYDAY+BYMONTHDAY+BYMONTH",    "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYMONTHDAY=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15;BYSETPOS=2", "dropped"),
    ("2: BYDAY+BYWEEKNO",              "FREQ=YEARLY;BYDAY=WE;BYWEEKNO=2,36;BYSETPOS=2", "dropped"),
    ("3: BYDAY+BYWEEKNO+BYMONTHDAY",   "FREQ=YEARLY;BYDAY=WE;BYWEEKNO=2,36;BYMONTHDAY=5,10;BYSETPOS=2", "refused"),
    ("1: BYYEARDAY",                   "FREQ=YEARLY;BYYEARDAY=100,200,300;BYSETPOS=2", "dropped"),
    ("2: BYYEARDAY+BYDAY",             "FREQ=YEARLY;BYYEARDAY=100,200,300;BYDAY=WE,TH,FR;BYSETPOS=2", "dropped"),
]

# The one-month control that 104 already published, kept here because the branch
# table explains it: it takes the SAME branch as 104's defect, and per-month and
# per-year coincide when there is one month, so nothing can go wrong.
CONTROL = ("2: BYDAY+BYMONTH, one month", "FREQ=YEARLY;BYMONTH=9;BYDAY=WE;BYSETPOS=2", "honoured")


def classify(rule):
    got, err = ask("icaljs", rule)
    if err:
        return "refused", got, err
    if not got:
        return "empty", got, None
    without, werr = ask("icaljs", strip_setpos(rule))
    if not werr and got == without:
        return "dropped", got, None
    ref, rerr = ask("dateutil", rule)
    if not rerr and got == ref:
        return "honoured", got, None
    if got == single_month_merge(rule):
        return "per-month", got, None
    return "other", got, None


def main():
    print("finding 106 -- BYSETPOS at FREQ=YEARLY lives in one branch of fourteen")
    print(f"ical.js via {' '.join(ADAPTERS['icaljs'])}, reference = dateutil")
    print(f"DTSTART={DTSTART}, limit={LIMIT}\n")
    bad = []
    measured_by_label = {}
    rows = list(PROBES) + [CONTROL]
    print(f"{'branch of expand_year_days()':34} {'predicted':10} {'measured':10} note")
    print("-" * 96)
    for label, rule, predicted in rows:
        measured, got, err = classify(rule)
        measured_by_label[label] = measured
        note = err or " ".join(got[:4])
        flag = "" if measured == predicted else "   *** MISMATCH"
        if measured != predicted:
            bad.append((label, predicted, measured))
        print(f"{label:34} {predicted:10} {measured:10} {note[:44]}{flag}")

    honoured = [l for l, _r, _p in rows
                if measured_by_label[l] in ("honoured", "per-month")]
    print()
    print(f"branches where BYSETPOS has ANY effect: {len(honoured)}")
    for h in honoured:
        print(f"    {h}")
    print("Both are the same branch of the table (partCount == 2, BYDAY + BYMONTH).")
    print("Every other reachable branch answers the rule as if BYSETPOS were absent,")
    print("which makes finding 074's defect E exclusion clause ('unless the day set")
    print("came from BYDAY') too generous: BYDAY alone drops it as well.")

    print()
    print("WHY ONE STUB ANSWERS `empty` AND TWO ANSWER `refused`: TWO KINDS OF THROW")
    print("  recur_iterator.js wraps init() and swallows exactly one error class:")
    print("      catch (e) { if (e instanceof InvalidRecurrenceRuleError) this.completed = true;")
    print("                  else throw e; }")
    print("  The BYWEEKNO-alone stub produces no days, so init()'s year search runs to its")
    print("  untilYear default of 20000 and raises InvalidRecurrenceRuleError, which is")
    print("  swallowed into an empty iterator. Expansions before giving up:")
    print(f"      {count_year_expansions('FREQ=YEARLY;BYWEEKNO=2,36')} calls to expand_year_days()")
    print("  That unbounded search is finding 103's, already published; it is cited here,")
    print("  not re-claimed. The BYWEEKNO+BYMONTHDAY pair instead raises a plain Error,")
    print("  which propagates and reaches the caller as a refusal.")
    print()
    print("THE TWO 'refused' ROWS ARE THE SAME init() CHECK, NOT THE STUBS BEHIND THEM")
    print('    recur_iterator.js init(): throw new Error("BYWEEKNO does not fit to BYMONTHDAY")')
    print("  Both TODO stubs that mention BYWEEKNO together with BYMONTHDAY are therefore")
    print("  unreachable. Corpus case " + REFUSED_ID + " is a real rule that lands on it:")
    got, err = ask("icaljs", REFUSED_RULE, dtstart=REFUSED_DTSTART, limit=19)
    ref, rerr = ask("dateutil", REFUSED_RULE, dtstart=REFUSED_DTSTART, limit=19)
    print(f"    {REFUSED_RULE}")
    print(f"      ical.js   {err or ' '.join(got[:4])}")
    print(f"      dateutil  {rerr or str(len(ref)) + ' occurrences: ' + ' '.join(ref[:4])}")
    print("  RFC 5545 s3.3.10's table marks BYWEEKNO and BYMONTHDAY both as Expand at")
    print("  FREQ=YEARLY and states no prohibition on the pair; the only stated")
    print("  restriction on BYWEEKNO is that FREQ must be YEARLY. NOT CLAIMED HERE as a")
    print("  separate defect: see the finding for what is and is not asserted.")

    print()
    if bad:
        print(f"FAIL: {len(bad)} branch(es) did not behave as the code reading predicts")
        for label, predicted, measured in bad:
            print(f"    {label}: predicted {predicted}, measured {measured}")
        return 1
    print("OK: every branch behaves as the code reading predicts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
