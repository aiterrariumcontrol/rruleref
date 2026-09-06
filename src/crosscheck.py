"""Cross-implementation check of the disputed cases, under matching bounds.

Two defects in the earlier comparison are addressed here.

1. **Bounds mismatch.** `differ.compare` clips both expanders at a 30-year
   horizon, which is correct for deciding *agreement*, but the clipped lists
   were then saved and compared against rrule.js output that had been asked
   for eight occurrences with no horizon. Two cases whose dateutil list was
   six entries long were recorded as "agreeing with neither implementation".
   Here every implementation is asked for exactly N occurrences, so the three
   lists are comparable elementwise.

   *Correction, 2026-09-06.* An earlier version of this docstring said "with no
   horizon clip". That was still false for the naive expander: `expand`
   substitutes a default horizon of DTSTART + ~30 years whenever none is
   passed, so it was bounded while the other two were not — the same class of
   bounds mismatch as defect 1, one level down. `naive_n` now *extends* the
   horizon (doubling, up to ~480 years) until it has N occurrences or the
   extension stops producing any, and each row records the horizon actually
   used and whether extension was needed.

   Two rows needed it, and the effect was real but not the whole story:
   `FREQ=YEARLY;BYWEEKNO=53;BYYEARDAY=1,200` from 20270101 returned 6 dates at
   30 years and 8 at 120. The disagreement with dateutil survives the fix
   (dateutil emits 2039 and 2050, naive at any horizon does not), but before
   the fix the comparison past index 3 was between a truncated list and a full
   one and could not have shown that.

2. **One mechanism was asserted for every case.** `explains_truncation`
   tests, per case, the specific claim that dateutil truncates the first
   period at DTSTART before applying BYSETPOS: re-run dateutil with DTSTART
   moved back to the start of its own period (so no truncation can occur),
   drop occurrences before the original DTSTART, and see whether the result
   then matches the naive full-period expansion. A case is "explained" only
   if that substitution actually removes the divergence.
"""
import sys, json, subprocess, os
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from datetime import datetime, timedelta
import dateutil.rrule as du
import itertools
from naive import expand, parse, _period_start

N = 8
NODE_DIR = "/home/agent/terrarium/scratch/rrulejs"


def fmt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def parse_dt(s):
    return datetime.strptime(s, "%Y%m%dT%H%M%S")


def du_expand(rule, dtstart, n=N):
    try:
        it = du.rrulestr("RRULE:" + rule, dtstart=dtstart)
        return list(itertools.islice(iter(it), n))
    except Exception as e:
        return "ERROR:" + type(e).__name__


def naive_n(rule, dtstart, n=N, start_years=30, max_years=480):
    """Naive expansion of exactly n occurrences, with the horizon made non-binding.

    `naive.expand` needs *some* horizon — it is a brute-force enumerator — and
    it silently substitutes dtstart + ~30 years. That default is a real bound
    the other two implementations do not have, so comparing elementwise against
    them is only valid once the bound has been shown not to bind. Double the
    horizon until either n occurrences are found or an extension yields nothing
    new. Returns (occurrences, horizon_years_used, extended?).
    """
    years = start_years
    prev = None
    while True:
        got = expand(rule, dtstart, horizon=dtstart + timedelta(days=365 * years + years // 4),
                     limit=n)[:n]
        if len(got) >= n or years >= max_years or (prev is not None and len(got) == prev):
            return got, years, years != start_years
        prev = len(got)
        years *= 2


def explains_truncation(rule, dtstart, n=N):
    """Does 'dateutil truncates the first period at DTSTART' explain this case?

    Returns (verdict, evidence). verdict is True only when re-running dateutil
    from the start of DTSTART's own period reproduces the naive expansion.
    """
    r = parse(rule)
    ps = _period_start(dtstart, r["FREQ"], r["WKST"])
    if ps == dtstart:
        return False, "DTSTART is already the period start; nothing to truncate"
    # Ask for extra occurrences: the shifted run may emit some before dtstart.
    shifted = du_expand(rule, ps, n * 3)
    if isinstance(shifted, str):
        return False, shifted
    shifted = [x for x in shifted if x >= dtstart][:n]
    mine = naive_n(rule, dtstart, n)[0]
    if shifted == mine:
        return True, "dateutil from period start %s reproduces the naive expansion" % fmt(ps)
    i = next((k for k in range(min(len(shifted), len(mine)))
              if shifted[k] != mine[k]), min(len(shifted), len(mine)))
    return False, ("dateutil from period start %s still differs from naive at "
                   "index %d (%s vs %s)"
                   % (fmt(ps), i,
                      fmt(shifted[i]) if i < len(shifted) else "-",
                      fmt(mine[i]) if i < len(mine) else "-"))


def rrulejs(cases):
    """Run rrule.js on the same cases, asking for the same N occurrences."""
    payload = [{"rrule": c["rrule"], "dtstart": c["dtstart"]} for c in cases]
    with open(os.path.join(NODE_DIR, "cases.json"), "w") as f:
        json.dump(payload, f)
    script = """
const {rrulestr} = require('rrule');
const cases = require('./cases.json');
const N = %d;
const fmt = d => d.toISOString().replace(/[-:]/g,'').replace(/\\.\\d+Z$/,'');
console.log(JSON.stringify(cases.map(c => {
  try {
    const r = rrulestr(`DTSTART:${c.dtstart}Z\\nRRULE:${c.rrule}`, {forceset:false});
    return r.all((d,i)=>i<N).map(fmt);
  } catch(e) { return ['ERROR:'+e.message]; }
})));
""" % N
    path = os.path.join(NODE_DIR, "crosscheck.js")
    with open(path, "w") as f:
        f.write(script)
    out = subprocess.run(["node", path], cwd=NODE_DIR, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


def main():
    disputed = json.load(open("corpus/disputed.json"))["cases"]
    cases = [c for c in disputed if c["dtstart_synchronized"]]
    js = rrulejs(cases)
    rows = []
    for c, jsout in zip(cases, js):
        ds = parse_dt(c["dtstart"])
        mine_dts, years, extended = naive_n(c["rrule"], ds)
        mine = [fmt(x) for x in mine_dts]
        theirs = du_expand(c["rrule"], ds)
        theirs = theirs if isinstance(theirs, str) else [fmt(x) for x in theirs]
        ok, why = explains_truncation(c["rrule"], ds)

        first = next((i for i in range(min(len(mine), len(theirs)))
                      if mine[i] != theirs[i]), None)
        rows.append({
            "rrule": c["rrule"], "dtstart": c["dtstart"],
            "naive": mine, "dateutil": theirs, "rrulejs": jsout,
            "first_divergence_index": first,
            "dateutil_matches_rrulejs": theirs == jsout,
            "explained_by_first_period_truncation": ok,
            "explanation_evidence": why,
            "naive_horizon_years": years,
            "naive_horizon_extended": extended,
        })
    meta = {
        "about": "Disputed synchronized cases under matching bounds: every "
                 "implementation asked for %d occurrences. The naive expander "
                 "needs a horizon; it is extended per case until it no longer "
                 "binds, so the three lists are comparable elementwise." % N,
        "occurrences_requested": N,
        "naive_horizon": "extended per case until N occurrences are found or "
                         "extension stops helping; see naive_horizon_years",
        "cases_needing_horizon_extension": None,  # filled below
        "implementations": {
            "naive": "rruleref src/naive.py (spec-derived brute force)",
            "dateutil": "python-dateutil " + __import__("dateutil").__version__,
            "rrulejs": "rrule.js 2.8.1 via node",
        },
        "cases": len(rows),
        "dateutil_matches_rrulejs": sum(r["dateutil_matches_rrulejs"] for r in rows),
        "explained_by_first_period_truncation":
            sum(r["explained_by_first_period_truncation"] for r in rows),
    }
    meta["cases_needing_horizon_extension"] = sum(r["naive_horizon_extended"] for r in rows)
    meta["cases_still_short_of_n"] = sum(len(r["naive"]) < N for r in rows)
    json.dump({"meta": meta, "cases": rows},
              open("findings/data/004-crosscheck.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))
    for r in rows:
        print("%-58s %s  du==js:%-5s explained:%-5s idx=%s"
              % (r["rrule"][:58], r["dtstart"], r["dateutil_matches_rrulejs"],
                 r["explained_by_first_period_truncation"],
                 r["first_divergence_index"]))


if __name__ == "__main__":
    main()
