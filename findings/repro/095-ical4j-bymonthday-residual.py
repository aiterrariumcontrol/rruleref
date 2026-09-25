#!/usr/bin/env python3
"""095 -- what is left of ical4j's BYMONTHDAY failures after 4.3.0's repair.

Default mode is READ-ONLY and fast: it replays the stored raw answers in
findings/data/095-ical4j-bymonthday-residual.json and re-derives every figure
in finding 095 from them.

    python3 findings/repro/095-ical4j-bymonthday-residual.py
    python3 findings/repro/095-ical4j-bymonthday-residual.py --run-ical4j   # ~20s, WRITES

Following finding 094's rule, every stored answer carries the `limit` it was
asked for, and this script REFUSES to report if the corpus limit for a case has
moved since the answers were captured -- an occurrence count is an answer to a
question that includes how much was asked for.
"""
import argparse, calendar, datetime, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "findings/data/095-ical4j-bymonthday-residual.json")
CASES = os.path.join(ROOT, "conformance/cases.ndjson")
N411 = os.path.join(ROOT, "findings/data/088-necessity-bymonthday-ical4j411.json")
N430 = os.path.join(ROOT, "findings/data/088-necessity-bymonthday-ical4j430.json")

ARGV = {
    "ical4j411": ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*",
                  "Ical4jAdapter"],
    "ical4j430": ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs430/*:"
                  "conformance/adapters/java/libs/*", "Ical4jAdapter"],
}


def corpus():
    out = {}
    with open(CASES) as fh:
        for line in fh:
            c = json.loads(line)
            out[c["id"]] = c
    return out


def residual():
    """The BYMONTHDAY cases 4.1.1 fails attributably and 4.3.0 still fails."""
    a = {r["id"]: r for r in json.load(open(N411))["rows"]}
    b = {r["id"]: r for r in json.load(open(N430))["rows"]}
    both = {i for i, r in a.items() if r["verdict"] == "ATTRIBUTABLE"} & \
           {i for i, r in b.items() if r["verdict"] == "ATTRIBUTABLE"}
    strat = {i: b[i]["stratum"] for i in both}
    return sorted(both), strat


def ordinal_population(cs):
    """Every corpus case with BYMONTHDAY and BYDAY at FREQ=MONTHLY or YEARLY,
    split by whether any BYDAY value carries an ordinal prefix."""
    pop = {}
    for i, c in cs.items():
        r = c["rrule"]
        if not re.search(r"FREQ=(MONTHLY|YEARLY)", r) or "BYMONTHDAY=" not in r:
            continue
        m = re.search(r"BYDAY=([^;]+)", r)
        if not m:
            continue
        pop[i] = any(re.match(r"[+-]?\d", v) for v in m.group(1).split(","))
    return pop


def ask(adapter, cs, ids):
    payload = "".join(json.dumps({"id": i, "dtstart": cs[i]["dtstart"],
                                  "rrule": cs[i]["rrule"], "limit": cs[i]["limit"]}) + "\n"
                      for i in ids)
    env = dict(os.environ, TZ="UTC")
    p = subprocess.run(ARGV[adapter], input=payload, capture_output=True, text=True,
                       cwd=ROOT, env=env)
    out = {}
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out[d["id"]] = {"limit": cs[d["id"]]["limit"],
                        "occurrences": d.get("occurrences"),
                        "error": d.get("error")}
    return out


def _bymonthday(rule):
    m = re.search(r"BYMONTHDAY=([^;]+)", rule)
    return [int(v) for v in m.group(1).split(",")] if m else []


def overlapping_bymonthday(rule):
    """True if two BYMONTHDAY values name the same day in some month length.

    This is the precondition for 051 A: the rule asks for one day twice, so an
    implementation that does not deduplicate carries a repeated instant. It can
    surface either as a literal duplicate or, under BYSETPOS, as a selection
    that only exists because the duplicate was retained.
    """
    vals = _bymonthday(rule)
    for length in (28, 29, 30, 31):
        seen = set()
        for v in vals:
            d = v if v > 0 else length + 1 + v
            if not 1 <= d <= length:
                continue
            if d in seen:
                return True
            seen.add(d)
    return False


def _violates_other_expansion(rule, stamp):
    """True if `stamp` satisfies BYMONTHDAY but not the rule's BYYEARDAY.

    075's chaining mechanism lets the first expansion pick a month and
    re-expands BYMONTHDAY inside it, so it emits days of the right month-day
    that are not the yeardays the rule asked for.
    """
    m = re.search(r"BYYEARDAY=([^;]+)", rule)
    if not m:
        return False
    d = datetime.date(int(stamp[0:4]), int(stamp[4:6]), int(stamp[6:8]))
    doy = d.timetuple().tm_yday
    ndays = 366 if calendar.isleap(d.year) else 365
    wanted = {int(v) if int(v) > 0 else ndays + 1 + int(v) for v in m.group(1).split(",")}
    if doy in wanted:
        return False
    length = calendar.monthrange(d.year, d.month)[1]
    return any((v if v > 0 else length + 1 + v) == d.day for v in _bymonthday(rule))


def classify(case, ans):
    """Positive tests for three already-published ical4j mechanisms.

    Deliberately NOT an elimination bucket. The first version of this function
    classified by falling through to a default, and that default silently
    swallowed a 051 A case whose duplicate had been consumed by BYSETPOS
    (`9e1f525849c4`). Finding 094's lesson, on my own instrument.
    """
    rule, g = case["rrule"], ans["occurrences"]
    if g is None:
        return ["error"]
    hits = []
    if g == [] and re.search(r"BYDAY=[^;]*[+-]?\d", rule):
        hits.append("051B-ordinal-byday-empty")
    if len(set(g)) < len(g) or (overlapping_bymonthday(rule) and "BYSETPOS=" in rule
                                and g != case["expect"]):
        hits.append("051A-no-deduplication")
    if any(_violates_other_expansion(rule, s) for s in g):
        hits.append("075C-chained-expansion")
    if not hits:
        hits.append("agrees" if g == case["expect"] else "UNEXPLAINED")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-ical4j", action="store_true",
                    help="re-ask both ical4j releases and overwrite the stored answers")
    args = ap.parse_args()

    cs = corpus()
    ids, strat = residual()
    pop = ordinal_population(cs)

    if args.run_ical4j:
        store = {
            "about": "ical4j 4.1.1 and 4.3.0 answers for finding 095. Every answer "
                     "carries the limit it was asked for (finding 094's rule).",
            "jvm_locale": "en-US", "tz": "UTC",
            "residual_ids": ids,
            "ordinal_population": pop,
            "answers": {a: ask(a, cs, sorted(set(ids) | set(pop))) for a in ARGV},
        }
        json.dump(store, open(DATA, "w"), indent=1, sort_keys=True)
        print("wrote", os.path.relpath(DATA, ROOT))
    store = json.load(open(DATA))

    # Refuse to report against a corpus whose depths have moved (rule from 094).
    moved = [i for a in store["answers"] for i, v in store["answers"][a].items()
             if i in cs and v["limit"] != cs[i]["limit"]]
    if moved:
        print("REFUSING: the corpus limit moved for %d case(s) since these answers "
              "were captured, e.g. %s. Re-run with --run-ical4j."
              % (len(sorted(set(moved))), sorted(set(moved))[0]), file=sys.stderr)
        return 2

    print("ical4j BYMONTHDAY residual after 4.3.0's negative-value repair")
    print("  measured at JVM locale %s, TZ=%s, each case at its own corpus limit"
          % (store["jvm_locale"], store["tz"]))
    print()
    for stratum in ("accompanied", "alone"):
        sub = [i for i in ids if strat[i] == stratum]
        print("  stratum %-12s residual %d" % (stratum, len(sub)))
    print()

    buckets, multi = {}, []
    for i in ids:
        ks = classify(cs[i], store["answers"]["ical4j430"][i])
        if len(ks) > 1:
            multi.append((i, ks))
        for k in ks:
            buckets.setdefault(k, []).append(i)
    print("  mechanism split of the %d residual cases:" % len(ids))
    for k in sorted(buckets):
        print("    %-28s %2d" % (k, len(buckets[k])))
    print("    %-28s %2d" % ("cases matching >1 mechanism", len(multi)))
    for i, ks in multi:
        print("      %s  %s" % (i, " + ".join(ks)))
    print()

    # Blind cross-check against 075's independently produced per-case attribution.
    prior = os.path.join(ROOT, "findings/data/075-ical4j-residual-reproduced.json")
    if os.path.exists(prior):
        theirs = {}
        for bucket, bids in json.load(open(prior))["ids"].items():
            for i in bids:
                theirs[i] = bucket
        key = {"051A-no-deduplication": "051-A", "051B-ordinal-byday-empty": "051-B",
               "075C-chained-expansion": "075-J"}
        agree = [i for i in ids if i in theirs
                 and theirs[i].startswith(key.get(classify(cs[i],
                     store["answers"]["ical4j430"][i])[0], "\0"))]
        missing = [i for i in ids if i not in theirs]
        differ = [i for i in ids if i in theirs and i not in agree]
        print("  cross-check against 075's independent attribution:")
        print("    agree %d / %d   absent from 075 %d" % (len(agree), len(ids), len(missing)))
        for i in differ:
            print("    DIFFER %s  here=%s  075=%s"
                  % (i, "+".join(classify(cs[i], store["answers"]["ical4j430"][i])), theirs[i]))
        print()

    print("  BYMONTHDAY + BYDAY at FREQ=MONTHLY/YEARLY, whole corpus:")
    for rel in ("ical4j411", "ical4j430"):
        t = {}
        for i, is_ord in pop.items():
            g = store["answers"][rel][i]["occurrences"]
            t[(is_ord, g == [])] = t.get((is_ord, g == []), 0) + 1
        print("    %s  ordinal BYDAY: %d empty / %d non-empty   "
              "plain BYDAY: %d empty / %d non-empty"
              % (rel, t.get((True, True), 0), t.get((True, False), 0),
                 t.get((False, True), 0), t.get((False, False), 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
