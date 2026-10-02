#!/usr/bin/env python3
"""A persisted adapter cache is an equivalence, not a shortcut.

The property sweep over an adapter is expensive -- the dtical build is hours of
Perl, which is why its column in finding 118 is the one that is missing. A
cache that survives between runs is what makes a column like that reachable at
all, and it buys that by letting a reported row be computed from answers this
process never saw an adapter produce. So it has to be held to three things,
which is what this file checks:

1. **A warm run equals a cold run.** The reported tally and the failing
   (property, rule, dtstart) triples must be identical, and the warm run must
   make no adapter call at all. If the cache changed any answer, the row it
   produces is not the row the build produces.
2. **Chunking changes nothing.** Splitting one resolve round across several
   adapter calls is what makes progress durable, and it is only sound because
   an adapter answers each line from that line alone. One call and several
   calls must write a *byte-identical* cache file.
3. **A cache from another build is refused, loudly.** Silently reusing it
   would put an answer from one library behind another library's name in a
   published table. Stopping is the cheap failure; the expensive one is a
   wrong row nobody can see is wrong.

Uses the `dateutil` adapter because it is pure Python and a few seconds, and
`rustrrule` for the cross-build refusal. No network, no Java, no Perl.
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import properties as P
import adapter_expanders as A
from run_properties import load_rules
from run_properties_adapters import sweep, Budget

SAMPLE = 60
SEED = 11
FAIL = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))
    if not ok:
        FAIL.append(label)


def normal(cache):
    """A cache in a comparable form; AdapterError has no __eq__."""
    out = {}
    for key, (limit, raw) in cache.items():
        if isinstance(raw, A.AdapterError):
            out[key] = (limit, "error:" + str(raw))
        else:
            out[key] = (limit, [t.strftime(P.FMT) for t in raw])
    return out


def triples(failures):
    return sorted((f["property"], f["rrule"], f["dtstart"]) for f in failures)


def main():
    import random
    rules = random.Random(SEED).sample(load_rules(), SAMPLE)
    tmp = tempfile.mkdtemp(prefix="adapter-cache-")
    try:
        # -- 1. cold, then warm -----------------------------------------
        cold = A.AdapterExpander("dateutil", chunk=0)
        path = os.path.join(tmp, "dateutil.jsonl")
        cold.attach_cache(path)
        t_cold, f_cold, passes = sweep(cold, rules, P.HORIZON_DAYS, P.CAP,
                                       verbose=False)
        cold.close()
        check("a cold run with a cache attached still reaches a fixpoint",
              cold.misses == 0 and passes >= 1,
              "%d passes, %d rounds, %d keys"
              % (passes, cold.rounds, len(cold.cache)))

        warm = A.AdapterExpander("dateutil", chunk=0)
        loaded = warm.attach_cache(path)
        t_warm, f_warm, warm_passes = sweep(warm, rules, P.HORIZON_DAYS, P.CAP,
                                           verbose=False)
        warm.close()
        check("the warm run holds exactly the cold run's cache",
              normal(warm.cache) == normal(cold.cache),
              "%d keys warm, %d cold" % (len(warm.cache), len(cold.cache)))
        # The file has more records than keys because an escalated key was
        # written once per limit. Loading has to replay them in order so the
        # highest limit wins; comparing the caches above is what proves it did.
        check("escalation really did write a key more than once",
              loaded > len(cold.cache), "%d records, %d keys"
              % (loaded, len(cold.cache)))
        check("the warm run makes no adapter call",
              warm.rounds == 0 and warm.requests == 0,
              "%d rounds, %d requests" % (warm.rounds, warm.requests))
        check("the warm run settles in one pass", warm_passes == 1,
              "%d passes" % warm_passes)
        check("warm tally == cold tally", t_warm == t_cold)
        check("warm failures == cold failures, as the same triples",
              triples(f_warm) == triples(f_cold),
              "%d vs %d" % (len(f_warm), len(f_cold)))

        # -- 2. chunked == unchunked ------------------------------------
        chunked_path = os.path.join(tmp, "chunked.jsonl")
        chunked = A.AdapterExpander("dateutil", chunk=40)
        chunked.attach_cache(chunked_path)
        t_chunk, f_chunk, _ = sweep(chunked, rules, P.HORIZON_DAYS, P.CAP,
                                    verbose=False)
        chunked.close()
        check("chunking really did split the rounds",
              chunked.rounds > cold.rounds,
              "%d calls chunked vs %d unchunked" % (chunked.rounds, cold.rounds))
        check("chunked cache file is byte-identical to the unchunked one",
              open(chunked_path).read() == open(path).read())
        check("chunked tally == unchunked tally", t_chunk == t_cold)
        check("chunked failures == unchunked failures",
              triples(f_chunk) == triples(f_cold))

        # -- 3. a cache from another build is refused --------------------
        alien = os.path.join(tmp, "alien.jsonl")
        shutil.copy(path, alien)
        lines = open(alien).read().split("\n")
        meta = json.loads(lines[0])
        meta["fingerprint"] = "0" * 64
        lines[0] = json.dumps(meta, sort_keys=True)
        open(alien, "w").write("\n".join(lines))
        try:
            A.AdapterExpander("dateutil").attach_cache(alien)
            check("a cache with a foreign fingerprint is refused", False,
                  "it was accepted")
        except SystemExit as exc:
            check("a cache with a foreign fingerprint is refused",
                  "different build" in str(exc), str(exc)[:60])

        # The fingerprint must actually move when the build moves, or check 3
        # is testing a constant. Two different adapters must not share one.
        d_fp = A.AdapterExpander("dateutil").fingerprint()[0]
        r_fp = A.AdapterExpander("rrulejs").fingerprint()[0]
        check("different adapters have different fingerprints", d_fp != r_fp)
        check("the cap is part of the fingerprint",
              A.AdapterExpander("dateutil", cap=64).fingerprint()[0] != d_fp)

        # -- 4. a torn last line is survivable --------------------------
        torn = os.path.join(tmp, "torn.jsonl")
        body = open(path).read()
        open(torn, "w").write(body[:len(body) - 12])
        t_exp = A.AdapterExpander("dateutil")
        n_torn = t_exp.attach_cache(torn)
        check("a cache torn by a kill loads every complete record",
              n_torn == loaded - 1, "%d records of %d" % (n_torn, loaded))
        whole, part = normal(cold.cache), normal(t_exp.cache)
        check("a torn cache is a subset of the whole one, never a mutation",
              set(part) <= set(whole)
              and all(whole[k] == v for k, v in part.items()),
              "%d keys vs %d" % (len(part), len(whole)))
        t_exp.close()

        # -- 5. the budget refuses to report a partial pass -------------
        broke = A.AdapterExpander("dateutil")
        try:
            sweep(broke, rules, P.HORIZON_DAYS, P.CAP, verbose=False,
                  budget=-1.0)
            check("an exhausted budget raises instead of reporting", False,
                  "it returned a tally")
        except Budget as exc:
            check("an exhausted budget raises instead of reporting",
                  "unresolved" in str(exc), str(exc)[:70])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("FAILED: %s" % ", ".join(FAIL) if FAIL else "all checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
