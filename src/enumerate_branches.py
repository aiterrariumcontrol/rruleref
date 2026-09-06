"""Systematic cases: at least one per branch of RFC 5545 3.3.10's RECUR ABNF.

src/enumerate_cells.py covers the *semantic* model 3.3.10 prints -- the
BYxxx/FREQ table. That table has no column for INTERVAL, WKST, COUNT, UNTIL,
the explicit `+` sign, or list arity, so the corpus could be 57/57 on it and
still never have terminated a rule. Measuring the corpus against the grammar
(src/grammar.py) showed exactly that: 61 of 79 branches, with UNTIL, COUNT,
every `plus`, four WKST weekdays, and single-element BYSECOND/BYMINUTE/BYHOUR
lists never exercised once in 2,598 cases.

Cases are *synthesized from the grammar*, not transcribed: `_synth` walks the
parsed ABNF choosing, at each choice point, the branch that can reach the
target feature and otherwise the shortest one. So the case for
`BYMONTHDAY|monthdaynum/0/0|plus` is whatever the grammar says a BYMONTHDAY
with an explicit plus sign looks like, and adding a branch to the grammar adds
a case rather than silently going uncovered.

Two things the grammar cannot supply, and they are tables here:

  * `VALUE` -- the grammar says `monthnum = 1*2DIGIT ;1 to 12`; the range is a
    prose comment. Values are picked once, in range, and shared with
    enumerate_cells.py's choices where they overlap.
  * `HOST` -- a rule part is not usable at every frequency (BYWEEKNO is
    YEARLY-only; BYSETPOS needs a companion). The host FREQ and companions
    make the synthesized part into a rule that src/validity.py accepts, which
    is asserted in tests/test_grammar.py rather than assumed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from datetime import datetime
import grammar

#: Concrete values for the numeric leaves the ABNF only bounds in a comment.
VALUE = {
    "seconds": "15", "minutes": "30", "hour": "9",
    "ordwk": "2", "ordmoday": "15", "ordyrday": "60",
    "weeknum": "20", "monthnum": "3",
    "DIGIT": "3",
}

#: Where one production is reached from two rule parts and the range differs.
#: `setposday = yeardaynum`, but a set of three weekdays has no 60th member.
VALUE_IN = {("BYSETPOS", "ordyrday"): "1"}

#: Literal leaves defined outside this ABNF block (3.3.4 / 3.3.5). Both bound
#: the rule a few days after the DAILY anchor, so an UNTIL case actually
#: terminates within the eight occurrences the corpus records: a branch that
#: is taken but never changes the answer is coverage on paper only.
EXTERNAL = {"date": "20260305", "date-time": "20260305T090000"}

#: Branches no case in this corpus can take *conformantly*. 3.3.10: "The value
#: of the UNTIL rule part MUST have the same value type as the 'DTSTART'
#: property." Every DTSTART here is a DATE-TIME, so a DATE-valued UNTIL
#: violates that MUST no matter which rule it is attached to. The case is
#: still generated and adjudicated -- what the two expanders do with it is
#: data -- but it is reported separately rather than counted as covered.
#: Covered conformantly since 2026-09-06 by the DATE-valued corpus,
#: `src/datevalue_cases.py` / `corpus/date-value-type.json`, which the main
#: generator cannot produce because dateutil has no DATE value type.
#:
#: (The neighbouring question, whether a floating DTSTART may take
#: `UNTIL=...Z`, is *not* open: RFC 5545 as printed says both "MUST also be
#: specified as a date with local time" and "If specified as a DATE-TIME
#: value, then it MUST be specified in a UTC time format", which no floating
#: DATE-TIME DTSTART can satisfy at once. Erratum 4414, verified, deletes the
#: second sentence. python-dateutil rejects the combination, which is the
#: corrected text's answer.)
NEEDS_DATE_DTSTART = {"UNTIL|enddate|date"}

#: (host FREQ, extra parts) making a synthesized rule part valid per 3.3.10.
HOST = {
    "FREQ":       ("DAILY",   ""),
    "UNTIL":      ("DAILY",   ""),
    "COUNT":      ("DAILY",   ""),
    "INTERVAL":   ("DAILY",   ""),
    "BYSECOND":   ("MINUTELY", ""),
    "BYMINUTE":   ("HOURLY",  ""),
    "BYHOUR":     ("DAILY",   ""),
    "BYDAY":      ("MONTHLY", ""),
    "BYMONTHDAY": ("MONTHLY", ""),
    "BYYEARDAY":  ("YEARLY",  ""),
    "BYWEEKNO":   ("YEARLY",  ""),
    "BYMONTH":    ("YEARLY",  ""),
    "BYSETPOS":   ("MONTHLY", "BYDAY=MO,WE,FR"),
    "WKST":       ("WEEKLY",  "BYDAY=MO,TH"),
}

#: DTSTART per host FREQ. Sub-daily hosts start where the naive brute force
#: reaches occurrence one quickly, for enumerate_cells.py's reason.
ANCHOR = {
    "SECONDLY": datetime(2026, 3, 2, 9, 30, 0),
    "MINUTELY": datetime(2026, 3, 2, 9, 30, 15),
    "HOURLY":   datetime(2026, 3, 2, 9, 30, 0),
    "DAILY":    datetime(2026, 3, 2, 9, 0, 0),
    "WEEKLY":   datetime(2026, 3, 2, 9, 0, 0),   # a Monday
    "MONTHLY":  datetime(2026, 3, 2, 9, 0, 0),
    "YEARLY":   datetime(2026, 3, 1, 9, 0, 0),   # day 60 of 2026
}


def _synth(node, target, rule, path, ctx, g):
    """(text, reached) for `node`, taking the branches that reach `target`.

    `target` is a set of feature ids (or None). `reached` is the subset of
    them the emitted text exercises. When no branch can reach any of them the
    shortest available branch is taken, so every call still produces a legal
    string.

    More than one target at a time is what src/pairs.py needs: a case for
    `BYDAY|weekdaynum/0|present` *and* `BYDAY|bywdaylist/1|repeat=1+` has to
    reach both inside one rule part. For a single target the result is
    unchanged -- a feature id names exactly one branch, so at most one
    alternative can ever reach it.
    """
    if target is None:
        target = frozenset()
    kind = node[0]
    if kind == "lit":
        return node[1], frozenset()
    if kind == "ref":
        name = node[1]
        if name in EXTERNAL:
            return EXTERNAL[name], frozenset()
        sub = g.get(name)
        if sub is None or grammar._is_leaf_rule(sub):
            return VALUE_IN.get((ctx, name), VALUE.get(name, VALUE["DIGIT"])), frozenset()
        return _synth(sub, target, name, "", ctx, g)
    if kind == "seq":
        out, got = [], frozenset()
        for i, b in enumerate(node[1]):
            # A target a child has already reached is dropped for later
            # siblings, so they take their own shortest branch: the case for
            # `BYDAY|weekday|MO` is `BYDAY=MO`, not a two-element list.
            t, r = _synth(b, target - got, rule, path + "/%d" % i, ctx, g)
            out.append(t)
            got |= r
        return "".join(out), got
    if kind == "alt":
        best = None
        for i, b in enumerate(node[1]):
            fid = grammar._fid(ctx, rule, path, grammar._lit_label(node, i))
            nctx = grammar._branch_ctx(rule, node, i) or ctx
            t, r = _synth(b, target, rule, path + "/%d" % i, nctx, g)
            hit = r | (target & {fid})
            if hit:
                return t, hit
            # A branch that cannot be taken conformantly is never the default;
            # otherwise the case for `recur-rule-part|UNTIL` would inherit
            # `enddate`'s DATE form and be non-conformant for a reason that
            # has nothing to do with the branch it was built for.
            if fid in NEEDS_DATE_DTSTART:
                continue
            if best is None or len(t) < len(best):
                best = t
        return best, frozenset()
    if kind == "opt":
        here = grammar._fid(ctx, rule, path, "present")
        t, r = _synth(node[1], target, rule, path + "/0", ctx, g)
        hit = r | (target & {here})
        if hit:
            return t, hit
        return "", target & {grammar._fid(ctx, rule, path, "absent")}
    if kind == "rep":
        one, r = _synth(node[3], target, rule, path + "/0", ctx, g)
        if grammar._is_leaf_rule(node):
            return one * max(1, node[1]), frozenset()
        many = grammar._fid(ctx, rule, path, "repeat=1+")
        want_many = target & {many}
        if not (want_many or r):
            return "", target & {grammar._fid(ctx, rule, path, "repeat=0")}
        # One repeat is enough for the `1+` branch. The repeated copy must
        # differ from the element before it, or the list carries a duplicate
        # rather than two members, so its numeric leaf is moved -- unless the
        # copy is there to reach a target of its own, in which case moving it
        # is exactly what must not happen. `BYDAY=SU,MO` reaches `weekday|SU`
        # in the head and `weekday|MO` in the tail; varying the tail would
        # turn it into `BYDAY=SU,TU` and silently lose the branch it was
        # built for.
        return (one if r else _vary(one)), r | want_many
    raise RuntimeError("unknown node %r" % (kind,))


WEEKDAYS = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]


def _vary(text):
    """Move a repeated element off its neighbour, so a two-element list has
    two members rather than the same one twice. Numbers step; a bare weekday
    steps through `weekday`'s own alternation."""
    import re
    m = re.search(r"(\d+)", text)
    if m:
        n = int(m.group(1))
        return text[:m.start(1)] + str(n + 1 if n < 9 else n - 1) + text[m.end(1):]
    m = re.search(r"(%s)$" % "|".join(WEEKDAYS), text)
    if m:
        return text[:m.start(1)] + WEEKDAYS[(WEEKDAYS.index(m.group(1)) + 1) % 7]
    return text


def _part_of(feature):
    """The recur-rule-part a feature belongs to, or None for `recur` itself.

    A feature id is `<context>|<rule><path>|<choice>`. Branches *of*
    `recur-rule-part` are the choice of part, so the part is the choice;
    branches of `recur` are the number of parts and belong to no single one.
    """
    ctx, rule, choice = feature.split("|")
    if rule == "recur-rule-part":
        return choice
    if rule == "recur" or rule.startswith("recur/"):
        return None
    return ctx


def cases(path=grammar.RFC):
    """[(feature, rrule, dtstart)] -- one rule per grammar branch, ordered."""
    g = grammar.grammar(path)
    part_rule = g["recur-rule-part"]
    out = []
    for feature in grammar.features(path):
        part = _part_of(feature)
        if part is None:
            # Branches of `recur` itself: the *number* of rule parts.
            one = "FREQ=DAILY"
            rule = one if feature.endswith("repeat=0") else one + ";INTERVAL=2"
            out.append((feature, rule, ANCHOR["DAILY"]))
            continue
        text, reached = _synth(part_rule, frozenset([feature]),
                               "recur-rule-part", "", None, g)
        freq, extra = HOST[part]
        if part == "FREQ":
            rule = text
            freq = text.split("=", 1)[1]
        else:
            rule = ";".join(x for x in ("FREQ=" + freq, text, extra) if x)
        out.append((feature, rule, ANCHOR[freq]))
    return out


if __name__ == "__main__":
    for feature, rule, ds in cases():
        print("%-46s %-46s DTSTART=%s" % (feature, rule, ds))
