"""024 -- Does one rewrite rule reproduce three independent lineages?

Hypothesis. On FREQ=YEARLY rules where RFC 5545 section 3.3.10's expand/limit
table is the *sole* authority and leaves a coarser date field unspecified, the
three independent lineages (libical, ical4j, dmfs lib-recur) behave exactly as
if that field had been filled from DTSTART -- i.e. as if the corresponding BYxxx
part were present with the DTSTART value:

    FREQ=YEARLY + BYMONTHDAY, no BYMONTH  ->  add BYMONTH=month(DTSTART)
    FREQ=YEARLY + BYWEEKNO,   no BYDAY    ->  add BYDAY=weekday(DTSTART)

The model is python-dateutil expanding the *rewritten* rule. Nothing else is
changed: same adapter, same limit, same DTSTART.

Run from the repository root, with each adapter's raw output already captured.
D is --outdir (default findings/repro/024-adapter-out). Do NOT point it at a
shared scratch directory such as /tmp; see finding 092 for what that cost.

    python3 conformance/adapters/dateutil_adapter.py  < cases > D/out.dateutil.ndjson
    java -cp <cp> Ical4jAdapter                       < cases > D/out.ical4j.ndjson
    java -cp <cp> DmfsAdapter                         < cases > D/out.dmfs.ndjson
    LD_LIBRARY_PATH=<prefix>/lib conformance/adapters/c/libical_adapter < cases \
                                                      > D/out.libical.ndjson

    python3 findings/repro/024-dtstart-fill-model.py --out findings/data/024-dtstart-fill.json

where `cases` is cases.ndjson reduced to the id/rrule/dtstart/limit fields.
"""
import argparse, datetime, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
import env
env.add_dateutil_to_path()
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"
WEEKDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
INDEPENDENT = ("ical4j", "dmfs", "libical")


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def expand(rrule, dtstart, limit):
    ds = datetime.datetime.strptime(dtstart, FMT)
    out = []
    for i, d in enumerate(rrulestr("RRULE:" + rrule, dtstart=ds)):
        if i >= limit:
            break
        out.append(d.strftime(FMT))
    return out


def rewrite(case):
    """The model. Returns the rewritten rule, or None if the shape does not apply."""
    p = parts(case["rrule"])
    if p.get("FREQ") != "YEARLY":
        return None
    if "BYMONTHDAY" in p and "BYMONTH" not in p:
        return case["rrule"] + ";BYMONTH=%d" % int(case["dtstart"][4:6])
    if "BYWEEKNO" in p and "BYDAY" not in p:
        wd = datetime.datetime.strptime(case["dtstart"], FMT).weekday()
        return case["rrule"] + ";BYDAY=" + WEEKDAY[wd]
    return None


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="conformance/cases.ndjson")
    ap.add_argument("--outdir", default="findings/repro/024-adapter-out")
    ap.add_argument("--out")
    args = ap.parse_args()

    with open(args.cases) as f:
        cases = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    impls = {n: load(os.path.join(args.outdir, "out.%s.ndjson" % n)) for n in INDEPENDENT}

    # Wake 140. This script used to default --outdir to /tmp and exit 0 when the
    # files there had nothing to do with the corpus. On 2026-09-25 the documented
    # command scored all 1727 corpus cases against 29-case leftovers written by an
    # unrelated probe eight days earlier, reproduced nothing, and reported success.
    # A missing or partial input is now a hard error, not a clean run. Finding 092.
    missing = []
    for n in INDEPENDENT:
        if impls[n] is None:
            missing.append("%s: out.%s.ndjson not present" % (n, n))
            continue
        covered = len(set(impls[n]) & set(cases))
        if covered < len(cases):
            missing.append("%s: %d of %d corpus ids" % (n, covered, len(cases)))
    if missing:
        sys.stderr.write(
            "024: adapter output under %s does not cover the corpus:\n  %s\n"
            "Capture it first -- see this file's header. Refusing to report.\n"
            % (args.outdir, "\n  ".join(missing)))
        return 2

    # The cluster: every case where all three independent lineages disagree with
    # the corpus *and* return the identical answer. Chosen before any model is
    # applied, so the model cannot have selected its own test set.
    cluster = []
    for cid, c in cases.items():
        answers = []
        for n in INDEPENDENT:
            o = impls[n].get(cid)
            if o is None or "error" in o:
                answers = None
                break
            answers.append(tuple(o["occurrences"]))
        if not answers or len(set(answers)) != 1:
            continue
        if answers[0] == tuple(c["expect"]):
            continue
        cluster.append((cid, list(answers[0])))

    result = {
        "cases_scored": len(cases),
        "three_way_identical_disagreements": len(cluster),
        "shapes": {},
        "model": {"reproduced": 0, "disagreed": 0, "out_of_shape": 0},
        "misses": [],
        "by_shape": {},
    }
    for cid, actual in cluster:
        p = parts(cases[cid]["rrule"])
        shape = "FREQ=%s %s" % (p.get("FREQ"), ",".join(sorted(k for k in p if k.startswith("BY"))))
        result["shapes"][shape] = result["shapes"].get(shape, 0) + 1

        rule = rewrite(cases[cid])
        if rule is None:
            result["model"]["out_of_shape"] += 1
            continue
        which = "bymonthday" if "BYMONTHDAY" in p else "byweekno"
        slot = result["by_shape"].setdefault(which, {"reproduced": 0, "disagreed": 0})
        pred = expand(rule, cases[cid]["dtstart"], cases[cid]["limit"])
        if pred == actual:
            result["model"]["reproduced"] += 1
            slot["reproduced"] += 1
        else:
            result["model"]["disagreed"] += 1
            slot["disagreed"] += 1
            result["misses"].append(
                {"id": cid, "rrule": cases[cid]["rrule"], "dtstart": cases[cid]["dtstart"],
                 "rewritten": rule, "model": pred, "implementations": actual}
            )

    # Superset test. The cluster above was selected by *disagreement*, so the
    # model was only ever asked about cases it was built to explain. Re-ask it
    # about every corpus case of the model's shape on which the three lineages
    # are three-way identical -- including the ones where they agree with the
    # corpus because BYSETPOS collapses both readings to the same instance.
    sup = {"reproduced": 0, "disagreed": 0, "shape_total": 0, "not_identical": 0,
           "identical_and_agreeing_with_corpus": 0}
    for cid, c in cases.items():
        rule = rewrite(c)
        if rule is None:
            continue
        sup["shape_total"] += 1
        answers = [impls[n].get(cid) or {} for n in INDEPENDENT]
        if any("error" in a or "occurrences" not in a for a in answers):
            sup["not_identical"] += 1
            continue
        distinct = {tuple(a["occurrences"]) for a in answers}
        if len(distinct) != 1:
            sup["not_identical"] += 1
            continue
        actual = list(distinct.pop())
        if actual == c["expect"]:
            sup["identical_and_agreeing_with_corpus"] += 1
        if expand(rule, c["dtstart"], c["limit"]) == actual:
            sup["reproduced"] += 1
        else:
            sup["disagreed"] += 1
    result["superset"] = sup

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")
    if result["model"]["reproduced"] == 0:
        sys.stderr.write("024: the model reproduced 0 cases; that is not a pass.\n")
        return 3
    return 0 if result["model"]["disagreed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
