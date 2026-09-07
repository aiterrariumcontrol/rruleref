"""Adapters presenting each expander with the same bounded interface.

    expander(rule, dtstart, horizon, cap) -> [datetime] within [dtstart, horizon]

Bounds are passed in, never assumed, because every earlier comparison bug in
this repository came from two implementations being asked different questions
(see src/crosscheck.py's docstring).
"""
import itertools
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

env.add_dateutil_to_path()
import dateutil.rrule as du  # noqa: E402
import naive  # noqa: E402


def naive_expander(rule, dtstart, horizon, cap):
    return naive.expand(rule, dtstart, horizon=horizon, limit=cap)


def dateutil_expander(rule, dtstart, horizon, cap):
    it = du.rrulestr("RRULE:" + rule, dtstart=dtstart)
    out = []
    for t in it:
        if t > horizon:
            break
        out.append(t)
        if len(out) >= cap:
            break
    return out


EXPANDERS = {"naive": naive_expander, "dateutil": dateutil_expander}
