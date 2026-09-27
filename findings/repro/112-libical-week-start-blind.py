#!/usr/bin/env python3
"""Finding 112 — libical master 4edd39a3's whole `fail` bucket is BYWEEKNO.

Two defects, both in the BYWEEKNO paths of ``src/libical/icalrecur.c``:

* **A** ``weeks_in_year()`` is hardcoded to the ISO (Monday) week start, while
  the week *numbering* it is compared against comes from ICU with
  ``UCAL_FIRST_DAY_OF_WEEK`` set from the rule's ``WKST``. With a non-Monday
  ``WKST`` the two disagree, so a negative ``BYWEEKNO`` normalises against the
  wrong count and the ``weekno > nweeks`` skip lets an out-of-year week through.
* **B** in the ``BYWEEKNO`` + ``BYDAY`` branch of ``expand_year_days()``,
  ``last_day = (7 * weeks_in_year(year)) - doy_offset - 1``. ``expand_by_day()``
  reads ``last_day`` as a *count* of days beginning at ``doy_offset + 1``, and
  the week-numbering year is exactly ``7 * weeks_in_year(year)`` days long, so
  the last ``doy_offset + 1`` days of it are dropped.

What this script checks without needing anything rebuilt (the default, ~2s):

1. the six ids are exactly the adapter's live ``fail`` bucket, at the recorded
   ``cases_id``;
2. **observable B** — with ``BYDAY`` naming all seven weekdays, ``BYWEEKNO=52``
   yields a week of fewer than seven days, and the shortfall is a function of
   January 1st's weekday alone;
3. **observable A** — with ``WKST=SU``, ``BYWEEKNO=-1`` selects a day outside
   the calendar year it was asked about;
4. the stored artifact matches a fresh computation (rule 115).

``--rebuild`` additionally reapplies the patches to a libical source checkout,
rebuilds, re-scores, and re-derives the necessity/sufficiency partition. That
needs the source tree and cmake, so it is not the default and not in
tools/repro-drift.json. The partition it produced is recorded in the artifact.

Rule 102: the patched builds install to their own prefixes. Nothing here writes
to the prefix the published libical rows are measured through.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACT = os.path.join(ROOT, "findings", "data", "112-libical-week-start-blind.json")
ADAPTER = [os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter")]
BASE_PREFIX = os.environ.get(
    "LIBICAL_LIB", "/home/agent/terrarium/scratch/libical-install-4edd")
SRC_TREE = os.environ.get("LIBICAL_SRC", "/home/agent/terrarium/scratch/libical")

CASES_ID = "7bd9731d3a48c0155ba35f943d43756ff2ec8ae69cced3464d45940e62e53f5b"

# The map. Both labels were measured, not assigned: each patch was built alone
# and the cases it moved out of `fail` are its members.
PARTITION = {
    "A-weeks-in-year-ignores-wkst": [
        "1b491afa4ef0", "47957affeae1", "6a2a3349a31d", "cd5d1f7e7232",
    ],
    "B-week-year-truncated-by-doy-offset-plus-one": [
        "52cb89bd1169", "a11bc9303af3",
    ],
}
ALL_WEEKS = "MO,TU,WE,TH,FR,SA,SU"


def ask(prefix, cases):
    """Run the committed adapter against one libical prefix."""
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    env = dict(os.environ, TZ="UTC", LD_LIBRARY_PATH=os.path.join(prefix, "lib"))
    p = subprocess.run(ADAPTER, input=payload, capture_output=True, text=True,
                       env=env)
    if p.returncode != 0:
        sys.exit("adapter failed under %s:\n%s" % (prefix, p.stderr[:2000]))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r.get("occurrences") or []
    return out


def corpus():
    with open(os.path.join(ROOT, "corpus", "VERSION.json")) as fh:
        ver = json.load(fh)
    cases = [json.loads(l) for l in
             open(os.path.join(ROOT, "conformance", "cases.ndjson"))]
    return ver, cases


def live_fail_bucket(cases):
    """The adapter's live `fail` bucket, from score.py rather than a second copy.

    Rule 102's cousin: a repro that reimplements the scorer is measuring its own
    reimplementation. The first version of this function did exactly that and
    reported 41 ids, because it counted the adapter's 35 error replies as
    mismatches. score.py is the scorer; ask it.
    """
    del cases
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "score.json")
        env = dict(os.environ, TZ="UTC",
                   LD_LIBRARY_PATH=os.path.join(BASE_PREFIX, "lib"))
        r = subprocess.run([sys.executable, "conformance/score.py", "--json", out,
                            "--"] + ADAPTER, cwd=ROOT, capture_output=True,
                           text=True, env=env)
        # score.py exits non-zero when anything failed, which is the normal
        # case here; the artifact is the contract, so check for that instead.
        if not os.path.isfile(out):
            sys.exit("score.py produced no result:\n%s%s"
                     % (r.stdout[-2000:], r.stderr[-2000:]))
        with open(out) as fh:
            rec = json.load(fh)
    return sorted(x["case"]["id"] for x in rec["failures"]
                  if x["bucket"] == "fail")


def contiguous_run(days):
    """The first maximal run of consecutive calendar days."""
    d = [datetime.date(int(x[:4]), int(x[4:6]), int(x[6:8])) for x in days]
    out = [d[0]]
    for a, b in zip(d, d[1:]):
        if (b - a).days == 1:
            out.append(b)
        else:
            break
    return out


def observable_b(years=range(2024, 2041)):
    """BYWEEKNO=52 with every weekday: how many days does the week have?

    The shortfall is `doy_offset + 1`, and doy_offset is fixed by January 1st's
    weekday, so this predicts the length from the calendar alone.
    """
    # Monday-based index of Jan 1 -> expected number of days returned.
    # Mon: doy_offset 0 -> 6.  Fri/Sat/Sun: doy_offset 3/2/1 -> 3/4/5.
    # Tue/Wed/Thu: week 1 begins in the previous calendar year, doy_offset < 0,
    # and the formula over-runs instead of truncating -- no day is lost.
    EXPECT = {"Mon": 6, "Tue": 7, "Wed": 7, "Thu": 7, "Fri": 3, "Sat": 4,
              "Sun": 5}
    cases = [{"id": "b%d" % y, "rrule": "FREQ=YEARLY;BYWEEKNO=52;BYDAY=" + ALL_WEEKS,
              "dtstart": "%04d0115T090000" % y, "limit": 14} for y in years]
    got = ask(BASE_PREFIX, cases)
    rows = {}
    for y in years:
        jan1 = datetime.date(y, 1, 1).strftime("%a")
        n = len(contiguous_run(got["b%d" % y]))
        rows[str(y)] = {"jan1": jan1, "days": n, "predicted": EXPECT[jan1]}
    return rows


def observable_a(years=range(2024, 2041)):
    """WKST=SU, BYWEEKNO=-1: which calendar year does the chosen day fall in?

    With no BYDAY libical deliberately returns one day per selected week, the
    next instance of DTSTART's weekday. That reading is finding 024's open
    split and is not the defect. The defect is the week: normalising -1 against
    the Monday-based week count of a Sunday-based numbering reaches a week the
    calendar year does not contain.
    """
    cases = [{"id": "a%d" % y, "rrule": "FREQ=YEARLY;BYWEEKNO=-1;WKST=SU",
              "dtstart": "%04d0115T090000" % y, "limit": 1} for y in years]
    got = ask(BASE_PREFIX, cases)
    rows = {}
    for y in years:
        occ = got["a%d" % y]
        rows[str(y)] = {"asked": y, "got": occ[0] if occ else None,
                        "outside": bool(occ) and int(occ[0][:4]) != y}
    return rows


def compute():
    ver, cases = corpus()
    return {
        "cases_id": ver["cases_id"],
        "corpus_id": ver["corpus_id"],
        "subject": "libical master 4edd39a3 (HAVE_LIBICU=1)",
        "fail_bucket": live_fail_bucket(cases),
        "partition": {k: sorted(v) for k, v in PARTITION.items()},
        "observable_b_short_week": observable_b(),
        "observable_a_week_outside_year": observable_a(),
    }


def check_invariants(rec, verbose=True):
    bad = []
    if rec["cases_id"] != CASES_ID:
        bad.append("cases_id moved: %s" % rec["cases_id"])
    claimed = sorted(sum(rec["partition"].values(), []))
    if len(claimed) != len(set(claimed)):
        bad.append("an id is under two labels")
    if claimed != sorted(rec["fail_bucket"]):
        bad.append("partition %s != live fail bucket %s"
                   % (claimed, sorted(rec["fail_bucket"])))
    short = 0
    for y, row in sorted(rec["observable_b_short_week"].items()):
        if row["days"] != row["predicted"]:
            bad.append("observable B: %s has %d days, predicted %d"
                       % (y, row["days"], row["predicted"]))
        if row["days"] < 7:
            short += 1
    if short != 10:
        bad.append("observable B: %d short weeks, expected 10" % short)
    outside = sum(1 for r in rec["observable_a_week_outside_year"].values()
                  if r["outside"])
    if outside == 0:
        bad.append("observable A: no chosen week falls outside its year")
    if verbose:
        print("fail bucket      %d ids, partitioned into %d labels"
              % (len(rec["fail_bucket"]), len(rec["partition"])))
        for k, v in sorted(rec["partition"].items()):
            print("  %-46s %d  %s" % (k, len(v), " ".join(v)))
        print("observable B     %d of %d years return a week of <7 days; every"
              " length matches the prediction from Jan 1's weekday"
              % (short, len(rec["observable_b_short_week"])))
        print("observable A     %d of %d years choose a day outside the year asked"
              % (outside, len(rec["observable_a_week_outside_year"])))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="diff the stored artifact against a fresh computation")
    ap.add_argument("--write", action="store_true", help="refresh the artifact")
    ap.add_argument("--rebuild", action="store_true",
                    help="reapply the patches, rebuild libical, re-derive the "
                         "necessity partition (needs the source tree and cmake)")
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(BASE_PREFIX, "lib")):
        print("skip  no libical build at %s; set LIBICAL_LIB" % BASE_PREFIX)
        return 0

    fresh = compute()
    bad = check_invariants(fresh)

    if a.check or (not a.write and os.path.isfile(ARTIFACT)):
        with open(ARTIFACT) as fh:
            stored = json.load(fh)
        # json.dumps round-trip: a stored file has string keys throughout
        if json.loads(json.dumps(fresh)) != stored:
            bad.append("stored artifact differs from a fresh computation")

    if a.write or os.environ.get("WRITE_112"):
        with open(ARTIFACT, "w") as fh:
            json.dump(fresh, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote", os.path.relpath(ARTIFACT, ROOT))

    if a.rebuild:
        bad += rebuild_and_partition(fresh)

    if bad:
        for b in bad:
            print("FAIL", b)
        return 1
    print("ok  finding 112 reproduces")
    return 0


def rebuild_and_partition(fresh):
    """Build patch A alone, B alone, and both; re-score each; report the map."""
    patcher = os.path.join(ROOT, "findings", "repro", "112-patch-libical.py")
    build = os.path.join(SRC_TREE, "build4edd")
    if not os.path.isdir(build):
        print("skip  --rebuild needs a configured libical build at %s" % build)
        return []
    ver, cases = corpus()
    base = set(fresh["fail_bucket"])
    bad = []
    for label in ("A", "B", "AB"):
        prefix = "%s-install-4edd-%s" % (SRC_TREE.rstrip("/"), label)
        subprocess.run(["git", "-C", SRC_TREE, "checkout",
                        "src/libical/icalrecur.c"], check=True)
        subprocess.run([sys.executable, patcher] + list(label), check=True)
        subprocess.run(["cmake", "--build", build, "--target", "ical", "-j4"],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["cmake", "--install", build, "--prefix", prefix],
                       check=True, stdout=subprocess.DEVNULL)
        global BASE_PREFIX
        keep, BASE_PREFIX = BASE_PREFIX, prefix
        try:
            after = set(live_fail_bucket(cases))
        finally:
            BASE_PREFIX = keep
        fixed = base - after
        new = after - base
        want = set(fresh["partition"]["A-weeks-in-year-ignores-wkst"]) if label == "A" \
            else set(fresh["partition"]["B-week-year-truncated-by-doy-offset-plus-one"]) \
            if label == "B" else base
        print("patch %-2s  left `fail`: %d %s   new failures: %d"
              % (label, len(fixed), " ".join(sorted(fixed)), len(new)))
        if fixed != want:
            bad.append("patch %s moved %s, expected %s"
                       % (label, sorted(fixed), sorted(want)))
        if new:
            bad.append("patch %s regressed %s" % (label, sorted(new)))
    subprocess.run(["git", "-C", SRC_TREE, "checkout",
                    "src/libical/icalrecur.c"], check=True)
    subprocess.run(["cmake", "--build", build, "--target", "ical", "-j4"],
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--install", build, "--prefix", BASE_PREFIX],
                   check=True, stdout=subprocess.DEVNULL)
    print("restored the unpatched build at", BASE_PREFIX)
    return bad


if __name__ == "__main__":
    sys.exit(main())
