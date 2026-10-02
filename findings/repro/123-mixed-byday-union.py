#!/usr/bin/env python3
"""Finding 123: what dateutil PR 1589 fixes, and what it leaves alone.

Finding 013 adjudicated six corpus cases against python-dateutil: a BYDAY list
mixing a signed weekdaynum with an unsigned one is a union of its elements, and
dateutil applies it as an intersection. On 2026-09-30 a third party filed the
same defect upstream (dateutil/dateutil#1588) with the same mechanism, and a fix
(dateutil/dateutil#1589). Four hand-written tests accompany that fix.

This script asks the question the four tests cannot: over the whole space of
mixed BYDAY lists, does the patch make dateutil agree with an expander written
from the spec text -- and does it break anything that already agreed?

Three columns per case: `naive` (src/naive.py, spec brute force), `stock`
(the dateutil pinned in vendor/pylibs), and `patched` (a temporary copy of that
same tree with PR 1589's one-site change to rrule.py applied here, so the run
needs nothing from outside the repository).

Two control arms matter. A mixed list carrying BYSETPOS is scored next to the
*unmixed* lists of the same shape, because dateutil and naive already disagree
about BYSETPOS for reasons that predate this patch (findings 004 and 032); only
a divergence the mixing introduces can be charged to BYDAY.

    python3 findings/repro/123-mixed-byday-union.py
    python3 findings/repro/123-mixed-byday-union.py --check   # diff vs artifact
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
import naive  # noqa: E402

ARTIFACT = os.path.join(REPO, "findings", "data", "123-mixed-byday-union.json")
STOCK = os.path.join(REPO, "vendor", "pylibs")

DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
ORDINALS = (1, 2, 3, 4, 5, -1, -2, -3, -4, -5)
DTSTART = datetime.datetime(2026, 1, 5, 9, 0, 0)       # a Monday
HORIZON = DTSTART + datetime.timedelta(days=760)
LIMIT = 8

# PR 1589, src/dateutil/rrule.py. Kept as literal text rather than a patch file
# so that a mismatch fails loudly against whatever dateutil is vendored.
PATCH_OLD = """                    (byweekday and ii.wdaymask[i] not in byweekday) or
                    (ii.nwdaymask and not ii.nwdaymask[i]) or
"""
PATCH_NEW = """                    ((byweekday or ii.nwdaymask)
                     and not (byweekday and ii.wdaymask[i] in byweekday)
                     and not (ii.nwdaymask and ii.nwdaymask[i])) or
"""


def ord_str(n):
    return "%d%s" % (n, "")


def cases():
    """Every case, as (arm, rrule). Mixed arms first, then their controls."""
    out = []
    for freq in ("MONTHLY", "YEARLY"):
        for n in ORDINALS:
            for w1 in DAYS:
                for w2 in DAYS:
                    out.append(("core-%s" % freq.lower(),
                                "FREQ=%s;BYDAY=%d%s,%s" % (freq, n, w1, w2)))
    # Mixed + BYSETPOS, and the two unmixed controls of the same shape.
    for n in (1, -1):
        for sp in (1, 2, -1):
            for w1 in DAYS:
                for w2 in DAYS:
                    out.append(("setpos-mixed",
                                "FREQ=MONTHLY;BYDAY=%d%s,%s;BYSETPOS=%d"
                                % (n, w1, w2, sp)))
            for w1 in DAYS:
                out.append(("setpos-control-ordinal",
                            "FREQ=MONTHLY;BYDAY=%d%s;BYSETPOS=%d" % (n, w1, sp)))
                out.append(("setpos-control-plain",
                            "FREQ=MONTHLY;BYDAY=%s;BYSETPOS=%d" % (w1, sp)))
    # Lists longer than two, where the union has to hold across three elements.
    for extra in ("MO", "SU", "FR"):
        for lead in ("1SU,-1SU", "1MO,2MO", "-1FR,3FR", "1MO,-2WE"):
            out.append(("multi", "FREQ=MONTHLY;BYDAY=%s,%s" % (lead, extra)))
            out.append(("multi", "FREQ=YEARLY;BYDAY=%s,%s" % (lead, extra)))
    # Mixed list under an INTERVAL, and under a BYMONTH limit.
    for n in (1, -1):
        for w2 in DAYS:
            out.append(("interval",
                        "FREQ=MONTHLY;INTERVAL=3;BYDAY=%d%s,%s" % (n, "SU", w2)))
            out.append(("bymonth",
                        "FREQ=YEARLY;BYMONTH=3,7;BYDAY=%d%s,%s" % (n, "SU", w2)))
    return out


def expand_naive(rrule):
    try:
        occ = naive.expand(rrule, DTSTART, horizon=HORIZON, limit=LIMIT)
        return [d.strftime("%Y%m%dT%H%M%S") for d in occ]
    except Exception as e:
        return "error:%s" % type(e).__name__


CHILD = r'''
import json, sys, datetime
sys.path.insert(0, sys.argv[1])
from dateutil.rrule import rrulestr
import dateutil
dtstart = datetime.datetime(2026, 1, 5, 9, 0, 0)
horizon = dtstart + datetime.timedelta(days=760)
out = {"version": dateutil.__version__, "rows": {}}
for rule in json.load(sys.stdin):
    try:
        r = rrulestr("RRULE:" + rule, dtstart=dtstart)
        occ = []
        for x in r:
            if x > horizon or len(occ) >= 8:
                break
            occ.append(x.strftime("%Y%m%dT%H%M%S"))
        out["rows"][rule] = occ
    except Exception as e:
        out["rows"][rule] = "error:%s" % type(e).__name__
json.dump(out, sys.stdout)
'''


def run_dateutil(pylibs, rules):
    p = subprocess.run([sys.executable, "-c", CHILD, pylibs],
                       input=json.dumps(rules), capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("dateutil child failed for %s:\n%s" % (pylibs, p.stderr[-2000:]))
    return json.loads(p.stdout)


def patched_tree(tmp):
    dst = os.path.join(tmp, "pylibs")
    shutil.copytree(STOCK, dst, ignore=shutil.ignore_patterns("__pycache__"))
    path = os.path.join(dst, "dateutil", "rrule.py")
    src = open(path).read()
    if src.count(PATCH_OLD) != 1:
        sys.exit("PR 1589's pre-image appears %d times in the vendored "
                 "rrule.py; the patch no longer applies."
                 % src.count(PATCH_OLD))
    open(path, "w").write(src.replace(PATCH_OLD, PATCH_NEW))
    return dst


def measure():
    rules = cases()
    just = [r for _, r in rules]
    with tempfile.TemporaryDirectory() as tmp:
        stock = run_dateutil(STOCK, just)
        patched = run_dateutil(patched_tree(tmp), just)
    rows = []
    for arm, rule in rules:
        n, s, p = expand_naive(rule), stock["rows"][rule], patched["rows"][rule]
        rows.append({
            "arm": arm, "rrule": rule,
            "naive": n, "stock": s, "patched": p,
            "verdict": verdict(n, s, p),
        })
    return {
        "dateutil_version": stock["version"],
        "patch": "dateutil/dateutil#1589",
        "dtstart": DTSTART.strftime("%Y%m%dT%H%M%S"),
        "horizon_days": 760, "limit": LIMIT,
        "rows": rows,
    }


def verdict(n, s, p):
    if s == n and p == n:
        return "agreed-both"
    if s != n and p == n:
        return "fixed"
    if s == n and p != n:
        return "regressed"
    return "divergent-both"


def summarise(data):
    arms, counts = {}, {}
    for r in data["rows"]:
        arms.setdefault(r["arm"], {}).setdefault(r["verdict"], 0)
        arms[r["arm"]][r["verdict"]] += 1
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    order = ("fixed", "agreed-both", "divergent-both", "regressed")
    w = max(len(a) for a in arms)
    lines = ["%-*s %7s %7s %7s %7s %7s" % (w, "arm", "cases", "fixed",
                                           "agreed", "diverg", "regress")]
    for arm in sorted(arms):
        a = arms[arm]
        lines.append("%-*s %7d %7d %7d %7d %7d" % (
            w, arm, sum(a.values()), a.get("fixed", 0), a.get("agreed-both", 0),
            a.get("divergent-both", 0), a.get("regressed", 0)))
    lines.append("%-*s %7d %7d %7d %7d %7d" % (
        w, "TOTAL", len(data["rows"]), counts.get("fixed", 0),
        counts.get("agreed-both", 0), counts.get("divergent-both", 0),
        counts.get("regressed", 0)))
    return "\n".join(lines), order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="re-measure and diff against the committed artifact")
    ap.add_argument("--show", type=int, default=6,
                    help="example rows to print per non-agreeing verdict")
    args = ap.parse_args()

    data = measure()
    table, order = summarise(data)
    print("dateutil %s, patch %s" % (data["dateutil_version"], data["patch"]))
    print("DTSTART %s, horizon %d days, limit %d\n"
          % (data["dtstart"], data["horizon_days"], data["limit"]))
    print(table)

    for v in ("regressed", "divergent-both", "fixed"):
        ex = [r for r in data["rows"] if r["verdict"] == v]
        if not ex:
            continue
        print("\n%s (%d), first %d:" % (v, len(ex), min(args.show, len(ex))))
        for r in ex[:args.show]:
            print("  %-46s" % r["rrule"])
            for k in ("naive", "stock", "patched"):
                val = r[k]
                print("    %-8s %s" % (k, val if isinstance(val, str)
                                       else " ".join(x[:8] for x in val) or "(empty)"))

    if args.check:
        if not os.path.exists(ARTIFACT):
            sys.exit("no artifact at %s" % ARTIFACT)
        old = json.load(open(ARTIFACT))
        bad = 0
        oldrows = {r["rrule"]: r for r in old["rows"]}
        for r in data["rows"]:
            o = oldrows.get(r["rrule"])
            if o is None or o["verdict"] != r["verdict"]:
                bad += 1
                print("DIFF %s: %s -> %s" % (
                    r["rrule"], o["verdict"] if o else "(absent)", r["verdict"]))
        print("\n--check: %d of %d rows differ from the artifact"
              % (bad, len(data["rows"])))
        return 1 if bad else 0

    os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
    json.dump(data, open(ARTIFACT, "w"), indent=1, sort_keys=True)
    print("\nartifact -> %s" % os.path.relpath(ARTIFACT, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
