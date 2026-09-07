"""Reference adapter: python-dateutil. ~40 lines, which is the point --
the protocol is meant to be a morning's work in any language.

    python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
try:
    import env
    env.add_dateutil_to_path()
except Exception:
    pass  # a system-wide dateutil is fine; this only finds the vendored one
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    c = json.loads(line)
    try:
        r = rrulestr("RRULE:" + c["rrule"], dtstart=datetime.strptime(c["dtstart"], FMT))
        occ = []
        for x in r:
            if len(occ) >= c["limit"]:
                break
            occ.append(x.strftime(FMT))
        out = {"id": c["id"], "occurrences": occ}
    except Exception as e:                       # a parse refusal is a result
        out = {"id": c["id"], "error": "%s: %s" % (type(e).__name__, e)}
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
