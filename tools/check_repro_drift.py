#!/usr/bin/env python3
"""Do the documented reproduce commands still print what the findings published?

Finding 091 checks a published figure against a *stored* artifact. That cannot
see the other way a figure goes wrong: a finding documents a script, the script
keeps running and keeps exiting 0, and the data underneath it moves. Finding
031 drifted that way for five days -- commit 5d6745e changed the corpus and two
rows of its table silently stopped being true. Nothing re-ran the script.

This is the missing re-run. Each manifest entry pairs a reproduce command with a
baseline of its output, captured at a known corpus identity. Drift is a diff.

    python3 tools/check_repro_drift.py            # check, exit 1 on drift
    python3 tools/check_repro_drift.py --update   # re-baseline, deliberately

Only fast, self-contained, deterministic commands belong here. A command that
needs an adapter, a network, or thirty minutes does not; see MANIFEST comments
for what is deliberately excluded and why.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", "repro-drift.json")
BASELINES = os.path.join(ROOT, "findings", "repro", "baselines")


def corpus_id():
    r = subprocess.run([sys.executable, "tools/corpus_id.py"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "unknown"
    for line in (r.stdout or "").splitlines():
        if line.startswith("cases_id"):
            return line.split()[1]
    return "unknown"


def run(entry):
    r = subprocess.run(entry["argv"], cwd=ROOT, capture_output=True, text=True,
                       timeout=entry.get("timeout", 300))
    return r.returncode, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true",
                    help="rewrite the baselines from the current output")
    ap.add_argument("--only", help="run one entry by finding number")
    a = ap.parse_args()

    entries = json.load(open(MANIFEST))["entries"]
    if a.only:
        entries = [e for e in entries if e["finding"] == a.only]
        if not entries:
            sys.stderr.write("no manifest entry for %s\n" % a.only)
            return 2

    os.makedirs(BASELINES, exist_ok=True)
    cid = corpus_id()
    drifted, broken = [], []

    for e in entries:
        path = os.path.join(BASELINES, e["baseline"])
        rc, out = run(e)
        label = "%s  %s" % (e["finding"], " ".join(e["argv"]))
        if rc != e.get("expect_rc", 0):
            print("BROKEN  %s\n        exit %d, expected %d"
                  % (label, rc, e.get("expect_rc", 0)))
            broken.append(e["finding"])
            continue
        if a.update:
            with open(path, "w") as f:
                f.write(out)
            print("baselined  %s" % label)
            continue
        if not os.path.exists(path):
            print("NO BASELINE  %s" % label)
            broken.append(e["finding"])
            continue
        want = open(path).read()
        if want == out:
            print("same    %s" % label)
        else:
            print("DRIFT   %s" % label)
            drifted.append(e["finding"])
            wl, ol = want.splitlines(), out.splitlines()
            for i in range(max(len(wl), len(ol))):
                w = wl[i] if i < len(wl) else "<absent>"
                o = ol[i] if i < len(ol) else "<absent>"
                if w != o:
                    print("        baseline: %s\n        now     : %s" % (w, o))

    if a.update:
        m = json.load(open(MANIFEST))
        m["baselined_at_cases_id"] = cid
        json.dump(m, open(MANIFEST, "w"), indent=1, sort_keys=True)
        open(MANIFEST, "a").write("\n")
        print("\nbaselines now describe cases_id %s" % cid)
        return 0

    print("\ncases_id now  : %s" % cid)
    print("baselined at : %s" % json.load(open(MANIFEST)).get("baselined_at_cases_id"))
    if drifted:
        print("\nDRIFTED: %s" % ", ".join(drifted))
        print("A drift is not automatically an error. Decide which is right, correct")
        print("the finding if the published number is now wrong, then --update.")
    if broken:
        print("\nBROKEN: %s" % ", ".join(broken))
    return 1 if (drifted or broken) else 0


if __name__ == "__main__":
    sys.exit(main())
