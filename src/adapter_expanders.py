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

**The cache can outlive the process** (finding 120). `DateTime::Event::ICal`'s
column is about twenty hours of adapter time, which no single run gets to
finish, and before `attach_cache` a sweep killed at nineteen hours had produced
nothing at all. So answers append to a JSONL file and `chunk` splits a resolve
round across several adapter calls, flushing after each. Both are only sound as
*equivalences* -- a cached or chunked sweep must report exactly what a cold
single-call sweep reports -- and `tests/test_adapter_cache.py` is what holds
them to that. The file is keyed on `fingerprint()`, because an answer from one
build published under another build's name is the one failure here that nobody
could see.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
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
    "dtical": {"argv": ["perl", "conformance/adapters/perl/dtical_adapter.pl"],
               "version_argv": ["perl", "-MDateTime::Event::ICal",
                                "-MDateTime::Event::Recurrence", "-MDateTime",
                                "-e", "print join q(,), "
                                "$DateTime::Event::ICal::VERSION, "
                                "$DateTime::Event::Recurrence::VERSION, "
                                "$DateTime::VERSION"]},
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

    def __init__(self, name, cap=3000, timeout=3600, chunk=0):
        if name not in REGISTRY:
            raise KeyError("no adapter %r; known: %s"
                           % (name, ", ".join(sorted(REGISTRY))))
        self.name = name
        self.spec = REGISTRY[name]
        self.cap = cap
        self.timeout = timeout
        #: keys per adapter subprocess; 0 means one call for the whole round
        self.chunk = chunk
        #: (rule, dtstart) -> (limit_asked, [datetime] | AdapterError)
        self.cache = {}
        #: (rule, dtstart) -> limit to ask for next
        self.pending = {}
        self.misses = 0
        self.rounds = 0
        self.requests = 0
        self.adapter_seconds = 0.0
        self.cache_path = None
        #: records read from a persisted cache -- not distinct keys. A key that
        #: escalated 64 -> 512 was written once per limit, and loading replays
        #: those in append order so the highest limit wins, exactly as a live
        #: round would have left it.
        self.loaded = 0
        self._fh = None

    # -- the launch spec, in one place so the fingerprint cannot drift ----
    def argv(self):
        return [a.replace("@CP@", classpath()) for a in self.spec["argv"]]

    def cwd(self):
        return (os.path.join(REPO, self.spec["cwd"])
                if self.spec.get("cwd") else REPO)

    def env(self):
        return dict(os.environ, TZ="UTC", LC_ALL="en_US.UTF-8",
                   **self.spec.get("env", {}))

    def fingerprint(self):
        """Identify the *build* a cached answer came from.

        A persisted cache is only sound if the thing that produced it has not
        changed, so this hashes everything that selects an answer: the launch
        argv, the working directory, the environment this module overrides,
        the cap and the escalation ladder, the bytes of every argv token that
        is a file in the tree, and -- where the spec says how to ask -- the
        version of the installed library behind the adapter.

        It cannot see an upgrade of a system library that the spec gives no
        `version_argv` for. That is a real gap, not a solved problem: for
        those adapters a stale cache is detectable only by re-running.
        """
        argv, cwd = self.argv(), self.cwd()
        over = self.spec.get("env", {})
        parts = ["name=%s" % self.name, "cap=%d" % self.cap, "cwd=%s" % cwd,
                 "argv=%s" % json.dumps(argv),
                 "env=%s" % json.dumps(sorted(over.items())),
                 "ladder=%s" % json.dumps(list(LADDER))]
        for tok in argv:
            path = tok if os.path.isabs(tok) else os.path.join(cwd, tok)
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
                parts.append("file:%s=%s" % (tok, digest))
        vargv = self.spec.get("version_argv")
        if vargv:
            try:
                res = subprocess.run(vargv, cwd=cwd, env=self.env(),
                                     capture_output=True, text=True,
                                     timeout=120)
            except Exception as exc:
                raise SystemExit("%s: version probe failed (%s); refusing to "
                                 "key a persistent cache on an unknown build"
                                 % (self.name, exc))
            if res.returncode != 0 or not res.stdout.strip():
                raise SystemExit("%s: version probe exit %d, stdout %r; "
                                 "refusing to key a persistent cache on an "
                                 "unknown build"
                                 % (self.name, res.returncode, res.stdout))
            parts.append("version=%s" % res.stdout.strip())
        hsh = hashlib.sha256()
        for part in parts:
            hsh.update(part.encode("utf-8") + b"\0")
        return hsh.hexdigest(), parts

    # -- the persistent cache --------------------------------------------
    def attach_cache(self, path, reset=False):
        """Load `path` if it matches this build, and append to it from now on.

        A header mismatch is a hard error rather than a silent discard. A
        dtical sweep is hours of adapter time, and quietly throwing it away
        because a comment moved in the adapter script is worse than stopping
        to say so -- while quietly *using* answers from another build would
        put a wrong row in a published table.
        """
        digest, parts = self.fingerprint()
        if reset and os.path.exists(path):
            os.remove(path)
        if os.path.exists(path):
            with open(path) as fh:
                head = fh.readline()
                if not head.strip():
                    raise SystemExit("%s: %s is empty of its header"
                                     % (self.name, path))
                meta = json.loads(head)
                if meta.get("fingerprint") != digest:
                    raise SystemExit(
                        "%s: %s was written by a different build\n"
                        "  cached: %s\n  current: %s\n"
                        "Pass --cache-reset to discard it, or --cache with a "
                        "different path to keep both."
                        % (self.name, path, meta.get("fingerprint"), digest))
                for lineno, line in enumerate(fh, 2):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        # A run killed mid-write leaves one torn line. Every
                        # earlier line is still a complete record, and a key
                        # that is missing is simply recomputed.
                        sys.stderr.write("%s: %s line %d is torn, stopping "
                                         "the load there\n"
                                         % (self.name, path, lineno))
                        break
                    key = (rec["r"], rec["d"])
                    if "e" in rec:
                        self.cache[key] = (rec["l"], AdapterError(rec["e"]))
                    else:
                        self.cache[key] = (
                            rec["l"],
                            [datetime.strptime(x, FMT) for x in rec["o"]])
                    self.loaded += 1
            self._fh = open(path, "a")
        else:
            self._fh = open(path, "w")
            self._fh.write(json.dumps({
                "adapter": self.name, "fingerprint": digest,
                "identity": parts,
                "written_by": "src/adapter_expanders.py",
            }, sort_keys=True) + "\n")
            self._fh.flush()
        self.cache_path = path
        return self.loaded

    def _append(self, keys):
        if self._fh is None:
            return
        for key in keys:
            limit, raw = self.cache[key]
            rec = {"r": key[0], "d": key[1], "l": limit}
            if isinstance(raw, AdapterError):
                rec["e"] = str(raw)
            else:
                rec["o"] = [t.strftime(FMT) for t in raw]
            self._fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None

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
        """Ask the adapter for every pending key. Returns the number asked.

        With `chunk` set, the round is split across several adapter calls and
        the cache file is flushed after each one, so an interrupted sweep
        keeps the adapter time it already spent. Splitting is only sound
        because an adapter answers each line from the line itself; the
        equivalence is asserted by `tests/test_adapter_cache.py`, which
        requires a chunked round and a single-call round to produce
        byte-identical cache files.
        """
        if not self.pending:
            return 0
        items = sorted(self.pending.items())
        self.pending = {}
        size = self.chunk if self.chunk else len(items)
        for off in range(0, len(items), size):
            self._resolve_batch(items[off:off + size])
        return len(items)

    def _resolve_batch(self, items):
        lines = []
        for i, ((rule, ds), limit) in enumerate(items):
            lines.append(json.dumps({"id": str(i), "rrule": rule,
                                     "dtstart": ds, "limit": limit}))
        t0 = time.time()
        p = subprocess.run(self.argv(), input="\n".join(lines) + "\n",
                           cwd=self.cwd(), env=self.env(),
                           capture_output=True, text=True,
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
        self._append([key for key, _ in items])
        if p.returncode != 0:
            sys.stderr.write("%s: exit %d; stderr tail:\n%s\n"
                             % (self.name, p.returncode, p.stderr[-800:]))
