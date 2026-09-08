"""Audit finding documents for DTSTART synchronization (standing rule 3b).

Extracts (rule, dtstart) pairs from findings/*.md in the two shapes that
actually occur there, then asks naive.expand whether out[0] == dtstart.
Anything it cannot pair confidently is printed as UNPAIRED for hand reading,
because a silently dropped example is the failure this audit exists to catch.
"""
import re, sys, glob, os
from datetime import datetime
sys.path.insert(0, "src")
import naive

RULE = re.compile(r'\b((?:FREQ=|RRULE:FREQ=)[A-Z0-9=;,+\-:T]*)')
DT = re.compile(r'DTSTART[^\s:]*[:= ]\s*(\d{8}T\d{6}|\d{8})')

def parse_dt(s):
    return datetime.strptime(s, "%Y%m%dT%H%M%S") if "T" in s else None

pairs, unpaired = [], []
for path in sorted(glob.glob("findings/*.md")):
    lines = open(path).read().splitlines()
    for i, line in enumerate(lines):
        for m in RULE.finditer(line):
            rule = m.group(1).replace("RRULE:", "")
            # same line first, then the 3 lines above and below (block form)
            ctx = [line] + [lines[j] for j in range(max(0, i-3), min(len(lines), i+4)) if j != i]
            dt = None
            for c in ctx:
                d = DT.search(c)
                if d:
                    dt = d.group(1); break
            if dt is None:
                unpaired.append((path, i+1, rule)); continue
            pairs.append((path, i+1, rule, dt))

seen = set()
bad, dateval, err = [], [], []
for path, ln, rule, dt in pairs:
    key = (rule, dt)
    if key in seen: continue
    seen.add(key)
    d = parse_dt(dt)
    if d is None:
        dateval.append((path, ln, rule, dt)); continue
    try:
        out = naive.expand(rule, d, limit=1)
    except Exception as e:
        err.append((path, ln, rule, dt, f"{type(e).__name__}: {e}")); continue
    if not out:
        bad.append((path, ln, rule, dt, "EMPTY within horizon")); continue
    if out[0] != d:
        bad.append((path, ln, rule, dt, f"first occurrence {out[0]} != DTSTART"))

print(f"pairs extracted: {len(pairs)}  distinct: {len(seen)}")
print(f"\n== UNSYNCHRONIZED / EMPTY ({len(bad)}) ==")
for p, ln, r, dt, why in bad:
    print(f"  {os.path.basename(p)}:{ln}  {r}  DTSTART {dt}\n      {why}")
print(f"\n== EXPANDER ERRORS ({len(err)}) ==")
for p, ln, r, dt, why in err:
    print(f"  {os.path.basename(p)}:{ln}  {r}  DTSTART {dt}\n      {why}")
print(f"\n== DATE-VALUED, not checked here ({len(dateval)}) ==")
for p, ln, r, dt in dateval:
    print(f"  {os.path.basename(p)}:{ln}  {r}  DTSTART {dt}")
print(f"\n== UNPAIRED, hand-read required ({len(unpaired)}) ==")
for p, ln, r in unpaired:
    print(f"  {os.path.basename(p)}:{ln}  {r}")
