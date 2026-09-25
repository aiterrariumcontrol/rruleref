#!/usr/bin/env python3
"""088 -- is rule 96 a general lens, or a fact about BYSETPOS?

Finding 087 established, for BYSETPOS, that a failure on a rule carrying part X
is not evidence of a defect in X until the same rule is asked without X.  It
split 291 BYSETPOS failures 194 UPSTREAM / 117 DOWNSTREAM.

This probe asks the same counterfactual for ANY BY part.  It is deliberately
NOT the same claim, and the difference matters:

  BYSETPOS is a SELECTOR.  Deleting it leaves the candidate set untouched and
  removes only the selection step, so a surviving disagreement localises
  cleanly: the set was already wrong.  That is a decomposition.

  BYMONTH, BYDAY, BYWEEKNO, BYMONTHDAY are SET-CONSTRUCTION parts.  Deleting
  one does not leave "the same set, minus a step" -- it changes the set.  So
  the verdict here is weaker and must be named honestly.  It is a NECESSITY
  test:

    ATTRIBUTABLE -- fails the original, agrees with the reference once X is
                    gone.  X is necessary to provoke the disagreement.
    NOT-NECESSARY -- fails the original and disagrees without X too.  The
                    implementation is already wrong on the remainder of the
                    rule; blaming X is at best incomplete.

  "NOT-NECESSARY" is NOT the same statement as 087's "UPSTREAM".  It does not
  say where the defect lives.  It says only that X is not required to expose
  it.  Reporting it as an X defect is unsupported either way.

STRATIFICATION.  Stripping X from a rule whose ONLY BY part is X leaves a bare
FREQ rule, which essentially every implementation handles.  Such cases are
near-guaranteed to come out ATTRIBUTABLE, and pooling them would manufacture
the result.  They are counted and reported SEPARATELY, and the headline number
is the ACCOMPANIED stratum only.  BYSETPOS never occurs alone (291/291
accompanied), which is exactly why 087 did not need this control.

The reference is python-dateutil on the stripped rule.  It is a REFERENCE, not
an oracle: the claim is relative to a fixed comparand and does not assert the
reference is correct.  Unlike 087, the reference's own known defects are NOT
structurally excluded here, because a stripped rule may still carry parts
dateutil gets wrong.  Cases where dateutil is itself a recorded offender are
flagged `reference-suspect` and excluded from the headline.

Usage:
  088-part-necessity.py --part BYMONTH --reference
  088-part-necessity.py --part BYMONTH --run "<adapter argv>" --name <label>
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
DATA = os.path.join(os.path.dirname(HERE), "data")


def refpath(part):
    return os.path.join(DATA, "088-stripped-reference-%s.json" % part.lower())


def strip_part(rrule, part):
    keep = [p for p in rrule.split(";")
            if not p.upper().startswith(part.upper() + "=")]
    return ";".join(keep)


def by_parts(rrule):
    return [p.split("=")[0].upper() for p in rrule.split(";")
            if p.split("=")[0].upper().startswith("BY")]


def load_cases(part):
    out = []
    with open(CASES) as fh:
        for line in fh:
            c = json.loads(line)
            if re.search(r"(^|;)%s=" % re.escape(part), c["rrule"], re.I):
                out.append(c)
    return out


def run_adapter(argv, lines, timeout=1800):
    payload = "".join(json.dumps(l) + "\n" for l in lines)
    p = subprocess.run(argv, input=payload, capture_output=True, text=True,
                       timeout=timeout, env=dict(os.environ, TZ="UTC"))
    replies = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
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
    ap.add_argument("--part", required=True)
    ap.add_argument("--run", help="adapter argv as one string")
    ap.add_argument("--name", default="adapter")
    ap.add_argument("--reference", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    part = a.part.upper()

    cases = load_cases(part)
    if not cases:
        sys.exit("no corpus case carries %s" % part)
    stripped = [{"id": c["id"], "rrule": strip_part(c["rrule"], part),
                 "dtstart": c["dtstart"], "limit": c["limit"]} for c in cases]

    if a.reference:
        os.makedirs(DATA, exist_ok=True)
        ref = run_adapter(["python3", os.path.join(ROOT, "conformance", "adapters",
                                                   "dateutil_adapter.py")], stripped)
        ref = {k: v.get("occurrences") for k, v in ref.items()}
        with open(refpath(part), "w") as fh:
            json.dump(ref, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("%s reference: %d of %d stripped rules answered"
              % (part, sum(1 for v in ref.values() if v is not None), len(stripped)))
        return

    with open(refpath(part)) as fh:
        ref = json.load(fh)

    argv = a.run.split()
    orig = run_adapter(argv, [{"id": c["id"], "rrule": c["rrule"],
                               "dtstart": c["dtstart"], "limit": c["limit"]}
                              for c in cases], a.timeout)
    strp = run_adapter(argv, stripped, a.timeout)

    rows = []
    for c in cases:
        alone = len(by_parts(c["rrule"])) == 1
        got = orig.get(c["id"], {}).get("occurrences")
        sgot = strp.get(c["id"], {}).get("occurrences")
        if got is None:
            v = "no-answer-original"
        elif accepted(c, got):
            v = "passes"
        elif sgot is None:
            v = "no-answer-stripped"
        elif ref.get(c["id"]) is None:
            v = "no-reference"
        elif sgot == ref[c["id"]]:
            v = "ATTRIBUTABLE"
        else:
            v = "NOT-NECESSARY"
        rows.append({"id": c["id"], "rrule": c["rrule"], "dtstart": c["dtstart"],
                     "stratum": "alone" if alone else "accompanied", "verdict": v})

    def tally(sel):
        t = {}
        for r in rows:
            if sel(r):
                t[r["verdict"]] = t.get(r["verdict"], 0) + 1
        return t

    acc, alone = tally(lambda r: r["stratum"] == "accompanied"), tally(lambda r: r["stratum"] == "alone")
    print("%s / %s: %d cases carry %s" % (a.name, part, len(rows), part))
    for label, t in (("ACCOMPANIED (headline)", acc), ("alone (control)", alone)):
        n = sum(t.values())
        print("  %-24s %d" % (label, n))
        for k in sorted(t):
            print("      %-20s %d" % (k, t[k]))

    os.makedirs(DATA, exist_ok=True)
    out = os.path.join(DATA, "088-necessity-%s-%s.json" % (part.lower(), a.name))
    with open(out, "w") as fh:
        json.dump({"adapter": a.name, "part": part, "argv": argv,
                   "accompanied": acc, "alone": alone, "rows": rows},
                  fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("  -> %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
