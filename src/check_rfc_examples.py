"""Run implementations against the RFC's own worked examples and report.

The corpus in `corpus/corroborated.json` records what two implementations
agree on. This file is the other kind of evidence: what the specification
itself prints. Disagreement here is a much stronger signal, because the
expected values are normative text rather than a second opinion.

Implementations checked:
  naive+tzexpand -- this repository's spec-derived expander plus the
                    section 3.3.5 localization rule
  python-dateutil -- driven exactly as an application would, with a
                    `zoneinfo` DTSTART and UNTIL parsed as a UTC instant
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import dateutil.rrule as du

import tzexpand
from rfc_worked_examples import build


def as_tuples(dts):
    return [[d.strftime("%Y%m%dT%H%M%S"), int(d.utcoffset().total_seconds() // 60)]
            for d in dts]


def dateutil_expand(rule, dtstart_naive, tzid, want):
    """Expand with python-dateutil, the way an application actually would."""
    dtstart = dtstart_naive.replace(tzinfo=ZoneInfo(tzid))
    r = du.rrulestr("RRULE:" + rule, dtstart=dtstart)
    return list(itertools.islice(iter(r), want))


def main():
    data = build()
    rows, mismatches = [], 0
    for ex in data["examples"]:
        dtstart = datetime.strptime(ex["dtstart"], "%Y%m%dT%H%M%S")
        want = [[e["local"], e["utc_offset_minutes"]] for e in ex["expected"]]
        n = len(want)
        for rule in ex["rrules"]:
            row = {"desc": ex["desc"], "tzid": ex["tzid"], "dtstart": ex["dtstart"],
                   "rrule": rule, "errata_applied": ex["errata_applied"],
                   "prefix_only": ex["expected_is_prefix_only"], "rfc": want}
            for name, fn in (("rruleref", lambda: tzexpand.expand(rule, dtstart, ex["tzid"],
                                                                  limit=max(n + 2, 16))),
                             # Ask for one more than the RFC prints, so an
                             # implementation that stops early or runs on is
                             # visible rather than being truncated into
                             # agreement -- the defect tests/test_differ.py
                             # exists for.
                             ("dateutil", lambda: dateutil_expand(rule, dtstart, ex["tzid"],
                                                                  n + 1))):
                try:
                    got = as_tuples(fn())
                    row[name] = got
                    row[name + "_matches_rfc"] = (got[:n] == want if ex["expected_is_prefix_only"]
                                                  else got == want)
                except Exception as e:
                    row[name] = "ERROR:%s: %s" % (type(e).__name__, e)
                    row[name + "_matches_rfc"] = False
            if not (row["rruleref_matches_rfc"] and row["dateutil_matches_rfc"]):
                mismatches += 1
            rows.append(row)

    meta = {
        "about": "RFC 5545 section 3.8.5.3 worked examples as known answers.",
        "source": data["source"],
        "errata_applied": data["errata_applied"],
        "expansions": len(rows),
        "crossing_dst": sum(1 for r in rows if len({e[1] for e in r["rfc"]}) > 1),
        "rruleref_matches_rfc": sum(1 for r in rows if r["rruleref_matches_rfc"]),
        "dateutil_matches_rfc": sum(1 for r in rows if r["dateutil_matches_rfc"]),
        "expansions_with_any_mismatch": mismatches,
        "implementations": {
            "rruleref": "src/naive.py + src/tzexpand.py",
            "dateutil": "python-dateutil " + __import__("dateutil").__version__,
        },
    }
    out = os.path.join(os.path.dirname(__file__), "..", "findings", "data",
                       "005-rfc-examples.json")
    with open(out, "w") as f:
        json.dump({"meta": meta, "cases": rows}, f, indent=1)
    print(json.dumps(meta, indent=1))
    for r in rows:
        if not (r["rruleref_matches_rfc"] and r["dateutil_matches_rfc"]):
            print("\nMISMATCH %s\n  %s  DTSTART;TZID=%s:%s"
                  % (r["desc"], r["rrule"], r["tzid"], r["dtstart"]))
            print("  rfc      ", r["rfc"][:6])
            for k in ("rruleref", "dateutil"):
                v = r[k]
                print("  %-9s" % k, v[:6] if isinstance(v, list) else v,
                      "MATCH" if r[k + "_matches_rfc"] else "")


if __name__ == "__main__":
    main()
