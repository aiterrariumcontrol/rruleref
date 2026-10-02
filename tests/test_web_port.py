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
import naive  # noqa: E402
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


def test_the_two_horizons_agree():
    """Rule 66 across a language boundary.

    `web/src/naive.js` must carry its own copy of `HORIZON_DAYS` -- nothing
    links a Python module to a browser at run time -- so the only thing that
    can stop the two drifting is this check. They did drift: 064's repair of
    the constant reached two Python modules and not this one, and when 066
    raised the horizon the port kept the old value and stopped agreeing with
    the corpus on 95 cases. Finding 067.
    """
    import re
    js = open(os.path.join(ROOT, "web", "src", "naive.js")).read()
    m = re.search(r"export const HORIZON_DAYS\s*=\s*(\d+)", js)
    if not m:
        fails.append("web/src/naive.js: no exported HORIZON_DAYS to compare")
        return
    if int(m.group(1)) != naive.HORIZON_DAYS:
        fails.append("horizon drift: web/src/naive.js %s vs src/naive.py %s"
                     % (m.group(1), naive.HORIZON_DAYS))
    else:
        print("  horizon: web/src/naive.js and src/naive.py agree at %d days"
              % naive.HORIZON_DAYS)


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
        # Finding 019, the case reported upstream as libical#1374. Fixed in
        # libical master at 4edd39a but still present in every released
        # version, so the note must keep firing. It had no coverage here until
        # 2026-09-11, which is exactly the gap this test exists to close.
        ("FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1", "20260705T090000",
         "libical-weekly-bymonth-bysetpos"),
        # Finding 103. A fifth Monday in February needs a leap year whose
        # 1 February is a Monday: 2044, 2072, then 2112 -- a 40-year hole that
        # is 39 empty iterations, past ical.js 2.2.1's bound of 28, so it
        # stops at 2072 and reports the series complete. The note's accuracy
        # about *where* it stops is checked against the real library in
        # tests/test_icaljs_abandon.py; this row only pins that it fires.
        ("FREQ=YEARLY;BYMONTH=2;BYDAY=5MO", "20260101T000000",
         "icaljs-yearly-abandon"),
        # Finding 101. April has no 31st in any year, so RFC 5545 3.3.10
        # requires the empty set; ical.js 2.2.1 answers 1 May, every year. The
        # correct series being empty is the point: this note has to survive
        # analyze()'s early return for a rule that produces no occurrences,
        # which is where it was invisible before. Its accuracy about *which*
        # dates ical.js emits is checked against the real library in
        # tests/test_icaljs_monthday_rollover.py; this row only pins that it
        # fires, and that it fires alongside "empty" rather than instead of it.
        ("FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31", "20260115T090000",
         "icaljs-monthday-rollover"),
        # The same note on a rule that is NOT empty: 1 February is a real date
        # and is returned, 30 February is not and becomes 2 March. A guard that
        # only looked at empty series would miss this one.
        ("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=1,30", "20260201T090000",
         "icaljs-monthday-rollover"),
        # Finding 111. ISO 8601 gives 2021-2025 no week 53 at all, so this
        # rule's correct answer inside its own UNTIL is the empty set; dmfs
        # lib-recur 0.17.1 answers 27 December 2021 and four more, each from an
        # instance it placed at December 32nd. Like finding 101's note this one
        # has to survive analyze()'s early return (rule 121), which is why the
        # window is closed with UNTIL rather than left to the horizon.
        ("FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO;UNTIL=20251231T000000", "20210101T090000",
         "dmfs-weekno-overflow"),
        # Finding 105. 1SA is always days 1-7 and 3FR always days 15-21, so the
        # month's set is {1SA, 3FR} and -2 always names 1SA. In the months whose
        # first Saturday IS the first -- May 2027 is the first inside this
        # window -- ical.js 2.2.1 loses that date, and since it is the month's
        # only selection the month vanishes. Its accuracy about which dates
        # ical.js emits is checked against the real library in
        # tests/test_icaljs_negative_bysetpos.py; this row only pins that it
        # fires. Unlike findings 101 and 111 this note cannot reach the empty
        # path: its guard requires DTSTART to be the rule's own first
        # occurrence, so the series it fires on is never empty.
        ("FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2", "20270102T090000",
         "icaljs-negative-bysetpos-rollover"),
        # The same note where the month does NOT empty: adding position 2
        # positively keeps 3FR, so only the first-of-the-month date is lost.
        # This is the distinction that building the predictor forced on
        # finding 105, which had called the symptom a dropped month.
        ("FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2,2", "20270102T090000",
         "icaljs-negative-bysetpos-rollover"),
        # Finding 070's defect A. FREQ=DAILY;BYMONTHDAY=-1 is an ordinary way
        # to write "the last day of every month", and under DAILY BYMONTHDAY
        # limits rather than expands, so ical.js 2.2.1 compares -1 against a
        # day number in 1..31 and never matches. Nothing else can match
        # either, and the loop it spins in is unbounded at this frequency: the
        # first next() returns DTSTART and the second never returns. The
        # correct series here is perfectly ordinary, which is why this row sits
        # beside the empty-series one below.
        ("FREQ=DAILY;BYMONTHDAY=-1", "20240331T090000",
         "icaljs-contracting-negative"),
        # The same note's other symptom: 15 still matches, so the search
        # terminates and the library quietly answers a rule the user did not
        # write. Which of the two symptoms fires is computed, not guessed, and
        # the predicted stream is checked against the real library in
        # tests/test_icaljs_contracting_negative.py.
        ("FREQ=DAILY;BYMONTHDAY=-1,15", "20240331T090000",
         "icaljs-contracting-negative"),
        # And on a rule whose correct series IS empty -- February has no 31st
        # from either end -- so the note has to survive analyze()'s early
        # return (rule 121) exactly as findings 101's and 111's notes do.
        ("FREQ=DAILY;BYMONTH=2;BYMONTHDAY=-31", "20240201T090000",
         "icaljs-contracting-negative"),
        # The same note where the correct series is NOT empty: week 52 exists
        # in every year, so the rule returns something either way and the
        # phantom week is mixed in among real occurrences.
        ("FREQ=YEARLY;BYWEEKNO=52,53;BYDAY=MO", "20210101T090000",
         "dmfs-weekno-overflow"),
        # Finding 112's defect B. 2024 starts on a Monday, so libical's
        # `doy_offset` is 0 and the week-numbering year it expands BYDAY over is
        # one day short: week 52 of 2024 comes back as six days, 23-28
        # December, with the Sunday missing. Which dates master 4edd39a3 really
        # emits is checked against two real builds in
        # tests/test_libical_week_year.py; this row only pins that it fires.
        ("FREQ=YEARLY;BYWEEKNO=52;BYDAY=MO,TU,WE,TH,FR,SA,SU;WKST=MO",
         "20240101T090000", "libical-week-year-truncated"),
        # The other end of the same arithmetic. 2025 starts on a Wednesday, so
        # its first week reaches back into 2024, `doy_offset` goes negative, and
        # the period is one day too LONG -- which lets the stride loop reach a
        # 53rd week in a year ISO gives 52. Finding 112 looked for this
        # over-run and did not find it; it needs a BYWEEKNO naming a week the
        # year does not have, which is why BYWEEKNO=1 showed nothing.
        ("FREQ=YEARLY;BYWEEKNO=53;BYDAY=MO;WKST=MO", "20240101T090000",
         "libical-week-year-truncated"),
        # And the note on the empty path (rule 121). 2024 has no 53rd week
        # under any reading, so the correct answer inside this UNTIL is
        # nothing and analyze() returns early -- but libical does not return an
        # empty series here, it reports MALFORMEDDATA, because the week is
        # always inside the part of the year it drops and its constructor
        # searches to MAX_TIME_T_YEAR before giving up.
        ("FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE;WKST=SA;UNTIL=20241231T000000",
         "20240101T090000", "libical-week-year-truncated"),
        # Finding 112's defect A, in the OTHER branch of expand_year_days():
        # BYWEEKNO with no BYDAY. `weeks_in_year()` counts ISO weeks and so
        # normalises BYWEEKNO=-1 against 52 where the WKST=SU numbering the
        # count is compared against says the year has 53 -- so libical answers
        # the wrong week. Here the correct series inside the UNTIL has one date
        # and libical's has none, which is also the empty-path case (rule 121):
        # the note has to fire where analyze() returns early.
        ("FREQ=YEARLY;BYWEEKNO=-1;WKST=SU;UNTIL=20261231T000000",
         "20261227T090000", "libical-weeks-in-year-blind"),
        # The same helper, the other consumer: `weekno > nweeks` is the only
        # guard against a week the year does not have, and with the ISO count
        # too high the week survives the guard and the one-day-per-week stride
        # lands it outside the year it was selected for.
        ("FREQ=YEARLY;BYWEEKNO=-1;WKST=SU;UNTIL=20261231T000000",
         "20240101T090000", "libical-weeks-in-year-blind"),
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
    test_the_two_horizons_agree()
    test_expander_scores_every_case()
    test_validity_agrees_with_python()
    test_diagnostics_fire_where_the_findings_say_they_do()
    test_every_quoted_rfc_sentence_is_in_the_pinned_rfc()
    for f in fails:
        print("FAIL " + f)
    raise SystemExit(1 if fails else 0)

