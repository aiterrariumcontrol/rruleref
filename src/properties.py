"""Metamorphic conformance properties for RFC 5545 RRULE.

The corpus answers "what should this rule produce?" with expected values that
two independent expanders agreed on. That is useful and it is also limited:
a reader who wants to check a *third* implementation has to trust my expected
values, and every corpus case looks at one short window near DTSTART.

This module is the other half. A property is a relation between the outputs of
two rules -- not an expected value -- so it can be checked against any
implementation without taking anything from this repository on faith, and it
can be checked over years of output rather than eight occurrences.

Every property below carries the sentence of RFC 5545 it is derived from and
the line numbers of that sentence in the pinned text, so the derivation is
auditable rather than asserted. Two of them (P6, P7) are marked ``hedged``:
the spec's own wording is "generally", or the relation is my reading of a
sentence that does not state it outright. A hedged property that fails is a
question, not a defect report.

Bounding, and why it is recorded per check
------------------------------------------
Sub-daily frequencies emit hundreds of thousands of instances over a few
years, so every expansion is bounded by a horizon and an instance cap. A cap
is a property of my harness, not of the rule (standing rule 4). When either
side of a comparison hits its cap the two lists cover different spans of time
and a naive subset test would report failures that are pure truncation.
``_align`` therefore clips both sides to the last instant both are known to
have covered completely, and every result records ``bounded``.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage
import validity

FMT = "%Y%m%dT%H%M%S"
DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

#: Default bounds. Both are harness artifacts and are reported with results.
HORIZON_DAYS = 365 * 3
CAP = 3000


# --------------------------------------------------------------------------
# rule-part surgery
# --------------------------------------------------------------------------

def parts(rule):
    """RRULE string -> list of (NAME, value), order preserved."""
    out = []
    for tok in rule.split(";"):
        if not tok:
            continue
        k, _, v = tok.partition("=")
        out.append((k.upper(), v))
    return out


def unparse(ps):
    return ";".join("%s=%s" % (k, v) for k, v in ps)


def get(rule, name):
    for k, v in parts(rule):
        if k == name:
            return v
    return None


def drop(rule, *names):
    names = {n.upper() for n in names}
    return unparse([(k, v) for k, v in parts(rule) if k not in names])


def put(rule, name, value):
    """Set a part, replacing it in place if present, else appending."""
    ps = parts(rule)
    for i, (k, _) in enumerate(ps):
        if k == name:
            ps[i] = (name, value)
            return unparse(ps)
    return unparse(ps + [(name, value)])


def byxxx(rule):
    return [k for k, _ in parts(rule) if k.startswith("BY")]


# --------------------------------------------------------------------------
# bounded expansion
# --------------------------------------------------------------------------

class Bounded(object):
    """One expansion plus what bounded it."""

    __slots__ = ("times", "capped", "horizon")

    def __init__(self, times, capped, horizon):
        self.times = times
        self.capped = capped
        self.horizon = horizon

    @property
    def covered_to(self):
        """Last instant this expansion is known to have covered completely."""
        if self.capped:
            return self.times[-1] if self.times else self.horizon
        return self.horizon


def run(expander, rule, dtstart, horizon_days=HORIZON_DAYS, cap=CAP):
    horizon = dtstart + timedelta(days=horizon_days)
    times = expander(rule, dtstart, horizon, cap)
    return Bounded(times, len(times) >= cap, horizon)


def _align(a, b):
    """Clip two bounded expansions to a span both covered completely."""
    edge = min(a.covered_to, b.covered_to)
    bounded = a.capped or b.capped
    return ([t for t in a.times if t <= edge],
            [t for t in b.times if t <= edge], bounded)


# --------------------------------------------------------------------------
# properties
# --------------------------------------------------------------------------

PASS, FAIL, NA, ERROR = "pass", "fail", "n/a", "error"


def _r(status, **kw):
    kw["status"] = status
    return kw


def p1_ordered(exp, rule, dtstart, **kw):
    """P1. Occurrences are non-decreasing and none precedes DTSTART.

    Non-decreasing rather than strictly increasing on purpose: RFC 5545 does
    not define when two DATE-TIME values are duplicates, and a DST repeat can
    legitimately put two instances at the same local time (finding 006).
    """
    a = run(exp, rule, dtstart, **kw)
    bad = [i for i in range(1, len(a.times)) if a.times[i] < a.times[i - 1]]
    early = [t for t in a.times if t < dtstart]
    if bad or early:
        return _r(FAIL, bounded=a.capped, out_of_order=len(bad),
                  before_dtstart=len(early), n=len(a.times))
    return _r(PASS, bounded=a.capped, n=len(a.times),
              strict=all(a.times[i] > a.times[i - 1]
                         for i in range(1, len(a.times))))


p1_ordered.id = "P1"
p1_ordered.quote = ('The "DTSTART" property value always counts as the first '
                    "occurrence.")
p1_ordered.lines = "5545:2273-2274"
p1_ordered.hedged = False


def p2_count_prefix(exp, rule, dtstart, **kw):
    """P2. COUNT=n yields exactly the first n occurrences of the unbounded rule."""
    base = drop(rule, "COUNT", "UNTIL")
    full = run(exp, base, dtstart, **kw)
    for n in (1, 3, 8):
        if not full.capped and len(full.times) < n:
            break
        got = run(exp, put(base, "COUNT", str(n)), dtstart, **kw)
        want = full.times[:n]
        if got.times != want:
            return _r(FAIL, count=n, bounded=full.capped,
                      got=[t.strftime(FMT) for t in got.times[:10]],
                      want=[t.strftime(FMT) for t in want[:10]], base=base)
    return _r(PASS, bounded=full.capped)


p2_count_prefix.id = "P2"
p2_count_prefix.quote = ("The COUNT rule part defines the number of "
                         "occurrences at which to range-bound the recurrence.")
p2_count_prefix.lines = "5545:2272-2274"
p2_count_prefix.hedged = False


def p3_until_truncates(exp, rule, dtstart, **kw):
    """P3. UNTIL=u yields exactly the unbounded occurrences at or before u.

    "bounds the recurrence rule in an inclusive manner" -- so the boundary
    instant itself is in, which is why one probe is placed exactly on an
    occurrence and one a second earlier.
    """
    base = drop(rule, "COUNT", "UNTIL")
    full = run(exp, base, dtstart, **kw)
    if len(full.times) < 4:
        return _r(NA, reason="fewer than 4 occurrences to bound")
    probes = [full.times[3], full.times[3] - timedelta(seconds=1)]
    for u in probes:
        got = run(exp, put(base, "UNTIL", u.strftime(FMT)), dtstart, **kw)
        want = [t for t in full.times if t <= u]
        if got.times != want:
            return _r(FAIL, until=u.strftime(FMT), bounded=full.capped,
                      got=[t.strftime(FMT) for t in got.times[:10]],
                      want=[t.strftime(FMT) for t in want[:10]], base=base)
    return _r(PASS, bounded=full.capped)


p3_until_truncates.id = "P3"
p3_until_truncates.quote = ("The UNTIL rule part defines a DATE or DATE-TIME "
                            "value that bounds the recurrence rule in an "
                            "inclusive manner.")
p3_until_truncates.lines = "5545:2255-2259"
p3_until_truncates.hedged = False


def p4_setpos_subset(exp, rule, dtstart, **kw):
    """P4. BYSETPOS selects from the set the rest of the rule specifies."""
    if get(rule, "BYSETPOS") is None:
        return _r(NA, reason="no BYSETPOS")
    base = drop(rule, "BYSETPOS")
    if not validity.is_valid(base):
        return _r(NA, reason="rule without BYSETPOS is not valid")
    a = run(exp, rule, dtstart, **kw)
    b = run(exp, base, dtstart, **kw)
    ta, tb, bounded = _align(a, b)
    extra = sorted(set(ta) - set(tb))
    if extra:
        return _r(FAIL, bounded=bounded, base=base, n_extra=len(extra),
                  extra=[t.strftime(FMT) for t in extra[:10]])
    return _r(PASS, bounded=bounded, n=len(ta))


p4_setpos_subset.id = "P4"
p4_setpos_subset.quote = ("The BYSETPOS rule part specifies a COMMA-separated "
                          "list of values that corresponds to the nth "
                          "occurrence within the set of recurrence instances "
                          "specified by the rule.")
p4_setpos_subset.lines = "5545:2364-2366"
p4_setpos_subset.hedged = False


def _wkst_significant(rule):
    """The two situations RFC 5545 names as making WKST significant."""
    freq = get(rule, "FREQ")
    interval = int(get(rule, "INTERVAL") or "1")
    if freq == "WEEKLY" and interval > 1 and get(rule, "BYDAY") is not None:
        return True
    if freq == "YEARLY" and get(rule, "BYWEEKNO") is not None:
        return True
    return False


def p5_wkst_inert(exp, rule, dtstart, **kw):
    """P5. Outside the two situations the RFC names, WKST changes nothing.

    The RFC states where WKST *is* significant and does not add "and nowhere
    else"; treating the list as exhaustive is a reading, but it is the reading
    the sentence invites, and an implementation for which WKST matters
    elsewhere is at minimum surprising.
    """
    if _wkst_significant(rule):
        return _r(NA, reason="WKST is significant here by the RFC's own text")
    base = drop(rule, "WKST")
    ref = None
    for d in DAYS:
        out = run(exp, put(base, "WKST", d), dtstart, **kw)
        if ref is None:
            ref = (d, out.times)
        elif out.times != ref[1]:
            i = next((j for j in range(min(len(out.times), len(ref[1])))
                      if out.times[j] != ref[1][j]), min(len(out.times), len(ref[1])))
            return _r(FAIL, bounded=out.capped, wkst_a=ref[0], wkst_b=d,
                      first_diff_index=i, base=base,
                      a=[t.strftime(FMT) for t in ref[1][max(0, i - 1):i + 3]],
                      b=[t.strftime(FMT) for t in out.times[max(0, i - 1):i + 3]])
    return _r(PASS, n=len(ref[1]))


p5_wkst_inert.id = "P5"
p5_wkst_inert.quote = ('[WKST] is significant when a WEEKLY "RRULE" has an '
                       "interval greater than 1, and a BYDAY rule part is "
                       "specified.  This is also significant when in a YEARLY "
                       '"RRULE" when a BYWEEKNO rule part is specified.')
p5_wkst_inert.lines = "5545:2349-2362"
p5_wkst_inert.hedged = True


def p6_limit_superset(exp, rule, dtstart, **kw):
    """P6. Dropping a part the RFC's table marks Limit cannot lose occurrences.

    Hedged: the prose says such parts "generally reduce or limit" the number
    of occurrences. The table classification itself is not hedged, but the
    set-inclusion reading of it is mine.
    """
    freq = get(rule, "FREQ")
    base = drop(rule, "COUNT", "UNTIL")
    limits = [p for p in byxxx(base) if coverage._plain(p, freq) == "Limit"]
    if not limits:
        return _r(NA, reason="no Limit part for this FREQ")
    a = run(exp, base, dtstart, **kw)
    for p in limits:
        wider = drop(base, p)
        if not validity.is_valid(wider):
            continue
        b = run(exp, wider, dtstart, **kw)
        ta, tb, bounded = _align(a, b)
        lost = sorted(set(ta) - set(tb))
        if lost:
            return _r(FAIL, dropped=p, bounded=bounded, base=base,
                      n_lost=len(lost),
                      lost=[t.strftime(FMT) for t in lost[:10]])
    return _r(PASS, checked=limits, bounded=a.capped)


p6_limit_superset.id = "P6"
p6_limit_superset.quote = ("BYxxx rule parts for a period of time that is the "
                           "same or greater than the frequency generally "
                           "reduce or limit the number of occurrences of the "
                           "recurrence generated.")
p6_limit_superset.lines = "5545:2395-2398"
p6_limit_superset.hedged = True


def p7_interval_subset(exp, rule, dtstart, **kw):
    """P7. INTERVAL=k selects periods; it cannot invent occurrences.

    Excluded when BYSETPOS is present: the RFC says BYSETPOS operates on "one
    interval of the recurrence rule" and never says whether that is one FREQ
    period or k of them, so the two rules are not comparable.
    """
    if get(rule, "BYSETPOS") is not None:
        return _r(NA, reason="BYSETPOS interval scope is undefined")
    base = drop(rule, "COUNT", "UNTIL", "INTERVAL")
    a = run(exp, base, dtstart, **kw)
    for k in (2, 3):
        b = run(exp, put(base, "INTERVAL", str(k)), dtstart, **kw)
        ta, tb, bounded = _align(a, b)
        extra = sorted(set(tb) - set(ta))
        if extra:
            return _r(FAIL, interval=k, bounded=bounded, base=base,
                      n_extra=len(extra),
                      extra=[t.strftime(FMT) for t in extra[:10]])
    return _r(PASS, bounded=a.capped)


p7_interval_subset.id = "P7"
p7_interval_subset.quote = ("The INTERVAL rule part contains a positive "
                            "integer representing at which intervals the "
                            "recurrence rule repeats.")
p7_interval_subset.lines = "5545:2247-2253"
p7_interval_subset.hedged = True


PROPERTIES = [p1_ordered, p2_count_prefix, p3_until_truncates,
              p4_setpos_subset, p5_wkst_inert, p6_limit_superset,
              p7_interval_subset]

BY_ID = {p.id: p for p in PROPERTIES}


def check(exp, rule, dtstart, props=None, **kw):
    """Run every property against one rule, returning {id: result}."""
    out = {}
    for p in (props or PROPERTIES):
        try:
            out[p.id] = p(exp, rule, dtstart, **kw)
        except Exception as e:  # an expander crash is data, not a stop
            out[p.id] = _r(ERROR, error="%s: %s" % (type(e).__name__, e))
    return out


if __name__ == "__main__":
    for p in PROPERTIES:
        print("%s %-22s hedged=%-5s %s" % (p.id, p.__name__, p.hedged, p.lines))
