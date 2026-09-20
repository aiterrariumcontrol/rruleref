"""Finding 064: can the field be scored at a 300-year horizon?

Builds the 67 non-empty horizon-bounded cases with their 300-year expectations
and puts them to six adapters at limit=8 with NO adapter-side window, then
reports agreement. Read the ical4j and dmfs rows with standing rule 49 in hand:
both Java adapters hardcode the corpus's own 10958-day horizon, so their
disagreement here is my instrument, not the subject.

    python3 findings/repro/064-far-future-adapters.py
"""
import sys, os, json, glob, subprocess, tempfile
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env; env.add_dateutil_to_path()
import naive
from differ import du_expand

N, DAYS, FMT = 8, 109575, "%Y%m%dT%H%M%S"
CP = "%s/conformance/adapters/java/classes:%s" % (
    ROOT, ":".join(sorted(glob.glob(ROOT + "/conformance/adapters/java/libs/*.jar"))))
LIBICAL_PREFIX = "/home/agent/terrarium/scratch/libical-install-4edd"

ADAPTERS = [
    ("dateutil",  ["python3", ROOT + "/conformance/adapters/dateutil_adapter.py"], {}),
    ("rrulejs",   ["node", ROOT + "/conformance/adapters/rrulejs_adapter.js"], {}),
    ("rustrrule", [ROOT + "/conformance/adapters/rust/target/release/rustrrule_adapter"], {}),
    ("libical",   [ROOT + "/conformance/adapters/c/libical_adapter"],
                  {"LD_LIBRARY_PATH": LIBICAL_PREFIX + "/lib"}),
    ("ical4j",    ["java", "-Duser.language=en", "-Duser.country=US", "-cp", CP, "Ical4jAdapter"], {}),
    ("dmfs",      ["java", "-Duser.language=en", "-Duser.country=GB", "-cp", CP, "DmfsAdapter"], {}),
]

cases, expect = [], {}
for c in json.load(open(ROOT + "/corpus/corroborated.json"))["cases"]:
    if c["expect_bound"] != "horizon" or not c["expect"]:
        continue
    ds = datetime.strptime(c["dtstart"], FMT)
    h = ds + timedelta(days=DAYS)
    mine = [x.strftime(FMT) for x in naive.expand(c["rrule"], ds, horizon=h, limit=N) if x <= h][:N]
    theirs = du_expand(c["rrule"], ds, N)
    assert not isinstance(theirs, str) and [x.strftime(FMT) for x in theirs if x <= h][:N] == mine
    cid = "h%03d" % len(cases)
    cases.append({"id": cid, "rrule": c["rrule"], "dtstart": c["dtstart"], "limit": N})
    expect[cid] = mine

print("%d cases; maximum year reached: %s"
      % (len(cases), max(max(v)[:4] for v in expect.values())))
stdin = "".join(json.dumps(c) + "\n" for c in cases)

for name, cmd, extra in ADAPTERS:
    envv = dict(os.environ, TZ="UTC", **extra)
    try:
        out = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                             env=envv, timeout=1800).stdout
    except Exception as e:
        print("%-10s could not run: %s" % (name, e)); continue
    ok = differ = err = miss = 0
    got = {}
    for line in out.splitlines():
        try: d = json.loads(line)
        except Exception: continue
        got[d.get("id")] = d
    for c in cases:
        d = got.get(c["id"])
        if d is None: miss += 1
        elif d.get("error"): err += 1
        elif d.get("occurrences") == expect[c["id"]]: ok += 1
        else: differ += 1
    print("%-10s ok=%-3d differ=%-3d error=%-3d missing=%d" % (name, ok, differ, err, miss))
