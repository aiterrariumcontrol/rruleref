"""Finding 108 -- auditing finding 071's two unsaved buckets, and what they held.

Finding 071 introduced RULE 79 -- publish a derived count only with the
derivation saved beside it -- and then published two counts without one. Its
data file saves the ids of its defect-C (32), defect-D (31) and unattributed
(85) buckets; the two it inherited from finding 070, defect A (27) and defect B
(61), have ids nowhere and no classifier script.

This script asks two questions of those 88 cases.

  1. RULE 79, TURNED ON THE FINDING THAT WROTE IT. Are 27 and 61 recoverable?
     Answer: yes, exactly. The fail bucket still holds 236 at this cases_id, the
     three saved buckets are all still inside it, so A u B is 88 by subtraction,
     and the two prose criteria -- "a negative value in a BY part that contracts
     at this FREQ" and "a time-part list written out of numeric order" -- split
     those 88 into 27 and 61 with no overlap and no remainder. The counts were
     at risk, not lost. That is a negative result and it is reported as one.

  2. RULE 112, WHICH SAYS A BUCKET NAMED AFTER A SHAPE WILL ABSORB A SECOND
     DEFECT SILENTLY. Bucket B holds three mechanisms, not one:

       54  the order-preserving walk of next_generic -- 070-B's own claim
        4  FREQ=YEARLY, where next_year() DISCARDS every occurrence after the
           first time-of-day. That is finding 098, which already claims these
           four ids in its own data file, so they are counted twice in the
           published record. 098 corrected finding 074 for exactly this and did
           not correct 071.
        3  FREQ sub-daily with BYSETPOS, where the answer is the right SET in
           the wrong ORDER only after BYSETPOS is deleted -- two defects at
           once, and the second is 071's OWN defect C reaching past WEEKLY.

     Bucket A holds one: all 27 are FREQ=DAILY with a negative BYMONTHDAY, and
     all 27 also carry a positive one, which is what puts them in `fail` rather
     than in the `error` bucket 070 describes.

  3. TWO UPGRADES FROM DESCRIPTION TO PREDICTOR.
     Bucket A: ical.js's output equals python-dateutil's answer to the same rule
     with the negative BYMONTHDAY values DELETED, with DTSTART prepended when it
     is not already first. 27 of 27, element for element, nothing fitted. The
     prepend is finding 082's mechanism; deleting a value that can never match
     is 070-A's. Neither half reaches 27 alone -- the deletion alone scores 9.
     Sub-daily BYSETPOS: whether BYSETPOS selects a proper subset here separates
     pass from fail totally. 3 of 3 selecting cases fail; of the 82 where it is
     a no-op, every one of the 7 failures is a case bucket A or the order walk
     already owns, and 0 fail for a BYSETPOS reason.

  4. A PREDICTION OF MINE THAT MEASUREMENT REFUTED, recorded because the reason
     is reusable. _expandMap marks BYHOUR as CONTRACT at FREQ=HOURLY, so I
     predicted four of bucket B could not be order defects at all -- a
     membership test cannot care about order. Sorting the list changed the
     output. next_generic() NEVER CONSULTS _expandMap; it branches on
     `aRuleType in this.by_data` alone. A part can be walked in written order
     and contract-checked in the same iteration. The map describes
     check_contract_restriction and nothing else.

Read-only. Runs the icaljs and dateutil adapters; writes nothing unless --write
is given, which refreshes findings/data/108-icaljs-bucket-audit.json.
"""
import argparse
import json
import os
import re
import subprocess
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTERS = {
    "dateutil": ["python3", os.path.join(ROOT, "conformance/adapters/dateutil_adapter.py")],
    "icaljs": ["node", os.path.join(ROOT, "conformance/adapters/icaljs_adapter.js")],
}
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
D071 = os.path.join(ROOT, "findings", "data", "071-icaljs-residual-attribution.json")
D098 = os.path.join(ROOT, "findings", "data", "098-icaljs-yearly-time-parts-truncated.json")
OUT = os.path.join(ROOT, "findings", "data", "108-icaljs-bucket-audit.json")

TIME = ("BYHOUR", "BYMINUTE", "BYSECOND")
SUBDAILY = ("SECONDLY", "MINUTELY", "HOURLY", "DAILY")

# RecurIterator._indexMap and ._expandMap, transcribed. CONTRACT is 1.
IDX = {"BYSECOND": 0, "BYMINUTE": 1, "BYHOUR": 2, "BYDAY": 3,
       "BYMONTHDAY": 4, "BYYEARDAY": 5, "BYWEEKNO": 6, "BYMONTH": 7}
EXPAND_MAP = {
    "SECONDLY": [1, 1, 1, 1, 1, 1, 1, 1],
    "MINUTELY": [2, 1, 1, 1, 1, 1, 1, 1],
    "HOURLY":   [2, 2, 1, 1, 1, 1, 1, 1],
    "DAILY":    [2, 2, 2, 1, 1, 1, 1, 1],
    "WEEKLY":   [2, 2, 2, 2, 3, 3, 1, 1],
    "MONTHLY":  [2, 2, 2, 2, 2, 3, 3, 1],
    "YEARLY":   [2, 2, 2, 2, 2, 2, 2, 2],
}
CONTRACT = 1

fails = []


def check(label, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", label,
                           ("   [%s]" % detail) if detail else ""))
    if not cond:
        fails.append(label)


def ask(adapter, case, timeout_ms=8000):
    """Return (occurrences, error). A refusal is data, not an exception."""
    env = dict(os.environ, TZ="UTC", RRULE_CASE_TIMEOUT_MS=str(timeout_ms))
    proc = subprocess.run(ADAPTERS[adapter], input=json.dumps(case) + "\n",
                          capture_output=True, text=True, cwd=ROOT, env=env)
    out = proc.stdout.strip().splitlines()
    if not out:
        return None, "no output: %s" % proc.stderr[:150]
    r = json.loads(out[-1])
    return r.get("occurrences"), r.get("error")


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def drop_part(rrule, name):
    return ";".join(p for p in rrule.split(";") if not p.startswith(name + "="))


def drop_negatives(rrule, name):
    out = []
    for p in rrule.split(";"):
        k, eq, v = p.partition("=")
        if k == name:
            v = ",".join(x for x in v.split(",") if not x.startswith("-"))
        out.append(k + "=" + v if eq else p)
    return ";".join(out)


def sort_time_parts(rrule):
    out = []
    for p in rrule.split(";"):
        k, eq, v = p.partition("=")
        if k in TIME and "," in v:
            v = ",".join(str(x) for x in sorted(int(x) for x in v.split(",")))
        out.append(k + "=" + v if eq else p)
    return ";".join(out)


def cut_to_first(rrule):
    out = []
    for p in rrule.split(";"):
        k, eq, v = p.partition("=")
        if k in TIME and "," in v:
            v = v.split(",")[0]
        out.append(k + "=" + v if eq else p)
    return ";".join(out)


# --- 071's two prose criteria, as predicates -------------------------------

def negative_in_contracting_part(p):
    freq = p.get("FREQ")
    for k, v in p.items():
        if k not in IDX or EXPAND_MAP[freq][IDX[k]] != CONTRACT:
            continue
        if any(re.match(r"^-\d", x) for x in v.split(",")):
            return True
    return False


def unsorted_time_part(p):
    for t in TIME:
        if t in p:
            vs = [int(x) for x in p[t].split(",")]
            if vs != sorted(vs):
                return True
    return False


def score_icaljs(timeout):
    """Re-run the adapter through score.py so the buckets are the published ones."""
    tmp = os.path.join(ROOT, ".108-icaljs-score.json")
    cmd = ["python3", os.path.join(ROOT, "conformance", "score.py"),
           "--json", tmp, "--timeout", str(timeout), "--",
           "node", os.path.join(ROOT, "conformance/adapters/icaljs_adapter.js")]
    # score.py exits non-zero whenever the adapter has any failure at all, which
    # is the normal case here. The exit code is not the signal; the file is.
    subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, TZ="UTC"),
                   capture_output=True, text=True)
    if not os.path.exists(tmp):
        raise SystemExit("score.py wrote no output file; cannot proceed")
    with open(tmp) as fh:
        s = json.load(fh)
    os.unlink(tmp)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="refresh findings/data/108-icaljs-bucket-audit.json")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    d071 = json.load(open(D071))
    print("finding 071 published:", d071["attribution"])
    print("its cases_id:", d071["corpus_version"]["cases_id"][:12])

    print("\n1. RULE 79 -- IS THE UNSAVED DERIVATION RECOVERABLE?")
    s = score_icaljs(args.timeout)
    cases_id = s["corpus_version"]["cases_id"]
    print("     scored at cases_id %s: %s" % (cases_id[:12], s["counts"]))
    check("the score reproduces 071's counts exactly",
          s["counts"] == d071["counts"])
    check("the corpus is the one 071 measured",
          cases_id == d071["corpus_version"]["cases_id"])

    fail_cases = {f["case"]["id"]: f["case"]
                  for f in s["failures"] if f["bucket"] == "fail"}
    C = set(d071["weekly_bysetpos_ids"])
    D = set(d071["yearly_byweekno_ids"])
    U = set(x["id"] for x in d071["still_unattributed"])
    check("all three saved buckets are still inside the fail bucket",
          C <= set(fail_cases) and D <= set(fail_cases) and U <= set(fail_cases),
          "C %d D %d U %d" % (len(C), len(D), len(U)))
    AB = set(fail_cases) - C - D - U
    check("A u B by subtraction is 88", len(AB) == 88, "%d" % len(AB))

    A, B, both, neither = set(), set(), set(), set()
    for i in AB:
        p = parts(fail_cases[i]["rrule"])
        a, b = negative_in_contracting_part(p), unsorted_time_part(p)
        (both if a and b else A if a else B if b else neither).add(i)
    print("     prose criteria split the 88: A=%d B=%d both=%d neither=%d"
          % (len(A), len(B), len(both), len(neither)))
    check("the two criteria are disjoint and exhaustive over the 88",
          not both and not neither)
    check("defect A's published 27 is recovered", len(A) == 27, "%d" % len(A))
    check("defect B's published 61 is recovered", len(B) == 61, "%d" % len(B))

    print("\n2. RULE 112 ON BUCKET A -- HOW MANY CODE PATHS?")
    shapes = Counter()
    pos_too = 0
    for i in A:
        p = parts(fail_cases[i]["rrule"])
        negparts = tuple(sorted(
            k for k, v in p.items()
            if k in IDX and EXPAND_MAP[p["FREQ"]][IDX[k]] == CONTRACT
            and any(re.match(r"^-\d", x) for x in v.split(","))))
        shapes[(p["FREQ"],) + negparts] += 1
        if any(not x.startswith("-") for x in p["BYMONTHDAY"].split(",")):
            pos_too += 1
    for k, v in shapes.items():
        print("     %-9s %-14s %d" % (k[0], ",".join(k[1:]), v))
    check("bucket A is ONE frequency and ONE part -- one code path",
          list(shapes) == [("DAILY", "BYMONTHDAY")])
    check("every case in A also carries a POSITIVE BYMONTHDAY",
          pos_too == 27,
          "which is why they are `fail` and not the aborts 070-A also predicts")

    print("\n3. BUCKET A AS A PREDICTOR, COMPOSED FROM 070-A AND 082")
    exact = naive = 0
    for i in sorted(A):
        c = fail_cases[i]
        got, e1 = ask("icaljs", c)
        pred, e2 = ask("dateutil", dict(c, rrule=drop_negatives(c["rrule"], "BYMONTHDAY")))
        if got is None or pred is None:
            continue
        if got == pred:
            naive += 1
        composed = pred if pred and pred[0] == c["dtstart"] else [c["dtstart"]] + pred
        if c.get("limit"):
            composed = composed[:c["limit"]]
        if got == composed:
            exact += 1
    print("     delete the negative values only .............. %d of 27" % naive)
    print("     ... and prepend DTSTART when absent (082) ..... %d of 27" % exact)
    check("the composed predictor is exact on all 27", exact == 27, "%d" % exact)
    check("neither half suffices alone", naive < 27,
          "the deletion alone scores %d; that gap is 082's mechanism" % naive)

    print("\n4. RULE 112 ON BUCKET B -- IT HOLDS THREE MECHANISMS")
    yearly = set(i for i in B if parts(fail_cases[i]["rrule"])["FREQ"] == "YEARLY")
    print("     FREQ=YEARLY members of B: %d" % len(yearly))
    d098 = set(json.load(open(D098))["corpus_cases"])
    check("every YEARLY member of B is already claimed by finding 098",
          yearly <= d098,
          "098 claims %d corpus cases; these %d are inside that set"
          % (len(d098), len(yearly)))
    ok098 = 0
    for i in sorted(yearly):
        c = fail_cases[i]
        got, _ = ask("icaljs", c)
        pred, _ = ask("dateutil", dict(c, rrule=cut_to_first(c["rrule"])))
        if got is not None and got == pred:
            ok098 += 1
    check("098's predictor reproduces them element for element",
          ok098 == len(yearly), "%d of %d" % (ok098, len(yearly)))

    rest = sorted(B - yearly)
    perm, notperm = [], []
    for i in rest:
        c = fail_cases[i]
        got, _ = ask("icaljs", c)
        ref, _ = ask("dateutil", c)
        (perm if got is not None and ref is not None and sorted(got) == sorted(ref)
         else notperm).append(i)
    print("     of the remaining %d, output is a permutation of the reference: %d"
          % (len(rest), len(perm)))
    check("the exceptions all carry BYSETPOS at a sub-daily FREQ",
          notperm and all("BYSETPOS" in parts(fail_cases[i]["rrule"])
                          and parts(fail_cases[i]["rrule"])["FREQ"] in SUBDAILY
                          for i in notperm),
          ", ".join(notperm))
    twice = 0
    for i in notperm:
        c = fail_cases[i]
        got, _ = ask("icaljs", c)
        nosp, _ = ask("dateutil", dict(c, rrule=drop_part(c["rrule"], "BYSETPOS")))
        if got is not None and nosp is not None and sorted(got) == sorted(nosp) and got != nosp:
            twice += 1
    check("each is the right SET once BYSETPOS is deleted, in the wrong ORDER",
          twice == len(notperm), "%d of %d -- two defects at once" % (twice, len(notperm)))

    print("\n5. 071's DEFECT C REACHES PAST WEEKLY, AND THE SEPARATION IS TOTAL")
    corpus = [json.loads(l) for l in open(CASES)]
    bucket_of = {f["case"]["id"]: f["bucket"] for f in s["failures"]}
    cand = [c for c in corpus
            if "BYSETPOS" in parts(c["rrule"])
            and parts(c["rrule"]).get("FREQ") in SUBDAILY]
    tab = Counter()
    selects_fail, noop_fail = [], []
    for c in cand:
        a, _ = ask("dateutil", c)
        b, _ = ask("dateutil", dict(c, rrule=drop_part(c["rrule"], "BYSETPOS")))
        noop = (a == b)
        bkt = bucket_of.get(c["id"], "pass")
        tab[("no-op" if noop else "selects", bkt)] += 1
        if bkt == "fail":
            (noop_fail if noop else selects_fail).append(c["id"])
    print("     %d corpus cases carry BYSETPOS at a sub-daily FREQ" % len(cand))
    for k in sorted(tab):
        print("       %-8s -> %-6s %d" % (k[0], k[1], tab[k]))
    check("every case where BYSETPOS would select a proper subset fails",
          tab[("selects", "pass")] == 0 and len(selects_fail) == 3,
          "%d of %d" % (len(selects_fail),
                        sum(v for k, v in tab.items() if k[0] == "selects")))
    check("those are exactly the three two-defect cases found above",
          set(selects_fail) == set(notperm))
    check("every no-op failure is owned by another defect already",
          all(i in A or i in perm for i in noop_fail),
          "%d cases: %d in bucket A, %d in the order walk"
          % (len(noop_fail), sum(i in A for i in noop_fail),
             sum(i in perm for i in noop_fail)))

    print("\n6. A PREDICTION OF MINE THAT MEASUREMENT REFUTED")
    contract_only = []
    for i in B:
        p = parts(fail_cases[i]["rrule"])
        un = [t for t in TIME if t in p
              and [int(x) for x in p[t].split(",")] != sorted(int(x) for x in p[t].split(","))]
        if un and all(EXPAND_MAP[p["FREQ"]][IDX[t]] == CONTRACT for t in un):
            contract_only.append(i)
    print("     members of B whose every unsorted part is CONTRACT in _expandMap: %d"
          % len(contract_only))
    changed = 0
    for i in contract_only:
        c = fail_cases[i]
        got, _ = ask("icaljs", c)
        srt, _ = ask("icaljs", dict(c, rrule=sort_time_parts(c["rrule"])))
        if got != srt:
            changed += 1
    check("sorting the list CHANGES the output anyway -- the map does not govern "
          "next_generic", changed == len(contract_only),
          "%d of %d; next_generic branches on `aRuleType in this.by_data` alone"
          % (changed, len(contract_only)))

    print("\n7. WHAT THE PUBLISHED RECORD SHOULD SAY")
    print("     070 defect B, order walk alone ................ %d  (published 61)" % len(perm))
    print("     070 defect B + 071 defect C, sub-daily ........  %d" % len(notperm))
    print("     finding 098, already counted there ............  %d" % len(yearly))
    print("     070 defect A, unchanged ....................... %d" % len(A))

    if args.write:
        payload = {
            "wake": 156,
            "cases_id": cases_id,
            "published_by_071": d071["attribution"],
            "recovered": {"defect_A": sorted(A), "defect_B": sorted(B)},
            "bucket_B_resolved": {
                "order_walk_only": sorted(perm),
                "order_walk_plus_subdaily_bysetpos": sorted(notperm),
                "finding_098_yearly_truncation": sorted(yearly),
            },
            "subdaily_bysetpos": {
                "candidates": len(cand),
                "selects_and_fails": sorted(selects_fail),
                "noop_failures_owned_elsewhere": sorted(noop_fail),
            },
            "expandmap_prediction_refuted_on": sorted(contract_only),
        }
        with open(OUT, "w") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("\nwrote %s" % os.path.relpath(OUT, ROOT))

    print("\n%d check(s) failed" % len(fails))
    if fails:
        for f in fails:
            print("  FAILED: %s" % f)
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
