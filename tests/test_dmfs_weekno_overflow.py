#!/usr/bin/env python3
"""Finding 111 as a debugger diagnostic, and the predictor that backs it.

`web/src/diagnostics.js` now warns, on the user's own rule, that dmfs
`lib-recur` 0.17.1 answers a `BYWEEKNO` the year does not have with December
32nd: `ByWeekNoYearlyExpander.expand()` normalises the requested week against
`getWeeksPerYear(year)` and then, when the result is larger than that count,
adds an instance at December 31st plus one day instead of skipping it.

A warning like that is worth nothing unless it is right about *which* dates the
library emits, so the diagnostic does not match a shape -- it predicts
lib-recur's whole stream, out of the library's own arithmetic:
`setDayOfWeek`'s delta, `prevDay` tolerating a day of month of
`daysInMonth + 1` where `nextDay` clamps it to `daysInMonth`, the zero-delta
weekday dropped as an impossible date, and the iterator never going backwards.
That prediction is required here to reproduce the real library BYTE FOR BYTE,
on rules where the note fires and on rules where it does not.

This harness is shaped differently from finding 101's and 103's, which run
inside node next to the library they model. lib-recur is Java, so the
prediction and the implementation cannot share a process: node is asked for the
prediction, the compiled `DmfsAdapter` is asked for the truth, and this file --
which can read neither library -- owns every comparison.

The COUNTEREXAMPLES section asserts both halves of each exclusion: that the
guard really declines the shape, and that declining it was necessary rather
than superstitious, by showing the predictor would have been wrong there with
the guard off.

Skips, loudly, without node or without a JVM and the compiled adapter: the
check needs the real library, not a model of it. Runs in about twenty seconds.
"""
import datetime
import json
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICT = os.path.join(ROOT, "web", "test", "dmfs-weekno-predict.mjs")
CLASSES = os.path.join(ROOT, "conformance", "adapters", "java", "classes")
LIBS = os.path.join(ROOT, "conformance", "adapters", "java", "libs")
CP = CLASSES + os.pathsep + os.path.join(LIBS, "*")

ALL = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


# --- the two oracles -------------------------------------------------------

def predictor(cases):
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    r = subprocess.run([shutil.which("node"), PREDICT], input=payload,
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("the predictor harness failed:\n" + r.stderr[-2000:])
    return {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}


def library(cases):
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    r = subprocess.run(["java", "-Duser.language=en", "-Duser.country=US",
                        "-cp", CP, "DmfsAdapter"], input=payload,
                       capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise SystemExit("the dmfs adapter failed:\n" + r.stderr[-2000:])
    return {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}


def reference(cases):
    """python-dateutil and rrule.js, the two libraries the note names as returning
    nothing. A note that tells a user what other implementations do has to be
    checked on that too, not only on its subject."""
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    out = {}
    for name, cmd in (("dateutil", [sys.executable,
                                    "conformance/adapters/dateutil_adapter.py"]),
                      ("rrule.js", [shutil.which("node"),
                                    "conformance/adapters/rrulejs_adapter.js"])):
        r = subprocess.run(cmd, input=payload, capture_output=True, text=True,
                           cwd=ROOT, env=dict(os.environ, TZ="UTC"))
        if r.returncode != 0:
            raise SystemExit("the %s adapter failed:\n%s" % (name, r.stderr[-2000:]))
        out[name] = {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines()
                                         if l.strip())}
    return out


def iso_weeks_in(year):
    """ISO 8601, i.e. WKST=MO. Used only to describe the sweep, never to predict."""
    return datetime.date(year, 12, 28).isocalendar()[1]


# --- the sweep -------------------------------------------------------------

def sweep():
    """Rules the note fires on, and controls it must stay silent about.

    Every one of the seven WKST values, because lib-recur's week count honours
    WKST (unlike libical's, finding 112) and the predictor has to as well;
    eight DTSTARTs, including ones not in January, because the phantom week
    straddles the year boundary; and BYWEEKNO lists that overshoot, that do
    not, and that mix the two -- the mixed ones are what found the iterator's
    monotonicity filter, since a phantom week of one year can reach past the
    first real week of the next.
    """
    rng = random.Random(1111)
    bydays = [ALL, ["MO"], ["MO", "TU"], ["SU"], ["SA", "SU"],
              ["TH", "FR", "SA"], ["WE"], ["SU", "MO"], ["FR", "SU"]]
    weeknos = [[53], [52], [52, 53], [1, 53], [-1], [-1, 53], [2, 40, 53], [53, 1]]
    starts = [(2020, "0101"), (2021, "0715"), (2023, "1130"), (2026, "0301"),
              (2032, "1231"), (2047, "0601"), (2099, "0101"), (2041, "0918")]
    cases = []
    for wkst in ALL:
        for y0, md in starts:
            for byday in bydays:
                for wk in weeknos:
                    for interval in (1, 2, 3):
                        if rng.random() > 0.22:
                            continue
                        cases.append({
                            "id": "s%04d" % len(cases),
                            "dtstart": "%04d%sT090000" % (y0, md),
                            "rrule": "FREQ=YEARLY;WKST=%s;INTERVAL=%d;BYWEEKNO=%s;BYDAY=%s;COUNT=30"
                                     % (wkst, interval, ",".join(str(v) for v in wk),
                                        ",".join(byday)),
                            "limit": 30,
                        })
    return cases


# Each exclusion, with the reason it is excluded. The guard must decline all of
# them, and with the guard off the predictor must be WRONG about all of them --
# an exclusion no measurement contradicts is indistinguishable from
# superstition (the rule finding 101's harness earned at wake 171).
EXCLUSIONS = [
    ("month-0-day-0-branch", "FREQ=YEARLY;BYWEEKNO=-53;BYDAY=%s;COUNT=12" % ",".join(ALL)),
    ("month-0-day-0-branch", "FREQ=YEARLY;BYWEEKNO=-53;BYDAY=MO;COUNT=12"),
    ("bymonth-routes-elsewhere", "FREQ=YEARLY;BYWEEKNO=53;BYMONTH=1;BYDAY=%s;COUNT=12" % ",".join(ALL)),
    ("bymonth-routes-elsewhere", "FREQ=YEARLY;BYWEEKNO=53;BYMONTH=12;BYDAY=%s;COUNT=12" % ",".join(ALL)),
    ("bysetpos-reshapes-the-set", "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,TU,WE;BYSETPOS=1;COUNT=12"),
    ("byhour-multiplies-the-set", "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,TU;BYHOUR=9,17;COUNT=12"),
    ("bymonthday-filters-the-set", "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,TU;BYMONTHDAY=27;COUNT=12"),
]
# Rejected by lib-recur itself, so there is no output to predict. The guard
# declines these too, but the second half of the test is different: the claim
# is about the library refusing, not about the predictor being wrong.
REFUSED = [
    "FREQ=YEARLY;BYWEEKNO=53;BYDAY=1MO;COUNT=12",
    "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,2TU;COUNT=12",
]
DTSTART = "20210101T090000"


def main():
    if not shutil.which("node"):
        print("SKIP: node is not installed; the predictor cannot be run")
        return 0
    if shutil.which("java") is None or not os.path.isfile(
            os.path.join(CLASSES, "DmfsAdapter.class")):
        print("SKIP: no JVM or no compiled dmfs adapter (run tools/bootstrap.sh);")
        print("      this check compares the diagnostic against the real library only")
        return 0

    bad = []
    cases = sweep()
    pred, real = predictor(cases), library(cases)

    firing = silent = 0
    phantom_years = set()
    for c in cases:
        cid = c["id"]
        p, a = pred[cid], real[cid]
        got = a.get("occurrences")
        if got is None:
            bad.append("%s: the library errored: %s" % (cid, a.get("error")))
            continue
        if p.get("declined"):
            bad.append("%s: the predictor declined a shape the sweep is inside" % cid)
            continue
        if p["predicted"] != got:
            bad.append("%s %s\n    predicted %r\n    library   %r"
                       % (cid, c["rrule"], p["predicted"][:6], got[:6]))
            continue
        if p["phantom"] and not p["years"]:
            bad.append("%s: a phantom date with no overshot year to explain it" % cid)
        if not p["years"] or not p["phantom"]:
            # The note stays silent -- either the rule overshoots nothing, or
            # it does and every phantom date was dropped or also reached by a
            # real week. The silence is checked rather than assumed: the whole
            # stream still had to be predicted correctly to get here.
            silent += 1
            continue
        firing += 1
        # lib-recur's week count honours WKST, so python's ISO calendar is an
        # independent check of the count only where WKST is Monday. Where it
        # applies it is worth having: it is not computed by the predictor.
        if ";WKST=MO;" in c["rrule"]:
            phantom_years.update(p["years"])
        for t in p["phantom"]:
            if t not in got:
                bad.append("%s: claims a phantom date the library does not emit: %s" % (cid, t))

    print("sweep              %d rules, %d firing, %d silent, all byte-exact against lib-recur 0.17.1"
          % (len(cases), firing, silent))
    if firing < 300:
        bad.append("the sweep fired on only %d rules, too few to call this measured" % firing)
    print("independent check   %d overshot years under WKST=MO, none of which ISO gives a week 53"
          % len(phantom_years))
    for y in sorted(phantom_years):
        if iso_weeks_in(y) == 53:
            bad.append("%d has an ISO week 53 and the note claimed an overflow in it" % y)
    if len(phantom_years) < 20:
        bad.append("only %d WKST=MO overshot years; too few to call that check measured"
                   % len(phantom_years))

    # --- COUNTEREXAMPLES ---------------------------------------------------
    cases = [{"id": "x%d" % i, "dtstart": DTSTART, "rrule": rr, "limit": 12}
             for i, (_, rr) in enumerate(EXCLUSIONS)]
    pred = predictor(cases)
    ungated = predictor([dict(c, ungated=True) for c in cases])
    real = library(cases)
    for c, (reason, rr) in zip(cases, EXCLUSIONS):
        cid = c["id"]
        if not pred[cid].get("declined"):
            bad.append("the guard did not decline %s (%s)" % (rr, reason))
        got = real[cid].get("occurrences")
        if got is None:
            bad.append("%s: the library errored where it was expected to answer" % rr)
            continue
        u = ungated[cid]
        if not u.get("declined") and u["predicted"] == got:
            bad.append("the exclusion %s is superstition: ungated, the predictor is "
                       "right about %s" % (reason, rr))
    print("counterexamples    %d exclusions, each declined by the guard and each wrong without it"
          % len(EXCLUSIONS))

    # --- what the note says about the OTHER implementations ----------------
    # The note tells the reader that python-dateutil and rrule.js return
    # nothing in a short year. Measured here rather than asserted: the same
    # rule closed with UNTIL inside a run of short years must be empty in
    # both, and left open must fire only in the long years.
    cases = [{"id": "short",
              "dtstart": "20210101T090000",
              "rrule": "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO;UNTIL=20251231T000000",
              "limit": 12},
             {"id": "long",
              "dtstart": "20210101T090000",
              "rrule": "FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO,TU;COUNT=4",
              "limit": 4}]
    ref = reference(cases)
    for name, got in ref.items():
        if got["short"].get("occurrences") != []:
            bad.append("%s does not return nothing in 2021-2025, which the note claims: %r"
                       % (name, got["short"].get("occurrences")))
        years = sorted({o[:4] for o in (got["long"].get("occurrences") or [])})
        if years != ["2026", "2032"]:
            bad.append("%s fires in %s, not only in the long years 2026 and 2032"
                       % (name, years))
    print("the note's other claims  dateutil and rrule.js return nothing in 2021-2025 "
          "and fire only in 2026 and 2032")

    cases = [{"id": "r%d" % i, "dtstart": DTSTART, "rrule": rr, "limit": 12}
             for i, rr in enumerate(REFUSED)]
    pred, real = predictor(cases), library(cases)
    for c, rr in zip(cases, REFUSED):
        if not pred[c["id"]].get("declined"):
            bad.append("the guard did not decline the ordinal BYDAY in %s" % rr)
        if real[c["id"]].get("occurrences") is not None:
            bad.append("lib-recur answered %s; it was measured as refusing it" % rr)
    print("refused by lib-recur %d rules with an ordinal BYDAY, declined here too"
          % len(REFUSED))

    if bad:
        print("\nFAILED")
        for b in bad[:12]:
            print("  " + b)
        if len(bad) > 12:
            print("  ... and %d more" % (len(bad) - 12))
        return 1
    print("\nOK: the finding 111 diagnostic predicts dmfs lib-recur 0.17.1 exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
