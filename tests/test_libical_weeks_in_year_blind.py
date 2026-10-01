#!/usr/bin/env python3
"""Finding 112's defect A as a debugger diagnostic, and the predictor behind it.

`web/src/diagnostics.js` now warns, on the user's own rule, that `libical`
master `4edd39a3` counts a year's weeks with a helper that has never heard of
`WKST`:

    static int weeks_in_year(int year)   /* "Calculate ISO weeks per year" */

ISO means `WKST=MO`, and the comment says so. But the week *numbering* the
count is compared against is ICU's, which `icalrecur_iterator_new()` configures
with four minimal days and `UCAL_FIRST_DAY_OF_WEEK` taken from the rule. So the
numbering honours `WKST` and the count does not, and the two consumers of the
count are the only normalisation of a negative `BYWEEKNO` and the only guard
against a week the year does not have.

This is the second half of finding 112; `tests/test_libical_week_year.py` owns
defect B, which lives in the `BYWEEKNO`+`BYDAY` branch. Defect A is visible in
the branch libical takes with `BYWEEKNO` and NO `BYDAY`, where it expands to
one day per selected week.

As with defect B, the diagnostic does not match a shape -- it predicts
libical's whole stream from the library's own arithmetic, and it is required to
reproduce TWO real builds byte for byte: pristine `4edd39a3` and the same
source with finding 112's one-line patch A. The second arm is what makes the
claim "this is what the week-start-blind count costs" falsifiable rather than
rhetorical.

libical is C, so prediction and implementation cannot share a process. node is
asked for the prediction, the compiled C adapter is asked for the truth, and
this file -- which can read neither library -- owns every comparison.

The CONTROLS matter more here than usual and are asserted, not assumed:
`WKST=MO` is the one value for which the ISO count is right, so the note must
be silent on every Monday rule however the rest of the rule is shaped. A
predictor that fired there would be describing nothing.

Skips, loudly, without node or without a provisioned libical build.
"""
import json
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICT = os.path.join(ROOT, "web", "test", "libical-weeks-in-year-blind-predict.mjs")
ADAPTER = os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter")
PLAIN = os.environ.get("LIBICAL_LIB",
                       "/home/agent/terrarium/scratch/libical-install-4edd")
PATCHED = os.environ.get("LIBICAL_LIB_A",
                         "/home/agent/terrarium/scratch/libical-install-4edd-A")

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
    env = dict(os.environ, TZ="UTC", LD_LIBRARY_PATH=os.path.join(prefix, "lib"))
    r = subprocess.run([ADAPTER], input=payload, capture_output=True, text=True,
                       cwd=ROOT, env=env)
    if r.returncode != 0:
        raise SystemExit("the libical adapter failed against %s:\n%s"
                         % (prefix, r.stderr[-2000:]))
    return {o["id"]: o for o in (json.loads(l) for l in r.stdout.splitlines() if l.strip())}


# --- the sweep -------------------------------------------------------------

def sweep():
    """Rules the note fires on, and controls it must stay silent about.

    All seven WKST values, because the disagreement is between an ISO count and
    a WKST-aware numbering and `MO` is the control; negative BYWEEKNO, because
    `weekno += nweeks + 1` normalises against the wrong total; week 53, because
    `weekno > nweeks` is the only overflow guard and the two readings disagree
    about whether 53 exists; and ordinary weeks well inside the year, which no
    reading of the count can move and which therefore must stay silent.

    DTSTART's weekday is varied deliberately: with no BYDAY the branch selects
    the next instance of DTSTART's own weekday, so it is part of the answer.
    """
    rng = random.Random(1120)
    weeknos = [[1], [2], [26], [51], [52], [53], [-1], [-2], [-3],
               [1, 53], [52, 53], [-1, 1], [-1, -53], [49, 50, 51, 52, 53]]
    starts = [(2024, "0101"), (2025, "0311"), (2026, "1227"), (2027, "1215"),
              (2030, "0629"), (2034, "1228"), (2031, "1231"), (2040, "0701")]
    tails = ["", ";COUNT=6", ";UNTIL=20351231T090000"]
    cases = []
    for wkst in ALL:
        for y0, md in starts:
            for wk in weeknos:
                for interval in (1, 2, 3):
                    for tail in tails:
                        if rng.random() > 0.55:
                            continue
                        cases.append({
                            "id": "s%05d" % len(cases),
                            "dtstart": "%04d%sT090000" % (y0, md),
                            "rrule": "FREQ=YEARLY;INTERVAL=%d;BYWEEKNO=%s;WKST=%s%s"
                                     % (interval, ",".join(str(v) for v in wk), wkst, tail),
                            "limit": 12,
                        })
    return cases


# Each exclusion, with the reason, and with what the measurement has to show.
# "wrong" means the ungated predictor must disagree with the library, which is
# what makes the exclusion necessary rather than superstitious (the rule
# finding 101's harness earned at wake 171). "refused" means the library
# raises UNIMPLEMENTED for the shape while the ungated predictor happily
# answers -- also a disagreement, and the honest way to record it.
EXCLUSIONS = [
    # NOT BYWEEKNO=-1 here. With one week selected the per-year set has one
    # member, so BYSETPOS=1 picks the only thing there is and the exclusion
    # would look like superstition. NOOP below measures exactly that case.
    ("bysetpos-reshapes-the-set",
     "FREQ=YEARLY;BYWEEKNO=49,50,51,52,53;BYSETPOS=1;WKST=SU"),
    ("byhour-multiplies-the-set", "FREQ=YEARLY;BYWEEKNO=-1;BYHOUR=9,17;WKST=SU"),
    ("bymonth-without-byday-is-unimplemented", "FREQ=YEARLY;BYWEEKNO=-1;BYMONTH=12;WKST=SU"),
    ("bymonthday-is-unimplemented", "FREQ=YEARLY;BYWEEKNO=-1;BYMONTHDAY=3;WKST=SU"),
    ("byyearday-is-unimplemented", "FREQ=YEARLY;BYWEEKNO=-1;BYYEARDAY=3;WKST=SU"),
]
DTSTART = "20261227T090000"


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
    realA = library(cases, PATCHED) if patched else None

    firing = silent = refused = 0
    mondays = monday_firing = 0
    neg_firing = overflow_firing = 0
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
        if realA is not None:
            gotA = realA[cid].get("occurrences")
            if gotA is None:
                bad.append("%s: the patched build refused a rule it was expected to answer"
                           % cid)
            elif p["fixed"] != gotA:
                bad.append("%s %s\n    patch-A predicted %r\n    patch-A build   %r"
                           % (cid, c["rrule"], p["fixed"][:6], gotA[:6]))

        fires = bool(p["lost"] or p["phantom"] or p["refused"])
        is_monday = ";WKST=MO" in c["rrule"]
        if is_monday:
            mondays += 1
            if fires:
                monday_firing += 1
                bad.append("%s %s: the note fired on a WKST=MO rule, where the ISO count "
                           "libical uses is the right one" % (cid, c["rrule"]))
        if fires:
            firing += 1
            if "BYWEEKNO=-" in c["rrule"]:
                neg_firing += 1
            if "53" in c["rrule"].split("BYWEEKNO=")[1].split(";")[0]:
                overflow_firing += 1
            for t in p["lost"]:
                if got is not None and t in got:
                    bad.append("%s: claims %s is lost, but 4edd39a3 emits it" % (cid, t))
            for t in p["phantom"]:
                if got is not None and t not in got:
                    bad.append("%s: claims 4edd39a3 invents %s, and it does not" % (cid, t))
                if realA is not None and t in (realA[cid].get("occurrences") or []):
                    bad.append("%s: calls %s invented, but the patched build emits it too"
                               % (cid, t))
        else:
            # The silence is checked rather than assumed: the whole stream still
            # had to be predicted correctly to get here, against both builds.
            silent += 1

    print("sweep              %d rules, %d firing, %d silent, %d refused by the library,"
          % (len(cases), firing, silent, refused))
    print("                   every stream byte-exact against libical master 4edd39a3%s"
          % (" AND against the patch-A build" if patched else ""))
    print("controls           %d WKST=MO rules, %d of them fired"
          % (mondays, monday_firing))
    # The count is consumed in exactly two places and each has its own
    # observable: the negative normalisation and the overflow guard.
    print("two consumers      %d firing rules use a negative BYWEEKNO, %d name week 53"
          % (neg_firing, overflow_firing))
    if not patched:
        print("NOTE: no patch-A build at %s, so the second arm was not checked." % PATCHED)
        print("      Build it with findings/repro/112-patch-libical.py A.")
    if firing < 150:
        bad.append("the sweep fired on only %d rules, too few to call this measured" % firing)
    if silent < 150:
        bad.append("only %d silent controls; silence that is never checked is not evidence"
                   % silent)
    if mondays < 50:
        bad.append("only %d WKST=MO rules; the control arm is too thin to mean anything"
                   % mondays)
    if neg_firing < 20 or overflow_firing < 20:
        bad.append("one of the two consumers of the count is barely exercised: "
                   "%d negative, %d overflow" % (neg_firing, overflow_firing))

    # --- COUNTEREXAMPLES ---------------------------------------------------
    cases = [{"id": "x%d" % i, "dtstart": DTSTART, "rrule": rr, "limit": 12}
             for i, (_, rr) in enumerate(EXCLUSIONS)]
    pred = predictor(cases)
    ungated = predictor([dict(c, ungated=True) for c in cases])
    real = library(cases, PLAIN)
    necessary = 0
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
            # The library refuses the shape outright. The exclusion is still
            # necessary, and for a reason worth stating: ungated, the predictor
            # would have answered where the library errors.
            if u["refused"]:
                bad.append("the exclusion %s is superstition: ungated, the predictor is "
                           "right that the library refuses %s" % (reason, rr))
            else:
                necessary += 1
            continue
        if not u["refused"] and u["predicted"] == got:
            bad.append("the exclusion %s is superstition: ungated, the predictor is "
                       "right about %s" % (reason, rr))
        else:
            necessary += 1
    print("counterexamples    %d exclusions, each declined by the guard and each shown "
          "necessary" % necessary)
    if necessary != len(EXCLUSIONS):
        bad.append("only %d of %d exclusions were shown necessary"
                   % (necessary, len(EXCLUSIONS)))

    # --- WHAT THE BYSETPOS EXCLUSION COSTS --------------------------------
    # The exclusion above is necessary, but it is not necessary everywhere, and
    # the honest thing is to print both halves rather than only the one that
    # flatters the guard (the standard finding 105's addendum set). BYSETPOS is
    # a no-op when it selects the whole per-year set, and with no BYDAY a
    # single-valued BYWEEKNO makes that set one date per year. The guard
    # declines those rules too, and on them the predictor would have been
    # right -- so this part of the exclusion throws away coverage. It stays
    # anyway: deciding which side a rule falls on means evaluating BYSETPOS,
    # which is the stage this predictor deliberately does not model.
    noop, real_sel = [], []
    i = 0
    for wks, bucket in ((["1", "26", "52", "53", "-1", "-2"], noop),
                        (["49,50,51,52,53", "52,53", "-1,-53", "1,53"], real_sel)):
        for wk in wks:
            for sp in ("1", "-1"):
                for wkst in ("SU", "SA", "WE", "TU"):
                    for ds in ("20261227T090000", "20240101T090000",
                               "20300629T090000", "20341228T090000"):
                        i += 1
                        bucket.append({
                            "id": "n%04d" % i, "dtstart": ds, "limit": 12,
                            "rrule": "FREQ=YEARLY;BYWEEKNO=%s;BYSETPOS=%s;WKST=%s"
                                     % (wk, sp, wkst)})
    cases = noop + real_sel
    gated = predictor(cases)
    ungated = predictor([dict(c, ungated=True) for c in cases])
    real = library(cases, PLAIN)
    tally = {"noop": [0, 0], "selecting": [0, 0]}
    for c in cases:
        cid = c["id"]
        if not gated[cid].get("declined"):
            bad.append("the BYSETPOS guard let %s through" % c["rrule"])
            continue
        u, got = ungated[cid], real[cid].get("occurrences")
        ok = ((got is None and u["refused"])
              or (got is not None and not u["refused"] and u["predicted"] == got))
        tally["noop" if c in noop else "selecting"][0 if ok else 1] += 1
    print("bysetpos cost      %d/%d rules where BYSETPOS is a no-op on a one-date set: "
          "the guard declines them and the predictor would have been right"
          % (tally["noop"][0], sum(tally["noop"])))
    print("                   %d/%d where it really selects: the guard is load-bearing"
          % (tally["selecting"][1], sum(tally["selecting"])))
    if tally["noop"][1]:
        bad.append("the predictor was wrong on %d no-op-BYSETPOS rules, so the claim that "
                   "the guard costs coverage there is overstated" % tally["noop"][1])
    if tally["selecting"][1] < 0.8 * sum(tally["selecting"]):
        bad.append("BYSETPOS only changed the answer on %d of %d selecting rules; the "
                   "exclusion is weaker than claimed"
                   % (tally["selecting"][1], sum(tally["selecting"])))

    if bad:
        print("\nFAILED")
        for b in bad[:12]:
            print("  " + b)
        if len(bad) > 12:
            print("  ... and %d more" % (len(bad) - 12))
        return 1
    print("\nOK: the finding 112 defect A diagnostic predicts libical 4edd39a3 exactly, "
          "and the patch-A build too")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
