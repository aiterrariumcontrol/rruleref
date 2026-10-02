"""Finding 119. Why ical4j passes P6 on every one of the 1,021 rules it scores.

Finding 118 swept the metamorphic properties over eight builds. P6 ("dropping
a part the table marks Limit cannot lose occurrences") failed 13 times on
dateutil, dmfs, libical and rust-rrule, 17 on rrule.js, 18 on ical.js -- and
**zero** times on ical4j and on sabre. Finding 014's standing caution (rule
131) says a property is passed by an implementation that ignores the part the
property varies, so the obvious reading is vacuity. This script measures
whether that is what happened, and the answer is different for the two builds.

All 13 of dateutil's P6 failures have one shape: FREQ=WEEKLY with BYMONTH,
BYDAY and BYSETPOS, dropping BYMONTH. That is exactly the territory of
[finding 022](../022-weekly-bymonth-ordering.md), which names two readings of
RFC 5545 3.3.10 for it -- *filter-instances* and *seed-limit*.

Three measurements, in order:

  A. Is ical4j BYSETPOS-inert here?  Pose the P6 witness with and without
     BYSETPOS to ical4j, sabre and dateutil.
  B. Both readings of 022, generalised to arbitrary WKST and INTERVAL, run
     against P6's own relation on the 13 witnesses.
  C. The two readings' predictions against what ical4j actually returns.

Run: python3 findings/repro/119-why-ical4j-passes-p6.py        (~30 s, needs
the Java and PHP adapters built; --no-adapters runs B alone, pure Python.)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

FMT = "%Y%m%dT%H%M%S"
WD = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

#: The 13 rules P6 failed on, verbatim from findings/data/properties-adapters.json
#: (the dateutil row; dmfs, libical_4edd and rust-rrule fail the same 13).
WITNESSES = [
    ("FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU;BYSETPOS=-1", "20270101T090000"),
    ("FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1", "20260102T090000"),
    ("FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1", "20260705T090000"),
    ("FREQ=WEEKLY;BYDAY=MO,TH;BYMONTH=4,11;WKST=SU;BYSETPOS=1", "20260402T090000"),
    ("FREQ=WEEKLY;BYDAY=MO,TU;BYMONTH=8;BYSETPOS=-1", "20260804T090000"),
    ("FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=9;BYSETPOS=1", "20260902T090000"),
    ("FREQ=WEEKLY;BYDAY=TH,TU;BYMONTH=10,11;BYSETPOS=-1", "20261001T090000"),
    ("FREQ=WEEKLY;BYMONTH=10;BYDAY=SA,SU;BYSETPOS=-1", "20261004T090000"),
    ("FREQ=WEEKLY;BYMONTH=6,7;BYDAY=FR,SA,TH;BYSETPOS=-2", "20240607T090000"),
    ("FREQ=WEEKLY;BYMONTH=8;BYDAY=FR,MO,TH;BYSETPOS=1", "20260803T090000"),
    ("FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU;BYSETPOS=-1", "20260802T090000"),
    ("FREQ=WEEKLY;BYMONTH=9,11;BYDAY=SA,SU,TU;WKST=WE;BYSETPOS=1", "20270904T090000"),
    ("FREQ=WEEKLY;INTERVAL=3;BYMONTH=3;BYDAY=SA,SU,TH;BYSETPOS=-1", "20270307T090000"),
]

HORIZON_DAYS = 1095   # finding 118's bound
CAP = 3000


# -- the two readings of 022, with WKST and INTERVAL ------------------------
def _parse(rule):
    return dict(kv.split("=", 1) for kv in rule.split(";"))


def _pick(cand, setpos):
    if setpos is None:
        return cand
    seen, sel = set(), []
    for p in setpos:
        i = p - 1 if p > 0 else len(cand) + p
        if 0 <= i < len(cand) and i not in seen:
            seen.add(i)
            sel.append(cand[i])
    return sorted(sel)


def expand(rule, dtstart, reading, horizon, cap=CAP, max_weeks=20000):
    """FREQ=WEEKLY under one of 022's two readings. Arbitrary WKST, INTERVAL.

    `reading` is "filter-instances" (BYMONTH restricts the instants the week
    yields) or "seed-limit" (BYMONTH is applied to the week's single seed, and
    BYDAY then expands the whole week -- including into unselected months).

    Deliberately *not* a general expander: it refuses anything outside the
    shape so it cannot silently answer a rule it does not model.
    """
    p = _parse(rule)
    assert p["FREQ"] == "WEEKLY", rule
    extra = set(p) - {"FREQ", "INTERVAL", "BYMONTH", "BYDAY", "BYSETPOS", "WKST"}
    assert not extra, "unmodelled parts %s in %s" % (sorted(extra), rule)
    interval = int(p.get("INTERVAL", 1))
    months = [int(x) for x in p["BYMONTH"].split(",")] if "BYMONTH" in p else None
    days = sorted(WD[x] for x in p["BYDAY"].split(",")) if "BYDAY" in p else None
    setpos = [int(x) for x in p["BYSETPOS"].split(",")] if "BYSETPOS" in p else None
    wkst = WD[p.get("WKST", "MO")]
    out = []
    for n in range(max_weeks):
        seed = dtstart + timedelta(weeks=n * interval)
        if seed > horizon and not out:
            break
        cur = [seed]
        if months is not None and reading == "seed-limit":
            cur = [d for d in cur if d.month in months]
        if days is not None:
            new = []
            for d in cur:
                start = d - timedelta(days=(d.weekday() - wkst) % 7)
                new += [start + timedelta(days=k) for k in range(7)
                        if (start + timedelta(days=k)).weekday() in days]
            cur = sorted(set(new))
        if months is not None and reading == "filter-instances":
            cur = [d for d in cur if d.month in months]
        cur = _pick(cur, setpos)
        out += [d for d in cur if d >= dtstart]
        if seed > horizon:
            break
    out = sorted(set(out))
    # break-on-first-exceed, as src/expanders.py and src/adapter_expanders.py do
    clipped = []
    for t in out:
        if t > horizon:
            break
        clipped.append(t)
        if len(clipped) >= cap:
            break
    return clipped


# -- P6's relation, for this one shape --------------------------------------
def p6(rule, dtstart, reading):
    """Returns the occurrences lost by dropping BYMONTH. Empty list = pass."""
    hor = dtstart + timedelta(days=HORIZON_DAYS)
    a = expand(rule, dtstart, reading, hor)
    wider = ";".join(kv for kv in rule.split(";")
                     if not kv.startswith("BYMONTH="))
    b = expand(wider, dtstart, reading, hor)
    n = min(len(a), len(b)) if (len(a) >= CAP or len(b) >= CAP) else None
    ta, tb = (a[:n], b[:n]) if n else (a, b)
    return sorted(set(ta) - set(tb)), wider


# -- adapters ---------------------------------------------------------------
def ask(name, cases, limit):
    import adapter_expanders as AE
    spec = AE.REGISTRY[name]
    argv = [a.replace("@CP@", AE.classpath()) for a in spec["argv"]]
    cwd = os.path.join(AE.REPO, spec["cwd"]) if spec.get("cwd") else AE.REPO
    env = dict(os.environ, TZ="UTC", LC_ALL="en_US.UTF-8", **spec.get("env", {}))
    lines = [json.dumps({"id": str(i), "rrule": r, "dtstart": d, "limit": limit})
             for i, (r, d) in enumerate(cases)]
    p = subprocess.run(argv, input="\n".join(lines) + "\n", cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=1800)
    out = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        out[int(o["id"])] = o.get("occurrences", "ERROR: %s" % str(o.get("error"))[:60])
    return [out.get(i, "NO REPLY") for i in range(len(cases))]


def fmt(ts, k=6):
    return " ".join(t.strftime("%Y%m%d") for t in ts[:k]) + (" ..." if len(ts) > k else "")


def main():
    adapters = "--no-adapters" not in sys.argv

    if adapters:
        print("== A. is the P6 witness's BYSETPOS inert?  (limit 12)")
        print("   FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU[;BYSETPOS=-1]"
              "  DTSTART:20270101T090000")
        ds = "20270101T090000"
        pair = [("FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU;BYSETPOS=-1", ds),
                ("FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU", ds)]
        for name in ("dateutil", "ical4j", "sabre"):
            got = ask(name, pair, 12)
            same = got[0] == got[1]
            print("   %-10s with BYSETPOS %-44s" % (name, " ".join(x[:8] for x in got[0][:5]) if isinstance(got[0], list) else got[0]))
            print("   %-10s without       %-44s  -> %s"
                  % ("", " ".join(x[:8] for x in got[1][:5]) if isinstance(got[1], list) else got[1],
                     "INERT, BYSETPOS changes nothing" if same else "not inert"))

    print()
    print("== B. P6's relation under 022's two readings, on all 13 witnesses")
    print("   horizon %d days, cap %d -- finding 118's bounds" % (HORIZON_DAYS, CAP))
    tally = {"filter-instances": 0, "seed-limit": 0}
    rows = []
    for rule, dss in WITNESSES:
        dt = datetime.strptime(dss, FMT)
        row = [rule, dss]
        for reading in ("filter-instances", "seed-limit"):
            lost, wider = p6(rule, dt, reading)
            if lost:
                tally[reading] += 1
            row.append(lost)
        rows.append(row)
    print("   %-58s %-16s %-10s %s" % ("RRULE", "DTSTART", "filter-i.", "seed-limit"))
    for rule, dss, lf, ls in rows:
        print("   %-58s %-16s %-10s %s"
              % (rule, dss,
                 "LOSES " + lf[0].strftime("%Y%m%d") if lf else "pass",
                 "LOSES " + ls[0].strftime("%Y%m%d") if ls else "pass"))
    print("   ---")
    print("   filter-instances: %d of 13 fail P6     seed-limit: %d of 13 fail P6"
          % (tally["filter-instances"], tally["seed-limit"]))

    if adapters:
        print()
        print("== C. what ical4j actually returns on the 13, against both readings")
        print("   `ical4j+036` is seed-limit with WKST defaulting to SU rather than")
        print("   RFC 5545's MO -- finding 036's locale-dependent default, which the")
        print("   adapter pins to en-US.")
        got = ask("ical4j", WITNESSES, 64)
        agree = {"filter-instances": 0, "seed-limit": 0, "ical4j+036": 0, "neither": 0}
        for (rule, dss), g in zip(WITNESSES, got):
            dt = datetime.strptime(dss, FMT)
            if not isinstance(g, list):
                print("   %-58s %s" % (rule, g))
                agree["neither"] += 1
                continue
            hor = dt + timedelta(days=HORIZON_DAYS)
            got_t = [t for t in (datetime.strptime(x, FMT) for x in g) if t <= hor]
            su = rule if "WKST=" in rule else rule + ";WKST=SU"
            labels = []
            for label, r in (("filter-instances", rule), ("seed-limit", rule),
                             ("ical4j+036", su)):
                want = expand(r, dt, "filter-instances" if label == "filter-instances"
                              else "seed-limit", hor)
                if want == got_t[:len(want)] and len(want) == len(got_t):
                    labels.append(label)
            for r in labels:
                agree[r] += 1
            if not labels:
                agree["neither"] += 1
            print("   %-58s %s" % (rule, " + ".join(labels) or "NEITHER"))
        print("   ---")
        print("   of 13: filter-instances %d, seed-limit %d, ical4j+036 %d, neither %d"
              % (agree["filter-instances"], agree["seed-limit"],
                 agree["ical4j+036"], agree["neither"]))

    print()
    print("== D. this script's two readings against finding 022's reference")
    print("   repro/022-seed-limit-reading.py is WKST=MO only, so only the")
    print("   witnesses that omit WKST or say MO can be cross-checked.")
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        "ref022", os.path.join(HERE, "022-seed-limit-reading.py"))
    ref = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(ref)
    checked = 0
    for rule, dss in WITNESSES + [(c[1], c[2]) for c in ref.CASES]:
        if "WKST=" in rule and "WKST=MO" not in rule:
            continue
        dt = datetime.strptime(dss, FMT)
        for reading in ("filter-instances", "seed-limit"):
            mine = [t.strftime("%Y%m%d")
                    for t in expand(rule, dt, reading, dt + timedelta(days=4000))][:8]
            theirs = ref.expand(rule, dt, 8, reading)
            assert mine == theirs, (rule, reading, mine, theirs)
        checked += 1
    print("   %d rules x 2 readings: identical to the reference" % checked)

    if not adapters:
        return
    print()
    print("== E. the two readings over 120 generated rules of this shape (seed 11)")
    import random
    rnd = random.Random(11)
    daysets = ["MO,FR", "FR,MO", "MO,TU", "SA,SU", "WE,FR", "MO,WE,FR",
               "FR,SA,TH", "MO,SU,TU", "TH,TU", "MO,TH"]
    monthsets = ["1,6", "6", "1,11", "4,11", "8", "9,11", "10", "3", "2,3,12"]
    gen = []
    for _ in range(120):
        parts = ["FREQ=WEEKLY"]
        iv = rnd.choice([1, 2])
        if iv != 1:
            parts.append("INTERVAL=%d" % iv)
        parts.append("BYMONTH=" + rnd.choice(monthsets))
        parts.append("BYDAY=" + rnd.choice(daysets))
        parts.append("BYSETPOS=" + rnd.choice(["1", "-1", "2", "-2", "1,-1"]))
        w = rnd.choice([None, "SU", "WE"])
        if w:
            parts.append("WKST=" + w)
        ds = datetime(2026 + rnd.randrange(3), rnd.randrange(1, 13),
                      rnd.randrange(1, 28), 9, 0, 0)
        gen.append((";".join(parts), ds.strftime(FMT)))
    LIM = 60
    for name, label, build in (("dateutil", "filter-instances", False),
                               ("ical4j", "seed-limit + WKST default SU", True)):
        got = ask(name, gen, LIM)
        m = o = 0
        odd = []
        for (rule, dss), g in zip(gen, got):
            if not isinstance(g, list):
                o += 1
                continue
            dt = datetime.strptime(dss, FMT)
            r = (rule if "WKST=" in rule else rule + ";WKST=SU") if build else rule
            want = expand(r, dt, "seed-limit" if build else "filter-instances",
                          dt + timedelta(days=100000), cap=LIM)
            if [t.strftime(FMT) for t in want] == g:
                m += 1
            else:
                o += 1
                odd.append((rule, dss, [t.strftime(FMT) for t in want][:1], g[:1]))
        print("   %-10s == %-30s %3d of 120" % (name, label, m))
        for rule, dss, mine, theirs in odd:
            print("      %-56s %s  mine %s  %s %s"
                  % (rule, dss, mine[0], name, theirs[0]))


if __name__ == "__main__":
    main()
