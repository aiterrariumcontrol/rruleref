"""073 — split a score.py `error` bucket into deadline and non-deadline parts.

  python3 073-split-error-column.py SCORE.json [SCORE.json ...]

score.py has no per-case deadline of its own: its --timeout is one deadline for
the whole adapter run, and a case that outlives it produces no scored row at
all. Every per-case deadline in this repository lives inside an adapter, and
only three adapters have one -- the Perl, PHP and JavaScript ones. Each reports
the expiry in the same channel a library's own refusal uses, the `error` key,
so a published `error` column can mix two different kinds of fact:

  * the subject refused, declared a limitation, or threw -- a property of the
    subject, reproducible anywhere;
  * the subject had not answered yet -- a property of this box's load at that
    moment (standing rule 80).

This prints the split and the per-case membership of each part, so that a
published error count can be re-derived rather than remembered (rule 79).
The patterns below are the exact strings those three adapters emit.
"""
import json
import re
import sys

DEADLINE = re.compile(
    r"no answer within \d+s"          # php/vobject_adapter.php, SIGALRM
    r"|timeout: no answer in \d+ms"   # icaljs_adapter.js, supervisor
    r"|RRULE_CASE_TIMEOUT"            # perl/dtical_adapter.pl
    r"|\btimed? ?out\b",
    re.I)


def split(path):
    doc = json.load(open(path))
    deadline, refusal = [], []
    for f in doc.get("failures", []):
        if f.get("bucket") != "error":
            continue
        msg = str((f.get("reply") or {}).get("error", ""))
        (deadline if DEADLINE.search(msg) else refusal).append(
            {"id": f["case"]["id"], "rrule": f["case"]["rrule"],
             "dtstart": f["case"]["dtstart"], "limit": f["case"].get("limit"),
             "error": msg[:200]})
    return doc, deadline, refusal


def main(argv):
    out = {}
    for path in argv:
        doc, deadline, refusal = split(path)
        cv = doc.get("corpus_version", {})
        print("%s\n  adapter      %s\n  cases_id     %s\n  counts       %s"
              % (path, " ".join(doc.get("adapter", [])) or "?",
                 str(cv.get("cases_id"))[:12], json.dumps(doc.get("counts", {}), sort_keys=True)))
        print("  error        %d = %d deadline + %d refusal"
              % (len(deadline) + len(refusal), len(deadline), len(refusal)))
        for r in refusal:
            print("    refusal  %s  %s" % (r["id"], r["error"][:80]))
        for r in deadline:
            print("    deadline %s  %s" % (r["id"], r["rrule"][:60]))
        out[path] = {"cases_id": cv.get("cases_id"), "counts": doc.get("counts"),
                     "deadline": deadline, "refusal": refusal}
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
