"""How much does a short prefix hide? (standing rule 33b, finding 039)

Every count in RESULTS.md is a count of disagreements *inside the horizon the
corpus chose* -- typically the first 8 occurrences. This script measures the
gap that caveat names: it re-runs the scored corpus at a much longer limit and
asks how many cases that SCORE AS PASSES diverge from a cross-lineage control
once the horizon is extended.

    python3 conformance/horizon_sweep.py --limit 64 --json out.json ical4j

The control is agreement between two independent lineages (dateutil and
libical, see standing rule 24 -- rrule.js is a dateutil port and does not get a
second vote). Where the control disagrees with itself the case is INCONCLUSIVE
and is reported as such rather than charged to anybody.

A divergence found here is a disagreement with the control at a horizon the
corpus never adjudicated. It is NOT a corpus failure and NOT by itself a defect
claim: nobody checked those later occurrences against RFC 5545 by hand.
"""
import json, os, sys, argparse, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CP = "%s/conformance/adapters/java/classes:%s/conformance/adapters/java/libs/*" % (ROOT, ROOT)

ADAPTERS = {
    "dateutil": ["python3", HERE + "/adapters/dateutil_adapter.py"],
    "libical":  [HERE + "/adapters/c/libical_adapter"],
    "rrulejs":  ["node", HERE + "/adapters/rrulejs_adapter.js"],
    "ical4j":   ["java", "-Duser.language=en", "-Duser.country=US", "-cp", CP, "Ical4jAdapter"],
    "dmfs":     ["java", "-Duser.language=en", "-Duser.country=US", "-cp", CP, "DmfsAdapter"],
    "rustrrule":[HERE + "/adapters/rust/target/release/rustrrule_adapter"],
}
ENV = dict(os.environ)
ENV["LD_LIBRARY_PATH"] = "/home/agent/terrarium/scratch/libical-install-4edd/lib"


def run(name, cases, limit, timeout=1800):
    payload = "".join(json.dumps({"id": c["id"], "rrule": c["rrule"],
                                  "dtstart": c["dtstart"], "limit": limit}) + "\n"
                      for c in cases)
    p = subprocess.run(ADAPTERS[name], input=payload, capture_output=True,
                       text=True, timeout=timeout, env=ENV)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-2000:])
        raise SystemExit("%s exited %d" % (name, p.returncode))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = o
    return out


def occ(reply):
    if reply is None or "error" in reply:
        return None
    g = reply.get("occurrences")
    return g if isinstance(g, list) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", nargs="+", help="adapter name(s) from ADAPTERS")
    ap.add_argument("--limit", type=int, default=64)
    ap.add_argument("--json")
    a = ap.parse_args()

    cases = [json.loads(l) for l in open(HERE + "/cases.ndjson")]
    by_id = {c["id"]: c for c in cases}

    ctrl = {n: run(n, cases, a.limit) for n in ("dateutil", "libical")}
    report = {"limit": a.limit, "cases": len(cases), "subjects": {}}

    for name in a.subject:
        got = run(name, cases, a.limit)
        # short-horizon score, exactly as score.py sees it
        counts = collections.Counter()
        rows = []
        for c in cases:
            cid = c["id"]
            ref = occ(ctrl["dateutil"].get(cid))
            ref2 = occ(ctrl["libical"].get(cid))
            mine = occ(got.get(cid))
            if ref is None or ref2 is None or ref != ref2:
                counts["inconclusive_control"] += 1
                continue
            if mine is None:
                counts["subject_error"] += 1
                continue
            n = c["limit"]
            short_agrees = mine[:n] == ref[:n] == c["expect"][:n]
            if mine == ref:
                counts["agrees_long"] += 1
                continue
            if short_agrees:
                first = next((i for i in range(max(len(mine), len(ref)))
                              if mine[i:i+1] != ref[i:i+1]), None)
                # Two very different things hide behind a short horizon. If the
                # subject's answer is a proper PREFIX of the control's, it did
                # not get a date wrong -- it stopped expanding early, which is
                # an expansion cap, not a divergence about dates. Only the rest
                # are cases where the subject emits a date the control does not.
                early = len(mine) < len(ref) and mine == ref[:len(mine)]
                counts["hidden_early_stop" if early else "hidden_content"] += 1
                rows.append({"id": cid, "rrule": c["rrule"], "dtstart": c["dtstart"],
                             "corpus_limit": n, "first_divergence_index": first,
                             "kind": "early_stop" if early else "content",
                             "control_len": len(ref), "subject_len": len(mine),
                             "control": ref[:first+2] if first is not None else ref,
                             "subject": mine[:first+2] if first is not None else mine})
            else:
                counts["visible_at_corpus_limit"] += 1
        report["subjects"][name] = {"counts": dict(counts), "hidden": rows}
        print(name, dict(counts))

    if a.json:
        json.dump(report, open(a.json, "w"), indent=1, sort_keys=True)
        print("wrote", a.json)


if __name__ == "__main__":
    main()
