#!/usr/bin/env python3
"""Finding 115 -- an exhaustive per-id partition of libical 3.0.20's fail bucket.

    python3 findings/repro/115-libical-3020-partition.py            # measure + print
    python3 findings/repro/115-libical-3020-partition.py --write    # regenerate the data file
    python3 findings/repro/115-libical-3020-partition.py --check    # guard: stored == live

Needs TWO adapter binaries, because libical 3 and 4 differ in API and one binary
cannot be pointed at the other library:

    make -C conformance/adapters/c libical_adapter3                       # system 3.0.20
    make -C conformance/adapters/c LIBICAL_PREFIX=<master-install>        # master 4edd39a3

Finding 017 classified this bucket BY SYMPTOM and said so: "The classification
is by symptom, not by root cause -- I did not bisect."  This script keeps the
symptom classes but makes two of them testable, and the labels it emits are
exactly the ones the finding claims.
"""
import argparse, collections, json, os, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
DATA = os.path.join(ROOT, "findings", "data", "115-libical-3020-partition.json")
ADP3 = os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter3")
ADP4 = os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter")
MASTER_LIB = os.environ.get("LIBICAL_LIB",
                            "/home/agent/terrarium/scratch/libical-install-4edd")

# The published row this partition must equal, from conformance/RESULTS.md.
PUBLISHED_FAIL_3020 = 107


def score(argv, env=None):
    tmp = os.path.join(ROOT, ".115-score.json")
    cmd = [sys.executable, os.path.join(ROOT, "conformance", "score.py"),
           "--json", tmp, "--show", "0", "--"] + argv
    e = dict(os.environ, TZ="UTC", **(env or {}))
    r = subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True, text=True)
    if not os.path.exists(tmp):
        raise SystemExit("score.py wrote nothing for %s\n%s" % (argv, r.stderr[-800:]))
    with open(tmp) as fh:
        s = json.load(fh)
    os.unlink(tmp)
    return s


def probe(rrules):
    """[(id, dtstart, rrule, limit)] -> {id: occurrences} through 3.0.20."""
    if not rrules:
        return {}
    inp = "".join(json.dumps(dict(id=i, dtstart=d, rrule=r, limit=l)) + "\n"
                  for i, d, r, l in rrules)
    p = subprocess.run([ADP3], input=inp, capture_output=True, text=True,
                       env=dict(os.environ, TZ="UTC"))
    if p.returncode != 0:
        raise SystemExit("adapter rc=%d: %s" % (p.returncode, p.stderr[-400:]))
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = o.get("occurrences")
    return out


def links(binary):
    """The libical soname `binary` actually resolves. Trusting the build here
    would be a mistake I made while writing this script: the Makefile has ONE
    target name, so rebuilding with a different LIBICAL_PREFIX is a silent
    no-op when the binary is newer than the source, and the run then reports
    the wrong library's numbers with no sign that anything is wrong."""
    out = subprocess.run(["ldd", binary], capture_output=True, text=True).stdout
    for line in out.splitlines():
        name = line.strip().split(" ")[0]
        if name.startswith("libical.so."):
            return name
    raise SystemExit("%s links no libical at all:\n%s" % (binary, out))


def drop(rrule, key):
    return ";".join(kv for kv in rrule.split(";") if not kv.startswith(key + "="))


def classify():
    """-> (partition, evidence, corpus_version). Partition covers all 107."""
    for p, what in ((ADP3, "make -C conformance/adapters/c libical_adapter3"),
                    (ADP4, "make -C conformance/adapters/c LIBICAL_PREFIX=...")):
        if not os.path.exists(p):
            raise SystemExit("missing %s -- build it:\n  %s" % (p, what))

    want = {ADP3: "libical.so.3", ADP4: "libical.so.4"}
    for b, soname in want.items():
        got = links(b)
        if not got.startswith(soname):
            raise SystemExit(
                "%s links %s, expected %s. Rebuild it -- and note that `make`\n"
                "alone will NOT do it if the binary is newer than the source:\n"
                "  rm -f %s && make -C conformance/adapters/c %s"
                % (b, got, soname, b,
                   os.path.basename(b) if b == ADP3
                   else "LIBICAL_PREFIX=" + MASTER_LIB))

    s3 = score([ADP3])
    s4 = score([ADP4], {"LD_LIBRARY_PATH": os.path.join(MASTER_LIB, "lib")})
    fails = {f["case"]["id"]: f for f in s3["failures"] if f["bucket"] == "fail"}
    if len(fails) != PUBLISHED_FAIL_3020:
        raise SystemExit("3.0.20 fail bucket is %d, RESULTS.md publishes %d"
                         % (len(fails), PUBLISHED_FAIL_3020))
    master = {f["case"]["id"]: f["bucket"] for f in s4["failures"]}
    # Every non-pass bucket in 3.0.20, not just `fail`. The regression question
    # below is about what 3.0.20 got RIGHT, so it needs the whole complement,
    # and getting this wrong once already made the script print "3 regressions"
    # for three cases 3.0.20 never passed.
    nonpass_3020 = {f["case"]["id"] for f in s3["failures"]}

    part = collections.defaultdict(list)
    ev = {}

    # Class 1 -- libical #797/#937: right occurrences, wrong order, or DTSTART
    # emitted twice. VERIFIED, not guessed: the reply is a permutation of
    # expect, or it repeats DTSTART. No rule-text pattern is involved.
    rest = []
    for i, f in sorted(fails.items()):
        e, g = f["case"]["expect"], f["reply"].get("occurrences") or []
        if sorted(g) == sorted(e) and g != e:
            part["115 937-order"].append(i)
        elif g and g[0] == f["case"]["dtstart"] and len(g) != len(set(g)):
            part["115 937-dtstart-twice"].append(i)
        else:
            rest.append(i)

    # Class 2 -- libical #795, BYSETPOS not applied. The TEST: re-run the same
    # rule with BYSETPOS deleted and require 3.0.20's real output back, byte
    # for byte. A superset test would be wrong here: the corpus caps output at
    # `limit`, so ignoring BYSETPOS returns a PREFIX of the unfiltered stream,
    # not a superset of the filtered one.
    cand = [i for i in rest if "BYSETPOS=" in fails[i]["case"]["rrule"]]
    got = probe([(i, fails[i]["case"]["dtstart"],
                  drop(fails[i]["case"]["rrule"], "BYSETPOS"),
                  fails[i]["case"]["limit"]) for i in cand])
    for i in cand:
        actual = fails[i]["reply"].get("occurrences") or []
        if got.get(i) == actual:
            part["115 795-bysetpos-ignored"].append(i)
            rest.remove(i)
    ev["795_predictor"] = {"candidates": len(cand),
                           "reproduced": len(part["115 795-bysetpos-ignored"])}

    # Class 3 -- BYWEEKNO with no BYDAY (libical #794's shape). The predictor
    # "BYWEEKNO is ignored" is REFUTED here and the finding says so; these are
    # held as a symptom class, and what makes them a class is that master
    # scores every one of them fail_other_reading -- a different reading, not
    # a pass.
    wk = [i for i in rest
          if "BYWEEKNO=" in fails[i]["case"]["rrule"]
          and "BYDAY=" not in fails[i]["case"]["rrule"]]
    got = probe([(i, fails[i]["case"]["dtstart"],
                  drop(fails[i]["case"]["rrule"], "BYWEEKNO"),
                  fails[i]["case"]["limit"]) for i in wk])
    refuted = sum(1 for i in wk
                  if got.get(i) != (fails[i]["reply"].get("occurrences") or []))
    ev["794_ignore_predictor_refuted_in"] = {"candidates": len(wk),
                                             "refuted": refuted}
    for i in wk:
        part["115 794-byweekno-no-byday"].append(i)
        rest.remove(i)

    # Class 4 -- FREQ=YEARLY combining BYWEEKNO/BYYEARDAY with BYDAY. libical
    # #1276's family, and the only class with cases master still fails.
    for i in list(rest):
        r = fails[i]["case"]["rrule"]
        if "BYWEEKNO=" in r or "BYYEARDAY=" in r:
            part["115 1276-yearly-weekno-byday"].append(i)
            rest.remove(i)

    # Class 5 -- the residue. One case, named, with no mechanism claimed.
    for i in rest:
        part["115 unexplained"].append(i)

    ev["master_bucket_by_label"] = {
        lbl: dict(collections.Counter(master.get(i, "pass") for i in ids))
        for lbl, ids in sorted(part.items())}
    ev["counts"] = {lbl: len(ids) for lbl, ids in sorted(part.items())}
    ev["total"] = sum(len(v) for v in part.values())
    # A regression would be a case 3.0.20 PASSES and master fails. Not "a case
    # master fails that is absent from 3.0.20's fail bucket" -- three cases sit
    # in 3.0.20's fail_other_reading or error and would be counted wrongly.
    ev["master_fails_that_3020_passes"] = sorted(
        i for i, b in master.items() if b == "fail" and i not in nonpass_3020)
    ev["795_predictor_misses"] = sorted(
        (i, fails[i]["case"]["rrule"]) for i in cand
        if i not in part["115 795-bysetpos-ignored"])
    return dict(part), ev, s3["corpus_version"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    part, ev, cv = classify()

    print("libical 3.0.20 fail bucket, %d cases, %d labels"
          % (ev["total"], len(part)))
    for lbl, n in sorted(ev["counts"].items()):
        print("  %-34s %3d   master: %s"
              % (lbl, n, ev["master_bucket_by_label"][lbl]))
    print("  #795 predictor 'BYSETPOS ignored' reproduced %d of %d"
          % (ev["795_predictor"]["reproduced"], ev["795_predictor"]["candidates"]))
    print("  #794 predictor 'BYWEEKNO ignored' REFUTED in %d of %d"
          % (ev["794_ignore_predictor_refuted_in"]["refuted"],
             ev["794_ignore_predictor_refuted_in"]["candidates"]))
    print("  regressions (3.0.20 passes, master fails): %d"
          % len(ev["master_fails_that_3020_passes"]))
    for i, r in ev["795_predictor_misses"]:
        print("  #795 predictor MISS %s  %s" % (i, r))

    seen = {}
    for lbl, ids in part.items():
        for i in ids:
            if i in seen:
                raise SystemExit("id %s under two labels: %s, %s"
                                 % (i, seen[i], lbl))
            seen[i] = lbl
    if ev["total"] != PUBLISHED_FAIL_3020:
        raise SystemExit("partition holds %d, bucket is %d"
                         % (ev["total"], PUBLISHED_FAIL_3020))

    out = {"finding": "115", "cases_id": cv["cases_id"], "corpus_version": cv,
           "master_lib": MASTER_LIB, "partition": part, "evidence": ev}
    if args.write:
        with open(DATA, "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote %s" % DATA)
        return
    if args.check:
        with open(DATA) as fh:
            stored = json.load(fh)
        bad = []
        if stored["cases_id"] != cv["cases_id"]:
            bad.append("cases_id moved")
        if {k: sorted(v) for k, v in stored["partition"].items()} != \
           {k: sorted(v) for k, v in part.items()}:
            bad.append("partition differs from live measurement")
        for k in ("counts", "795_predictor", "794_ignore_predictor_refuted_in",
                  "master_fails_that_3020_passes"):
            if stored["evidence"][k] != ev[k]:
                bad.append("evidence.%s differs" % k)
        if bad:
            for b in bad:
                print("FAIL: %s" % b)
            raise SystemExit(1)
        print("OK: stored partition and evidence reproduce exactly")


if __name__ == "__main__":
    main()
