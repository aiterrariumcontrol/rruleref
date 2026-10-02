#!/usr/bin/env python3
"""Finding 123's claims about dateutil PR 1589 still hold.

Four kinds of check:

* structural, over the committed artifact -- the shape of the case space and
  the headline that nothing diverges or regresses;
* the *characterisation* of the fourteen cases that agree either way, which is
  the finding's one novel claim and the one most likely to rot silently if the
  case space is ever widened;
* live, that the patch still applies to the vendored ``rrule.py`` at exactly
  one site and still produces the union;
* a vacuity guard. If the vendored dateutil is ever bumped past a release that
  carries the fix, every "fixed" cell becomes "agreed-both" and every assertion
  above would still pass while the finding silently stopped being about
  anything. So the defect is asserted to be *present* in the stock library.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "findings", "data", "123-mixed-byday-union.json")
DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")

fails = []


def check(name, cond, detail=""):
    print("%-4s %s%s" % ("ok" if cond else "FAIL", name,
                         "" if cond else "  -- " + str(detail)))
    if not cond:
        fails.append(name)


d = json.load(open(ART))
rows = d["rows"]
by_verdict = {}
for r in rows:
    by_verdict.setdefault(r["verdict"], []).append(r)

check("artifact has 1410 rows", len(rows) == 1410, len(rows))
check("artifact names the patch", d["patch"] == "dateutil/dateutil#1589", d["patch"])
check("no case regresses", not by_verdict.get("regressed"),
      [r["rrule"] for r in by_verdict.get("regressed", [])][:5])
check("no case diverges after the patch", not by_verdict.get("divergent-both"),
      [r["rrule"] for r in by_verdict.get("divergent-both", [])][:5])
check("1312 cases fixed", len(by_verdict.get("fixed", [])) == 1312,
      len(by_verdict.get("fixed", [])))

core = [r for r in rows if r["arm"].startswith("core-")]
check("core arm is 980 cases, all fixed",
      len(core) == 980 and all(r["verdict"] == "fixed" for r in core), len(core))

# The novel claim: the cases BYSETPOS hides are exactly the self-coincident
# shapes, nothing more and nothing less.
hidden = sorted(r["rrule"] for r in rows
                if r["arm"] == "setpos-mixed" and r["verdict"] == "agreed-both")
expect = sorted(["FREQ=MONTHLY;BYDAY=1%s,%s;BYSETPOS=1" % (w, w) for w in DAYS]
                + ["FREQ=MONTHLY;BYDAY=-1%s,%s;BYSETPOS=-1" % (w, w) for w in DAYS])
check("the 14 BYSETPOS-hidden cases are exactly the self-coincident shapes",
      hidden == expect, set(hidden) ^ set(expect))

controls = [r for r in rows if r["arm"].startswith("setpos-control-")]
check("the 84 unmixed BYSETPOS controls all agree both ways",
      len(controls) == 84 and all(r["verdict"] == "agreed-both" for r in controls),
      len(controls))

# Live: the patch applies, and it unions.
sys.path.insert(0, os.path.join(ROOT, "findings", "repro"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "probe123", os.path.join(ROOT, "findings", "repro", "123-mixed-byday-union.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

stock_rrule = open(os.path.join(probe.STOCK, "dateutil", "rrule.py")).read()
check("PR 1589's pre-image appears exactly once in the vendored rrule.py",
      stock_rrule.count(probe.PATCH_OLD) == 1,
      stock_rrule.count(probe.PATCH_OLD))

PROBE = ["FREQ=MONTHLY;BYDAY=1MO,TU", "FREQ=MONTHLY;BYDAY=1MO,MO"]
stock = probe.run_dateutil(probe.STOCK, PROBE)["rows"]
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    patched = probe.run_dateutil(probe.patched_tree(tmp), PROBE)["rows"]
naive = {r: probe.expand_naive(r) for r in PROBE}

check("patched dateutil matches naive on both live probes",
      all(patched[r] == naive[r] for r in PROBE),
      {r: (patched[r], naive[r]) for r in PROBE})

# Vacuity guard: the defect must still be present in the stock library, or this
# finding is about a library that no longer exists.
check("stock dateutil still shows the intersection (finding is not vacuous)",
      stock["FREQ=MONTHLY;BYDAY=1MO,TU"] == []
      and stock["FREQ=MONTHLY;BYDAY=1MO,MO"] != naive["FREQ=MONTHLY;BYDAY=1MO,MO"],
      {r: stock[r] for r in PROBE})

print()
if fails:
    print("FAIL %d of the checks above" % len(fails))
    sys.exit(1)
print("ok  all %d checks" % 11)
