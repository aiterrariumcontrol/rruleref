"""Interaction coverage: pairs of RECUR grammar branches, not branches alone.

src/enumerate_cells.py and src/enumerate_branches.py each answer a *presence*
question -- does some case in the corpus reach this cell, does some case reach
this branch -- and they answer it independently. Both now read 100%, which is
exactly the point at which the measurement stops being informative: the
recurrence bugs this corpus has actually caught were interactions. Finding 001
was BYSETPOS *under* WEEKLY. Finding 004 was BYSETPOS *with* a first period the
rule truncates. Neither is visible to a model that only asks whether BYSETPOS
appears somewhere.

So the model here is the pair. For the 79 branches of 3.3.10's RECUR ABNF there
are C(79,2) = 3081 unordered pairs, and a case covers a pair when its branch
set (src/grammar.py `classify`) contains both. Most pairs are not realizable --
`FREQ=DAILY` and `FREQ=WEEKLY` are alternatives of one choice; BYWEEKNO is
YEARLY-only, so it shares no rule with `FREQ|freq|MONTHLY`; UNTIL and COUNT
MUST NOT occur in the same recur. Those are not gaps, and the report must not
count them as gaps.

Realizability is therefore decided by *construction*, and the construction is
checked rather than trusted: a pair is realizable when this module can emit a
rule that (a) RFC 5545 3.3.10's own ABNF parses, (b) src/validity.py accepts
against the MUST sentences of 3.3.10, and (c) `classify` reports as taking both
branches. A pair this module fails to realize is reported with the reason it
failed, so "unrealizable" stays distinguishable from "my synthesizer is too
weak" -- see `report()` and tests/test_pairs.py.
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import grammar
import coverage
import validity
import enumerate_branches as eb

#: Frequencies at which a rule part may appear at all. For the BYxxx parts
#: this is read off 3.3.10's table -- an N/A cell says the part MUST NOT be
#: used at that FREQ -- rather than restated here. The rest are unrestricted
#: by the table, which has no column for them.
def allowed_freqs(part, path=grammar.RFC):
    freqs, parts, t = coverage.table(path)
    if part in parts:
        return [f for f in freqs if t[(part, f)] != "N/A"]
    return list(freqs)


#: Rule-part order in the emitted rule. FREQ first because 3.3.10's ABNF
#: permits any order but every worked example in the RFC leads with it.
ORDER = ["FREQ", "UNTIL", "COUNT", "INTERVAL", "BYSECOND", "BYMINUTE",
         "BYHOUR", "BYDAY", "BYMONTHDAY", "BYYEARDAY", "BYWEEKNO", "BYMONTH",
         "BYSETPOS", "WKST"]

ARITY_ONE = "recur|recur/1|repeat=0"
ARITY_MANY = "recur|recur/1|repeat=1+"


def choice_point(feature):
    """The (context, rule, path) the branch is an alternative *at*.

    Two branches sharing a choice point are alternatives of one `/`, `[x]` or
    `*(x)` in the ABNF: `byseclist/1` is either repeated or it is not. Where
    the ABNF can reach that node more than once inside a single rule part --
    `weekday` inside `bywdaylist` -- both branches are still realizable, and
    `build` realizes them (`BYDAY=SU,MO`), so this is a label for a synthesis
    failure and never a reason to skip trying.
    """
    # A feature id is `<context>|<rule><path>|<choice>`, so the middle field
    # already carries the path and identifies the node on its own.
    ctx, node, _choice = feature.split("|")
    return ctx, node


def _why_not(targets):
    a, b = sorted(targets)[:2]
    if len(targets) == 2 and choice_point(a) == choice_point(b):
        return "same-choice-point"
    return "not-co-synthesizable"


class Unrealizable(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def build(features, path=grammar.RFC, _cache={}):
    """(rule, dtstart) exercising every feature in `features`.

    Raises Unrealizable, carrying a reason, when no rule can be constructed --
    or when the one constructed fails its own check.
    """
    g = _cache.get(path)
    if g is None:
        g = _cache[path] = grammar.grammar(path)
    part_rule = g["recur-rule-part"]

    features = set(features)
    if features & eb.NEEDS_DATE_DTSTART:
        raise Unrealizable("needs-date-dtstart")
    arity = features & {ARITY_ONE, ARITY_MANY}
    if arity == {ARITY_ONE, ARITY_MANY}:
        raise Unrealizable("arity-conflict")

    want = {}
    for f in features - arity:
        want.setdefault(eb._part_of(f), set()).add(f)

    # FREQ. A FREQ branch pins it; otherwise take a frequency every part is
    # permitted at, preferring the host each part is enumerated at alone.
    ok = set(validity.FREQS)
    for part in want:
        ok &= set(allowed_freqs(part, path))
    if not ok:
        raise Unrealizable("no-common-freq")
    pinned = [f.split("|")[2] for f in want.get("FREQ", ())
              if f.split("|")[1] == "freq"]
    if pinned:
        if len(set(pinned)) > 1 or pinned[0] not in ok:
            raise Unrealizable("no-common-freq")
        candidates = [pinned[0]]
    else:
        # Every permitted frequency is tried, not just a preferred one. A
        # signed BYDAY with a BYSECOND is realizable -- at MONTHLY -- and
        # would be reported as a conformance gap if the host were chosen
        # greedily from the part enumerated first. Order only decides which
        # of several working rules is recorded.
        prefer = [eb.HOST[p][0] for p in ORDER if p in want] + list(validity.FREQS)
        candidates = [f for f in dict.fromkeys(prefer) if f in ok]

    texts0 = {}
    for part, targets in want.items():
        text, reached = eb._synth(part_rule, frozenset(targets),
                                  "recur-rule-part", "", None, g)
        if reached != frozenset(targets):
            raise Unrealizable(_why_not(targets))
        texts0[part] = text

    why = "no-common-freq"
    for freq in candidates:
        texts = dict(texts0)
        texts["FREQ"] = "FREQ=" + freq

        # Companions the spec requires, added only when the pair has not
        # already supplied one. BYSETPOS "MUST only be used in conjunction
        # with another BYxxx rule part"; WKST is inert without one, so it gets
        # a companion for the same reason the single-branch enumerator does.
        if ARITY_ONE not in arity:
            has_by = any(p.startswith("BY") and p != "BYSETPOS" for p in texts)
            if "BYSETPOS" in texts and not has_by:
                extra = eb.HOST["BYSETPOS"][1] if freq in ("MONTHLY", "YEARLY") \
                    else "BYHOUR=9"
                texts.setdefault(extra.split("=")[0], extra)
            if "WKST" in texts and len(texts) == 2:
                texts.setdefault("BYDAY", "BYDAY=MO,TH")

        rule = ";".join(texts[p] for p in ORDER if p in texts)
        if ARITY_ONE in arity and len(texts) != 1:
            raise Unrealizable("arity-conflict")
        if ARITY_MANY in arity and len(texts) < 2:
            rule += ";INTERVAL=2"

        ok_here, why = _check(rule, features, path)
        if ok_here:
            return rule, eb.ANCHOR[freq]
    raise Unrealizable(why)


def _check(rule, features, path):
    """(True, None) if `rule` is valid, grammatical, and takes `features`."""
    bad = validity.violations(rule)
    if bad:
        return False, "invalid:" + ",".join(sorted({v["rule"] for v in bad}))
    try:
        taken = grammar.classify(rule, path)
    except ValueError:
        return False, "ungrammatical"
    if not features <= taken:
        return False, "not-taken"
    return True, None


def all_pairs(path=grammar.RFC):
    """Every unordered branch pair, each as a sorted tuple.

    Sorted, because a pair has to mean the same thing here and where corpus
    cases are counted: a case covers `(a, b)` when its branch set contains
    both, and nothing about the pair depends on which branch came first in
    `features()`.
    """
    return [tuple(sorted(p))
            for p in itertools.combinations(sorted(grammar.features(path)), 2)]


def report(path=grammar.RFC):
    """(realized, unrealized) -- {pair: (rule, dtstart)} and {pair: reason}."""
    realized, unrealized = {}, {}
    for a, b in all_pairs(path):
        try:
            realized[(a, b)] = build((a, b), path)
        except Unrealizable as e:
            unrealized[(a, b)] = e.reason
    return realized, unrealized


def cases(path=grammar.RFC):
    """[(pair-id, rrule, dtstart)] -- one rule per realizable branch pair."""
    realized, _ = report(path)
    return [("%s + %s" % p, r, ds) for p, (r, ds) in sorted(realized.items())]


if __name__ == "__main__":
    realized, unrealized = report()
    print("pairs=%d realized=%d unrealized=%d"
          % (len(realized) + len(unrealized), len(realized), len(unrealized)))
    from collections import Counter
    for reason, n in Counter(unrealized.values()).most_common():
        print("  %-40s %d" % (reason, n))
