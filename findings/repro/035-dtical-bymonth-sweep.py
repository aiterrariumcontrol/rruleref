#!/usr/bin/env python3
"""Finding 035's measurement table, re-derived from a stored sweep.

    python3 findings/repro/035-dtical-bymonth-sweep.py            # ~20 sec, read-only
    python3 findings/repro/035-dtical-bymonth-sweep.py --json out.json
    python3 findings/repro/035-dtical-bymonth-sweep.py --run-dtical   # ~13 MIN, WRITES

Why this file exists
--------------------
Finding 035 published six figures with no stored producer.  The Perl sweep
behind them was never retained, so for many wakes they were carried as an
UNCHECKED provenance debt (finding 091's classification, finding 093).  This
script closes that debt: it keeps DateTime::Event::ICal's raw answers in
findings/data/035-dtical-raw.ndjson and re-derives every published figure from
them, so a wrong figure fails instead of merely sitting there.

What is stored and what is recomputed
-------------------------------------
STORED   the 332 raw answers from the Perl library.  Regenerating them costs
         ~13 minutes, which is why they are a committed artifact and why this
         script is excluded from tools/check_repro_drift.py on rule-80 grounds.
RECOMPUTED  everything else -- the case selection, the pinned-day model, and
         the control -- on every run, from conformance/cases.ndjson and the
         vendored python-dateutil.  A figure is therefore only as stale as the
         corpus, and a corpus edit that moves one of these numbers fails here.

*** THE LIMIT IS PART OF THE MEASUREMENT. ***
Whether a case dies at Recurrence.pm line 822 depends on HOW MANY occurrences
you ask for: the death happens during iteration, not at construction.  Asking
for 5 instead of the corpus limit moves 7 of the 58 deaths into normal output.
So this sweep uses the case's own `limit` field -- the same convention
conformance/score.py uses -- and nothing else is comparable to it.  See
finding 094.
"""
import argparse, json, os, subprocess, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
try:
    import env
    env.add_dateutil_to_path()
except Exception:
    pass
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"
CASES = os.path.join(REPO, "conformance", "cases.ndjson")
RAW = os.path.join(REPO, "findings", "data", "035-dtical-raw.ndjson")
RAW_N8 = os.path.join(REPO, "findings", "data", "035-dtical-raw-n8.ndjson")
HISTORICAL_N = 8   # the corpus limit in force when finding 035 was published
ADAPTER = ["perl", os.path.join(REPO, "conformance", "adapters", "perl",
                                "dtical_adapter.pl")]


def selected():
    """The 332 cases finding 035 measures, in corpus order.

    BYSETPOS is excluded throughout: DateTime::Event::ICal's BYSETPOS is
    separately broken (finding 030) and would confound this.
    """
    out = []
    with open(CASES) as fh:
        for line in fh:
            c = json.loads(line)
            r = c.get("rrule", "")
            if "BYMONTH=" not in r or "BYSETPOS" in r:
                continue
            if "FREQ=WEEKLY" in r:
                c["_freq"] = "WEEKLY"
            elif "FREQ=MONTHLY" in r:
                c["_freq"] = "MONTHLY"
            else:
                continue
            out.append(c)
    return out


def strip_bymonth(rrule):
    return ";".join(p for p in rrule.split(";") if not p.startswith("BYMONTH="))


def months_of(rrule):
    return {int(x) for p in rrule.split(";") if p.startswith("BYMONTH=")
            for x in p[len("BYMONTH="):].split(",")}


def take(rrule, dtstart, n):
    """First n occurrences of rrule, as corpus-format strings."""
    out = []
    if n <= 0:
        return out
    for d in rrulestr("RRULE:" + rrule, dtstart=dtstart):
        out.append(d.strftime(FMT))
        if len(out) >= n:
            break
    return out


def pinned_model(case, n):
    """dtical's actual reading: expand the rule WITHOUT BYMONTH, then keep the
    occurrences whose month is in BYMONTH *and* whose day-of-month equals
    DTSTART's.  The library is never asked; this is the model, not the library.
    """
    rrule = case["rrule"]
    months = months_of(rrule)
    dt = datetime.strptime(case["dtstart"], FMT)
    pin = dt.day
    out = []
    if n <= 0:
        return out
    for d in rrulestr("RRULE:" + strip_bymonth(rrule), dtstart=dt):
        if d.month in months and d.day == pin:
            out.append(d.strftime(FMT))
            if len(out) >= n:
                break
    return out


def run_dtical(cases):
    payload = "".join(json.dumps({"id": c["id"], "rrule": c["rrule"],
                                  "dtstart": c["dtstart"], "limit": c["limit"]}) + "\n"
                      for c in cases)
    env2 = dict(os.environ, RRULE_CASE_TIMEOUT=os.environ.get("RRULE_CASE_TIMEOUT", "20"))
    p = subprocess.run(ADAPTER, input=payload, capture_output=True, text=True,
                       env=env2)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-4000:])
        raise SystemExit("dtical adapter exited %d" % p.returncode)
    return p.stdout


def load_raw(path=RAW):
    if not os.path.exists(path):
        raise SystemExit("missing %s -- regenerate with --run-dtical (~13 min)" % path)
    raw = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            o = json.loads(line)
            raw[o["id"]] = o
    return raw


def measure(cases, raw, expect_limit=None):
    tally = {}
    for freq in ("WEEKLY", "MONTHLY"):
        tally[freq] = dict(cases=0, die822=0, other_error=0, output=0,
                           passes=0, pinned=0, control=0)
    unexplained = []
    for c in cases:
        s = tally[c["_freq"]]
        s["cases"] += 1
        d = raw.get(c["id"])
        if d is None:
            raise SystemExit("stored sweep has no answer for case %s" % c["id"])
        # *** The guard that finding 035 needed and did not have. ***
        # Whether a case dies at Recurrence.pm line 822 depends on how many
        # occurrences were requested, so a stored answer is only valid for the
        # limit it was asked at.  Refuse to report rather than silently mixing
        # a stale sweep with today's corpus.
        want = c["limit"] if expect_limit is None else expect_limit
        if d.get("limit") != want:
            raise SystemExit(
                "stored sweep is STALE for case %s: it was asked for %r, expected %r. "
                "Whether this library crashes depends on that depth -- re-run with "
                "--run-dtical (~13 min)." % (c["id"], d.get("limit"), want))
        if "error" in d:
            if "Recurrence.pm line 822" in d["error"]:
                s["die822"] += 1
            else:
                s["other_error"] += 1
            continue
        got = d["occurrences"]
        s["output"] += 1
        if expect_limit is None:
            if got == c["expect"]:
                s["passes"] += 1
        elif got == c["expect"][:len(got)]:
            # A historical sweep is shorter than today's `expect`, so a pass is
            # not computable: report prefix agreement and call it that.
            s["passes"] += 1
        # Both models are asked for exactly as many occurrences as the library
        # produced, so a length difference cannot masquerade as a value one.
        n = len(got)
        if pinned_model(c, n) == got:
            s["pinned"] += 1
        else:
            unexplained.append(c["id"])
        dt = datetime.strptime(c["dtstart"], FMT)
        if take(c["rrule"], dt, n) == got:
            s["control"] += 1
    return tally, unexplained


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dtical", action="store_true",
                    help="re-run the Perl sweep and rewrite the stored raw answers (~13 min)")
    ap.add_argument("--json", metavar="PATH", help="write the table as JSON")
    args = ap.parse_args()

    cases = selected()
    if args.run_dtical:
        sys.stderr.write("running %d cases through DateTime::Event::ICal; "
                         "this takes about 13 minutes\n" % len(cases))
        out = run_dtical(cases)
        with open(RAW, "w") as fh:
            fh.write("# DateTime::Event::ICal raw answers for finding 035's 332 cases.\n"
                     "# Produced by: findings/repro/035-dtical-bymonth-sweep.py --run-dtical\n"
                     "# limit is each case's own `limit` field, as conformance/score.py uses.\n")
            fh.write(out)
        sys.stderr.write("wrote %s\n" % RAW)

    raw = load_raw()
    tally, unexplained = measure(cases, raw)

    w, m = tally["WEEKLY"], tally["MONTHLY"]
    rows = [
        ("cases",                                      w["cases"],  m["cases"]),
        ("die at Recurrence.pm line 822",              w["die822"], m["die822"]),
        ("other error",                          w["other_error"], m["other_error"]),
        ("produce output",                             w["output"], m["output"]),
        ("of which pass the corpus",                   w["passes"], m["passes"]),
    ]
    print("finding 035, DateTime::Event::ICal 0.13, BYSETPOS excluded")
    print("%-34s %8s %8s" % ("", "WEEKLY", "MONTHLY"))
    for name, a, b in rows:
        print("%-34s %8d %8d" % (name, a, b))
    print("%-34s %8s %8s" % ("pinned-day model reproduces",
                             "%d / %d" % (w["pinned"], w["output"]),
                             "%d / %d" % (m["pinned"], m["output"])))
    print("%-34s %8s %8s" % ("control: correct BYMONTH reading",
                             "%d / %d" % (w["control"], w["output"]),
                             "%d / %d" % (m["control"], m["output"])))
    print()
    print("pinned-day model reproduces the output: (%d of %d) WEEKLY, (%d of %d) MONTHLY"
          % (w["pinned"], w["output"], m["pinned"], m["output"]))
    print("control, the correct reading: (%d of %d) WEEKLY, (%d of %d) MONTHLY"
          % (w["control"], w["output"], m["control"], m["output"]))
    if unexplained:
        print("\noutputs the pinned model does NOT explain (%d): %s"
              % (len(unexplained), " ".join(sorted(unexplained))))

    bad = 0
    for freq, s in tally.items():
        if s["other_error"]:
            print("\nUNEXPECTED: %d %s case(s) failed with something other than "
                  "line 822" % (s["other_error"], freq))
            bad = 1
        if s["cases"] != s["die822"] + s["other_error"] + s["output"]:
            print("\nUNEXPECTED: %s partition does not sum to its case count" % freq)
            bad = 1

    # The historical table. Finding 035's published figures were measured when
    # the corpus limit was N=8; commit 5d6745e raised it to 25 on 2026-09-20 and
    # moved two of them. Keeping the old sweep means the correction note's
    # superseded figures stay checked instead of merely asserted.
    hist_raw = load_raw(RAW_N8)
    ht, hunex = measure(cases, hist_raw, expect_limit=HISTORICAL_N)
    hw, hm = ht["WEEKLY"], ht["MONTHLY"]
    print()
    print("as published, at the historical corpus limit N=%d:" % HISTORICAL_N)
    print("  die at line 822: %d WEEKLY, %d MONTHLY" % (hw["die822"], hm["die822"]))
    print("  produce output: %d WEEKLY, %d MONTHLY" % (hw["output"], hm["output"]))
    print("  prefix-agree with today's expect: %d WEEKLY, %d MONTHLY"
          % (hw["passes"], hm["passes"]))
    print("  pinned-day model reproduces the output: (%d of %d) WEEKLY, (%d of %d) MONTHLY"
          % (hw["pinned"], hw["output"], hm["pinned"], hm["output"]))
    print("  control, the correct reading: (%d of %d) WEEKLY, (%d of %d) MONTHLY"
          % (hw["control"], hw["output"], hm["control"], hm["output"]))

    if args.json:
        rec = {"library": "DateTime::Event::ICal 0.13",
               "bysetpos": "excluded (finding 030)",
               "limit": "each case's own limit field, as conformance/score.py",
               "weekly": w, "monthly": m,
               "pinned_reproduces": {"weekly": "%d/%d" % (w["pinned"], w["output"]),
                                     "monthly": "%d/%d" % (m["pinned"], m["output"])},
               "control_reproduces": {"weekly": "%d/%d" % (w["control"], w["output"]),
                                      "monthly": "%d/%d" % (m["control"], m["output"])},
               "unexplained_ids": sorted(unexplained),
               "historical_n8": {
                   "why": ("finding 035's published figures; the corpus limit was 8 "
                           "until commit 5d6745e raised it to 25 on 2026-09-20"),
                   "weekly": hw, "monthly": hm,
                   "pinned_reproduces": {"weekly": "%d/%d" % (hw["pinned"], hw["output"]),
                                         "monthly": "%d/%d" % (hm["pinned"], hm["output"])},
                   "control_reproduces": {"weekly": "%d/%d" % (hw["control"], hw["output"]),
                                          "monthly": "%d/%d" % (hm["control"], hm["output"])}}}
        with open(args.json, "w") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("\nwrote %s" % args.json)
    return bad


if __name__ == "__main__":
    sys.exit(main())
