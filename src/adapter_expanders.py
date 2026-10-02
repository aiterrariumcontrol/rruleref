"""Present a conformance adapter as an expander the properties can check.

`src/properties.py` checks a *relation between two expansions*, so unlike the
corpus it needs no expected values from this repository -- which means it can
be pointed at any implementation without asking anyone to trust me. Until now
it could not be, because `src/expanders.py` only knows the two in-process
Python expanders and every other measured build is reached through the
line-oriented adapter protocol (`conformance/PROTOCOL.md`).

Two mismatches have to be bridged, and they are the whole of this module.

**An adapter is a batch program, not a service.** `PROTOCOL.md` says
"buffering is yours", and the adapters take that up: several emit nothing
until stdin closes. So a per-call request/response loop is not available, and
a subprocess per call would be absurd -- the property sweep asks for ~28
expansions per rule. Instead every expansion is *recorded* on a miss and the
whole pass is replayed: a pass that asks for something uncached returns `[]`
(a lie, discarded), the driver resolves all misses in one subprocess, and the
pass runs again. Repeat to a fixpoint. Only a pass that completes with **zero
misses** is reported, so no answer in the output was ever computed from the
placeholder. Properties branch on the values they get -- P2 skips its COUNT
probes when the base expansion looks short -- so a single recording pass does
not discover every request, and iterating is not an optimisation but the
correctness argument.

**The protocol has no horizon, only `limit`.** `properties.run` wants the
occurrences within `[dtstart, dtstart+horizon_days]`, capped. Asking every
adapter for `cap` (3000) occurrences of a monthly rule to keep 36 of them is
not affordable, so the limit is escalated per rule -- 64, then 512, then
`cap` -- and a key is settled once the answer either runs past the horizon,
comes back short of the limit asked (the set is exhausted), or reaches `cap`.
Each escalation is just another round of the loop above.

Clipping uses **break-on-first-exceed**, not a filter, because that is what
`src/expanders.py` does: it stops at the first occurrence past the horizon.
Matching it matters -- a filter would silently repair an implementation that
emits occurrences out of order, and P1 exists to catch exactly that.
"""
import glob
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FMT = "%Y%m%dT%H%M%S"

#: Where a libical adapter finds the canonical build's shared library. Kept as
#: the default of an env var rather than hardcoded: the prefix lives outside
#: the repository (three of them do) and is not reproducible from the tree.
LIBICAL_LIB = os.environ.get(
    "LIBICAL_LIB", "/home/agent/terrarium/scratch/libical-install-4edd/lib")


def classpath():
    jars = sorted(glob.glob(os.path.join(
        REPO, "conformance/adapters/java/libs/*.jar")))
    return ":".join(["conformance/adapters/java/classes"]
                    + [os.path.relpath(j, REPO) for j in jars])


#: adapter id -> how to launch it. The ids are `src/builds.py` ids wherever one
#: exists, so a result here can be lined up with a `conformance/RESULTS.md`
#: row. `@CP@` is substituted with the Java classpath at launch.
REGISTRY = {
    "dateutil": {"argv": ["python3", "conformance/adapters/dateutil_adapter.py"]},
    "rrulejs": {"argv": ["node", "conformance/adapters/rrulejs_adapter.js"]},
    "icaljs": {"argv": ["node", "conformance/adapters/icaljs_adapter.js"]},
    "rustrrule": {"argv": ["conformance/adapters/rust/target/release/rustrrule_adapter"]},
    "dtical": {"argv": ["perl", "conformance/adapters/perl/dtical_adapter.pl"]},
    "libical_4edd": {"argv": ["conformance/adapters/c/libical_adapter"],
                     "env": {"LD_LIBRARY_PATH": LIBICAL_LIB}},
    "ical4j": {"argv": ["java", "-Duser.language=en", "-Duser.country=US",
                        "-cp", "@CP@", "Ical4jAdapter"]},
    "dmfs": {"argv": ["java", "-Duser.language=en", "-Duser.country=US",
                      "-cp", "@CP@", "DmfsAdapter"]},
    "sabre": {"argv": ["php", "vobject_adapter.php"],
              "cwd": "conformance/adapters/php"},
}

#: The escalation ladder for `limit`. 64 settles every rule whose frequency is
#: daily or coarser over a three-year horizon; only sub-daily rules climb.
LADDER = (64, 512)


class AdapterError(Exception):
    """The adapter answered with an `error` line, or unparseably.

    Raised rather than returned so that a refusal reaches `properties.check`
    the same way an in-process expander's exception does, and lands in the
    same ERROR bucket. A refusal to parse is a result, not a harness fault.
    """


class AdapterExpander(object):
    """Callable with the `expanders.py` signature, backed by a cache.

    Not thread-safe and not meant to be: the driver alternates strictly
    between replaying passes and resolving misses.
    """

    def __init__(self, name, cap=3000, timeout=3600):
        if name not in REGISTRY:
            raise KeyError("no adapter %r; known: %s"
                           % (name, ", ".join(sorted(REGISTRY))))
        self.name = name
        self.spec = REGISTRY[name]
        self.cap = cap
        self.timeout = timeout
        #: (rule, dtstart) -> (limit_asked, [datetime] | AdapterError)
        self.cache = {}
        #: (rule, dtstart) -> limit to ask for next
        self.pending = {}
        self.misses = 0
        self.rounds = 0
        self.requests = 0
        self.adapter_seconds = 0.0

    # -- the expander interface ------------------------------------------
    def __call__(self, rule, dtstart, horizon, cap):
        key = (rule, dtstart.strftime(FMT))
        ent = self.cache.get(key)
        if ent is None:
            self._want(key, LADDER[0])
            return []
        asked, raw = ent
        if isinstance(raw, AdapterError):
            raise raw
        times, exceeded = [], False
        for t in raw:
            if t > horizon:
                exceeded = True
                break
            times.append(t)
            if len(times) >= cap:
                break
        if not exceeded and len(raw) >= asked and asked < cap:
            self._want(key, self._next_limit(asked))
            return []
        return times

    def _next_limit(self, asked):
        for step in LADDER:
            if step > asked:
                return min(step, self.cap)
        return self.cap

    def _want(self, key, limit):
        self.misses += 1
        if self.pending.get(key, 0) < limit:
            self.pending[key] = limit

    # -- resolving misses -----------------------------------------------
    def resolve(self):
        """Ask the adapter for every pending key. Returns the number asked."""
        if not self.pending:
            return 0
        items = sorted(self.pending.items())
        self.pending = {}
        lines = []
        for i, ((rule, ds), limit) in enumerate(items):
            lines.append(json.dumps({"id": str(i), "rrule": rule,
                                     "dtstart": ds, "limit": limit}))
        argv = [a.replace("@CP@", classpath()) for a in self.spec["argv"]]
        cwd = os.path.join(REPO, self.spec["cwd"]) if self.spec.get("cwd") else REPO
        env = dict(os.environ, TZ="UTC", LC_ALL="en_US.UTF-8",
                   **self.spec.get("env", {}))
        import time
        t0 = time.time()
        p = subprocess.run(argv, input="\n".join(lines) + "\n", cwd=cwd,
                           env=env, capture_output=True, text=True,
                           timeout=self.timeout)
        self.adapter_seconds += time.time() - t0
        self.rounds += 1
        self.requests += len(items)
        seen = set()
        for lineno, line in enumerate(p.stdout.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                idx = int(r["id"])
            except Exception:
                raise SystemExit("%s: stdout line %d is not a reply: %r"
                                 % (self.name, lineno, line[:160]))
            key, limit = items[idx][0], items[idx][1]
            seen.add(idx)
            if "error" in r:
                self.cache[key] = (limit, AdapterError(str(r["error"])[:200]))
                continue
            try:
                times = [datetime.strptime(x, FMT) for x in r["occurrences"]]
            except Exception as e:
                self.cache[key] = (limit, AdapterError(
                    "unparseable occurrence: %s" % e))
                continue
            self.cache[key] = (limit, times)
        # A reply this adapter simply never produced is not a conformance
        # fact about the library, so it is recorded as an error on the key
        # rather than quietly left to miss forever and hang the fixpoint.
        for idx, (key, limit) in enumerate(items):
            if idx not in seen:
                self.cache[key] = (limit, AdapterError("no reply from adapter"))
        if p.returncode != 0:
            sys.stderr.write("%s: exit %d; stderr tail:\n%s\n"
                             % (self.name, p.returncode, p.stderr[-800:]))
        return len(items)
