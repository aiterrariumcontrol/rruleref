"""Predict sabre/vobject's answer on the DATE-value-type cases from two
already-published mechanisms, and replay the prediction over every case.

Neither mechanism is fitted here. Both are quoted:

  * finding 076, table "method / reads" -- each `next*()` method reads a fixed
    subset of the parsed BY parts and never reads the rest, so sabre's answer
    is the rule with its unread parts DELETED.
  * finding 082 -- on a rule whose DTSTART is not in the recurrence set, sabre
    alone among the thirteen builds PREPENDS DTSTART.

The predictor is their composition, in that order. A two-sided replay runs it
over all 20 cases, including the ones sabre gets right: if it claims a
different answer anywhere sabre agreed with the board, the model is too wide.
"""
import datetime, json, os, sys
REPO = "/home/agent/terrarium/projects/rruleref"
sys.path.insert(0, os.path.join(REPO, "src"))
import naive
FMT = "%Y%m%dT%H%M%S"

# finding 076, verbatim from its table.
READS = {
    "HOURLY":  set(),
    "DAILY":   {"BYHOUR", "BYDAY", "BYMONTH"},
    "WEEKLY":  {"BYHOUR", "BYDAY", "WKST"},
    "MONTHLY": {"BYMONTHDAY", "BYDAY", "BYSETPOS"},
    "YEARLY":  {"BYMONTH", "BYMONTHDAY", "BYDAY", "BYSETPOS",
                "BYWEEKNO", "BYYEARDAY"},
}
KEEP_ALWAYS = {"FREQ", "INTERVAL", "COUNT", "UNTIL"}


def delete_unread(rrule):
    parts = [p for p in rrule.split(";") if p]
    freq = next(p.split("=", 1)[1].upper() for p in parts
                if p.split("=", 1)[0].upper() == "FREQ")
    reads = READS[freq]
    out = [p for p in parts
           if p.split("=", 1)[0].upper() in KEEP_ALWAYS
           or p.split("=", 1)[0].upper() in reads]
    return ";".join(out)


def predict(rrule, dtstart, limit):
    reduced = delete_unread(rrule)
    ds = datetime.datetime.strptime(dtstart, FMT)
    occ = [x.strftime(FMT) for x in naive.expand(reduced, ds, limit=limit)]
    if not occ or occ[0] != dtstart:
        occ = [dtstart] + occ
    return reduced, occ[:limit]


def main():
    t = json.load(open("/home/agent/terrarium/scratch/dvt-audit/table.json"))
    det = t["detail"]
    sab = {}
    for line in open("/home/agent/terrarium/scratch/dvt-audit/out.sabre.ndjson"):
        o = json.loads(line)
        sab[o["id"]] = o.get("occurrences") if not o.get("error") else None

    agree = dis = 0
    bad = []
    print("%-12s %-46s %-6s %s" % ("id", "rrule", "board", "predicted?"))
    for cid, d in sorted(det.items(), key=lambda kv: kv[1]["rrule"]):
        red, pred = predict(d["rrule"], d["dtstart"], d["limit"])
        got = sab[cid]
        ok = (got == pred)
        verdict = t["grid"][cid]["sabre"]
        print("%-12s %-46s %-6s %-5s%s" % (
            cid, d["rrule"][:46], verdict, ok,
            "" if red == d["rrule"] else "   deleted -> " + red))
        if verdict == "X":
            dis += 1
        else:
            agree += 1
        if not ok:
            bad.append((cid, d["rrule"], pred, got))

    print()
    print("REPLAY over all %d cases -- %d sabre disagrees with the board, "
          "%d it agrees with." % (len(det), dis, agree))
    if bad:
        print("UNEXPLAINED %d:" % len(bad))
        for cid, r, p, g in bad:
            print("  %s %s\n    predicted %s\n    sabre     %s" % (cid, r, p, g))
        return 1
    print("The two published mechanisms, composed and fitted to nothing, "
          "predict sabre's exact output list on all %d." % len(det))
    return 0


if __name__ == "__main__":
    sys.exit(main())
