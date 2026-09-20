"""Build the conformance corpus.

A case earns a place in the corpus only when two independent expanders -- the
spec-derived brute force in naive.py and python-dateutil's interval machinery
-- agree on it. Agreement between implementations that share no code is the
evidence; it is not proof, but it is much stronger than one library's own
regression suite, which by construction cannot disagree with itself.

Cases where they disagree are not silently dropped. They go to
corpus/disputed.json for a human to adjudicate against the spec text.
"""
import sys, os, json, random, itertools, re, math
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env
env.add_dateutil_to_path()
from datetime import datetime, timedelta
import naive
from differ import compare, gen, DTSTARTS, du_expand


def _horizon(ds):
    """The corpus horizon for this DTSTART.

    Read through `naive` rather than imported by value, so that
    `--horizon-days` reaches every call site instead of just the ones that
    happen to look it up late. Finding 064 found the horizon defined in two
    modules and obeyed by neither consistently; `naive.HORIZON_DAYS` is now
    the single definition and this is the only way the corpus asks for it.
    """
    return ds + timedelta(days=naive.HORIZON_DAYS)
from naive import expand
import validity
import coverage
import grammar
import enumerate_cells
import enumerate_branches
import pairs

#: The committed corpus. Inputs (hand adjudications, the DATE-value
#: cases) are always read from here; outputs go wherever the caller asks,
#: so that a rebuild can be compared against this directory rather than
#: overwriting it. Absolute, so the script does not depend on the cwd.
CORPUS = os.path.join(env.REPO, "corpus")

N = 25  # occurrences recorded per case


def fmt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def is_synchronized(rule, dtstart):
    """RFC 5545 sec 3.8.5.3: DTSTART SHOULD be synchronized with the rule, and the
    recurrence set is *undefined* when it is not. Operationally, DTSTART is
    synchronized exactly when it is itself the first occurrence the rule
    generates from it."""
    occ = expand(rule, dtstart, horizon=_horizon(dtstart), limit=1)
    return bool(occ) and occ[0] == dtstart


def dtstart_variants(rule, base):
    """Yield the DTSTARTs to test this rule at.

    The original generator picked DTSTART independently of the rule, which meant
    ~90% of cases landed in the RFC-undefined unsynchronized region. Here we also
    derive a synchronized DTSTART -- the rule's own first occurrence at or after
    `base` -- so the corpus has real coverage of the region the spec actually
    defines.

    Using the naive expander to *choose* DTSTART does not weaken corroboration:
    the case is still adjudicated by naive vs dateutil agreement on the result,
    so a badly chosen DTSTART shows up as a dispute rather than a false pass.
    """
    out = [base]
    occ = expand(rule, base, horizon=_horizon(base), limit=1)
    if occ and occ[0] != base:
        out.append(occ[0])
    return out


def expect_bound(rule, dtstart, occ):
    """Why `expect` stops where it does. Decided from the rule text and the two
    caps this builder imposes -- never from an expander -- because a cap I chose
    is not a property of the recurrence.

    "complete"  the rule provably terminates inside the recorded window, so
                `expect` is the *entire* recurrence set and a consumer may
                assert there is nothing after it.
    "count"     stopped at the N-occurrence cap; the set continues.
    "horizon"   stopped at the HORIZON_DAYS cap with fewer than N occurrences.
                The set may still continue *after* the horizon, and for 67
                cases in the 2026-09-06 corpus it demonstrably did -- which is
                why this is not merged with "complete".

    Before 2026-09-07 this was a boolean `truncated` (= len(occ) == N), whose
    false branch was read as "complete" and was wrong for those 67 cases.
    """
    m = re.search(r"(?:^|;)COUNT=(\d+)(?:;|$)", rule)
    if m and int(m.group(1)) <= len(occ):
        return "complete"
    # The N-occurrence cap is checked *before* UNTIL: if it bit first, an
    # in-horizon UNTIL says nothing about whether the set ends at occurrence N.
    # Three FREQ=HOURLY/MINUTELY/SECONDLY cases proved that empirically.
    if len(occ) >= N:
        return "count"
    m = re.search(r"(?:^|;)UNTIL=([0-9TZ]+)(?:;|$)", rule)
    if m:
        raw = m.group(1).rstrip("Z")
        fmtstr = "%Y%m%dT%H%M%S" if "T" in raw else "%Y%m%d"
        if datetime.strptime(raw, fmtstr) <= _horizon(dtstart):
            return "complete"
    return "horizon"


def _other_reading(rule, ds, n, horizon=None):
    """The first `n` occurrences under the *other* reading of 3.3.10's first
    period, or None when the rule has no BYSETPOS and the question does not
    arise. See src/naive.py's `truncate_first_period` and finding 018."""
    if "BYSETPOS" not in rule or n == 0:
        return None
    return [fmt(x) for x in
            expand(rule, ds, horizon=horizon, limit=n,
                   truncate_first_period=True)][:n]


WEEKDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _dtstart_fill_rewrite(rule, ds):
    """The rival reading of 3.3.10 written as a source-to-source rewrite, or
    None when the rule is not one of the two shapes it applies to.

    Finding 024. In exactly two YEARLY cells the expand/limit table is the sole
    authority *and* leaves a coarser date field unspecified, and 3.3.10's own
    DTSTART-fill sentence then says where that field comes from. The table says
    expand; the sentence says the field is already determined. Neither says
    which wins, and three independent lineages (libical, ical4j, dmfs
    lib-recur) behave exactly as if the field had been filled from DTSTART:

        FREQ=YEARLY + BYMONTHDAY, no BYMONTH  ->  add BYMONTH=month(DTSTART)
        FREQ=YEARLY + BYWEEKNO,   no BYDAY    ->  add BYDAY=weekday(DTSTART)

    Both fills are applied when both shapes are present. Until finding 052 this
    function returned after the first match, so a rule carrying BYMONTHDAY and
    BYWEEKNO together got only the BYMONTH fill and the reading was recorded as
    not applying -- which scored a reading disagreement as a defect.

    BYDAY under YEARLY is the same collision, but Note 2 spells it out in prose
    and all six implementations expand it -- which is why this is a rewrite of
    two cells and not of a column.
    """
    parts = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    if parts.get("FREQ") != "YEARLY":
        return None
    out = rule
    if "BYMONTHDAY" in parts and "BYMONTH" not in parts:
        out += ";BYMONTH=%d" % ds.month
    if "BYWEEKNO" in parts and "BYDAY" not in parts:
        out += ";BYDAY=" + WEEKDAY[ds.weekday()]
    return out if out != rule else None


GREG_CYCLE_YEARS = 400
GREG_CYCLE_DAYS = 146097   # 400 Gregorian years: also exactly 20871 whole weeks


def _cycle_days(rule):
    """One full period of a YEARLY rule's calendar pattern, in days.

    The Gregorian calendar repeats exactly every 400 years -- 146097 days,
    which is also an exact whole number of weeks -- so month lengths, weekday
    alignment and ISO-8601 week numbering all return to their starting
    configuration. A YEARLY rule selects dates from that configuration alone,
    so if it fires at all it fires at least once per cycle; with INTERVAL=k
    the rule's own phase repeats every lcm(k, 400) years.
    """
    parts = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    years = math.lcm(int(parts.get("INTERVAL", "1")), GREG_CYCLE_YEARS)
    return years // GREG_CYCLE_YEARS * GREG_CYCLE_DAYS


def _short_of_horizon(alt_rule, ds, n):
    """`alt_rule` yielded fewer than `n` occurrences inside the corpus
    horizon. Return the reading's answer, or None when I cannot establish it.

    Rule 33: a difference measured inside a truncated window is not an
    omission. The corpus horizon is 30 years because that is what the
    differential harness compares over; it is a property of my instrument.
    An implementation has no such window, so before recording anything the
    two possible meanings of a short list have to be told apart, and
    `_cycle_days` makes that decidable rather than a matter of picking a
    bigger number:

      * occurrences exist but arrive sparsely -- one full cycle (or as many
        as the density needs) reaches `n`, and the 30-year window was the
        only reason the list was short;
      * nothing at all inside a full cycle -- the rewritten rule selects no
        date in any Gregorian configuration, so its occurrence set is empty
        and the empty list *is* the reading's answer.

    Anything else (still short after enough cycles to cover `n` at the
    observed density -- a rule bounded by its own COUNT or UNTIL, or a case
    my reasoning above does not cover) returns None and stays unrecorded.

    Either way the answer is corroborated at its own reach: `du_expand` asks
    dateutil for `n` occurrences with no horizon of mine at all.
    """
    cyc = _cycle_days(alt_rule)
    occ = expand(alt_rule, ds, horizon=ds + timedelta(days=cyc), limit=max(n, 1) * 4)
    if len(occ) >= n:
        answer = occ[:n]
    elif not occ:
        answer = []
    else:
        cycles = math.ceil(n / len(occ)) + 1
        occ = expand(alt_rule, ds, horizon=ds + timedelta(days=cyc * cycles),
                     limit=n * 4)
        if len(occ) < n:
            return None
        answer = occ[:n]
    theirs = du_expand(alt_rule, ds, n)
    if isinstance(theirs, str):
        return None
    if [fmt(x) for x in theirs[:n]] != [fmt(x) for x in answer]:
        return None
    return answer


def _dtstart_fill_reading(rule, ds, n, horizon=None):
    """The first `n` occurrences under the DTSTART-fill reading, or None.

    Two conditions beyond the shape, both deliberately conservative:

      * the rewritten rule must survive the same corroboration the corpus
        demands of everything else -- naive and dateutil agreeing on it. An
        alternative reading recorded on one expander's word would be weaker
        evidence than the `expect` it sits next to.
      * a list shorter than `n` must be explained rather than dropped. The
        DTSTART-fill reading fires strictly less often, so it can run out
        inside the expander's horizon where `expect` did not -- and that
        shortfall may be a property of the horizon (mine) or of the rule
        (the reading's own answer). `_short_of_horizon` separates the two
        over a full Gregorian cycle. Until finding 053 this function simply
        returned None on a short list, on the stated grounds that "an
        adapter, which has no horizon, would not produce it" -- false on
        FREQ=YEARLY;BYWEEKNO=53, where ical4j and dmfs return exactly the
        short list (finding 052).
    """
    if n == 0:
        return None
    alt_rule = _dtstart_fill_rewrite(rule, ds)
    if alt_rule is None:
        return None
    if compare(alt_rule, ds, n) is not None:
        return None
    occ = expand(alt_rule, ds, horizon=horizon, limit=n)[:n]
    if len(occ) != n:
        occ = _short_of_horizon(alt_rule, ds, n)
        if occ is None:
            return None
    return [fmt(x) for x in occ]


def _week_based_year_reading(rule, ds, n, fill=False, horizon=None):
    """The first `n` occurrences under the `week_based_year` reading, or None
    when the question does not arise for this rule.

    Finding 059. 3.3.10 says BYWEEKNO selects "weeks of the year" numbered as
    in ISO 8601, and that "a week is defined as a seven day period". Under
    FREQ=YEARLY it never says which *period* a day of such a week belongs to
    when the week straddles 1 January -- the calendar year the day sits in, or
    the year that owns the week. The corpus's `expect` takes the first; four
    independent lineages (ical4j, dmfs lib-recur, libical, and sabre where it
    is legible) take the second.

    Recorded like `first_period_truncated` rather than like `dtstart_fill`:
    it is an expander mode, not a source-to-source rewrite, so `dateutil`
    cannot be asked to corroborate it -- `dateutil` *is* one of the two
    expanders that produce `expect`.

    With `fill`, the reading is composed with `dtstart_fill`. The two are
    independent questions that happen to meet on BYWEEKNO rules with no BYDAY,
    and on those rules neither alone reproduces what the field returns.
    """
    if n == 0:
        return None
    if not rule.startswith("FREQ=YEARLY") or "BYWEEKNO=" not in rule:
        return None
    alt_rule = rule
    if fill:
        alt_rule = _dtstart_fill_rewrite(rule, ds)
        if alt_rule is None:
            return None
    occ = expand(alt_rule, ds, horizon=horizon, limit=n, week_based_year=True)[:n]
    if len(occ) != n:
        return None
    return [fmt(x) for x in occ]


def _readings(rule, ds, n, expect, horizon=None):
    """Every alternative reading of 3.3.10 that gives this case a *different*
    answer, by name. Empty dict means the readings coincide here (or none of
    them applies), which is the common case and is not the same as the question
    not existing.

    `horizon` is threaded through to the expander unchanged and defaults to
    None, which is the 30-year window every corpus row was built with. It
    exists for `conformance/reading_past_bound.py`, which has to compute the
    same readings further out than the corpus ever asked for them, and must
    compute them with the function that wrote them rather than with a copy
    (standing rule 57). Passing it does not change any corpus value: the
    builder never sets it."""
    out = {}
    for name, alt in (("first_period_truncated",
                       _other_reading(rule, ds, n, horizon)),
                      ("dtstart_fill",
                       _dtstart_fill_reading(rule, ds, n, horizon)),
                      ("week_based_year",
                       _week_based_year_reading(rule, ds, n, horizon=horizon)),
                      ("week_based_year+dtstart_fill",
                       _week_based_year_reading(rule, ds, n, fill=True,
                                                horizon=horizon))):
        if alt is not None and alt != expect:
            # The composed reading is only worth its own name when composing
            # actually changed something; on a rule where `dtstart_fill` does
            # not apply, or where it applies but the week-based-year period is
            # what does all the work, it would otherwise be recorded twice
            # under two names.
            if name == "week_based_year+dtstart_fill" and alt in out.values():
                continue
            out[name] = alt
    return out


def record(rule, ds, cell, agreed, disputed, seen):
    """Adjudicate one (rule, DTSTART) and file it. Returns False if a duplicate."""
    if (rule, ds) in seen:
        return False
    seen.add((rule, ds))
    synced = is_synchronized(rule, ds)
    # RFC 5545 3.3.10 validity is a separate dimension from DTSTART
    # synchronization and from implementation agreement. It is written here,
    # at generation time, so an ordinary rebuild cannot drop it.
    # See tests/test_validity.py.
    rule_valid = validity.is_valid(rule)
    # Which cells of 3.3.10's BYxxx/FREQ table this case exercises. Recorded
    # for every case, random or systematic, so coverage is measurable from the
    # corpus alone. See src/coverage.py and tests/test_coverage.py.
    cells = ["/".join(c) for c in coverage.classify(rule)]
    # Which branches of 3.3.10's RECUR ABNF this case takes -- the second,
    # orthogonal coverage axis. classify() raises if the rule is outside the
    # grammar, which would itself be a finding. See src/grammar.py.
    branches = sorted(grammar.classify(rule))
    diff = compare(rule, ds, N)
    if diff is None:
        occ = expand(rule, ds, horizon=_horizon(ds), limit=N)[:N]
        exp = [fmt(x) for x in occ]
        # Does `expect` depend on which reading of 3.3.10 the builder took?
        # Both expanders agreeing does not answer this: they share the
        # reading. `alts` maps each rival reading that would give a *different*
        # answer to that answer, so a consumer can see both rather than inherit
        # mine silently. Two are known: the first-period question (finding 018)
        # and the DTSTART-fill question (finding 024).
        alts = _readings(rule, ds, len(occ), exp, horizon=_horizon(ds))
        agreed.append({
            "rrule": rule,
            "dtstart": fmt(ds),
            "expect": exp,
            "expect_bound": expect_bound(rule, ds, occ),
            "reading_dependent": bool(alts),
            "dtstart_synchronized": synced,
            "rule_valid": rule_valid,
            "cells": cells,
            "branches": branches,
            "systematic_for": cell,
            "corroborated_by": ["naive-bruteforce", "python-dateutil-2.9.0"],
        })
        if alts:
            agreed[-1]["reading_alternatives"] = alts
    else:
        mine, theirs = diff
        disputed.append({
            "rrule": rule,
            "dtstart": fmt(ds),
            "dtstart_synchronized": synced,
            "rule_valid": rule_valid,
            "cells": cells,
            "branches": branches,
            "systematic_for": cell,
            "naive": mine if isinstance(mine, str) else [fmt(x) for x in mine],
            "dateutil": theirs if isinstance(theirs, str) else [fmt(x) for x in theirs],
        })
    return True


def main(seeds=(7, 11, 13, 17, 23), per=300, out=None, systematic=True):
    """Build a corpus into `out`.

    `systematic=False` skips the three enumerations below. They are ~97% of the
    committed corpus's 3846 cases and essentially all of a full build's ~12
    minutes, so a test that only needs to watch a case travel through this
    function can turn them off and finish in seconds. Nothing that produces the
    committed corpus may pass it: the default is True and the CLI never sets it.
    """
    out = out or CORPUS
    os.makedirs(out, exist_ok=True)
    agreed, disputed, seen = [], [], set()
    if systematic:
        # Systematic first: one case per permitted cell of the 3.3.10 table, so
        # what the corpus covers does not depend on which seeds were used.
        for cell, rule, ds in enumerate_cells.cases():
            record(rule, ds, "/".join(cell), agreed, disputed, seen)
        # ...and one per branch of the RECUR ABNF. The table says nothing about
        # UNTIL, COUNT, INTERVAL, WKST, the explicit '+' sign or list arity, and
        # before this the corpus had never exercised any of them.
        for feature, rule, ds in enumerate_branches.cases():
            record(rule, ds, "branch:" + feature, agreed, disputed, seen)
        # ...and one per *realizable pair* of branches. Both single-branch models
        # read 100%, and a presence measure that is saturated has stopped
        # measuring: the bugs this corpus has caught (findings 001, 004) were
        # interactions between parts, not parts appearing at all. See src/pairs.py.
        for pair, rule, ds in pairs.cases():
            record(rule, ds, "pair:" + pair, agreed, disputed, seen)
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(per):
            rule, base = gen(rng), rng.choice(DTSTARTS)
            for ds in dtstart_variants(rule, base):
                record(rule, ds, None, agreed, disputed, seen)

    agreed.sort(key=lambda c: (c["rrule"], c["dtstart"]))
    disputed.sort(key=lambda c: (c["rrule"], c["dtstart"]))
    meta = {
        "about": "Cross-implementation RFC 5545 RRULE conformance corpus.",
        "horizon_days": naive.HORIZON_DAYS,
        "occurrences_per_case": N,
        "cases": len(agreed),
    }
    json.dump({"meta": meta, "cases": agreed}, open(os.path.join(out, "corroborated.json"), "w"),
              indent=1, sort_keys=True)
    # Hand adjudications survive regeneration: they live in their own file and
    # are re-attached here by rule+DTSTART.
    adj = {}
    if os.path.exists(os.path.join(CORPUS, "adjudications.json")):
        adj = json.load(open(os.path.join(CORPUS, "adjudications.json")))["cases"]
    hit = 0
    for c in disputed:
        a = adj.get("%s|%s" % (c["rrule"], c["dtstart"]))
        if a:
            c["adjudication"] = a
            hit += 1
    json.dump({"meta": {"about": "Cases where the two expanders disagree. "
                                 "Unadjudicated unless carrying an "
                                 "'adjudication' key (see corpus/"
                                 "adjudications.json and findings/).",
                        "adjudicated": hit, "cases": len(disputed)},
               "cases": disputed}, open(os.path.join(out, "disputed.json"), "w"),
              indent=1, sort_keys=True)
    # Coverage against RFC 5545 3.3.10's own BYxxx/FREQ table. N/A cells are
    # excluded: the spec forbids them, so an empty one is conformance.
    all_cells = ["/".join(c) for c in coverage.cells()]
    hits = {c: 0 for c in all_cells}
    for c in agreed + disputed:
        for k in c["cells"]:
            if k in hits:
                hits[k] += 1
    missing = sorted(k for k, v in hits.items() if v == 0)
    json.dump({"meta": {"about": "Coverage of RFC 5545 3.3.10's BYxxx/FREQ "
                                 "table (N/A cells excluded by construction).",
                        "cells": len(all_cells),
                        "covered": len(all_cells) - len(missing),
                        "uncovered": len(missing)},
               "uncovered": missing,
               "cases_per_cell": hits},
              open(os.path.join(out, "coverage.json"), "w"), indent=1, sort_keys=True)
    # Coverage against 3.3.10's other printed model, the RECUR ABNF.
    feats = grammar.features()
    bhits = {f: 0 for f in feats}
    for c in agreed + disputed:
        for k in c["branches"]:
            if k in bhits:
                bhits[k] += 1
    bmiss = sorted(k for k, v in bhits.items() if v == 0)
    # Branches that need a DATE-valued DTSTART are covered by the separate
    # DATE corpus (src/datevalue_cases.py), which the main generator cannot
    # produce because `compare` adjudicates against dateutil, and dateutil has
    # no DATE value type. A branch covered there is covered conformantly; only
    # what is left counts as covered_nonconformantly.
    try:
        date_branches = set(json.load(open(os.path.join(CORPUS, "date-value-type.json")))["branches"])
    except FileNotFoundError:
        date_branches = set()
    nonconf = sorted(enumerate_branches.NEEDS_DATE_DTSTART - set(bmiss)
                     - date_branches)
    json.dump({"meta": {"about": "Branch coverage of RFC 5545 3.3.10's RECUR "
                                 "ABNF (src/grammar.py).",
                        "branches": len(feats),
                        "covered": len(feats) - len(bmiss),
                        "uncovered": len(bmiss),
                        "covered_nonconformantly": len(nonconf)},
               "uncovered": bmiss,
               "covered_nonconformantly": nonconf,
               "cases_per_branch": bhits},
              open(os.path.join(out, "grammar-coverage.json"), "w"), indent=1,
              sort_keys=True)
    # Interaction coverage: pairs of ABNF branches. Pairs no conformant rule
    # can take are excluded by construction and reported with the reason, so
    # "unrealizable" never silently absorbs a gap. src/pairs.py.
    realizable, unrealizable = pairs.report()
    seen_pairs = set()
    for c in agreed + disputed:
        seen_pairs |= set(itertools.combinations(sorted(c["branches"]), 2))
    try:
        for c in json.load(open(os.path.join(CORPUS, "date-value-type.json")))["cases"]:
            seen_pairs |= set(itertools.combinations(sorted(c["branches"]), 2))
    except (FileNotFoundError, KeyError):
        pass
    pmiss = sorted(p for p in realizable if p not in seen_pairs)
    reasons = {}
    for p, why in unrealizable.items():
        reasons.setdefault(why, []).append(list(p))
    json.dump({"meta": {"about": "Pairwise coverage of RFC 5545 3.3.10's "
                                 "RECUR ABNF branches (src/pairs.py).",
                        "branches": len(feats),
                        "pairs": len(realizable) + len(unrealizable),
                        "realizable": len(realizable),
                        "covered": len(realizable) - len(pmiss),
                        "uncovered": len(pmiss),
                        "unrealizable": len(unrealizable)},
               "uncovered": [list(p) for p in pmiss],
               "unrealizable_by_reason": {k: sorted(v)
                                          for k, v in sorted(reasons.items())}},
              open(os.path.join(out, "pair-coverage.json"), "w"), indent=1, sort_keys=True)
    print("pairs realizable=%d covered=%d uncovered=%d unrealizable=%d" % (
        len(realizable), len(realizable) - len(pmiss), len(pmiss),
        len(unrealizable)))
    print("branches covered=%d/%d (%d non-conformantly) uncovered=%s" % (
        len(feats) - len(bmiss), len(feats), len(nonconf), bmiss or "none"))
    print("corroborated=%d disputed=%d (of %d generated)" % (len(agreed), len(disputed), len(seen)))
    print("cells covered=%d/%d uncovered=%s" % (len(all_cells) - len(missing),
                                                len(all_cells), missing or "none"))


if __name__ == "__main__":
    # --out DIR writes the rebuild somewhere else, which is how
    # tools/verify_corpus.py checks that the committed corpus reproduces.
    argv = sys.argv[1:]
    dest = None
    if "--out" in argv:
        dest = argv[argv.index("--out") + 1]
    # --occurrences N builds a corpus at a different bound. The committed
    # corpus is N=25 and nothing here changes that default; the flag exists so
    # that raising the bound can be *costed and compared* against the
    # committed build rather than argued about. See tools/cost_bound.py and
    # rule 58: agreement inside the bound is not agreement.
    if "--occurrences" in argv:
        if "--out" not in argv:
            sys.exit("--occurrences requires --out: it must not overwrite the "
                     "committed N=%d corpus" % N)
        N = int(argv[argv.index("--occurrences") + 1])
    # --horizon-days D builds at a different horizon, under the same rule: it
    # must not overwrite the committed build either. The two flags exist to be
    # used *together*, because finding 062 showed raising the bound converts
    # count-bounded cases into horizon-bounded ones and finding 064 showed a
    # longer horizon converts them back. Neither number can be chosen alone.
    if "--horizon-days" in argv:
        if "--out" not in argv:
            sys.exit("--horizon-days requires --out: it must not overwrite the "
                     "committed %d-day corpus" % naive.HORIZON_DAYS)
        naive.HORIZON_DAYS = int(argv[argv.index("--horizon-days") + 1])
    sys.exit(main(out=dest))
