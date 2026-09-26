#!/usr/bin/env python3
"""Finding 109 -- rule 113 made mechanical: who else counts this case?

Finding 108 corrected one double count by auditing ONE bucket by hand, and left
rule 113 behind: a corrected attribution has more than one downstream consumer,
so when a case changes hands, search for every finding that counts it. A rule
nobody can run is a rule nobody applies. This script runs it over the whole
record.

WHAT IT DOES, IN TWO PARTS.

PART 1 -- THE PARTITIONS. Three findings publish a per-defect id map covering an
implementation's entire `fail` bucket: 076 (sabre, 980), 075 (ical4j, 230), and
074 (ical.js) once 071's four buckets are laid beside it -- which only became
possible when 108 recovered the ids for 071's defects A and B. For each, the
script re-scores the adapter and checks the map is an EXACT PARTITION of the
live fail bucket: no id under two labels, no id outside the bucket, no member of
the bucket unclaimed. 1446 case-failures, checked against measurement rather
than against the sum of the published counts.

PART 2 -- THE SWEEP. Every id named anywhere in findings/*.md, plus the claim
lists stored in findings/data/, is looked up in those partitions. Any id named
by more than one finding is a CANDIDATE double claim and must be adjudicated
here, with a verdict the script can check. An unadjudicated candidate is a
non-zero exit: when a new finding names one of these cases, this goes red until
somebody says which finding owns it.

WHAT IT FOUND, AND IT IS NOT NOTHING.

  * The three partitions are exact. 0 internal overlaps, 0 gaps, at one
    cases_id, verified by re-scoring all three adapters.

  * 336 ids are claimed by TWO OR THREE partitions at once, and every one of
    those is correct: a corpus case that breaks one library usually breaks
    several, and the claims are about different implementations. A detector
    that keys on the case id alone reports 336 collisions and is wrong 336
    times. THE UNIT OF A CLAIM IS (IMPLEMENTATION, CASE, DEFECT), NOT (CASE).

  * SIX cases inside ical.js that two findings both counted. All six belong to
    finding 098 -- next_year() keeps only the first time-of-day of the year --
    and they divide into two kinds, which is the point.

    FOUR were live double counts until finding 108 found them: 098 published
    them and 071's defect B went on counting them, and nothing anywhere said so.
    108 corrected 070 and 071 in prose.

    TWO are a different failure and NEW HERE:
        6e74ec2d96a8  FREQ=YEARLY;BYHOUR=9,18    filed `070-B BYHOUR not applied`
        a844fe388868  FREQ=YEARLY;BYSECOND=0,15  filed `070-B BYSECOND not applied`
    *** 098 ALREADY CORRECTED THESE, IN PROSE, ON 2026-09-25. Both 074's and
        070's markdown say so. findings/data/074-icaljs-residual-reproduced.json
        went on filing them under the old label for four wakes. ***
    That file is not decoration: it is what 102's producer reads, what 108's
    audit read, and what this sweep reads. So the published record contradicted
    itself, and every consumer of the record saw the wrong half.

    Both are wrong from the rule text alone, no adapter needed: defect 070-B IS
    the criterion "a time-part list written out of numeric order", and `9,18`
    and `0,15` are in numeric order. The four 108 found are all `9,8`, which is
    why 071's criterion caught them and these two escaped it.

  * THE SAME FAILURE MODE, TWICE, IN ONE SWEEP. findings/data/-
    102-icaljs-residual-ledger.json said `residual_n: 3` while its own producer
    computes 0. Findings 104 and 105 were added to 102's NAMED registry, the
    drift BASELINE of its stdout was refreshed to `RESIDUAL: 0`, and the DATA
    FILE it writes under --write was never rewritten. 102 exists precisely to
    stop a figure being carried by hand, and its own artifact was carrying one.

    *** RULE 115. A PRODUCER WITH TWO OUTPUTS IS GUARDED ON THE ONE YOU CHECK.
        Prose and stored data are two outputs; baselined stdout and a --write
        artifact are two outputs. Correct one and the other keeps its old
        answer, silently, and consumers read the unguarded one. ***
    FIXED: 074's map carries a machine-readable `corrections` list (the original
    measurement left exactly as measured -- the 035 pattern -- with the
    reassignment beside it, so a consumer can apply it); 102 has a --check mode
    that diffs its stored ledger against a fresh computation, wired into the
    suite as tests/test_ledger_is_current.py, and I watched it fail on the stale
    file before rerunning --write.

  * The contrast that makes the other half of rule 115 concrete. Finding 107
    also took eight ids out of another finding's bucket (071's defect D) and is
    NOT a double count, because it corrected D's stated cause for those eight in
    place and left D's count of 31 alone, deliberately and in writing. 098
    published its own seven and left the donors counting them. A REFINEMENT THAT
    SAYS "THESE IDS OF YOURS ARE MINE FOR A DIFFERENT REASON" MUST EDIT THE
    DONOR -- BOTH ITS OUTPUTS -- NOT ONLY PUBLISH ITSELF.

  * 098's seven corpus cases now account for themselves completely: 4 were in
    071's defect B, 2 in 074's two 070-B singletons, 1 in 074's `unexplained`
    where 102 credits 098 for it.

Read all of this narrowly. NO SCORE MOVES and no case changes bucket -- every one
of these was already a failure and still is. What was wrong is the per-defect
arithmetic, and the direction is always the same: the sum of the published defect
counts overstates the number of distinct failures explained.

USAGE
    python3 findings/repro/109-attribution-partition-audit.py
        Full run. Re-scores ical.js, ical4j and sabre (~2.5 min here).
    python3 findings/repro/109-attribution-partition-audit.py --no-adapters
        Parts 1 (structure only) and 2 from stored data. Fast, read-only,
        deterministic. This is the mode tests/test_attribution_partitions.py
        runs. NOT in tools/repro-drift.json: like 091 it scans findings/, so its
        output changes whenever a finding is added. Its guard is its exit code.

score.py exits non-zero whenever the adapter has any failure, which is normal
here. The output FILE is the signal, not the return code.
"""
import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "findings", "data")
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
TOKEN = re.compile(r"\b[0-9a-f]{12}\b")

# The three adapters whose whole fail bucket has a published id map, with the
# command each was scored through and the fail count RESULTS.md publishes.
ADAPTERS = {
    "icaljs": {
        "argv": ["node", "conformance/adapters/icaljs_adapter.js"],
        "fail": 236,
    },
    "ical4j": {
        "argv": ["java", "-Duser.language=en", "-Duser.country=US",
                 "-cp", "@CP@", "Ical4jAdapter"],
        "fail": 230,
    },
    "sabre": {
        "argv": ["php", "conformance/adapters/php/vobject_adapter.php"],
        "fail": 980,
    },
}

# ---------------------------------------------------------------------------
# PART 2's registry. Every id named by more than one finding gets a verdict.
#
#   CROSS_IMPL  the findings are about different implementations. CHECKED: the
#               id must appear in at least two of the three partitions.
#   REFINEMENT  a later finding subdivides an earlier finding's bucket and said
#               so. CHECKED: the later finding's ids are a subset of the parent
#               bucket, and the parent's published count is unchanged.
#   CITATION    the finding prints the id without claiming it. CHECKED: the id
#               is not in that finding's claim list.
#   DOUBLE      two findings about the SAME implementation both count it. These
#               are the defects in the record; each carries its resolution.
#
# The reason strings are not decoration. A verdict whose reason cannot be
# checked is written as CITATION with the sentence from the finding that makes
# it a citation, so a later reader can go and read it.
# ---------------------------------------------------------------------------

# Which implementation each finding makes its claims about. Used only to make
# CITATION verdicts legible; the CROSS_IMPL check does not rely on it.
CITATIONS = {
    ("039", "c29dd0b92b8f"): "039 prints it and explicitly declines to count it: "
                             "'is a scored failure but is not counted among the 14: "
                             "the three controls do not agree on it'.",
    ("055", "c29dd0b92b8f"): "055 is about ical4j's negative BYSETPOS index; it names "
                             "the case as the corpus's instance of that defect.",
    ("041", "0b0303cd2335"): "041 is about rust-rrule under an ambient TZ.",
    ("041", "eaf7b2453c5a"): "041 is about rust-rrule under an ambient TZ.",
    ("041", "3c45e01105a5"): "041 is about rust-rrule under an ambient TZ.",
    ("066", "0b0303cd2335"): "066 revisits 041's three cases, same implementation.",
    ("066", "eaf7b2453c5a"): "066 revisits 041's three cases, same implementation.",
    ("048", "690ba4d5ab73"): "048 is about DateTime::Event::ICal's deadline.",
    ("070", "6e74ec2d96a8"): "070's own correction notice names it in order to "
                             "DISOWN it -- the guard fired on that very edit "
                             "while 109 was being written, which is the "
                             "behaviour it exists for.",
    ("070", "a844fe388868"): "070's correction notice names it to disown it.",
    ("099", "111d7647f8a8"): "099 prints five cases side by side and claims the two "
                             "FREQ=YEARLY ones; the three FREQ=MONTHLY are 100's.",
    ("099", "be630fe23f8c"): "099 prints it; the MONTHLY three are 100's.",
    ("099", "e1b4925a5263"): "099 prints it; the MONTHLY three are 100's.",
    ("099", "1952128a3c40"): "099 prints it; 101 claims it and 102 credits 101.",
    ("102", "652f31e6bde6"): "102 records it as a WITHDRAWN claim of 101's.",
    ("099", "652f31e6bde6"): "printed by 099; the claim was withdrawn in 102.",
    ("101", "652f31e6bde6"): "101's claim on it was withdrawn; see 102's WITHDRAWN.",
    ("057", "1133012800b2"): "057 is a rescore of prefix buckets across adapters.",
    ("057", "afd39eca7f70"): "057 is a rescore of prefix buckets across adapters.",
    ("057", "9346b18d8869"): "057 is a rescore of prefix buckets across adapters.",
    ("057", "0fbbee9bbc5e"): "057 is a rescore of prefix buckets across adapters.",
    ("075", "9e1f525849c4"): "075's own map files it under ical4j `unexplained`; "
                             "the ical.js owner is 074-E. Different implementation.",
    ("095", "9e1f525849c4"): "095 closes ical4j's BYMONTHDAY residual.",
    ("096", "0fcc0ebb9669"): "096 published counts, not ids; 102 recovers its seven "
                             "from its own classifier and this is not among them.",
    ("096", "57bd6869b586"): "not among 096's seven; 099 claims it.",
    ("096", "5b57fff10b12"): "not among 096's seven; 099 claims it.",
    ("096", "71c5fc332bd4"): "not among 096's seven; 099 claims it.",
    ("096", "7a381d6a4176"): "not among 096's seven; 099 claims it.",
    ("096", "83ed4e4655a6"): "not among 096's seven; 099 claims it.",
    ("102", "d27c58ae379a"): "102's ledger records 105 as the claimant.",
    ("102", "7a6256afbb5b"): "102's ledger records 104 as the claimant.",
    ("102", "f9f6ec0cf765"): "102's ledger records 104 as the claimant.",
    ("102", "0fdd7d614fc6"): "102's ledger records 096 as the claimant.",
    ("102", "2e2cff862cec"): "102's ledger records 096 as the claimant.",
    ("102", "7251092e97dd"): "102's ledger records 096 as the claimant.",
    ("102", "9ef3e4e23567"): "102's ledger records 096 as the claimant.",
    ("102", "a3b31c376a82"): "102's ledger records 096 as the claimant.",
    ("102", "aba2c7ab25c4"): "102's ledger records 096 as the claimant.",
    ("102", "d7a9ed17f9fb"): "102's ledger records 096 as the claimant.",
    ("104", "d27c58ae379a"): "104 prints it beside its two and DECLINES it "
                             "(rule 109); 105 claims it.",
}

# Findings that name ids while measuring something other than a per-defect
# attribution: horizons, bounds, agreement past the bound, prefix rescores.
# Naming a case there is never a claim on it, and listing the findings once is
# clearer than one entry per id.
NON_ATTRIBUTION_FINDINGS = {
    "057": "a rescore of the prefix buckets across every adapter",
    "058": "the universal residual -- cases no implementation gets right",
    "059": "ical4j before/after, and a rescore",
    "060": "agreement past the corpus bound",
    "061": "readings past the bound",
    "109": "this finding -- an audit of the record, which names ids in order "
           "to report who else counts them and claims none of them itself",
    "090": "the part sweep's per-part ATTRIBUTABLE populations -- 090 prints "
           "ical.js's whole BYSECOND set as a sweep population, and says so",
}

# The genuine double counts, with the resolution. CHECKED: each id really is in
# BOTH the named partition bucket and the named finding's stored claim list.
DOUBLE = {
    "885892ba0a69": ("icaljs", "071-B", "098", "found by 108"),
    "b72c3712f042": ("icaljs", "071-B", "098", "found by 108"),
    "b96855e3bf8f": ("icaljs", "071-B", "098", "found by 108"),
    "c18ccdf31936": ("icaljs", "071-B", "098", "found by 108"),
    "6e74ec2d96a8": ("icaljs", "074 070-B  BYHOUR not applied", "098",
                     "NEW at 109. Corrected in 074's and 070's PROSE at 098 on "
                     "2026-09-25 and left under the old label in 074's DATA "
                     "FILE for four wakes. BYHOUR=9,18 is in numeric order, so "
                     "070-B's own criterion could never have held."),
    "a844fe388868": ("icaljs", "074 070-B  BYSECOND not applied", "098",
                     "NEW at 109. Same: prose corrected, artifact not. "
                     "BYSECOND=0,15 is in numeric order."),
}

# Stored claim lists: a finding's own published ids, read from its data file
# where it has one and from the 102 ledger where it does not.
def claim_lists():
    d102 = json.load(open(os.path.join(DATA, "102-icaljs-residual-ledger.json")))
    out = collections.defaultdict(set)
    for i, v in d102["attributed"].items():
        out[v["finding"]].add(i)
    d098 = json.load(open(os.path.join(DATA,
        "098-icaljs-yearly-time-parts-truncated.json")))
    out["098"] |= set(d098["corpus_cases"])
    d104 = json.load(open(os.path.join(DATA, "104-bysetpos-per-month.json")))
    out["104"] |= set(d104["claimed_residual_ids"])
    # 108 is the owner of record for 071's buckets A and B: it recovered their
    # ids and resolved B into three mechanisms. Every id it names, it names as a
    # claim about one of those.
    d108 = json.load(open(os.path.join(DATA, "108-icaljs-bucket-audit.json")))
    out["108"] |= set(d108["recovered"]["defect_A"])
    out["108"] |= set(d108["recovered"]["defect_B"])
    # 107 has no data file; its eight ids are named in its own prose and it says
    # so in the text. Recovered from the prose, then checked against 071-D below.
    return out


CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok)))
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))


def classpath():
    jars = sorted(glob.glob(os.path.join(
        ROOT, "conformance/adapters/java/libs/*.jar")))
    rel = [os.path.relpath(j, ROOT) for j in jars]
    return ":".join(["conformance/adapters/java/classes"] + rel)


def score(name, timeout):
    argv = [a.replace("@CP@", classpath()) for a in ADAPTERS[name]["argv"]]
    tmp = os.path.join(ROOT, ".109-%s-score.json" % name)
    cmd = ([sys.executable, os.path.join(ROOT, "conformance", "score.py"),
            "--json", tmp, "--timeout", str(timeout), "--"] + argv)
    subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, TZ="UTC"),
                   capture_output=True, text=True)
    if not os.path.exists(tmp):
        raise SystemExit("score.py wrote no output file for %s" % name)
    with open(tmp) as fh:
        s = json.load(fh)
    os.unlink(tmp)
    return s


def partitions():
    """impl -> {label: [ids]}, covering that adapter's whole fail bucket."""
    d071 = json.load(open(os.path.join(DATA,
        "071-icaljs-residual-attribution.json")))
    d108 = json.load(open(os.path.join(DATA, "108-icaljs-bucket-audit.json")))
    d074 = json.load(open(os.path.join(DATA,
        "074-icaljs-residual-reproduced.json")))
    d075 = json.load(open(os.path.join(DATA,
        "075-ical4j-residual-reproduced.json")))
    d076 = json.load(open(os.path.join(DATA,
        "076-sabre-residual-reproduced.json")))
    icaljs = {
        "071-A": d108["recovered"]["defect_A"],
        "071-B": d108["recovered"]["defect_B"],
        "071-C": d071["weekly_bysetpos_ids"],
        "071-D": d071["yearly_byweekno_ids"],
    }
    for k, v in d074["ids"].items():
        icaljs["074 " + k] = v
    ids = {}
    for d in (d071["corpus_version"], d074, d075, d076, d108):
        ids[d.get("cases_id") or d["cases_id"]] = True
    cases_ids = sorted(ids)
    return ({"icaljs": icaljs,
             "ical4j": {"075 " + k: v for k, v in d075["ids"].items()},
             "sabre": {"076 " + k: v for k, v in d076["ids"].items()}},
            cases_ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-adapters", action="store_true",
                    help="stored data only: structure, not re-measurement")
    ap.add_argument("--timeout", type=int, default=3000)
    args = ap.parse_args()

    parts, cases_ids = partitions()
    print("PART 1 -- the three published partitions")
    check("every source data file names ONE cases_id",
          len(cases_ids) == 1, cases_ids[0][:12] if len(cases_ids) == 1
          else ", ".join(c[:12] for c in cases_ids))

    owner = {}          # (impl, id) -> label
    for impl, labels in parts.items():
        seen = {}
        dupes = []
        for lbl, lst in labels.items():
            for i in lst:
                if i in seen:
                    dupes.append((i, seen[i], lbl))
                seen[i] = lbl
                owner[(impl, i)] = lbl
        n = sum(len(v) for v in labels.values())
        check("%s: %d ids over %d labels, no id under two labels"
              % (impl, n, len(labels)), not dupes, repr(dupes[:3]))
        check("%s: the published fail count is %d and the map holds %d"
              % (impl, ADAPTERS[impl]["fail"], len(seen)),
              len(seen) == ADAPTERS[impl]["fail"])

    if args.no_adapters:
        print("  (--no-adapters: the live fail buckets are NOT re-measured)")
    else:
        for impl in sorted(parts):
            s = score(impl, args.timeout)
            live = {f["case"]["id"] for f in s["failures"]
                    if f["bucket"] == "fail"}
            claimed = set()
            for v in parts[impl].values():
                claimed |= set(v)
            check("%s: scored at %s, fail=%d, and the map EQUALS the live "
                  "fail bucket" % (impl, s["corpus_version"]["cases_id"][:12],
                                   len(live)),
                  live == claimed and s["corpus_version"]["cases_id"] == cases_ids[0],
                  "extra %d, missing %d" % (len(claimed - live), len(live - claimed)))

    # The number that kills naive id-collision detection.
    per_id = collections.Counter()
    for (impl, i) in owner:
        per_id[i] += 1
    multi_impl = [i for i, n in per_id.items() if n > 1]
    print("\n  %d distinct cases appear in at least one partition; %d of them "
          "in TWO OR THREE" % (len(per_id), len(multi_impl)))
    print("  Those %d are what a detector keyed on the case id alone would "
          "report, and all %d are correct claims about different "
          "implementations." % (len(multi_impl), len(multi_impl)))

    print("\nPART 2 -- the sweep")
    claims = claim_lists()
    named = collections.defaultdict(set)     # id -> set(finding)
    for p in sorted(glob.glob(os.path.join(ROOT, "findings", "*.md"))):
        n = os.path.basename(p)[:3]
        with open(p) as fh:
            txt = fh.read()
        for t in set(TOKEN.findall(txt)):
            if any((impl, t) in owner for impl in parts):
                named[t].add(n)
    for f, ids in claims.items():
        for i in ids:
            if any((impl, i) in owner for impl in parts):
                named[i].add(f)
    # 107's ids come from its prose; check the claim it makes about them.
    d107 = [i for i in named if "107" in named[i]]
    check("107 names 8 ids and all 8 are inside 071's defect D",
          len(d107) == 8 and all(owner.get(("icaljs", i)) == "071-D"
                                 for i in d107), repr(sorted(d107)))
    claims["107"] = set(d107)

    multi = {i: sorted(v) for i, v in named.items() if len(v) > 1}
    print("  %d ids are named by a finding; %d by more than one"
          % (len(named), len(multi)))

    unadjudicated = []
    doubles_found = []
    for i, fs in sorted(multi.items()):
        # Who genuinely CLAIMS it, per the stored claim lists and the partitions?
        claimants = set()
        for f in fs:
            if i in claims.get(f, ()):
                claimants.add(f)
        owners = {impl: owner[(impl, i)] for impl in parts if (impl, i) in owner}
        for f in fs:
            if f in claimants:
                continue
            if f in NON_ATTRIBUTION_FINDINGS:
                continue
            if (f, i) in CITATIONS:
                continue
            # A finding that OWNS the id through a partition it published is a
            # claimant too.
            if any(lbl.startswith(f) for lbl in owners.values()):
                continue
            unadjudicated.append((i, f, owners))
        if len(claimants) > 1 or (claimants and owners):
            doubles_found.append((i, sorted(claimants), owners))

    check("every id named by more than one finding is adjudicated",
          not unadjudicated,
          "\n      ".join("%s named by %s, owners %s" % u
                          for u in unadjudicated[:8]))

    # Rule 115's other instance: 102's stored artifact against its producer.
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "findings/repro/102-residual-ledger.py"),
                        "--check"], cwd=ROOT, capture_output=True, text=True)
    check("102's stored ledger matches its own producer (it did NOT before this "
          "finding: stored residual_n 3, computed 0)", r.returncode == 0,
          r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")

    print("\n  Cases one implementation's record counted twice:")
    for i, (impl, lbl, f, why) in sorted(DOUBLE.items()):
        inpart = owner.get((impl, i)) == lbl
        inclaim = i in claims.get(f, ())
        print("    %s  %-38s  +  %s   %s" % (i, lbl, f, "ok" if (inpart and inclaim)
                                             else "FAIL"))
        print("        %s" % why)
        CHECKS.append(("%s is in both %s and %s's claims" % (i, lbl, f),
                       inpart and inclaim))
    check("098 publishes exactly 7 corpus cases and 6 of them sat in another "
          "finding's bucket too",
          len(claims["098"]) == 7
          and len([i for i in DOUBLE if DOUBLE[i][2] == "098"]) == 6)

    # The two new ones are visibly wrong from the rule text alone. Show that.
    rules = {}
    for line in open(CASES):
        c = json.loads(line)
        if c["id"] in DOUBLE:
            rules[c["id"]] = c["rrule"]
    def ascending(rrule, part):
        m = re.search(r"\b%s=([0-9,+-]+)" % part, rrule)
        if not m:
            return None
        v = [int(x) for x in m.group(1).split(",")]
        return v == sorted(v)
    print("\n  Defect 070-B/071-B IS the criterion 'a time-part list written out")
    print("  of numeric order'. Whether each double-counted case meets it:")
    for i in sorted(DOUBLE):
        for part in ("BYHOUR", "BYMINUTE", "BYSECOND"):
            a = ascending(rules[i], part)
            if a is None:
                continue
            print("    %s  %-42s  %s is %s" % (i, rules[i], part,
                  "IN ORDER -- 070-B cannot hold" if a else "out of order"))
    # The prose-vs-artifact divergence, machine-checked rather than asserted.
    d074 = json.load(open(os.path.join(DATA,
        "074-icaljs-residual-reproduced.json")))
    txt074 = open(glob.glob(os.path.join(ROOT, "findings", "074-*.md"))[0]).read()
    txt070 = open(glob.glob(os.path.join(ROOT, "findings", "070-*.md"))[0]).read()
    corr = {c["id"]: c for c in d074.get("corrections", [])}
    print("\n  074's prose-only correction, now in its data file as "
          "`corrections`:")
    for i, c in sorted(corr.items()):
        print("    %s  %s  ->  finding %s" % (i, c["from_label"], c["to_finding"]))
    check("074's data file carries a `corrections` entry for both ids whose "
          "label its own prose retracted at 098",
          set(corr) == {"6e74ec2d96a8", "a844fe388868"}, repr(sorted(corr)))
    check("074's prose names both, which is what made them prose-only",
          all(i in txt074 for i in corr))
    check("070's prose also records that 074 had filed two cases under its "
          "defect B", all(i in txt070 or "filed two cases" in txt070
                          for i in corr))
    check("every correction moves an id to a finding that claims it",
          all(i in claims.get(c["to_finding"], ()) for i, c in corr.items()))
    check("the label each correction moves the id OFF is the label the "
          "partition still records, so the two really do disagree",
          all(owner[("icaljs", i)] == "074 " + c["from_label"]
              for i, c in corr.items()))

    # Applying the corrections must leave the partition a partition: a
    # relabelling moves no case in or out of the fail bucket.
    corrected = dict(owner)
    for i, c in corr.items():
        corrected[("icaljs", i)] = "finding " + c["to_finding"]
    for i, (impl, lbl, f, why) in DOUBLE.items():
        if why == "found by 108":
            corrected[(impl, i)] = "finding " + f
    icaljs_n = len([1 for (impl, i) in corrected if impl == "icaljs"])
    o98 = [i for (impl, i), l in corrected.items()
           if impl == "icaljs" and l == "finding 098"]
    check("after the corrections ical.js's fail bucket still holds %d ids"
          % ADAPTERS["icaljs"]["fail"], icaljs_n == ADAPTERS["icaljs"]["fail"])
    check("098 owns 6 of the fail bucket, and its seventh is the one 102 "
          "credits it for inside 074's `unexplained`",
          len(o98) == 6 and len(claims["098"]) == 7
          and len(set(claims["098"]) - set(o98)) == 1,
          repr(sorted(o98)))

    new = [i for i in DOUBLE if DOUBLE[i][3].startswith("NEW")]
    check("both ids new at 109 carry a time-part list that IS in numeric order",
          all(any(ascending(rules[i], p) for p in
                  ("BYHOUR", "BYMINUTE", "BYSECOND")) for i in new),
          repr(sorted(new)))
    check("all four ids 108 found carry one OUT of numeric order (which is why "
          "071's criterion caught them)",
          all(any(ascending(rules[i], p) is False for p in
                  ("BYHOUR", "BYMINUTE", "BYSECOND"))
              for i in DOUBLE if DOUBLE[i][3] == "found by 108"))

    bad = [c for c, ok in CHECKS if not ok]
    print("\n%d checks, %d failed" % (len(CHECKS), len(bad)))
    for c in bad:
        print("  FAILED: %s" % c)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
