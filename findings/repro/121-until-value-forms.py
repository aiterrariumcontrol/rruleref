"""121 -- What nine builds do with an UNTIL whose value type does not match DTSTART.

Three independent reports filed against calendar software between 2026-09-29
and 2026-10-01 are about the *form* of an UNTIL value rather than about
recurrence arithmetic:

    FabianLizama/loa-to-calendar#5  UNTIL drops the last day of the semester
    mui/mui-x#23737                 UNTIL ending in Z read in the event's zone
    mui/mui-x#23738                 support the date-only UNTIL form

This repository's corpus cannot see any of that. All 1727 cases carry a
floating DATE-TIME `dtstart`, and all 28 cases that use UNTIL at all spell it
one way -- `UNTIL=20260305T090000`, a floating DATE-TIME. Zero date-only, zero
UTC. So the corpus covers exactly the one form RFC 5545 3.3.10 *requires* for
this DTSTART and none of the forms producers are reported to emit:

    "The value of the UNTIL rule part MUST have the same value type as the
     DTSTART property. Furthermore, if the DTSTART property is specified as a
     date with local time, then the UNTIL rule part MUST also be specified as
     a date with local time."

Both off-baseline arms below are therefore MUST violations of a rule the
adapter protocol's `dtstart` makes unavoidable, and this probe asks what the
builds do with them -- refuse, accept as equivalent, or accept and differ.
A refusal is a result, not a failure, and is reported as one.

The two in-arm questions are separate from the value-type question and hold
regardless: UNTIL is inclusive, and an UNTIL that falls between instances
stops at the preceding one.

Usage:  python3 findings/repro/121-until-value-forms.py [--adapter NAME,...]
        python3 findings/repro/121-until-value-forms.py --check  # verify
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
import adapter_expanders as A           # noqa: E402  -- for REGISTRY only

DTSTART = "20260301T090000"
#: 2026-03-05 is a Thursday; 09:00:00 is synchronized with every base rule.
BASES = [
    ("daily",        "FREQ=DAILY"),
    ("daily-byday",  "FREQ=DAILY;BYDAY=MO,TH"),
    ("weekly",       "FREQ=WEEKLY"),
    ("hourly",       "FREQ=HOURLY;BYHOUR=9"),
    ("monthly",      "FREQ=MONTHLY;BYMONTHDAY=5"),
    ("yearly",       "FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=5"),
]
#: arm -> the UNTIL value spliced into every base.
ARMS = [
    ("local",     "20260305T090000"),   # conformant for a floating DTSTART
    ("date-only", "20260305"),          # MUST violation; mui-x#23738's form
    ("utc",       "20260305T090000Z"),  # MUST violation; mui-x#23737's form
]
#: the two questions that do not depend on the value type, both on `daily`.
EDGE = [
    ("inclusive-synchronized", "FREQ=DAILY;UNTIL=20260305T090000"),
    ("unsynchronized-earlier", "FREQ=DAILY;UNTIL=20260305T083000"),
]
LIMIT = 64
#: both zones are measured by default. Under UTC a UTC-stamped UNTIL and a
#: floating one denote the same instant, so that run alone cannot tell a build
#: that honours the Z from one that ignores it. 2026-03-05 is CST, UTC-6.
TZS = ("UTC", "America/Chicago")


def cases():
    out = []
    for bname, rule in BASES:
        for arm, val in ARMS:
            out.append(("%s/%s" % (bname, arm), "%s;UNTIL=%s" % (rule, val)))
    for name, rule in EDGE:
        out.append(("edge/%s" % name, rule))
    return out


def run(name, cs, tz="UTC"):
    """Speak conformance/PROTOCOL.md to one adapter, one subprocess.

    `tz` overrides the `TZ=UTC` that `src/adapter_expanders.py` pins. Under
    UTC a UTC-stamped UNTIL and a floating one denote the same instant, so
    that run cannot tell a build that ignores the `Z` from one that honours
    it. A second run in a zone with a non-zero offset separates them.
    """
    spec = A.REGISTRY[name]
    argv = [t.replace("@CP@", A.classpath()) for t in spec["argv"]]
    cwd = os.path.join(REPO, spec["cwd"]) if spec.get("cwd") else REPO
    env = dict(os.environ, TZ=tz, LC_ALL="en_US.UTF-8", **spec.get("env", {}))
    stdin = "".join(json.dumps({"id": cid, "rrule": r, "dtstart": DTSTART,
                                "limit": LIMIT}) + "\n" for cid, r in cs)
    t0 = time.time()
    p = subprocess.run(argv, cwd=cwd, env=env, input=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=900)
    got = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        got[o["id"]] = o
    return got, time.time() - t0, p.returncode, p.stderr[-400:]


def verdict(o):
    """One short token per case, so a grid is readable."""
    if o is None:
        return "no-line"
    if "error" in o:
        return "error"
    return "n=%d last=%s" % (len(o["occurrences"]),
                             o["occurrences"][-1] if o["occurrences"] else "-")


def grid(names, tz, cs):
    """One TZ run: adapter -> {case id -> verdict token}."""
    rows = {}
    for name in names:
        got, secs, rc, err = run(name, cs, tz=tz)
        # The wall time is printed but deliberately NOT stored. It supports no
        # claim in the finding, and findings/data/*.json is the global pool
        # that findings/repro/091-figure-provenance-audit.py searches: an
        # incidental `0.1` in here silently backed another finding's declared
        # unbacked figure. An artifact should contain the measurement and
        # nothing else.
        print("  %-13s rc=%d %5.1fs" % (name, rc, secs))
        rows[name] = {"rc": rc, "stderr_tail": err,
                      "rows": {cid: verdict(got.get(cid)) for cid, _ in cs}}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="all")
    ap.add_argument("--tz", default=",".join(TZS),
                    help="comma-separated. The protocol pins TZ=UTC; a "
                         "non-UTC zone is what separates a build that "
                         "honours a UTC-stamped UNTIL from one that ignores "
                         "the Z")
    ap.add_argument("--check", action="store_true",
                    help="re-measure and compare to the committed data file "
                         "instead of rewriting it; exit 1 on any difference")
    ap.add_argument("--out", default=os.path.join(
        REPO, "findings", "data", "until-value-forms.json"))
    a = ap.parse_args()
    names = (sorted(A.REGISTRY) if a.adapter == "all" else a.adapter.split(","))
    zones = a.tz.split(",")
    cs = cases()
    print("%d cases (%d bases x %d arms + %d edge), dtstart=%s, limit=%d"
          % (len(cs), len(BASES), len(ARMS), len(EDGE), DTSTART, LIMIT))

    if a.check:
        want = json.load(open(a.out))
        bad = 0
        for tz in zones:
            got = grid(names, tz, cs)
            for name in names:
                ref = want["runs"].get(tz, {}).get(name)
                if ref is None:
                    print("  no committed run for %s/%s" % (tz, name))
                    bad += 1
                    continue
                for cid, _ in cs:
                    if ref["rows"][cid] != got[name]["rows"][cid]:
                        print("  DIFF %s/%s %s: committed %r, now %r"
                              % (tz, name, cid, ref["rows"][cid],
                                 got[name]["rows"][cid]))
                        bad += 1
            print("  %s: %d adapters checked" % (tz, len(names)))
        print("FAIL: %d differences" % bad if bad else "ok: identical")
        return 1 if bad else 0

    out = {"about": "121: UNTIL value forms against the adapter protocol",
           "dtstart": DTSTART, "limit": LIMIT,
           "cases": {cid: r for cid, r in cs}, "runs": {}}
    if os.path.exists(a.out):           # merge, so one zone can be re-run
        try:
            out["runs"] = json.load(open(a.out)).get("runs", {})
        except ValueError:
            pass
    for tz in zones:
        print("TZ=%s" % tz)
        got = grid(names, tz, cs)
        out["runs"].setdefault(tz, {}).update(got)
        for name in names:
            for cid, _ in cs:
                print("      %-28s %s" % (cid, got[name]["rows"][cid]))
        with open(a.out, "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
            fh.write("\n")
    print("wrote %s" % os.path.relpath(a.out, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
