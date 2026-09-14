"""Ambient-state sweep: does an answer depend on the machine it was computed on?

A conformance score is a measurement of an implementation *and the machine it
ran on* (finding 036). Nothing else in this harness checks for that, so this
runs every adapter over the scored corpus under a baseline environment and
under two hostile ones, and diffs the raw answers case by case.

    python3 conformance/ambient_sweep.py              # all adapters
    python3 conformance/ambient_sweep.py dmfs ical4j  # named ones

Run from the repository root. `dtical` is slow (the Perl adapter spends its
full alarm on every BYSETPOS case); name the others explicitly to skip it.

A non-zero `changed` count means one of two things, and they are not the same:

  * the implementation reads ambient state -- a finding about the library;
  * the *adapter* reads ambient state -- a defect in this instrument, which
    silently corrupts the score on a machine configured differently from mine.

Both have happened. `ical4j` is the first (see finding 036: it takes the
week's first day from Locale.getDefault() when WKST is omitted). The dmfs
adapter was the second: its String.format had no Locale, so under ar_EG it
emitted Arabic-Indic digits and would have scored 0/1721.
"""
import json, os, sys, subprocess, argparse

ADAPTERS = {
    "dateutil":  ["python3", "conformance/adapters/dateutil_adapter.py"],
    "rrulejs":   ["node", "conformance/adapters/rrulejs_adapter.js"],
    "libical":   ["conformance/adapters/c/libical_adapter"],
    "rustrrule": ["conformance/adapters/rust/target/release/rustrrule_adapter"],
    "vobject":   ["php", "vobject_adapter.php"],
    "dtical":    ["perl", "conformance/adapters/perl/dtical_adapter.pl"],
    "ical4j":    ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "Ical4jAdapter"],
    "dmfs":      ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "DmfsAdapter"],
}
CWD = {"vobject": "conformance/adapters/php"}
EXTRA_ENV = {"libical": {"LD_LIBRARY_PATH": os.environ.get(
    "LIBICAL_LIB", "/home/agent/terrarium/scratch/libical-install-4edd/lib")}}

# The hostile environments move three things at once: the zone (and its offset
# sign), the locale's first day of the week, and the locale's digit shapes.
# ar_EG starts the week on Saturday and numbers with Arabic-Indic digits;
# th_TH starts on Sunday. Both must be generated on the host (locale-gen).
ENVS = {
    "baseline":      {"TZ": "UTC",                "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
    "kiritimati_ar": {"TZ": "Pacific/Kiritimati", "LANG": "ar_EG.UTF-8", "LC_ALL": "ar_EG.UTF-8"},
    "honolulu_th":   {"TZ": "Pacific/Honolulu",   "LANG": "th_TH.UTF-8", "LC_ALL": "th_TH.UTF-8"},
}


def load_cases(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def payload(cases):
    return "".join(json.dumps({"id": c["id"], "rrule": c["rrule"],
                               "dtstart": c["dtstart"], "limit": c["limit"]}) + "\n"
                   for c in cases)


def run(name, envname, pl, timeout):
    env = dict(os.environ)
    for k in ("TZ", "LANG", "LC_ALL", "LANGUAGE"):
        env.pop(k, None)
    env.update(ENVS[envname])
    env.update(EXTRA_ENV.get(name, {}))
    p = subprocess.run(ADAPTERS[name], input=pl, capture_output=True, text=True,
                       env=env, cwd=CWD.get(name), timeout=timeout)
    out = {}
    for line in p.stdout.splitlines():
        if line.strip():
            o = json.loads(line)
            out[o["id"]] = o
    return out, p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("adapters", nargs="*", default=[])
    ap.add_argument("--cases", default="conformance/cases.ndjson")
    ap.add_argument("--timeout", type=float, default=7200)
    ap.add_argument("--json", help="write the full report here")
    a = ap.parse_args()

    names = a.adapters or list(ADAPTERS)
    pl = payload(load_cases(a.cases))
    report, bad = {}, 0
    for name in names:
        base, rc = run(name, "baseline", pl, a.timeout)
        entry = {"baseline_rc": rc, "baseline_n": len(base), "envs": {}}
        for envname in ENVS:
            if envname == "baseline":
                continue
            got, rc2 = run(name, envname, pl, a.timeout)
            changed = sorted(i for i in base if base[i] != got.get(i))
            entry["envs"][envname] = {"rc": rc2, "n": len(got),
                                      "changed": len(changed), "ids": changed}
            bad += len(changed)
        report[name] = entry
        print("%-10s %s" % (name, "  ".join(
            "%s=%d" % (e, v["changed"]) for e, v in sorted(entry["envs"].items()))),
            flush=True)
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1, sort_keys=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
