"""Coverage of RFC 5545 3.3.10's BYxxx/FREQ table, and the BYSETPOS streaming fix.

Two things are pinned here.

1. The corpus's coverage of the table is a *statement*, not a side effect of
   which random seeds were used. Every cell the spec permits must hold at
   least one case; the cells it marks N/A must hold none, because using them
   is a MUST NOT violation, not a gap.

2. src/naive.py's BYSETPOS path streams. It used to accumulate every period to
   the 30-year horizon before selecting, which is unusable below FREQ=DAILY
   and left three cells unreachable.
"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import env
env.add_dateutil_to_path()
from datetime import datetime
import coverage, enumerate_cells, validity
from naive import expand
from differ import compare

FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


# --- the table is read from the RFC, not transcribed ----------------------

freqs, parts, T = coverage.table()
check("table has the 7 FREQ columns", freqs == list(validity.FREQS),
      str(freqs))
check("table has 9 BYxxx rows", len(parts) == 9 and parts[0] == "BYMONTH"
      and parts[-1] == "BYSETPOS", str(parts))
check("63 cells parsed", len(T) == 63, str(len(T)))

# Spot checks, quoting the printed table. These are a canary for a column
# shift in the parser, not a re-transcription of the table.
for key, want in [(("BYWEEKNO", "YEARLY"), "Expand"),
                  (("BYWEEKNO", "MONTHLY"), "N/A"),
                  (("BYMONTH", "YEARLY"), "Expand"),
                  (("BYMONTH", "SECONDLY"), "Limit"),
                  (("BYMONTHDAY", "WEEKLY"), "N/A"),
                  (("BYYEARDAY", "DAILY"), "N/A"),
                  (("BYSECOND", "SECONDLY"), "Limit"),
                  (("BYSECOND", "MINUTELY"), "Expand"),
                  (("BYDAY", "MONTHLY"), "Note 1"),
                  (("BYDAY", "YEARLY"), "Note 2"),
                  (("BYSETPOS", "YEARLY"), "Limit")]:
    check("cell %s/%s is %s" % (key[0], key[1], want), T[key] == want, T[key])

cells = coverage.cells()
check("57 permitted cells after expanding the two BYDAY notes",
      len(cells) == 57, str(len(cells)))
check("no N/A cell is counted as coverable",
      not [c for c in cells if c[2] == "N/A"])

# --- classify puts rules in the branch the notes describe -----------------

CLASSIFY = [
    # Note 1: "Limit if BYMONTHDAY is present; otherwise, special expand"
    ("FREQ=MONTHLY;BYDAY=MO;BYMONTHDAY=15", ("BYDAY", "MONTHLY", coverage.NOTE1[0])),
    ("FREQ=MONTHLY;BYDAY=2MO", ("BYDAY", "MONTHLY", coverage.NOTE1[1])),
    # Note 2, in the order the note states the branches
    ("FREQ=YEARLY;BYDAY=MO;BYYEARDAY=60", ("BYDAY", "YEARLY", coverage.NOTE2[0])),
    ("FREQ=YEARLY;BYDAY=MO;BYMONTHDAY=15", ("BYDAY", "YEARLY", coverage.NOTE2[0])),
    ("FREQ=YEARLY;BYDAY=MO;BYWEEKNO=20", ("BYDAY", "YEARLY", coverage.NOTE2[1])),
    ("FREQ=YEARLY;BYDAY=MO;BYMONTH=3", ("BYDAY", "YEARLY", coverage.NOTE2[2])),
    ("FREQ=YEARLY;BYDAY=-1MO", ("BYDAY", "YEARLY", coverage.NOTE2[3])),
    # Note 2's branches are ordered: BYWEEKNO loses to BYYEARDAY/BYMONTHDAY,
    # BYMONTH loses to BYWEEKNO.
    ("FREQ=YEARLY;BYDAY=MO;BYWEEKNO=20;BYMONTHDAY=15", ("BYDAY", "YEARLY", coverage.NOTE2[0])),
    ("FREQ=YEARLY;BYDAY=MO;BYWEEKNO=20;BYMONTH=3", ("BYDAY", "YEARLY", coverage.NOTE2[1])),
    ("FREQ=WEEKLY;BYDAY=MO,WE", ("BYDAY", "WEEKLY", "Expand")),
    ("FREQ=HOURLY;BYDAY=MO", ("BYDAY", "HOURLY", "Limit")),
]
for rule, want in CLASSIFY:
    got = coverage.classify(rule)
    check("classify %s" % rule, want in got, str(got))

check("classify ignores parts that are absent",
      coverage.classify("FREQ=DAILY") == [])

# --- the enumerator hits every cell, with valid rules ---------------------

by_cell = {}
for cell, rule, ds in enumerate_cells.cases():
    by_cell.setdefault(cell, []).append((rule, ds))
check("enumerator emits a case for every permitted cell",
      set(by_cell) == set(cells),
      "missing=%s" % sorted(set(cells) - set(by_cell)))
bad_valid = [r for _, r, _ in enumerate_cells.cases() if not validity.is_valid(r)]
check("every systematic rule is valid under 3.3.10", not bad_valid, str(bad_valid))
misfiled = [(c, r) for c, r, _ in enumerate_cells.cases()
            if c not in coverage.classify(r)]
check("every systematic rule classifies into the cell it was built for",
      not misfiled, str(misfiled[:3]))

# --- the built corpus reports and possesses that coverage -----------------

CORPUS = os.path.join(HERE, "..", "corpus")
cov = json.load(open(os.path.join(CORPUS, "coverage.json")))
check("coverage.json reports no uncovered cell",
      cov["meta"]["uncovered"] == 0, str(cov["uncovered"]))
check("coverage.json counts all 57 cells", cov["meta"]["cells"] == 57)

seen = set()
for f in ("corroborated.json", "disputed.json"):
    for c in json.load(open(os.path.join(CORPUS, f)))["cases"]:
        seen.update(c.get("cells", []))
want = {"/".join(c) for c in cells}
check("the corpus files really do hold a case for every cell",
      want <= seen, "missing=%s" % sorted(want - seen))
check("no corpus case claims a cell outside the table",
      seen <= want, "extra=%s" % sorted(seen - want))

# --- BYSETPOS streams ------------------------------------------------------

t0 = time.time()
occ = expand("FREQ=SECONDLY;BYSETPOS=-1;BYSECOND=0,15,30",
             datetime(2026, 3, 2, 9, 0, 0), limit=8)
el = time.time() - t0
check("FREQ=SECONDLY with BYSETPOS returns in under a second", el < 1.0,
      "%.3fs" % el)
check("...and gives the whole limited set, one instant per one-second period",
      [x.strftime("%H:%M:%S") for x in occ] ==
      ["09:00:00", "09:00:15", "09:00:30", "09:01:00", "09:01:15", "09:01:30",
       "09:02:00", "09:02:15"],
      str([x.strftime("%H:%M:%S") for x in occ]))

# Streaming must not change any answer. dateutil is the independent check;
# these rules span the frequencies where periods complete at different rates.
SETPOS = [
    ("FREQ=SECONDLY;BYSETPOS=-1;BYSECOND=0,15,30", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=MINUTELY;BYSETPOS=-1;BYSECOND=0,15,30", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=HOURLY;BYSETPOS=1;BYMINUTE=0,30", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=DAILY;BYSETPOS=-1;BYHOUR=9,18", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=WEEKLY;BYSETPOS=-1;BYDAY=MO,WE,FR", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=MONTHLY;BYSETPOS=2;BYDAY=MO,WE,FR", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=YEARLY;BYSETPOS=-2;BYDAY=MO,WE,FR", datetime(2026, 3, 2, 9, 0, 0)),
    ("FREQ=MONTHLY;BYSETPOS=-1;BYDAY=MO,WE,FR;COUNT=3", datetime(2026, 3, 2, 9, 0, 0)),
    # DTSTART mid-period: the first period is partly in the past, and
    # BYSETPOS still selects from the whole period (3.8.5.3's undefined
    # region -- what is pinned here is only that both expanders agree).
    ("FREQ=MONTHLY;BYSETPOS=1;BYDAY=MO,WE,FR", datetime(2026, 3, 20, 9, 0, 0)),
]
for rule, ds in SETPOS:
    check("naive == dateutil: %s @ %s" % (rule, ds.strftime("%Y-%m-%d %H:%M")),
          compare(rule, ds, 8) is None)

check("COUNT still bounds the BYSETPOS path",
      len(expand("FREQ=MONTHLY;BYSETPOS=-1;BYDAY=MO,WE,FR;COUNT=3",
                 datetime(2026, 3, 2, 9, 0, 0), limit=99)) == 3)
check("limit still bounds the BYSETPOS path",
      len(expand("FREQ=SECONDLY;BYSETPOS=-1;BYSECOND=0,15,30",
                 datetime(2026, 3, 2, 9, 0, 0), limit=5)) == 5)

print("\n%d failure(s)" % len(FAILURES))
sys.exit(1 if FAILURES else 0)
