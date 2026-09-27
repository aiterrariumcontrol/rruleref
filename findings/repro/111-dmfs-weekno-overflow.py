#!/usr/bin/env python3
"""Finding 111 -- dmfs lib-recur: week 53 of a 52-week year is December 32nd.

dmfs lib-recur 0.17.1 has four cases in the `fail` bucket of this corpus, the
smallest unpartitioned bucket finding 109 named. This script partitions it and
backs the partition with measurement rather than with labels.

THREE of the four are one defect. ByWeekNoYearlyExpander.expand() normalises a
negative BYWEEKNO against getWeeksPerYear(year) and then, when the resulting
week number is LARGER than that count, does not skip the week. It emits

    setMonthAndDayOfMonth(instance, packedMonth(last), dayOfMonth(last) + 1)

where `last` is the last day of the year -- December 31 -- so the instance it
adds is DECEMBER 32nd, with no year adjustment. (The mirror branch, for a
normalised week number of zero or less, adds month 0 day 0.) Everything
downstream then works from a day that does not exist.

What that produces is measured here, not argued:

  * a BYDAY expansion around the phantom day yields SIX days, never seven, in
    every short year where it yields anything. An ISO week has seven days, so
    this is wrong under every reading of the year boundary -- findings 002, 008
    and 059 all decline to say which year owns a straddling week, and this
    claim does not need that question answered.
  * in some short years BYWEEKNO=52 and BYWEEKNO=53 select THE SAME DAY. Two
    distinct week numbers, one week.
  * in some short years `BYDAY=MO` yields nothing while `BYDAY=MO,TU` yields a
    MONDAY. Adding a value to an unordered by-part list made an occurrence of
    an already-listed value appear. That is a contradiction with no semantics
    argued, the same shape finding 107 used.
  * BYWEEKNO=54 is rejected as out of range. The library validates 1..53 and
    then treats 53 as unconditional, which it is not: ISO 8601 gives a year 53
    weeks only when it is long.

THE FOURTH CASE IS NOT THIS DEFECT AND IS NOT CALLED ONE. 39497d02ae1e is
FREQ=YEARLY;INTERVAL=2;BYWEEKNO=52, a week number that exists in every year.
dmfs's answer there is exactly: the DTSTART weekday of ISO week 52 (the
`dtstart_fill` reading), in years counted by INTERVAL from the CALENDAR year of
DTSTART, with DTSTART itself not injected. The corpus records `week_based_year`
and `week_based_year+dtstart_fill` for this case but not this combination, so
the case lands in `fail` for want of a recorded reading rather than for a
defect. The predictor below reproduces dmfs's 25 occurrences element for
element, which is what makes that a measurement instead of an opinion.

  python3 findings/repro/111-dmfs-weekno-overflow.py             # ~1 min
  python3 findings/repro/111-dmfs-weekno-overflow.py --no-adapters   # skips the re-score
  python3 findings/repro/111-dmfs-weekno-overflow.py --check     # the guard
  WRITE_111=1 python3 findings/repro/111-dmfs-weekno-overflow.py --write

Needs a JVM and the compiled adapter classes; without them it exits 0 and says
so, like finding 110 does for rrule.js.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "findings", "data", "111-dmfs-weekno-overflow.json")
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402

CLASSES = os.path.join(ROOT, "conformance", "adapters", "java", "classes")
LIBS = os.path.join(ROOT, "conformance", "adapters", "java", "libs")
CP = CLASSES + os.pathsep + os.path.join(LIBS, "*")

# The whole fail bucket, as published. Re-scoring checks it rather than trusting it.
# Three labels, not two, and the third one is why. The necessity test below
# REFUSED the two-label version: dropping 53 from 6f5eaa18e870 left dmfs still
# disagreeing, because that case carries the dtstart_fill reading as well.
A_ONLY = ["c6d0be82ba4a", "36fa68873abe"]
A_AND_B = ["6f5eaa18e870"]
B_ONLY = ["39497d02ae1e"]
DEFECT_A = A_ONLY + A_AND_B
READING_B = B_ONLY

YEARS = list(range(2020, 2101))
ALLDAYS = "MO,TU,WE,TH,FR,SA,SU"


def have_java():
    return (shutil.which("java") is not None
            and os.path.isfile(os.path.join(CLASSES, "DmfsAdapter.class")))


def dmfs(cases):
    """cases: list of dicts with id/dtstart/rrule/limit -> {id: reply}."""
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    r = subprocess.run(["java", "-Duser.language=en", "-Duser.country=US",
                        "-cp", CP, "DmfsAdapter"],
                       input=payload, capture_output=True, text=True,
                       cwd=ROOT, env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise SystemExit("dmfs adapter failed:\n" + r.stderr[-2000:])
    out = {}
    for line in r.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = o
    return out


def d(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def iso_weeks_in(year):
    return datetime.date(year, 12, 28).isocalendar()[1]


def iso_week_days(year, week):
    monday = datetime.date.fromisocalendar(year, week, 1)
    return ["%s%s" % ((monday + datetime.timedelta(days=i)).strftime("%Y%m%d"),
                      "T090000") for i in range(7)]


def reference(dtstart, rrule, limit):
    """python-dateutil, which scores 1727/1727 on this corpus."""
    env.add_dateutil_to_path()
    from dateutil.rrule import rrulestr
    start = datetime.datetime.strptime(dtstart, "%Y%m%dT%H%M%S")
    it = rrulestr("RRULE:" + rrule, dtstart=start)
    out = []
    for occ in it:
        out.append(occ.strftime("%Y%m%dT%H%M%S"))
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# part 1 -- the bucket


def fail_bucket(run_adapters):
    if not run_adapters:
        return None
    tmp = os.path.join(ROOT, ".111-dmfs-score.json")
    subprocess.run([sys.executable, os.path.join(ROOT, "conformance", "score.py"),
                    "--json", tmp, "--", "java", "-Duser.language=en",
                    "-Duser.country=US", "-cp", CP, "DmfsAdapter"],
                   cwd=ROOT, env=dict(os.environ, TZ="UTC"),
                   capture_output=True, text=True)
    if not os.path.exists(tmp):
        raise SystemExit("score.py wrote no output file for dmfs")
    with open(tmp) as fh:
        s = json.load(fh)
    os.unlink(tmp)
    return sorted(x["case"]["id"] for x in s["failures"] if x["bucket"] == "fail")


# ---------------------------------------------------------------------------
# part 2 -- what week 53 is, year by year


def sweep():
    """For every year 2020-2100: the BYWEEKNO=53 window and the BYWEEKNO=52 one."""
    cases = []
    for y in YEARS:
        until = "%04d0110T000000" % (y + 1)
        for tag, wk in (("w53", 53), ("w52", 52)):
            cases.append({"id": "%s-%d" % (tag, y),
                          "dtstart": "%04d0101T090000" % y,
                          "rrule": "FREQ=YEARLY;BYWEEKNO=%d;BYDAY=%s;UNTIL=%s"
                                   % (wk, ALLDAYS, until),
                          "limit": 30})
        # the monotonicity probe: one value against two.
        for tag, byday in (("mo", "MO"), ("motu", "MO,TU")):
            cases.append({"id": "%s-%d" % (tag, y),
                          "dtstart": "%04d0101T090000" % y,
                          "rrule": "FREQ=YEARLY;BYWEEKNO=53;BYDAY=%s;UNTIL=%s"
                                   % (byday, until),
                          "limit": 30})
    got = dmfs(cases)
    rows = {}
    for y in YEARS:
        rows[y] = {k: (got["%s-%d" % (k, y)].get("occurrences") or [])
                   for k in ("w53", "w52", "mo", "motu")}
    return rows


def analyse(rows):
    long_years, short_ok, short_sizes = [], [], {}
    duplicates, monotonicity = [], []
    problems = []
    for y in YEARS:
        r = rows[y]
        n = iso_weeks_in(y)
        if n == 53:
            long_years.append(y)
            if r["w53"] != iso_week_days(y, 53):
                problems.append("%d is a 53-week year and week 53 is wrong" % y)
            continue
        # short year: ISO has no week 53 at all, so the correct answer is nothing.
        short_sizes[len(r["w53"])] = short_sizes.get(len(r["w53"]), 0) + 1
        if not r["w53"]:
            short_ok.append(y)
            continue
        if len(r["w53"]) == 7:
            problems.append("%d yielded a full seven-day week for week 53" % y)
        if r["w53"][0] == r["w52"][0]:
            duplicates.append(y)
        mo = [s for s in r["mo"] if s in r["w53"]]
        motu = [s for s in r["motu"] if s in r["w53"] and d(s).weekday() == 0]
        if not mo and motu:
            monotonicity.append(y)
        if r["w52"] != iso_week_days(y, 52):
            problems.append("%d: week 52 itself is not ISO week 52" % y)
    return {
        "long_years": long_years,
        "short_years_correctly_empty": short_ok,
        "short_year_window_sizes": short_sizes,
        "weeks_52_and_53_same_day": duplicates,
        "monday_appears_only_when_tuesday_is_added": monotonicity,
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# part 3 -- necessity, on the three corpus cases


def corpus():
    out = {}
    with open(os.path.join(ROOT, "conformance", "cases.ndjson")) as fh:
        for line in fh:
            c = json.loads(line)
            out[c["id"]] = c
    return out


def drop_53(rrule):
    parts = []
    for p in rrule.split(";"):
        if p.startswith("BYWEEKNO="):
            keep = [v for v in p[len("BYWEEKNO="):].split(",") if v != "53"]
            if not keep:
                return None
            p = "BYWEEKNO=" + ",".join(keep)
        parts.append(p)
    return ";".join(parts)


def dtstart_fill(case, rrule):
    """The reading dmfs takes when BYWEEKNO has no BYDAY beside it: of the days
    the reference expands the week into, keep the DTSTART weekday only."""
    env.add_dateutil_to_path()
    from dateutil.rrule import rrulestr
    start = datetime.datetime.strptime(case["dtstart"], "%Y%m%dT%H%M%S")
    out = []
    for i, occ in enumerate(rrulestr("RRULE:" + rrule, dtstart=start)):
        if occ.weekday() == start.weekday():
            out.append(occ.strftime("%Y%m%dT%H%M%S"))
            if len(out) >= case["limit"]:
                break
        if i > 20000:
            break
    return out


def necessity(cases):
    """Removing 53 must remove the week-53 divergence and nothing else.

    For the two cases labelled A alone, dmfs must then agree with the reference
    exactly. For 6f5eaa18e870, which also takes the dtstart_fill reading, it
    must agree with that reading of the reduced rule -- so the reduced rule is
    still a live test and not a weakened one."""
    probes, reduced = [], {}
    for cid in DEFECT_A:
        c = cases[cid]
        reduced[cid] = drop_53(c["rrule"])
        probes.append({"id": cid, "dtstart": c["dtstart"], "rrule": reduced[cid],
                       "limit": c["limit"]})
    got = dmfs(probes)
    result = {}
    for cid in DEFECT_A:
        c = cases[cid]
        have = got[cid].get("occurrences") or []
        if cid in A_AND_B:
            want, against = dtstart_fill(c, reduced[cid]), "the dtstart_fill reading"
        else:
            want, against = reference(c["dtstart"], reduced[cid], c["limit"]), "the reference"
        result[cid] = {"reduced_rule": reduced[cid], "compared_against": against,
                       "agrees": have == want}
    return result


# ---------------------------------------------------------------------------
# part 4 -- the fourth case, predicted element for element


def predict_b(case):
    """dtstart_fill weekday of ISO week 52, calendar-year INTERVAL anchor."""
    start = d(case["dtstart"])
    isoday = start.isoweekday()
    hhmmss = case["dtstart"][8:]
    out, y = [], start.year
    while len(out) < case["limit"]:
        try:
            day = datetime.date.fromisocalendar(y, 52, isoday)
        except ValueError:
            day = None
        if day is not None and day >= start:
            out.append(day.strftime("%Y%m%d") + hhmmss)
        y += 2
        if y > start.year + 400:
            break
    return out


# ---------------------------------------------------------------------------


def compute(run_adapters):
    cases = corpus()
    rows = sweep()
    result = analyse(rows)
    result["necessity"] = necessity(cases)

    b = cases[READING_B[0]]
    got_b = dmfs([{"id": "b", "dtstart": b["dtstart"], "rrule": b["rrule"],
                   "limit": b["limit"]}])["b"].get("occurrences") or []
    result["case_39497d02ae1e_predicted_exactly"] = (predict_b(b) == got_b)

    live = fail_bucket(run_adapters)
    result["fail_bucket_rechecked"] = live is not None
    if live is not None:
        result["fail_bucket_live"] = live
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import corpus_id
    result["cases_id"] = corpus_id.compute()["cases_id"]
    result["partition"] = {
        "111-A week-53 overflow": sorted(A_ONLY),
        "111-A overflow + dtstart_fill reading": sorted(A_AND_B),
        "dtstart_fill reading + calendar-year interval anchor, not a defect":
            sorted(B_ONLY)}
    return result


def report(r):
    lines = []
    a = lines.append
    a("dmfs lib-recur 0.17.1 -- BYWEEKNO=53 over the years 2020-2100")
    a("")
    a("  53-week years (ISO), week 53 correct: %d" % len(r["long_years"]))
    a("  52-week years, correctly yielding nothing: %d"
      % len(r["short_years_correctly_empty"]))
    sizes = r["short_year_window_sizes"]
    for n in sorted(sizes):
        a("  52-week years whose week-53 window has %d days: %d" % (n, sizes[n]))
    a("  years where BYWEEKNO=52 and BYWEEKNO=53 give the same day: %d"
      % len(r["weeks_52_and_53_same_day"]))
    a("  years where BYDAY=MO yields nothing but BYDAY=MO,TU yields a Monday: %d"
      % len(r["monday_appears_only_when_tuesday_is_added"]))
    a("")
    a("NECESSITY -- drop 53 from each corpus case and ask dmfs again:")
    for cid in sorted(r["necessity"]):
        n = r["necessity"][cid]
        a("  %s  %s" % (cid, n["reduced_rule"]))
        a("      -> %s %s" % ("agrees with" if n["agrees"] else "STILL DISAGREES WITH",
                              n["compared_against"]))
    a("")
    a("FOURTH CASE 39497d02ae1e, not this defect: predicted element for element: %s"
      % ("yes" if r["case_39497d02ae1e_predicted_exactly"] else "NO"))
    a("")
    a("PARTITION of dmfs's fail bucket:")
    for label in sorted(r["partition"]):
        a("  %-62s %s" % (label, " ".join(r["partition"][label])))
    a("  bucket re-scored this run: %s" % ("yes" if r["fail_bucket_rechecked"] else "no"))
    a("")
    for p in r["problems"]:
        a("PROBLEM: " + p)
    return "\n".join(lines)


def verdict(r):
    """Non-zero exit is the guard. Rule 91."""
    bad = list(r["problems"])
    if len(r["long_years"]) != 15:
        bad.append("expected 15 long years in 2020-2100, saw %d" % len(r["long_years"]))
    if r["short_years_correctly_empty"]:
        bad.append("some short years now yield nothing; the defect may be fixed")
    if 7 in r["short_year_window_sizes"]:
        bad.append("a short year produced a seven-day week 53")
    if not r["weeks_52_and_53_same_day"]:
        bad.append("weeks 52 and 53 no longer collide anywhere")
    if not r["monday_appears_only_when_tuesday_is_added"]:
        bad.append("the BYDAY monotonicity break no longer reproduces")
    for cid, n in r["necessity"].items():
        if not n["agrees"]:
            bad.append("%s still disagrees with 53 removed: the week-53 branch "
                       "is not the whole cause" % cid)
    if not r["case_39497d02ae1e_predicted_exactly"]:
        bad.append("39497d02ae1e is no longer predicted element for element")
    if r.get("fail_bucket_live") is not None:
        want = sorted(DEFECT_A + READING_B)
        if sorted(r["fail_bucket_live"]) != want:
            bad.append("dmfs's fail bucket is now %s, published %s"
                       % (r["fail_bucket_live"], want))
    return bad


def main(argv):
    check = "--check" in argv
    write = "--write" in argv or os.environ.get("WRITE_111")
    run_adapters = "--no-adapters" not in argv
    if not have_java():
        print("skip  no JVM or no compiled dmfs adapter; finding 111 has nothing to measure")
        return 0
    r = compute(run_adapters)
    print(report(r))
    bad = verdict(r)
    if check:
        if not os.path.exists(DATA):
            print("FAIL stored artifact is missing")
            return 1
        with open(DATA) as fh:
            stored = json.load(fh)
        # JSON turns the int keys of short_year_window_sizes into strings;
        # compare what would be written, not what is in memory.
        fresh = json.loads(json.dumps(r, sort_keys=True))
        fresh.pop("fail_bucket_live", None)
        fresh.pop("fail_bucket_rechecked", None)
        was = dict(stored)
        was.pop("fail_bucket_live", None)
        was.pop("fail_bucket_rechecked", None)
        if was != fresh:
            print("FAIL the stored artifact no longer matches a fresh computation")
            bad.append("stored artifact is stale")
    if write:
        with open(DATA, "w") as fh:
            json.dump(r, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote findings/data/111-dmfs-weekno-overflow.json")
    for b in bad:
        print("FAIL " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
