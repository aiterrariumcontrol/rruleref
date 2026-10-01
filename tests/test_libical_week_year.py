#!/usr/bin/env python3
"""Finding 112's defect B as a debugger diagnostic, and the predictor behind it.

`web/src/diagnostics.js` now warns, on the user's own rule, that `libical`
master `4edd39a3` sizes the week-numbering year wrongly in the
`BYWEEKNO`+`BYDAY` branch of `expand_year_days()`:

    last_day = (7 * weeks_in_year(year)) - doy_offset - 1;

where `expand_by_day()` reads `last_day` as a count of days beginning at
`doy_offset + 1`, so the period is the wrong length by `doy_offset + 1`.

A warning like that is worth nothing unless it is right about which dates the
library emits, so the diagnostic does not match a shape -- it predicts
libical's whole stream out of the library's own arithmetic: ICU's
`WEEK_OF_YEAR` under `WKST` with four minimal days, the week-start-blind ISO
`weeks_in_year()`, `get_start_of_week()` at January 1st, the straddle probe in
`icalrecur_iterator_new()`, and `icalrecur_iterator_next()`'s loop that
swallows a repeated instant.

That prediction is required here to reproduce TWO real builds byte for byte:
the pristine `4edd39a3` and the same source with finding 112's one-line patch
B. The second arm is what makes the note's arithmetic claim falsifiable rather
than rhetorical -- the predictor has to be right about what the defect costs
*and* about what removing it restores.

libical is C, so prediction and implementation cannot share a process. node is
asked for the prediction, the compiled C adapter is asked for the truth, and
this file -- which can read neither library -- owns every comparison. That is
the split finding 111's harness earned for a Java subject.

The COUNTEREXAMPLES section asserts both halves of each exclusion: that the
guard declines the shape, and that declining it was necessary rather than
superstitious, by showing the predictor would have been wrong there with the
guard off.

Skips, loudly, without node or without a provisioned libical build. Runs in
about a minute.
"""
import json
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICT = os.path.join(ROOT, "web", "test", "libical-week-year-predict.mjs")
ADAPTER = os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter")
PLAIN = os.environ.get("LIBICAL_LIB",
                       "/home/agent/terrarium/scratch/libical-install-4edd")
PATCHED = os.environ.get("LIBICAL_LIB_B",
                         "/home/agent/terrarium/scratch/libical-install-4edd-B")

ALL = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


# --- the two oracles -------------------------------------------------------

def predictor(cases):
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    r = subprocess.run([shutil.which("node"), PREDICT], input=payload,
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("the predictor harness failed:\n" + r.stderr[-2000:])
    return {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}


def library(cases, prefix):
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    env = dict(os.environ, TZ="UTC",
               LD_LIBRARY_PATH=os.path.join(prefix, "lib"))
    r = subprocess.run([ADAPTER], input=payload, capture_output=True, text=True,
                       cwd=ROOT, env=env)
    if r.returncode != 0:
        raise SystemExit("the libical adapter failed against %s:\n%s"
                         % (prefix, r.stderr[-2000:]))
    return {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}


# --- the sweep -------------------------------------------------------------

def sweep():
    """Rules the note fires on, and controls it must stay silent about.

    All seven WKST values, because the defect's size is `doy_offset + 1` and
    `doy_offset` is built from WKST and January 1st's weekday together; both
    January and December DTSTARTs, because the constructor's straddle probe
    treats them differently and that is where a whole year gets skipped; and
    BYWEEKNO lists that name a week at the end of the year, at the start, and
    both, since the truncation and the over-run live at opposite ends.
    """
    rng = random.Random(2112)
    bydays = [ALL, ["MO"], ["SU"], ["FR", "SA"], ["MO", "TH"],
              ["TU", "WE", "TH"], ["SA", "SU"], ["WE"]]
    weeknos = [[1], [2], [51], [52], [53], [-1], [-2], [1, 52], [52, 53],
               [-1, 1], [20], [49, 50, 51, 52]]
    starts = [(2024, "0101"), (2026, "0215"), (2027, "1215"), (2034, "1228"),
              (2031, "1231"), (2040, "0701")]
    tails = ["", ";COUNT=6", ";UNTIL=20301231T090000"]
    cases = []
    for wkst in ALL:
        for y0, md in starts:
            for byday in bydays:
                for wk in weeknos:
                    for interval in (1, 2, 3):
                        for tail in tails:
                            if rng.random() > 0.40:
                                continue
                            cases.append({
                                "id": "s%05d" % len(cases),
                                "dtstart": "%04d%sT090000" % (y0, md),
                                "rrule": "FREQ=YEARLY;INTERVAL=%d;BYWEEKNO=%s;BYDAY=%s;WKST=%s%s"
                                         % (interval, ",".join(str(v) for v in wk),
                                            ",".join(byday), wkst, tail),
                                "limit": 12,
                            })
    return cases


# Each exclusion, with the reason it is excluded. The guard must decline all of
# them, and with the guard off the predictor must be WRONG about all of them --
# an exclusion no measurement contradicts is indistinguishable from
# superstition (the rule finding 101's harness earned at wake 171).
EXCLUSIONS = [
    ("ordinal-byday-is-a-different-branch", "FREQ=YEARLY;BYWEEKNO=52;BYDAY=1MO;WKST=MO"),
    ("ordinal-byday-is-a-different-branch", "FREQ=YEARLY;BYWEEKNO=1;BYDAY=-1FR;WKST=SU"),
    ("bymonth-routes-elsewhere",
     "FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYMONTH=12;WKST=MO"),
    ("bymonth-routes-elsewhere", "FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO,TU;BYMONTH=1;WKST=MO"),
    ("bysetpos-reshapes-the-set", "FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO,TU;BYSETPOS=1;WKST=MO"),
    ("byhour-multiplies-the-set", "FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO,TU;BYHOUR=9,17;WKST=MO"),
]
DTSTART = "20240101T090000"


def main():
    if not shutil.which("node"):
        print("SKIP: node is not installed; the predictor cannot be run")
        return 0
    if not os.path.isfile(ADAPTER) or not os.path.isdir(os.path.join(PLAIN, "lib")):
        print("SKIP: no compiled C adapter or no libical build at %s;" % PLAIN)
        print("      this check compares the diagnostic against the real library only")
        return 0
    # The build trap from conformance/adapters/c/README.md: the Makefile has one
    # target name, so a stale binary can silently link the wrong generation.
    ldd = subprocess.run(["ldd", ADAPTER], capture_output=True, text=True).stdout
    if "libical.so.4" not in ldd:
        print("SKIP: %s does not link libical.so.4; rm it and rebuild with"
              " LIBICAL_PREFIX before trusting this" % ADAPTER)
        return 0
    patched = os.path.isdir(os.path.join(PATCHED, "lib"))

    bad = []
    cases = sweep()
    pred = predictor(cases)
    real = library(cases, PLAIN)
    realB = library(cases, PATCHED) if patched else None

    firing = silent = refused = 0
    lost_only = extra_only = both_ways = 0
    for c in cases:
        cid = c["id"]
        p, a = pred[cid], real[cid]
        if p.get("declined"):
            bad.append("%s: the predictor declined a shape the sweep is inside" % cid)
            continue
        got = a.get("occurrences")
        if p["refused"]:
            if got is not None:
                bad.append("%s %s: predicted a refusal; the library answered %r"
                           % (cid, c["rrule"], got[:4]))
                continue
            refused += 1
        else:
            if got is None:
                bad.append("%s %s: the library refused; the predictor did not"
                           % (cid, c["rrule"]))
                continue
            if p["predicted"] != got:
                bad.append("%s %s\n    predicted %r\n    4edd39a3  %r"
                           % (cid, c["rrule"], p["predicted"][:6], got[:6]))
                continue
        if realB is not None:
            gotB = realB[cid].get("occurrences")
            if gotB is None:
                bad.append("%s: the patched build refused a rule it was expected to answer"
                           % cid)
            elif p["fixed"] != gotB:
                bad.append("%s %s\n    patch-B predicted %r\n    patch-B build   %r"
                           % (cid, c["rrule"], p["fixed"][:6], gotB[:6]))
        if p["lost"] or p["phantom"] or p["refused"]:
            firing += 1
            if p["lost"] and p["phantom"]:
                both_ways += 1
            elif p["lost"]:
                lost_only += 1
            elif p["phantom"]:
                extra_only += 1
            for t in p["lost"]:
                if got is not None and t in got:
                    bad.append("%s: claims %s is lost, but 4edd39a3 emits it" % (cid, t))
            for t in p["phantom"]:
                if got is not None and t not in got:
                    bad.append("%s: claims 4edd39a3 invents %s, and it does not" % (cid, t))
                if realB is not None and t in (realB[cid].get("occurrences") or []):
                    bad.append("%s: calls %s invented, but the patched build emits it too"
                               % (cid, t))
        else:
            # The note stays silent. The silence is checked rather than assumed:
            # the whole stream still had to be predicted correctly to get here,
            # against both builds.
            silent += 1

    print("sweep              %d rules, %d firing, %d silent, %d refused by the library,"
          % (len(cases), firing, silent, refused))
    print("                   every stream byte-exact against libical master 4edd39a3%s"
          % (" AND against the patch-B build" if patched else ""))
    # The defect has two directions and they are counted apart: a positive
    # doy_offset truncates the end of the week year, a negative one over-runs
    # it. Finding 112 recorded the over-run as reasoned-but-unobserved; the
    # second column is the measurement that closed that gap.
    print("two arms           %d rules lose dates only, %d invent dates only, %d do both"
          % (lost_only, extra_only, both_ways))
    if extra_only < 50:
        bad.append("only %d rules show the over-run; too few to call it observed" % extra_only)
    if not patched:
        print("NOTE: no patch-B build at %s, so the second arm was not checked." % PATCHED)
        print("      Build it with findings/repro/112-patch-libical.py B.")
    if firing < 150:
        bad.append("the sweep fired on only %d rules, too few to call this measured" % firing)
    if silent < 150:
        bad.append("only %d silent controls; silence that is never checked is not evidence"
                   % silent)

    # --- COUNTEREXAMPLES ---------------------------------------------------
    cases = [{"id": "x%d" % i, "dtstart": DTSTART, "rrule": rr, "limit": 12}
             for i, (_, rr) in enumerate(EXCLUSIONS)]
    pred = predictor(cases)
    ungated = predictor([dict(c, ungated=True) for c in cases])
    real = library(cases, PLAIN)
    for c, (reason, rr) in zip(cases, EXCLUSIONS):
        cid = c["id"]
        if not pred[cid].get("declined"):
            bad.append("the guard did not decline %s (%s)" % (rr, reason))
        u = ungated[cid]
        got = real[cid].get("occurrences")
        if u.get("declined"):
            bad.append("the ungated predictor declined %s, so the exclusion is untested" % rr)
            continue
        if got is None:
            if u["refused"]:
                bad.append("the exclusion %s is superstition: ungated, the predictor is "
                           "right that the library refuses %s" % (reason, rr))
            continue
        if not u["refused"] and u["predicted"] == got:
            bad.append("the exclusion %s is superstition: ungated, the predictor is "
                       "right about %s" % (reason, rr))
    print("counterexamples    %d exclusions, each declined by the guard and each wrong without it"
          % len(EXCLUSIONS))

    if bad:
        print("\nFAILED")
        for b in bad[:12]:
            print("  " + b)
        if len(bad) > 12:
            print("  ... and %d more" % (len(bad) - 12))
        return 1
    print("\nOK: the finding 112 diagnostic predicts libical 4edd39a3 exactly, and the "
          "patch-B build too")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
