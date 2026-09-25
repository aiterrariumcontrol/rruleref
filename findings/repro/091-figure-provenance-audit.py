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

NOWHERE is then PARTITIONED, because counting it was a dead end.  It sat at 31
for three wakes while the underlying situation changed, because "31 figures have
no stored producer" mixes six different situations and only one of them is an
error I can fix by measuring something.  A finding declares the situation for a
figure, IN ITS OWN MARKDOWN, next to the claim:

  <!-- provenance: TIMING 0.022 0.149 -- wall-clock; no stored producer exists -->

Recognised categories, and what each one costs to clear:

  TIMING              a wall-clock measurement.  Cannot have a stored producer;
                      re-running it produces a different number.  Never clears.
  RETRACTED-QUOTE     a superseded value quoted inside its own correction note.
                      It is SUPPOSED to be unbacked -- the artifact that used to
                      produce it is gone, which is the point.  Never clears.
  EXTRACTION-ARTIFACT not a published figure at all.  The extractor sliced "a / b"
                      out of a longer tuple like "1637 / 13 / 63".  Clears only by
                      making the extractor smarter, and is not a claim about the
                      world either way.
  HISTORICAL-CORPUS   a score against an earlier, smaller corpus, recorded as
                      history.  Today's corpus cannot reproduce it and should not.
  DERIVED             the finding states its own numerator and denominator inline.
                      CHECKED, NOT TAKEN ON TRUST: the audit finds "(a of b)" on
                      the same line and confirms the percentage.  A DERIVED
                      declaration the audit cannot confirm is a FAILURE.
  UNCHECKED           genuinely unverified.  THIS IS THE ONLY CATEGORY THAT IS A
                      DEBT.  Clearing it requires measuring something.

  UNCLASSIFIED        NOWHERE, and nobody has said why.  Clears by looking at it.

So the two numbers that should be driven to zero are UNCLASSIFIED (by reading)
and UNCHECKED (by measuring).  The other four are answers, not work.

THE DECLARATIONS ARE CHECKED AGAINST THE PRESENT, which is the whole lesson of
rule 102 and finding 092: an annotation that silences an audit is a way to make
the audit lie, unless something notices when it stops applying.  A declaration
naming a figure that is no longer NOWHERE in that finding -- because the figure
was corrected, deleted, or has since acquired an artifact -- is STALE, is
reported, and makes this script exit non-zero.  A declaration can only move a
figure OUT of NOWHERE; it can never affect a DIRECT or GLOBAL one.

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

CATEGORIES = ("TIMING", "RETRACTED-QUOTE", "EXTRACTION-ARTIFACT",
              "HISTORICAL-CORPUS", "DERIVED", "QUOTED", "UNCHECKED")

RE_DECL = re.compile(r'<!--\s*provenance:(.*?)-->', re.S)

def norm_fig(tok):
    """Compare figures the way a reader means them, not the way they are typed.
    U+2212 MINUS SIGN and ASCII hyphen are the same number; '237 / 244' and
    '237/244' are the same fraction."""
    return re.sub(r'\s+', '', tok.replace("\u2212", "-").lstrip("+"))

def declarations(md):
    """Parse <!-- provenance: CATEGORY fig fig -- reason --> blocks.
    Returns (map normalised-figure -> (category, reason), list of complaints)."""
    out, bad = {}, []
    # A declaration shown as an EXAMPLE inside a fenced code block is
    # documentation, not a declaration.  Finding 093 documents the syntax with a
    # worked example, and that example silently classified two of 093's own
    # figures before this line existed -- the audit's own manual acting on the
    # audit.  Same shape as the SELF exclusion: strip the fences first.
    md = re.sub(r'```.*?```', '', md, flags=re.S)
    for m in RE_DECL.finditer(md):
        head, sep, reason = m.group(1).partition("--")
        reason = reason.strip()
        parts = head.split()
        if not parts:
            bad.append("empty provenance declaration")
            continue
        cat, figs = parts[0], " ".join(parts[1:])
        if cat not in CATEGORIES:
            bad.append(f"unknown category {cat!r}")
            continue
        if not reason:
            bad.append(f"{cat} declaration with no reason after '--'")
        toks = [t for t in figs.split() if t]
        if not toks:
            bad.append(f"{cat} declaration names no figure")
        for t in toks:
            src = None
            if "@" in t:
                t, _, src = t.partition("@")
            if cat == "QUOTED" and not src:
                bad.append(f"QUOTED {t} must name its source as {t}@NNN")
                continue
            out[norm_fig(t)] = (cat, reason, src)
    return out, bad

def strip_provenance(md):
    """Remove the declarations before scanning for figures.  A declaration names
    figures and gives a reason in prose; if it stayed in the body the audit would
    read its own annotations as published claims, and a reason mentioning a
    number would certify that number.  Same shape as the SELF exclusion above."""
    return RE_DECL.sub("", md)

RE_OF = re.compile(r'(\d{1,6})\s+of\s+(\d{1,6})')

def derived_ok(raw, md):
    """A DERIVED percentage must be recomputable from an '(a of b)' stated on the
    same line as the figure.  This is the difference between a category and an
    excuse: the audit confirms the arithmetic or the declaration fails."""
    try:
        pct = int(raw.rstrip("%"))
    except ValueError:
        return False
    for line in strip_provenance(md).splitlines():
        if raw not in line:
            continue
        for a, b in RE_OF.findall(line):
            b = int(b)
            if b and round(int(a) * 100 / b) == pct:
                return True
    return False


def figures(md):
    out = []
    # strip fenced code blocks: a figure inside a command or stored output is
    # not a published claim, it is already evidence.
    body = re.sub(r'```.*?```', '', strip_provenance(md), flags=re.S)
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
    #
    # THIS SCRIPT ITSELF belongs in SELF too, and did not at first.  Adding the
    # worked examples above to the docstring -- "0.022 0.149", "1637 / 13 / 63",
    # "237 / 244" -- moved six figures from NOWHERE to GLOBAL, because this file
    # lives in findings/repro/ and so is one of the artifacts searched.  The
    # audit would have cited its own documentation as proof of the numbers that
    # documentation was describing.  RULE 102, fourth instance in two days, and
    # the first one I caused rather than inherited: an instrument whose input or
    # output path is shared with anything else will eventually read the wrong
    # thing, and the wrong thing will look like a pass.  Caught only because the
    # totals moved when nothing that could legitimately move them had changed.
    SELF = {"091-figure-provenance.json",
            pathlib.Path(__file__).name}
    # findings/repro/baselines/ holds the captured output of each reproduce
    # command checked by tools/check_repro_drift.py (finding 092).  Those are
    # stored artifacts in exactly the sense this audit means, and iterdir() is
    # not recursive, so they were invisible: 092's own corrected figures came
    # back NOWHERE while sitting in a file on disk.
    BASELINES = REPRO / "baselines"
    baselines = [q for q in sorted(BASELINES.glob("*")) if q.is_file()] \
                if BASELINES.is_dir() else []
    all_artifacts = [q for q in sorted(DATA.glob("*.json")) if q.name not in SELF] \
                  + [q for q in REPRO.iterdir()
                     if q.is_file() and q.name not in SELF] + baselines
    gvals, gtext = artifact_pool(all_artifacts)

    report = []
    totals = {"DIRECT": 0, "GLOBAL": 0, "NOWHERE": 0}
    buckets = {c: 0 for c in CATEGORIES}
    buckets["UNCLASSIFIED"] = 0
    problems = []          # stale / unsupported declarations -> non-zero exit
    pending_quotes = []    # QUOTED figures, resolved after every finding is read
    published = {}         # finding number -> set of normalised figures it publishes
    skip = {x.strip() for x in args.exclude.split(",") if x.strip()}
    for md_path in sorted(FINDINGS.glob("[0-9]*.md")):
        num = md_path.name[:3]
        if num in skip:
            continue
        own = [q for q in sorted(DATA.glob(f"{num}-*.json")) if q.name not in SELF] \
            + [q for q in REPRO.iterdir()
               if q.is_file() and q.name.startswith(num + "-")
               and q.name not in SELF] \
            + [q for q in baselines if q.stem.split("-")[0] == num]
        ovals, otext = artifact_pool(own)
        md = md_path.read_text(errors="replace")
        decls, decl_bad = declarations(md)
        for b in decl_bad:
            problems.append(f"{md_path.name}: {b}")
        used = set()
        figs = figures(md)
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
            row = {"figure": raw, "kind": kind, "status": status}
            key_n = norm_fig(raw)
            hit = decls.get(key_n)
            if hit:
                used.add(key_n)
            if status == "NOWHERE":
                if hit is None:
                    row["category"] = "UNCLASSIFIED"
                else:
                    cat, reason, src = hit
                    if cat == "DERIVED" and not derived_ok(raw, md):
                        problems.append(
                            f"{md_path.name}: DERIVED {raw} cannot be recomputed "
                            f"from an '(a of b)' on its own line")
                        row["category"] = "UNCLASSIFIED"
                    else:
                        row["category"] = cat
                        row["reason"] = reason
                        if cat == "QUOTED":
                            row["source"] = src
                            pending_quotes.append((md_path.name, raw, key_n, src))
                buckets[row["category"]] += 1
            elif hit:
                # A declaration must never touch a figure that HAS a producer.
                problems.append(
                    f"{md_path.name}: STALE declaration on {raw} -- it is "
                    f"{status} now, not NOWHERE; delete the declaration")
            rows.append(row)
        for k in sorted(set(decls) - used):
            problems.append(
                f"{md_path.name}: STALE declaration on {k} -- no such figure is "
                f"published in this finding any more")
        published[num] = {norm_fig(x["figure"]) for x in rows}
        report.append({
            "finding": md_path.name,
            "artifacts": [str(p.relative_to(ROOT)) for p in own],
            "figures": len(rows),
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in totals},
            "rows": rows,
        })

    # Resolve QUOTED declarations now that every finding has been read.  A
    # quotation is only honest if the thing quoted is still there: if finding
    # 093 cites 087's 83% and 087 has since corrected or deleted it, the
    # quotation is repeating a number nothing publishes any more.  That is the
    # 077 failure with an extra hop, so it is checked rather than trusted.
    for holder, raw, key_n, src in pending_quotes:
        if src not in published:
            problems.append(f"{holder}: QUOTED {raw}@{src} -- no finding {src}")
        elif key_n not in published[src]:
            problems.append(
                f"{holder}: QUOTED {raw}@{src} -- finding {src} does not publish "
                f"that figure any more; the quotation is stale")

    print(f"findings scanned: {len(report)}   distinct figures: {sum(r['figures'] for r in report)}")
    for k in ("DIRECT", "GLOBAL", "NOWHERE"):
        print(f"  {k:9s} {totals[k]}")
    print()
    print("NOWHERE, partitioned.  Only the last two are debts:")
    for c in CATEGORIES + ("UNCLASSIFIED",):
        mark = "   <-- DEBT" if c in ("UNCHECKED", "UNCLASSIFIED") else ""
        print(f"  {c:20s} {buckets[c]:3d}{mark}")
    debt = buckets["UNCHECKED"] + buckets["UNCLASSIFIED"]
    print(f"  {'':20s} {'':3s}   debt total: {debt}")
    print()
    if problems:
        print("DECLARATION PROBLEMS (these make this script exit non-zero):")
        for pr in problems:
            print(f"  ! {pr}")
        print()
    print("findings ranked by figures that exist in no stored artifact:")
    ranked = sorted(report, key=lambda r: -r["counts"]["NOWHERE"])
    for r in ranked:
        bad = r["counts"]["NOWHERE"]
        if bad < args.min_unbacked: continue
        tag = "no artifacts" if not r["artifacts"] else f"{len(r['artifacts'])} artifact(s)"
        print(f"  {bad:3d}/{r['figures']:<3d} {r['finding']:<62s} {tag}")
        if bad:
            by_cat = {}
            for x in r["rows"]:
                if x["status"] == "NOWHERE":
                    by_cat.setdefault(x.get("category", "UNCLASSIFIED"), []).append(x["figure"])
            for c in sorted(by_cat):
                print(f"        {c:20s} {' '.join(by_cat[c][:12])}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"totals": totals, "categories": buckets, "problems": problems,
             "findings": report}, indent=1) + "\n")
        print(f"\nwrote {args.json}")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
