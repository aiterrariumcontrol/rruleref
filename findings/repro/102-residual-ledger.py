#!/usr/bin/env python3
"""
102 -- a producer for the ical.js residual count.

The figure "074's residual is now N" has been carried in prose from finding to
finding since 096: 23 -> 16 -> 14 -> 13 -> 7 -> 4 -> 2. Nothing computed it.
Each step was a subtraction written by hand into a correction notice, and the
ids being subtracted were not always published.

This script is the missing producer. It does not measure anything new. It
states a DEFINITION and then checks the published claims against it.

DEFINITION. An id is ATTRIBUTED iff:
  (a) it is a member of 074's base set -- the 23 ids under
      data/074-icaljs-residual-reproduced.json ids.unexplained, which 074 drew
      from the `fail` bucket ONLY (repro/074-attribute-icaljs-residual.py
      selects bucket == 'fail'); and
  (b) some finding names that exact id in its own published .md text as
      reproduced by a predictor.

Membership in (a) is the check that matters, because a case outside the base set
cannot reduce the base set no matter how well a predictor reproduces it.

The residual is |base| minus the attributed ids. Nothing is subtracted by count.

Read-only. Uses stored data plus one re-run of 096's own classifier (which
recomputes its per-id buckets from stored outputs, no adapter).
"""
import contextlib
import glob
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BASE = os.path.join(REPO, "findings/data/074-icaljs-residual-reproduced.json")
LEDGER = os.path.join(REPO, "findings/data/102-icaljs-residual-ledger.json")

# Findings that claim ids by NAME in their own prose. The ids are not the
# authority -- the finding's .md text is, and every id below is verified to
# appear in it. 096 is absent on purpose: it published counts, not ids, so its
# seven are recovered from its own classifier instead (see below).
NAMED = {
    "097": ["88a59d144b92", "9346b18d8869"],
    "098": ["3939127583ee"],
    "099": ["0fcc0ebb9669", "57bd6869b586", "5b57fff10b12",
            "71c5fc332bd4", "7a381d6a4176", "83ed4e4655a6"],
    "100": ["111d7647f8a8", "be630fe23f8c", "e1b4925a5263"],
    "101": ["1952128a3c40"],
    "104": ["7a6256afbb5b", "f9f6ec0cf765"],
}

# Claims that WERE published and are now withdrawn. Each carries the reason, and
# the reason is re-checked on every run rather than trusted: a withdrawal that
# rests on "this id is outside the base set" stops being valid the moment the
# base set changes. This is the entry that made writing the producer worthwhile.
WITHDRAWN = [
    {
        "finding": "101",
        "id": "652f31e6bde6",
        "claim": "101 said both of its in-scope corpus cases 'were on 074's "
                 "unattributed residual', taking it 4 -> 2.",
        "reason": "652f31e6bde6 matches its own reading_alternatives.dtstart_fill "
                  "entry exactly, so the scorer buckets it fail_other_reading, "
                  "not fail. 074 drew its residual from the fail bucket only, so "
                  "this case was never in it. 101's predictor does reproduce the "
                  "case and that evidence stands; what does not stand is the "
                  "subtraction. The residual went 4 -> 3.",
        "check": "not_in_base",
    },
]


def finding_text(n):
    hits = glob.glob(os.path.join(REPO, "findings/%s-*.md" % n))
    assert len(hits) == 1, (n, hits)
    return open(hits[0]).read(), os.path.basename(hits[0])


def recover_096():
    """096 published counts (J=1, K=2, K+074-F=4) and not ids. Its committed
    classifier computes the per-id buckets; import it and read them, so the
    seven are derived from the same code that produced the published counts
    rather than transcribed by hand."""
    path = os.path.join(REPO, "findings/repro/096-icaljs-bymonth-cursor.py")
    spec = importlib.util.spec_from_file_location("r096", path)
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        spec.loader.exec_module(mod)
        with contextlib.redirect_stdout(io.StringIO()):
            hit = mod.main()
    finally:
        os.chdir(cwd)
    out = {}
    for bucket in ("J", "K", "K+074-F"):
        for i in hit[bucket]:
            out[i] = bucket
    assert len(out) == 7, out
    return out, sorted(hit["still unexplained"])


def main():
    base = json.load(open(BASE))
    unex = base["ids"]["unexplained"]
    assert len(set(unex)) == len(unex) == 23, len(unex)
    baseset = set(unex)
    print("074 base set: %d ids, from the `fail` bucket only, cases %s"
          % (len(baseset), base["cases_id"][:12]))

    problems = []
    attributed = {}

    d096, still16 = recover_096()
    print("\n096 -- recovered from its own classifier (it published counts, not ids):")
    for i, b in sorted(d096.items()):
        print("  %s  %s" % (i, b))
    assert len(still16) == 16, len(still16)
    for i, b in d096.items():
        if i not in baseset:
            problems.append("096 attributes %s, which is NOT in 074's base set" % i)
        attributed[i] = ("096", b)

    print("\nFindings that name their ids:")
    for n in sorted(NAMED):
        txt, fname = finding_text(n)
        for i in NAMED[n]:
            inprose = i in txt
            inbase = i in baseset
            flag = "" if (inprose and inbase) else "   <-- PROBLEM"
            print("  %s  %s   in %s: %-5s  in 074 base: %-5s%s"
                  % (n, i, fname[:3], inprose, inbase, flag))
            if not inprose:
                problems.append("%s: ledger lists %s but the finding's own text "
                                "does not name it" % (n, i))
            if not inbase:
                problems.append("%s: %s is NOT in 074's base set, so attributing "
                                "it cannot reduce the residual" % (n, i))
            if i in attributed and inbase:
                problems.append("%s: %s already attributed by %s"
                                % (n, i, attributed[i][0]))
            if inbase:
                attributed[i] = (n, "named in prose")

    print("\nWithdrawn claims, with their reasons re-checked:")
    for w in WITHDRAWN:
        assert w["check"] == "not_in_base", w
        still = w["id"] not in baseset
        txt, _ = finding_text(w["finding"])
        print("  %s  %s   still outside 074's base set: %s" % (w["finding"], w["id"], still))
        if not still:
            problems.append("%s: the withdrawal of %s rested on it being outside "
                            "074's base set, and it is now INSIDE. Re-read the "
                            "claim." % (w["finding"], w["id"]))
        if w["id"] in attributed:
            problems.append("%s: %s is both withdrawn and attributed"
                            % (w["finding"], w["id"]))

    residual = sorted(baseset - set(attributed))
    print("\nATTRIBUTED: %d of %d" % (len(attributed), len(baseset)))
    print("RESIDUAL:   %d" % len(residual))

    cases = {}
    for line in open(os.path.join(REPO, "conformance/cases.ndjson")):
        c = json.loads(line)
        if c["id"] in baseset:
            cases[c["id"]] = c
    print("\nThe current unattributed set, in full:")
    for i in residual:
        print("  %s  %s  %s" % (i, cases[i]["dtstart"], cases[i]["rrule"]))

    bysetpos = [i for i in residual if "BYSETPOS" in cases[i]["rrule"]]
    byday = [i for i in residual if "BYDAY" in cases[i]["rrule"]]
    print("\nOf the %d: %d carry BYSETPOS, %d carry BYDAY."
          % (len(residual), len(bysetpos), len(byday)))
    if len(bysetpos) == len(byday) == len(residual) and residual:
        print("074's defect E is `BYSETPOS silently dropped UNLESS the day set came")
        print("from BYDAY`. Every residual case has both, so E's own exclusion clause")
        print("is exactly what is left. The residual is not miscellaneous.")
        print("Finding 104 took the FREQ=YEARLY half of that population. What is")
        print("left is not automatically the same shape -- 104 declined to claim")
        print("d27c58ae379a on exactly those grounds. Check before assuming.")

    if problems:
        print("\n*** %d PROBLEM(S) ***" % len(problems))
        for p in problems:
            print("  - %s" % p)
    else:
        print("\nNo problems: every claimed id is in 074's base set, named in its")
        print("own finding, and claimed exactly once.")

    ledger = {
        "cases_id": base["cases_id"],
        "base_finding": "074",
        "base_key": "ids.unexplained",
        "base_bucket": "fail",
        "base_n": len(baseset),
        "attributed": {i: {"finding": f, "how": h}
                       for i, (f, h) in sorted(attributed.items())},
        "residual": residual,
        "residual_n": len(residual),
        "withdrawn": WITHDRAWN,
        "problems": problems,
    }
    if "--write" in sys.argv:
        json.dump(ledger, open(LEDGER, "w"), indent=1, sort_keys=True)
        print("\n-> %s" % LEDGER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
