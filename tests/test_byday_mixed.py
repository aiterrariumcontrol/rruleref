"""Finding 013: a BYDAY list mixing a signed weekdaynum with an unsigned one.

RFC 5545 3.3.10 makes the list a union -- its own worked example
`FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=1SU,-1SU` is "the first *and* last
Sunday". python-dateutil intersects the signed and unsigned halves instead,
so a mixed list with different weekdays yields nothing at all. Today's
dateutil behaviour is pinned here, not just naive's: a release that fixes it
must fail this file loudly rather than pass in silence.
"""
import sys, os, json
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from datetime import datetime
from naive import expand

FAIL = []
DS = datetime(2026, 3, 2, 9, 0)


def check(name, got, want):
    ok = got == want
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else
          "\n       got  %r\n       want %r" % (got, want)))
    if not ok:
        FAIL.append(name)


def days(rule, n=6, dtstart=DS):
    return [d.strftime("%m-%d") for d in expand(rule, dtstart, limit=n)][:n]


print("the union reading, from the RFC's own example")
check("BYDAY=1SU,-1SU is the first and the last Sunday",
      days("FREQ=MONTHLY;BYDAY=1SU,-1SU", 4, datetime(2026, 3, 1, 9, 0)),
      ["03-01", "03-29", "04-05", "04-26"])
check("BYDAY=+2SU,MO is the 2nd Sunday and every Monday",
      days("FREQ=MONTHLY;BYDAY=+2SU,MO"),
      ["03-02", "03-08", "03-09", "03-16", "03-23", "03-30"])
check("BYDAY=2SU,SU is every Sunday (the 2nd is one of them)",
      days("FREQ=MONTHLY;BYDAY=2SU,SU"),
      ["03-08", "03-15", "03-22", "03-29", "04-05", "04-12"])
check("BYMONTHDAY unions signed and unsigned the same way",
      days("FREQ=MONTHLY;BYMONTHDAY=15,-1", 4),
      ["03-15", "03-31", "04-15", "04-30"])

print()
print("python-dateutil 2.9.0.post0, pinned")
try:
    import dateutil
    from dateutil.rrule import rrulestr

    def du(rule, n=6, dtstart=DS):
        return [d.strftime("%m-%d") for d in rrulestr(rule, dtstart=dtstart)[:n]]

    check("version", dateutil.__version__, "2.9.0.post0")
    check("agrees on the all-signed list",
          du("FREQ=MONTHLY;BYDAY=1SU,-1SU", 4, datetime(2026, 3, 1, 9, 0)),
          ["03-01", "03-29", "04-05", "04-26"])
    check("agrees on BYMONTHDAY=15,-1",
          du("FREQ=MONTHLY;BYMONTHDAY=15,-1", 4), ["03-15", "03-31",
                                                   "04-15", "04-30"])
    check("returns NOTHING for BYDAY=+2SU,MO (the defect)",
          du("FREQ=MONTHLY;BYDAY=+2SU,MO"), [])
    check("returns NOTHING for BYDAY=-2SU,MO (the defect)",
          du("FREQ=MONTHLY;BYDAY=-2SU,MO"), [])
    check("drops the unsigned SU from BYDAY=2SU,SU (the defect)",
          du("FREQ=MONTHLY;BYDAY=2SU,SU"),
          ["03-08", "04-12", "05-10", "06-14", "07-12", "08-09"])
except ImportError:
    print("skip python-dateutil not installed")

print()
print("the six adjudicated cases reproduce from naive")
adj = {k: a for k, a in json.load(
    open(os.path.join(ROOT, "corpus", "adjudications.json")))["cases"].items()
    if a.get("finding") == "013-byday-mixed-signed-and-unsigned"}
check("six adjudicated cases", len(adj), 6)
for key, a in sorted(adj.items()):
    rule, ds = key.split("|")
    got = [d.strftime("%Y%m%dT%H%M%S")
           for d in expand(rule, datetime.strptime(ds, "%Y%m%dT%H%M%S"))]
    check(rule, got[:len(a["expected"])], a["expected"])

print()
print("all checks passed" if not FAIL else "%d failure(s)" % len(FAIL))
sys.exit(1 if FAIL else 0)
