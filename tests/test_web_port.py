"""The browser port must not drift from the reference it was ported from.

`web/` ships two JavaScript files that are ports of Python in `src/`:
`web/src/naive.js` from `src/naive.py`, and `web/src/validity.js` from
`src/validity.py`. A port is the kind of artifact that is correct on the day it
is written and quietly wrong six commits later, and nothing in a browser checks
it. So it is checked here, by the same corpus and the same scorer as any third-
party implementation:

  * the expander is scored through `conformance/score.py`, and anything short
    of every case passing is a failure -- it is a port of the very expander the
    corpus was built with, so it has no licence to disagree with it anywhere;
  * `violations()` is compared part-for-part against `src/validity.py` on every
    distinct rule in the corpus.

Skips, loudly, when node is not installed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402
import validity  # noqa: E402

fails = []


def corpus_rules():
    rules = set()
    for name in ("corroborated", "disputed", "date-value-type"):
        path = os.path.join(ROOT, "corpus", "%s.json" % name)
        cases = json.load(open(path))["cases"]
        for c in (cases if isinstance(cases, list) else cases.values()):
            rules.add(c["rrule"])
    return sorted(rules)


def test_expander_scores_every_case():
    out = os.path.join(tempfile.mkdtemp(), "score.json")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "conformance", "score.py"),
         "--json", out, "--", "node", os.path.join(ROOT, "web", "test", "adapter.mjs")],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 and not os.path.exists(out):
        fails.append("scorer did not run: %s" % (r.stderr.strip() or r.stdout.strip()))
        return
    counts = json.load(open(out))["counts"]
    total = sum(counts.values())
    if counts.get("pass", 0) != total:
        other = {k: v for k, v in counts.items() if k != "pass"}
        fails.append("web/src/naive.js: %d/%d cases pass; not-pass: %s"
                     % (counts.get("pass", 0), total, other))
    else:
        print("  expander: %d/%d corpus cases identical to src/naive.py" % (total, total))


def test_validity_agrees_with_python():
    rules = corpus_rules()
    expected = {r: sorted("%s|%s" % (v["rule"], v["part"])
                          for v in validity.violations(r)) for r in rules}
    driver = """
import fs from "node:fs";
const { violations } = await import(process.argv[2]);
const want = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const bad = [];
for (const [rule, exp] of Object.entries(want)) {
  const got = violations(rule).map(v => v.rule + "|" + v.part).sort();
  if (JSON.stringify(got) !== JSON.stringify(exp)) bad.push({ rule, exp, got });
}
process.stdout.write(JSON.stringify({ n: Object.keys(want).length, bad: bad.slice(0, 5),
                                      nbad: bad.length }));
"""
    tmp = tempfile.mkdtemp()
    dpath = os.path.join(tmp, "d.mjs")
    wpath = os.path.join(tmp, "want.json")
    open(dpath, "w").write(driver)
    json.dump(expected, open(wpath, "w"))
    r = subprocess.run(["node", dpath,
                        os.path.join(ROOT, "web", "src", "validity.js"), wpath],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("validity driver failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return
    res = json.loads(r.stdout)
    if res["nbad"]:
        fails.append("web/src/validity.js differs from src/validity.py on %d of %d rules: %s"
                     % (res["nbad"], res["n"], res["bad"]))
    else:
        print("  validity: %d/%d distinct corpus rules identical to src/validity.py"
              % (res["n"], res["n"]))


def test_diagnostics_fire_where_the_findings_say_they_do():
    """Each note must appear on the case its finding was written about.

    Without this, a diagnostic can stop firing -- because a predicate was
    tightened, or because a computed comparison stopped differing -- and the
    page would simply fall silent. Silence is this tool's failure mode: it
    looks exactly like "no known problem".
    """
    want = [
        # rrule, dtstart, note id that must be present
        ("FREQ=MONTHLY;BYDAY=+2SU,MO", "20260302T090000", "byday-mixed-signed"),
        ("FREQ=YEARLY;BYMONTHDAY=15", "20260115T090000", "yearly-expand-vs-inherit"),
        ("FREQ=YEARLY;BYWEEKNO=20", "20260513T090000", "yearly-expand-vs-inherit"),
        ("FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE", "20201230T090000", "byweekno"),
        ("FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE", "20201230T090000", "skipped-periods"),
        ("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1", "20260115T090000",
         "unsynchronized-dtstart"),
        ("FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,SU", "20260106T090000", "wkst-sensitive"),
        ("FREQ=MONTHLY;BYMONTHDAY=31", "20260131T090000", "skipped-periods"),
        ("FREQ=MONTHLY;BYMONTHDAY=30;BYMONTH=2", "20260228T090000", "empty"),
    ]
    driver = """
import fs from "node:fs";
const [, , naivePath, diagPath, casesPath] = process.argv;
const n = await import(naivePath);
const d = await import(diagPath);
const out = [];
for (const [rrule, dtstart] of JSON.parse(fs.readFileSync(casesPath, "utf8"))) {
  const ds = n.parseDtstart(dtstart);
  let occ = [];
  try { occ = n.expand(rrule, ds.t, { limit: 8 }); } catch (e) { out.push(["ERROR:" + e.message]); continue; }
  out.push(d.analyze({ rrule, dtstart: ds.t, dateOnly: ds.dateOnly, occurrences: occ, limit: 8 })
            .map(x => x.id));
}
process.stdout.write(JSON.stringify(out));
"""
    tmp = tempfile.mkdtemp()
    dpath = os.path.join(tmp, "d.mjs")
    cpath = os.path.join(tmp, "cases.json")
    open(dpath, "w").write(driver)
    json.dump([[a, b] for a, b, _ in want], open(cpath, "w"))
    r = subprocess.run(["node", dpath,
                        os.path.join(ROOT, "web", "src", "naive.js"),
                        os.path.join(ROOT, "web", "src", "diagnostics.js"), cpath],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("diagnostics driver failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return
    got = json.loads(r.stdout)
    for (rrule, dtstart, note), ids in zip(want, got):
        if note not in ids:
            fails.append("%s / DTSTART:%s -- expected note %r, got %s"
                         % (rrule, dtstart, note, ids))
    if not fails:
        print("  diagnostics: %d expected notes all fire" % len(want))


def test_every_quoted_rfc_sentence_is_in_the_pinned_rfc():
    """A sentence in quotation marks in the UI must be in RFC 5545, verbatim.

    This test exists because of a specific near-miss. `diagnostics.js` shipped
    the sentence "the recurrence instances will be generated using invalid
    dates", in quotation marks, attributed to RFC 5545 3.8.5.3. That sentence
    is not in RFC 5545. It was a plausible paraphrase of what 3.8.5.3 says
    (SHOULD be synchronized; the recurrence set is otherwise undefined) that
    had acquired quotation marks somewhere between reading and writing. It was
    caught by hand one command before the page was published.

    Nothing about that catch was reliable, so the check is mechanical now:
    every run of curly quotes in the file that looks like prose is required to
    appear in the pinned RFC text, modulo whitespace and page furniture. An
    ellipsis splits a quotation into fragments, each of which must appear.
    """
    # Every file that puts prose in front of the user, not just diagnostics.js.
    # The check was written for diagnostics.js because that is where the
    # fabricated citation happened; a citation in any other file was
    # unexamined, which is the same exposure with a different filename.
    sources = [os.path.join(ROOT, "web", "app.js")]
    srcdir = os.path.join(ROOT, "web", "src")
    sources += sorted(os.path.join(srcdir, f) for f in os.listdir(srcdir)
                      if f.endswith(".js"))
    # One file at a time, deliberately. Concatenating them lets an unmatched
    # curly quote in one file pair with a quote in the next and swallow
    # everything between -- which is exactly what happened when this check was
    # first widened past diagnostics.js. Per-file also names the culprit.
    try:
        rfc = open(env.rfc_path("5545"), encoding="utf-8", errors="replace").read()
    except env.MissingDependency as e:
        print("  skip: RFC 5545 not provisioned (%s)" % e)
        return
    keep = [l for l in rfc.splitlines()
            if not re.match(r"^(Desruisseaux\s|RFC 5545\s|\x0c)", l)]
    hay = re.sub(r"\s+", " ", " ".join(keep))

    # Flatten the source into the prose the reader will see: drop every
    # ${...} interpolation, then dissolve the string concatenation the
    # sentences are spread across. Doing this before looking for quotation
    # marks is the point -- an earlier version filtered out any quote whose
    # enclosing expression contained a `${`, which silently skipped the
    # longest citation in the file.
    checked = 0
    for path in sources:
        text = open(path, encoding="utf-8").read()
        flat = re.sub(r"\$\{[^{}]*\}", "", text)
        flat = re.sub(r"[\"`]\s*\+\s*\n?\s*[\"`]", " ", flat)
        for quote in re.findall(r"\u201c(.+?)\u201d", flat, re.S):
            q = re.sub(r"\s+", " ", quote).strip()
            # Short runs are the UI's own scare quotes ("the same rule gives
            # different results"), not citations. Cited sentences are long.
            if len(q) < 60:
                continue
            checked += 1
            for frag in [f.strip() for f in q.split("\u2026")]:
                frag = frag.strip(" .").replace("\u2018", '"').replace("\u2019", '"')
                if frag and frag not in hay:
                    fails.append("%s: quoted as RFC 5545 but not found in it: %r"
                                 % (os.path.basename(path), frag))
    print("  quotes: %d cited sentences in %d files checked against the pinned RFC"
          % (checked, len(sources)))


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the browser port is unchecked")
        raise SystemExit(0)
    test_expander_scores_every_case()
    test_validity_agrees_with_python()
    test_diagnostics_fire_where_the_findings_say_they_do()
    test_every_quoted_rfc_sentence_is_in_the_pinned_rfc()
    for f in fails:
        print("FAIL " + f)
    raise SystemExit(1 if fails else 0)

