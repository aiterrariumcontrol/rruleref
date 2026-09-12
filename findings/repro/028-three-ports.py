"""Finding 028. Three ports of python-dateutil, compared against their parent
and against each other on every corroborated case, without consulting `expect`
-- so the answer does not depend on this corpus's readings of RFC 5545.

    python3 findings/repro/028-three-ports.py <go-adapter> <rust-adapter> <node-path>

Run from the repository root, under TZ=UTC. Prints the pairwise divergence
counts, the decomposition of each port's divergence from its parent, and
whether the two ports that diverge do so on the same cases.
"""
import json, subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def build_input():
    cases = json.load(open(os.path.join(ROOT, "corpus", "corroborated.json")))["cases"]
    lines = []
    for c in cases:
        lim = len(c["expect"]) + 1 if c.get("expect_bound") == "complete" else len(c["expect"])
        lines.append(json.dumps({"id": c["rrule"] + "|" + c["dtstart"], "rrule": c["rrule"],
                                 "dtstart": c["dtstart"], "limit": max(lim, 1)}))
    return "\n".join(lines) + "\n", len(cases)

def run(cmd, data, env=None):
    e = dict(os.environ, **(env or {}))
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, env=e, cwd=ROOT)
    if p.returncode != 0:
        sys.exit("adapter failed: %s\n%s" % (cmd, p.stderr[:500]))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = ("ERR", o["error"]) if "error" in o else ("OK", tuple(o.get("occurrences") or []))
    return out

go_cmd, rust_cmd, node_path = sys.argv[1], sys.argv[2], sys.argv[3]
data, n = build_input()
print("corroborated cases: %d" % n)
results = {
    "python-dateutil": run([sys.executable, "conformance/adapters/dateutil_adapter.py"], data),
    "rrule.js": run(["node", "conformance/adapters/rrulejs_adapter.js"], data, {"NODE_PATH": node_path}),
    "rrule-go": run([go_cmd], data),
    "rust-rrule": run([rust_cmd], data),
}
ids = set.intersection(*(set(r) for r in results.values()))
print("ids compared: %d" % len(ids))
names = list(results)
for i, a in enumerate(names):
    for b in names[i+1:]:
        d = [k for k in ids if results[a][k] != results[b][k]]
        print("%-16s vs %-16s %5d differ (%.1f%%)" % (a, b, len(d), 100.0*len(d)/len(ids)))

du, js, rs = results["python-dateutil"], results["rrule.js"], results["rust-rrule"]
for nm, r in (("rrule.js", js), ("rust-rrule", rs)):
    d = [k for k in ids if du[k] != r[k]]
    nonasc = [k for k in d if r[k][0] == "OK" and list(r[k][1]) != sorted(r[k][1])]
    rest = [k for k in d if k not in nonasc]
    errs = [k for k in d if r[k][0] == "ERR"]
    print("\n%s divergence from dateutil: %d" % (nm, len(d)))
    print("  %4d non-ascending list" % len(nonasc))
    print("  %4d remainder, of which BYSETPOS: %d, errors: %d"
          % (len(rest), sum("BYSETPOS" in k for k in rest), len(errs)))
# do rrule.js and rust-rrule diverge on the SAME cases?
djs = set(k for k in ids if du[k] != js[k])
drs = set(k for k in ids if du[k] != rs[k])
print("\noverlap of the two ports' divergence sets: %d (js-only %d, rust-only %d)"
      % (len(djs & drs), len(djs - drs), len(drs - djs)))
