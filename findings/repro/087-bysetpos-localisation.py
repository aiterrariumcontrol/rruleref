#!/usr/bin/env python3
"""087 -- where a BYSETPOS failure actually lives.

For every corpus case carrying BYSETPOS, build the SAME case with the BYSETPOS
part deleted and nothing else changed.  Run both through an adapter.

The question is not whether the implementation is correct on the stripped rule.
It is whether its disagreement SURVIVES the removal of BYSETPOS:

  * it fails the original and AGREES with the reference on the stripped rule
      -> the candidate set it built matches the reference's, so whatever went
         wrong is at or after the BYSETPOS step.        DOWNSTREAM
  * it fails the original and DISAGREES on the stripped rule too
      -> the candidate set was already different before BYSETPOS ran.  The
         BYSETPOS case is a second symptom of that, not a BYSETPOS defect.
                                                        UPSTREAM

The reference is python-dateutil run on the stripped rule.  It is a REFERENCE,
not an oracle: the claim is localisation relative to a fixed comparand, and it
does not assert the reference is right.  dateutil's one known BYSETPOS defect
(finding 004, a first period truncated at DTSTART) cannot act here, because the
rules the reference is run on carry no BYSETPOS.

Usage:  087-bysetpos-localisation.py --run "<adapter argv>" --name <label>
        087-bysetpos-localisation.py --reference          (build reference once)
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
DATA = os.path.join(os.path.dirname(HERE), "data")
REFPATH = os.path.join(DATA, "087-stripped-reference.json")


def strip_bysetpos(rrule):
    parts = [p for p in rrule.split(";") if not p.upper().startswith("BYSETPOS=")]
    return ";".join(parts)


def load_bysetpos_cases():
    out = []
    with open(CASES) as fh:
        for line in fh:
            c = json.loads(line)
            if re.search(r"(^|;)BYSETPOS=", c["rrule"], re.I):
                out.append(c)
    return out


def run_adapter(argv, lines, timeout=1800):
    payload = "".join(json.dumps(l) + "\n" for l in lines)
    p = subprocess.run(argv, input=payload, capture_output=True, text=True,
                       timeout=timeout, env=dict(os.environ, TZ="UTC"))
    replies = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if "id" in r:
            replies[r["id"]] = r
    return replies


def accepted(case, got):
    """True if `got` is the corpus answer or one of its recorded rival readings."""
    if got == case["expect"]:
        return True
    for _, alt in sorted(case.get("reading_alternatives", {}).items()):
        if got == alt:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="adapter argv as one string")
    ap.add_argument("--name", default="adapter")
    ap.add_argument("--reference", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    cases = load_bysetpos_cases()
    stripped = [{"id": c["id"], "rrule": strip_bysetpos(c["rrule"]),
                 "dtstart": c["dtstart"], "limit": c["limit"]} for c in cases]

    if a.reference:
        os.makedirs(DATA, exist_ok=True)
        ref = run_adapter(["python3", os.path.join(ROOT, "conformance", "adapters",
                                                   "dateutil_adapter.py")], stripped)
        ref = {k: v.get("occurrences") for k, v in ref.items()}
        with open(REFPATH, "w") as fh:
            json.dump(ref, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("reference: %d of %d stripped rules answered" % (
            sum(1 for v in ref.values() if v is not None), len(stripped)))
        return

    with open(REFPATH) as fh:
        ref = json.load(fh)

    argv = a.run.split()
    orig_replies = run_adapter(argv, [{"id": c["id"], "rrule": c["rrule"],
                                       "dtstart": c["dtstart"], "limit": c["limit"]}
                                      for c in cases], a.timeout)
    strip_replies = run_adapter(argv, stripped, a.timeout)

    rows = []
    for c in cases:
        o = orig_replies.get(c["id"], {})
        s = strip_replies.get(c["id"], {})
        got = o.get("occurrences")
        sgot = s.get("occurrences")
        if got is None:
            verdict = "no-answer-original"
        elif accepted(c, got):
            verdict = "passes"
        elif sgot is None:
            verdict = "no-answer-stripped"
        elif ref.get(c["id"]) is None:
            verdict = "no-reference"
        elif sgot == ref[c["id"]]:
            verdict = "DOWNSTREAM"
        else:
            verdict = "UPSTREAM"
        rows.append({"id": c["id"], "rrule": c["rrule"], "dtstart": c["dtstart"],
                     "verdict": verdict})

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    fails = sum(v for k, v in counts.items() if k != "passes")
    print("%s: %d BYSETPOS cases, %d not accepted" % (a.name, len(rows), fails))
    for k in sorted(counts):
        print("   %-20s %d" % (k, counts[k]))

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "087-localisation-%s.json" % a.name)
    with open(out, "w") as fh:
        json.dump({"adapter": a.name, "argv": argv, "counts": counts, "rows": rows},
                  fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("   -> %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
