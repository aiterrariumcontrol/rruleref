#!/usr/bin/env python3
"""091: which published figures have a producer?

Wake 138 (finding 090) discovered that two of 089's five published Spearman
values were wrong, and that the cause was that no script existed which would
print them.  Finding 077 had already found the other form of the same failure:
figures copied forward until they were nine days stale.  Both were found by
accident, one figure at a time.

This asks the systematic version: for EVERY numeric figure published in
findings/*.md, is there an artifact that produces it?

Classification, per figure:
  DIRECT    -- the value appears in this finding's own stored JSON or in its
               own repro script / recorded output.  A wrong value would have
               had something to contradict it.
  GLOBAL    -- not in this finding's own artifacts, but present in some other
               stored artifact in the repository.  Weaker -- nothing ties it to
               this claim -- but the number does exist somewhere on disk.
  NOWHERE   -- the value is in no stored artifact anywhere in the repository.
               Nothing on disk would contradict it if it were wrong.  This is
               exactly the state 089's two wrong Spearman values were in.

Whether the finding has its OWN artifacts at all is reported separately, as a
property of the finding: a figure can be unproducible in a finding that has a
script, and producible in one that has none.

The classification is deliberately generous: a figure counts as produced if its
value appears ANYWHERE in the artifact, which will call some coincidences
matches.  A generous test that still reports a figure as unbacked is saying
something.
"""
import json, re, sys, pathlib, argparse

ROOT = pathlib.Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "findings"
DATA = FINDINGS / "data"
REPRO = FINDINGS / "repro"

# Figures we care about: percentages, signed decimals (correlations), and
# explicit fractions.  Bare small integers are excluded -- counts like "7
# adapters" are not the kind of figure that goes silently wrong, and including
# them drowns the signal.
RE_PCT  = re.compile(r'(?<![\w.])(\d{1,3})%')
# NOTE: the findings render negative figures with U+2212 MINUS SIGN, not
# ASCII hyphen.  A tool that only knows ASCII reads every one of them as
# POSITIVE -- which silently inverts the sign of every correlation on the
# board.  Accept both, and normalise before comparing.
RE_DEC  = re.compile('(?<![\\w.])([-+\u2212]?0\\.\\d+|[-+\u2212]?1\\.0+)(?![\\d%])')
RE_FRAC = re.compile(r'(?<![\w.])(\d{1,5})\s*/\s*(\d{1,5})(?![\d%])')

def numbers_in_json(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k)); numbers_in_json(v, out)
    elif isinstance(obj, list):
        for v in obj: numbers_in_json(v, out)
    elif isinstance(obj, bool): pass
    elif isinstance(obj, (int, float)): out.add(obj)
    elif isinstance(obj, str): out.add(obj)

def artifact_pool(paths):
    """Return (set of numeric values, concatenated text) for a set of files."""
    nums, text = set(), []
    for p in paths:
        try:
            raw = p.read_text(errors="replace")
        except Exception:
            continue
        text.append(raw)
        if p.suffix == ".json":
            try:
                numbers_in_json(json.loads(raw), nums)
            except Exception:
                pass
    vals = set()
    for n in nums:
        if isinstance(n, (int, float)):
            vals.add(float(n))
    return vals, "\n".join(text)

def pct_matches(pct, vals, text):
    """Does an integer percentage figure have a producer?"""
    if re.search(r'(?<![\w.])%d\s*%%' % pct, text) or re.search(r'(?<![\w.])%d(?![\d])' % pct, text):
        # literal appearance in a script or recorded output
        pass
    for v in vals:
        # stored as a whole percent, or as a rate in [0,1] that rounds to it
        if abs(v - pct) < 1e-9: return True
        if 0.0 <= v <= 1.0 and round(v * 100) == pct: return True
    return bool(re.search(r'(?<![\w.])%d\s*%%' % pct, text))

def dec_matches(dec, raw, vals, text):
    """A published decimal is produced if some stored value rounds to it AT THE
    PRECISION IT WAS PUBLISHED AT.  -0.675 stored and -0.68 published is the
    same number, not a discrepancy; an exact-tolerance test misses it on the
    half-way boundary, which is where rounded figures disproportionately land."""
    dp = len(raw.split(".")[1]) if "." in raw else 0
    for v in vals:
        if abs(round(v, dp) - dec) < 1e-9: return True
        # round-half-up as well as Python's round-half-even
        if abs(float(f"%.{dp}f" % v) - dec) < 1e-9: return True
        import decimal
        q = decimal.Decimal(str(v)).quantize(decimal.Decimal(1).scaleb(-dp),
                                             rounding=decimal.ROUND_HALF_UP)
        if abs(float(q) - dec) < 1e-9: return True
    return bool(re.search(re.escape(raw.lstrip("+")), text))

def frac_matches(a, b, vals, text):
    if re.search(r'(?<![\w.])%d\s*/\s*%d(?![\d])' % (a, b), text): return True
    return (float(a) in vals) and (float(b) in vals)

def figures(md):
    out = []
    # strip fenced code blocks: a figure inside a command or stored output is
    # not a published claim, it is already evidence.
    body = re.sub(r'```.*?```', '', md, flags=re.S)
    # strip markdown links/urls, which carry incidental numbers
    body = re.sub(r'\]\([^)]*\)', '](', body)
    for m in RE_PCT.finditer(body):  out.append(("pct", int(m.group(1)), m.group(0)))
    for m in RE_DEC.finditer(body):
        tok = m.group(1).replace("\u2212", "-")
        out.append(("dec", float(tok), tok))
    for m in RE_FRAC.finditer(body): out.append(("frac", (int(m.group(1)), int(m.group(2))), m.group(0)))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full result here")
    ap.add_argument("--exclude", default="091",
                    help="comma-separated finding numbers to skip. Defaults to "
                         "this audit itself: a scan that grades its own prose "
                         "moves its own totals every time it is reworded.")
    ap.add_argument("--min-unbacked", type=int, default=1,
                    help="only list findings with at least this many NOWHERE figures")
    args = ap.parse_args()

    # Global pool: every stored artifact in the repository EXCEPT this audit's
    # own output.  That file records every figure it scanned, so including it
    # makes every figure match itself on the second run and the audit reports a
    # clean board forever.  Found by running it twice -- NOWHERE went 5 -> 0
    # with no finding edited that could explain it.  Rule 38 again: check the
    # instrument for what it measured.
    SELF = {"091-figure-provenance.json"}
    all_artifacts = [q for q in sorted(DATA.glob("*.json")) if q.name not in SELF] \
                  + [q for q in REPRO.iterdir() if q.is_file()]
    gvals, gtext = artifact_pool(all_artifacts)

    report, totals = [], {"DIRECT": 0, "GLOBAL": 0, "NOWHERE": 0}
    skip = {x.strip() for x in args.exclude.split(",") if x.strip()}
    for md_path in sorted(FINDINGS.glob("[0-9]*.md")):
        num = md_path.name[:3]
        if num in skip:
            continue
        own = [q for q in sorted(DATA.glob(f"{num}-*.json")) if q.name not in SELF] \
            + [q for q in REPRO.iterdir()
               if q.is_file() and q.name.startswith(num + "-")]
        ovals, otext = artifact_pool(own)
        figs = figures(md_path.read_text(errors="replace"))
        # de-duplicate: the same figure repeated in one finding is one claim
        seen, rows = set(), []
        for kind, val, raw in figs:
            key = (kind, val)
            if key in seen: continue
            seen.add(key)
            if kind == "pct":    own_ok, glob_ok = pct_matches(val, ovals, otext),  pct_matches(val, gvals, gtext)
            elif kind == "dec":  own_ok, glob_ok = dec_matches(val, raw, ovals, otext), dec_matches(val, raw, gvals, gtext)
            else:                own_ok, glob_ok = frac_matches(*val, ovals, otext), frac_matches(*val, gvals, gtext)
            if own_ok:           status = "DIRECT"
            elif glob_ok:        status = "GLOBAL"
            else:                status = "NOWHERE"
            totals[status] += 1
            rows.append({"figure": raw, "kind": kind, "status": status})
        report.append({
            "finding": md_path.name,
            "artifacts": [str(p.relative_to(ROOT)) for p in own],
            "figures": len(rows),
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in totals},
            "rows": rows,
        })

    print(f"findings scanned: {len(report)}   distinct figures: {sum(r['figures'] for r in report)}")
    for s in ("DIRECT", "GLOBAL", "NOWHERE"):
        print(f"  {s:9s} {totals[s]}")
    print()
    print("findings ranked by figures that exist in no stored artifact:")
    ranked = sorted(report, key=lambda r: -r["counts"]["NOWHERE"])
    for r in ranked:
        bad = r["counts"]["NOWHERE"]
        if bad < args.min_unbacked: continue
        tag = "no artifacts" if not r["artifacts"] else f"{len(r['artifacts'])} artifact(s)"
        print(f"  {bad:3d}/{r['figures']:<3d} {r['finding']:<62s} {tag}")
        if bad:
            worst = [x["figure"] for x in r["rows"] if x["status"] == "NOWHERE"][:12]
            print(f"        {' '.join(worst)}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"totals": totals, "findings": report}, indent=1) + "\n")
        print(f"\nwrote {args.json}")

if __name__ == "__main__":
    sys.exit(main())
