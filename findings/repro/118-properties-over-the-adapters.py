"""Finding 118. The metamorphic properties, run against the adapter builds.

Reads `findings/data/properties-adapters.json` (produced by
`src/run_properties_adapters.py`) and prints the three things finding 118
claims, so that every figure in its prose is literal output of this script
rather than a number retyped from a run (standing rule 123).

    python3 findings/repro/118-properties-over-the-adapters.py
    python3 findings/repro/118-properties-over-the-adapters.py --check

Section 1 asks the `rrule.js` adapter five questions live -- it needs node and
takes about a second -- because the sharpest statement of the mechanism is a
pair of answers to the same set written two ways. Sections 2 and 3 are
re-readings of the recorded sweep and need nothing but the data file.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "findings", "data", "properties-adapters.json")
INPROC = os.path.join(ROOT, "findings", "data", "properties.json")
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")

CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok)))
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))


PROBES = [
    ("a", "FREQ=DAILY;BYHOUR=9,8", "descending list"),
    ("b", "FREQ=DAILY;BYHOUR=8,9", "same set, ascending"),
    ("c", "FREQ=DAILY;BYHOUR=8,9,8", "ascending with 8 repeated"),
    ("d", "FREQ=MINUTELY;BYSECOND=0,30", "no repeat"),
    ("e", "FREQ=MINUTELY;BYSECOND=0,30,0", "same set, 0 repeated"),
]
DTSTART = "20260302T090000"


def probe_rrulejs():
    payload = "".join(json.dumps({"id": i, "rrule": r, "dtstart": DTSTART,
                                  "limit": 5}) + "\n"
                      for i, r, _ in PROBES)
    p = subprocess.run(["node", "conformance/adapters/rrulejs_adapter.js"],
                       input=payload, cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, TZ="UTC"), timeout=120)
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r.get("occurrences", ["ERROR: " + str(r.get("error"))])
    return out


def section1():
    print("=== 1. rrule.js 2.8.1, DTSTART:%s, limit 5 ===" % DTSTART)
    got = probe_rrulejs()
    for i, rule, note in PROBES:
        print("  %-30s %-27s %s" % (rule, "(%s)" % note, " ".join(
            t[9:] for t in got[i])))
    print()
    check("BYHOUR=9,8 and BYHOUR=8,9 are the same set and differ in output",
          got["a"] != got["b"])
    check("BYHOUR=8,9 is non-decreasing",
          got["b"] == sorted(got["b"]))
    check("BYHOUR=9,8 is NOT non-decreasing",
          got["a"] != sorted(got["a"]))
    check("repeating a BYHOUR value emits a repeated instant",
          len(set(got["c"])) < len(got["c"]))
    check("BYSECOND=0,30 emits no repeated instant",
          len(set(got["d"])) == len(got["d"]))
    check("BYSECOND=0,30,0 emits the DTSTART instant twice",
          got["e"][0] == got["e"][1])
    return got


def keys(d, adapter, pid, status="fail"):
    """Failing (rule, dtstart) pairs. `status` matters: an adapter that timed
    out on a rule produced no answer, and counting that as a property failure
    would credit the property with a result it did not obtain."""
    return {(x["rrule"], x["dtstart"])
            for x in d["adapters"][adapter]["failures"]
            if x["property"] == pid and x["status"] == status}


def section2(d):
    print("\n=== 2. tally over %d corroborated, synchronized rules ==="
          % d["n_rules"])
    pids = [p["id"] for p in d["properties"]]
    hedged = {p["id"]: p["hedged"] for p in d["properties"]}
    print("  %-14s %s" % ("", "  ".join("%-9s" % p for p in pids)))
    print("  %-14s %s" % ("", "  ".join(
        "%-9s" % ("hedged" if hedged[p] else "") for p in pids)))
    for name in sorted(d["adapters"]):
        a = d["adapters"][name]
        row = []
        for pid in pids:
            t = a["tally"].get(pid, {})
            f = t.get("fail", 0) + t.get("error", 0)
            row.append("%-9s" % (str(f) if f else "."))
        print("  %-14s %s" % (name, "  ".join(row)))
    print("\n  '.' is no failure. A hedged property's failure is a question,")
    print("  not a defect report (finding 014).")
    print("\n  cost, per adapter: %s" % ", ".join(
        "%s %.0fs" % (n, d["adapters"][n]["elapsed_seconds"])
        for n in sorted(d["adapters"])))
    some = d["adapters"][sorted(d["adapters"])[0]]
    ncases = sum(1 for l in open(CASES) if l.strip())
    print("\n  distinct (rule, dtstart) pairs posed per adapter: %d"
          % some["distinct_keys"])
    print("  scorable cases in conformance/cases.ndjson:            %d" % ncases)
    print("  ratio: %.1fx, from the same %d rules and no new expected values"
          % (some["distinct_keys"] / float(ncases), d["n_rules"]))


def section3(d):
    print("\n=== 3. are P5's and P6's failures facts about the RFC? ===")
    names = sorted(d["adapters"])
    for pid in ("P5", "P6"):
        sets = {n: keys(d, n, pid) for n in names}
        errs = {n: len(keys(d, n, pid, "error")) for n in names}
        ref = sets["dateutil"]
        print("  %s: dateutil %d" % (pid, len(ref)))
        repro = []
        for n in names:
            if n == "dateutil":
                continue
            s = sets[n]
            if ref <= s:
                repro.append(n)
            print("     %-14s %3d   shared %3d   its own %3d   missing %3d"
                  "   (errors %d)"
                  % (n, len(s), len(ref & s), len(s - ref), len(ref - s),
                     errs[n]))
        print("     reproduces all %d of dateutil's: %s"
              % (len(ref), ", ".join(repro) or "none"))
        print("     does not: %s" % ", ".join(
            n for n in names if n != "dateutil" and n not in repro))


WKST_PROBE = ("FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1;WKST=%s",
              "20260102T090000")
#: Builds to ask whether WKST moves them at all, and how to launch them. Kept
#: short on purpose: the point needs one build that responds and one that does
#: not, not a second copy of the registry.
WKST_BUILDS = [
    ("dateutil", ["python3", "conformance/adapters/dateutil_adapter.py"], None),
    ("sabre", ["php", "vobject_adapter.php"], "conformance/adapters/php"),
    ("icaljs", ["node", "conformance/adapters/icaljs_adapter.js"], None),
]


def section3b():
    """A property is passed by an implementation that ignores its subject.

    P5 varies WKST and asks whether the answer moves. An implementation that
    never reads WKST passes it with nothing to its credit, so "did not
    reproduce P5's 23" has two possible meanings and only a direct probe
    separates them.
    """
    print("\n=== 3b. does a build that passes P5 respond to WKST at all? ===")
    print("  %s" % (WKST_PROBE[0] % "<day>"))
    print("  DTSTART:%s, limit 4\n" % WKST_PROBE[1])
    moved = {}
    for name, argv, cwd in WKST_BUILDS:
        payload = "".join(json.dumps(
            {"id": d, "rrule": WKST_PROBE[0] % d, "dtstart": WKST_PROBE[1],
             "limit": 4}) + "\n" for d in ("MO", "TH"))
        try:
            p = subprocess.run(
                argv, input=payload, cwd=os.path.join(ROOT, cwd) if cwd else ROOT,
                capture_output=True, text=True, timeout=180,
                env=dict(os.environ, TZ="UTC", LC_ALL="en_US.UTF-8"))
        except Exception as e:
            print("  %-14s could not run: %s" % (name, e))
            continue
        got = {}
        for line in p.stdout.splitlines():
            if line.strip():
                r = json.loads(line)
                got[r["id"]] = r.get("occurrences", ["ERROR"])
        if "MO" not in got or "TH" not in got:
            print("  %-14s no answer" % name)
            continue
        for d in ("MO", "TH"):
            print("  %-14s WKST=%s  %s" % (name, d, " ".join(
                t[:8] for t in got[d])))
        moved[name] = got["MO"] != got["TH"]
        print("  %-14s WKST moves the answer: %s\n" % ("", moved[name]))
    check("dateutil responds to WKST on this rule", moved.get("dateutil"))
    check("sabre does not respond to WKST on this rule",
          moved.get("sabre") is False)
    check("ical.js does not respond to WKST on this rule",
          moved.get("icaljs") is False)


def section4(d):
    print("\n=== 4. the bridge against the in-process expander ===")
    if not os.path.exists(INPROC):
        print("  findings/data/properties.json absent; skipped")
        return
    ip = json.load(open(INPROC))
    if ip["n_rules"] != d["n_rules"]:
        print("  different rule counts (%d vs %d); not comparable"
              % (ip["n_rules"], d["n_rules"]))
        return
    a = ip["tally"]["dateutil"]
    b = d["adapters"]["dateutil"]["tally"]
    print("  in-process dateutil : %s" % json.dumps(a, sort_keys=True))
    print("  adapter   dateutil : %s" % json.dumps(b, sort_keys=True))
    check("adapter-dateutil tally equals in-process dateutil tally", a == b)
    ka = {(x["property"], x["rrule"], x["dtstart"]) for x in ip["failures"]
          if x["expander"] == "dateutil"}
    kb = {(x["property"], x["rrule"], x["dtstart"])
          for x in d["adapters"]["dateutil"]["failures"]}
    check("and the same failing (property, rule, dtstart) triples", ka == kb,
          "%d vs %d" % (len(ka), len(kb)))


def classpath():
    import glob
    jars = sorted(glob.glob(os.path.join(
        ROOT, "conformance/adapters/java/libs/*.jar")))
    return ":".join(["conformance/adapters/java/classes"]
                    + [os.path.relpath(j, ROOT) for j in jars])


def section5():
    """ical4j's P8 column, as one rule asked twice.

    1097 of 1728 is too large a number to leave as a tally. The mechanism is
    finding 051's defect A -- a pipeline that never deduplicates -- and the
    cleanest statement of it is that repeating a BYDAY value doubles the
    expansion exactly.
    """
    print("\n=== 5. ical4j and a repeated BYDAY value ===")
    rules = [("base", "FREQ=DAILY;BYDAY=FR"), ("dup", "FREQ=DAILY;BYDAY=FR,FR")]
    payload = "".join(json.dumps({"id": i, "rrule": r,
                                  "dtstart": "20260102T090000",
                                  "limit": 400}) + "\n" for i, r in rules)
    try:
        p = subprocess.run(
            ["java", "-Duser.language=en", "-Duser.country=US",
             "-cp", classpath(), "Ical4jAdapter"],
            input=payload, cwd=ROOT, capture_output=True, text=True,
            timeout=300, env=dict(os.environ, TZ="UTC"))
    except Exception as e:
        print("  could not run ical4j: %s" % e)
        return
    got = {}
    for line in p.stdout.splitlines():
        if line.strip() and line.lstrip().startswith("{"):
            r = json.loads(line)
            got[r["id"]] = r.get("occurrences", [])
    if "base" not in got or "dup" not in got:
        print("  no answer from ical4j")
        return
    print("  DTSTART:20260102T090000, limit 400")
    for i, r in rules:
        o = got[i]
        print("  %-22s %d occurrences, %d distinct, first four: %s"
              % (r, len(o), len(set(o)), " ".join(t[:8] for t in o[:4])))
    # At a fixed limit the doubling cannot show up as a longer list -- both
    # answers are truncated at 400. It shows up as half the distinct instants
    # covering half the span, which is the same fact seen through the limit.
    check("ical4j repeats every instant when BYDAY repeats a value",
          len(set(got["dup"])) * 2 == len(got["dup"]),
          "%d distinct in %d occurrences" % (len(set(got["dup"])),
                                             len(got["dup"])))
    check("the base rule repeats nothing",
          len(set(got["base"])) == len(got["base"]),
          "%d distinct in %d" % (len(set(got["base"])), len(got["base"])))
    check("so at one limit the duplicated rule covers half the span",
          sorted(set(got["dup"])) == sorted(set(got["base"]))[:len(set(got["dup"]))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero if any check fails")
    a = ap.parse_args()
    if not os.path.exists(DATA):
        raise SystemExit("run src/run_properties_adapters.py first: %s" % DATA)
    d = json.load(open(DATA))
    section1()
    section2(d)
    section3(d)
    section3b()
    section4(d)
    section5()
    bad = [l for l, ok in CHECKS if not ok]
    print("\n%d checks, %d failed" % (len(CHECKS), len(bad)))
    if a.check and bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
