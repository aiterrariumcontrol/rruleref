"""Finding 027. Compare python-dateutil, rrule.js and rrule-go on every
corroborated case, without consulting `expect` — so the answer does not depend
on this corpus's readings of RFC 5545 being right.

    python3 findings/repro/027-port-drift.py <go-adapter> [<node-path>]

Run from the repository root. Prints the pairwise divergence counts and the
decomposition of rrule.js's divergence from its parent.
"""
import json, subprocess, sys, os, collections

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
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, env=e)
    if p.returncode != 0:
        sys.exit("adapter failed: %s\n%s" % (cmd, p.stderr[:500]))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = ("ERR", o["error"]) if "error" in o else ("OK", tuple(o.get("occurrences") or []))
    return out


def main():
    go_cmd = sys.argv[1] if len(sys.argv) > 1 else None
    node_path = sys.argv[2] if len(sys.argv) > 2 else None
    data, n = build_input()
    print("corroborated cases: %d" % n)

    results = {"python-dateutil": run([sys.executable, "conformance/adapters/dateutil_adapter.py"], data)}
    if node_path:
        results["rrule.js"] = run(["node", "conformance/adapters/rrulejs_adapter.js"], data,
                                  {"NODE_PATH": node_path})
    if go_cmd:
        results["rrule-go"] = run([go_cmd], data)

    ids = set.intersection(*(set(r) for r in results.values()))
    names = list(results)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = [k for k in ids if results[a][k] != results[b][k]]
            print("%-16s vs %-16s %5d differ (%.1f%%)" % (a, b, len(d), 100.0 * len(d) / len(ids)))

    if "rrule.js" in results:
        du, js = results["python-dateutil"], results["rrule.js"]
        d = [k for k in ids if du[k] != js[k]]
        nonasc = [k for k in d if list(js[k][1]) != sorted(js[k][1])]
        setpos = [k for k in d if k not in nonasc]
        print("\nrrule.js divergence from its parent, decomposed:")
        print("  %4d  rrule.js returned a non-ascending list" % len(nonasc))
        print("  %4d  remainder, of which BYSETPOS: %d" % (len(setpos), sum("BYSETPOS" in k for k in setpos)))
        print("  dateutil non-ascending anywhere in %d: %d"
              % (len(ids), sum(1 for k in ids if list(du[k][1]) != sorted(du[k][1]))))


if __name__ == "__main__":
    main()
