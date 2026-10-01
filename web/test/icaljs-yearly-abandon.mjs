// Does the ical.js silent-truncation note predict ical.js, or merely resemble
// finding 103's example?
//
// Finding 103 measured one defect: `ical.js` 2.2.1 abandons a `FREQ=YEARLY`
// expansion after 28 consecutive iterations that produce no occurrence, and
// reports the series as complete with no error. The search for the *first*
// occurrence is not bounded, so the same rule answered from the other side of
// the same empty run is correct.
//
// A note in diagnostics.js may not say that about the user's own rule unless
// the user's own rule is affected. So the note is backed by a PREDICTOR, not
// by the shape `FREQ=YEARLY` plus a wide gap:
//
//   from the reference series alone, predict the exact prefix ical.js will
//   return -- the occurrences up to and including the last one in the year
//   before the first gap of >= 28 empty iterations, or the whole series if
//   there is none.
//
// That prediction is then required to reproduce ical.js 2.2.1's real output
// BYTE FOR BYTE. A predictor that is right about where the series ends is
// evidence about the mechanism; a pattern match is not. (Rule from finding
// 115: a predictor beats a pattern match.)
//
// Pairs where finding 101's separate ical.js rollover defect also fires are
// excluded and reported, because there the two defects are superimposed.
//
// Pairs where finding 101's separate ical.js rollover defect also fires are
// excluded and reported, because there the two defects are superimposed.
//
// The grid below is built rather than taken from the corpus on purpose. The
// corpus asks for short prefixes of each rule and a 28-iteration empty run
// needs roughly three centuries of horizon to show up at all, so almost no
// corpus case can exhibit this defect. Finding 103 says so: the defect is
// outside the corpus.
//
// The INTERVAL rows are the discriminating ones. `BYMONTH=2;BYDAY=5MO` has a
// 40-YEAR gap after 2072, and ical.js truncates there at INTERVAL=1 -- but at
// INTERVAL=2 the same 40 years are only 19 ITERATIONS and it does not. A
// year-based reading of the defect predicts truncation in both.
import { createRequire } from "module";
import path from "path";
import { expand, parseDtstart, fmt } from "../src/naive.js";
import { icaljsAbandons } from "../src/diagnostics.js";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(new URL(".", import.meta.url).pathname, "..", "..");
const ICAL = require(path.join(ROOT, "js", "node_modules", "ical.js")).default;
const ICALJS_VERSION = require(path.join(ROOT, "js", "node_modules", "ical.js", "package.json")).version;

const pad = (n, w) => String(n).padStart(w, "0");
const icalFmt = (t) => pad(t.year, 4) + pad(t.month, 2) + pad(t.day, 2)
  + "T" + pad(t.hour, 2) + pad(t.minute, 2) + pad(t.second, 2);

function icaljs(rrule, dtstartStr, n) {
  const r = ICAL.Recur.fromString(rrule);
  const t = ICAL.Time.fromDateTimeString(dtstartStr);
  const it = r.iterator(t);
  const out = [];
  for (let i = 0; i < n; i++) {
    const x = it.next();
    if (!x) break;
    out.push(icalFmt(x));
  }
  return out;
}

const LIMIT = 40;
const rules = [];
for (const day of ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]) {
  rules.push(`FREQ=YEARLY;BYMONTH=2;BYDAY=5${day}`);
  rules.push(`FREQ=YEARLY;INTERVAL=2;BYMONTH=2;BYDAY=5${day}`);
  rules.push(`FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29;BYDAY=${day}`);
}
rules.push("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29");
rules.push("FREQ=YEARLY;BYYEARDAY=366");
rules.push("FREQ=YEARLY;INTERVAL=4;BYMONTH=2;BYDAY=5MO");
rules.push("FREQ=YEARLY;BYMONTH=1;BYDAY=MO");          // control: never empty
rules.push("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30");     // control: always empty

const starts = ["2024-01-01", "2026-01-01", "2045-01-01", "2073-01-01"];

// Finding 101 is a SECOND ical.js defect and it lands on some of the same
// rules: at FREQ=YEARLY a BYMONTHDAY larger than the month rolls forward into
// the next month instead of being ignored, so ical.js emits dates the
// reference never produces. Where that happens the two defects are
// superimposed and this test cannot isolate the one it is about, so the pair
// is excluded and counted -- not quietly skipped, and not failed.
let checked = 0, fired = 0, exact = 0, contaminated = 0;
const fails = [];
for (const rrule of rules) {
  for (const ds of starts) {
    const dtstartStr = `${ds}T00:00:00`;
    const dtstart = parseDtstart(ds.replace(/-/g, "") + "T000000").t;
    let ref;
    try { ref = expand(rrule, dtstart, { limit: LIMIT }); } catch { continue; }
    const got = icaljs(rrule, dtstartStr, LIMIT).map((s) => s.slice(0, 8));
    const refDates = ref.map((t) => fmt(t).slice(0, 8));
    checked++;

    const cut = icaljsAbandons(rrule, ref);
    const predicted = cut === null ? refDates : refDates.slice(0, cut.keep);
    if (cut !== null) fired++;

    // The reference list is capped at LIMIT, so a prediction of "the whole
    // series" can only be checked up to where the reference stops.
    const cmp = cut === null ? got.slice(0, refDates.length) : got;

    const inRef = new Set(refDates);
    if (cmp.some((d) => !inRef.has(d))) {
      contaminated++;
      continue;
    }

    if (cmp.join(" ") === predicted.join(" ")) {
      exact++;
    } else {
      fails.push(`${rrule} @${ds}\n      predicted ${predicted.join(" ") || "(none)"}`
               + `\n      ical.js   ${cmp.join(" ") || "(none)"}`);
    }
  }
}

console.log(`ical.js silent-truncation note, against ical.js ${ICALJS_VERSION}`);
console.log(`  rule/DTSTART pairs expanded by both: ${checked}`);
console.log(`  note would fire (a >= 28-iteration empty run is visible): ${fired}`);
console.log(`  excluded -- finding 101's rollover also fires, defects superimposed: ${contaminated}`);
console.log(`  prediction reproduces ical.js exactly: ${exact}/${checked - contaminated}`);
if (ICALJS_VERSION !== "2.2.1") {
  console.log(`  NOTE: finding 103 measured 2.2.1; this ran against ${ICALJS_VERSION}.`);
}
if (fails.length) {
  console.log(`${fails.length} failure(s):`);
  for (const f of fails.slice(0, 12)) console.log("  - " + f);
  process.exit(1);
}
if (!fired) {
  console.log("FAIL: the note fired on nothing, so nothing about it was tested.");
  process.exit(1);
}
console.log("OK: the predictor reproduces ical.js on every pair, firing and not firing alike.");
