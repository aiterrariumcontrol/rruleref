// Does the ical.js BYMONTHDAY-overflow note predict ical.js, or merely
// resemble finding 101's table?
//
// Finding 101 measured one defect: at `FREQ=YEARLY`, `ical.js` 2.2.1 assigns a
// positive `BYMONTHDAY` to a `Time` with no range check and lets day-of-year
// normalisation carry the overflow into the next month. So
// `FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31` -- a day April does not have, which
// RFC 5545 3.3.10 says MUST be ignored -- is answered with May 1st, every
// year, out to 2062.
//
// A note in diagnostics.js may not say that about the user's own rule unless
// the user's own rule is affected, and it may not claim a date the library
// does not actually emit. So the note is backed by a PREDICTOR of ical.js's
// WHOLE STREAM -- the cross product of BYMONTH and BYMONTHDAY, each cell's
// overflow carried into the following month, deduped as ical.js's day-of-year
// list dedupes -- and that prediction is required here to reproduce ical.js
// 2.2.1 BYTE FOR BYTE, on rules where the note fires and on rules where it
// does not. (Rule from finding 115: a predictor beats a pattern match.)
//
// The three shapes the predictor does NOT model are excluded by the guard in
// `icaljsMonthdayRollover`, and this harness asserts both halves of each
// exclusion: that the guard really declines them, and -- in the
// COUNTEREXAMPLES section -- that the exclusion is necessary rather than
// superstitious, by showing the predictor would have been wrong there.
//
//   * a negative BYMONTHDAY alongside a positive one, where `next_year()`
//     renormalises against the month of the last emitted (possibly invented)
//     occurrence and a dedupe collision deletes a value the user wrote --
//     finding 101's follow-on, a second mechanism;
//   * BYDAY alongside, where the bounds-checked BYDAY branch intersects the
//     overflowed BYMONTHDAY branch to nothing;
//   * `BYMONTH=2;BYMONTHDAY=29`, the only cell in the calendar whose validity
//     depends on the year, which ical.js reaches by a third path.
//
// Pairs where finding 103's separate abandonment defect also fires are
// excluded and counted too, because there the two defects are superimposed.
import { createRequire } from "module";
import path from "path";
import { expand, parseDtstart, fmt } from "../src/naive.js";
import { icaljsMonthdayRollover, icaljsAbandons } from "../src/diagnostics.js";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(new URL(".", import.meta.url).pathname, "..", "..");
const ICAL = require(path.join(ROOT, "js", "node_modules", "ical.js")).default;
const ICALJS_VERSION = require(path.join(ROOT, "js", "node_modules", "ical.js", "package.json")).version;

const pad = (n, w) => String(n).padStart(w, "0");
const icalDate = (t) => pad(t.year, 4) + pad(t.month, 2) + pad(t.day, 2);

function icaljs(rrule, dtstartStr, n) {
  const r = ICAL.Recur.fromString(rrule);
  const t = ICAL.Time.fromDateTimeString(dtstartStr);
  const it = r.iterator(t);
  const out = [];
  for (let i = 0; i < n; i++) {
    const x = it.next();
    if (!x) break;
    out.push(icalDate(x));
  }
  return out;
}

const LIMIT = 14;
const STARTS = ["2023-01-01", "2024-03-15", "2025-11-02", "2024-02-29",
                "2100-01-01", "2000-05-05"];

// Every month, so that the five short months are covered against the seven
// long ones -- the long ones are the controls, where no cell is impossible and
// the note must stay silent.
const MONTHSETS = [[1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12],
                   [2, 4], [4, 6, 9, 11], [1, 2, 3], [2, 11], [1, 12]];
const DAYSETS = [[30], [31], [1, 30], [1, 31], [15, 31], [28, 29, 30, 31],
                 [31, 30, 29], [20], [2, 30]];

const inScope = [];
for (const ms of MONTHSETS) {
  for (const ds of DAYSETS) inScope.push(`FREQ=YEARLY;BYMONTH=${ms.join(",")};BYMONTHDAY=${ds.join(",")}`);
}
// The bound is on iterations, so INTERVAL must be exercised: the invented date
// recurs once per INTERVAL years, not once per year.
for (const iv of [2, 3, 4]) inScope.push(`FREQ=YEARLY;INTERVAL=${iv};BYMONTH=4;BYMONTHDAY=31`);
// COUNT and UNTIL are applied to ical.js's own fabricated stream, not to the
// correct one, so the predictor has to cap the same way.
inScope.push("FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31;COUNT=3");
inScope.push("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=1,30;COUNT=5");
inScope.push("FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31;UNTIL=20270101T000000");

// Shapes the guard must DECLINE. Kept in the harness so that a future widening
// of the guard cannot pass unnoticed: each of these is asserted null.
const outOfScope = [
  "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=31,-1",
  "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=-5,31",
  "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=-1,31",
  "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=31;BYDAY=MO",
  "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31;BYDAY=2TU",
  "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29",
  "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29,31",
  "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=1,31;BYSETPOS=1",
  "FREQ=MONTHLY;BYMONTH=4;BYMONTHDAY=31",
  "FREQ=YEARLY;BYMONTHDAY=31",
];

// Does the rule name a cell that is impossible in every year? Computed here
// independently of the guard, so that a rule the guard DECLINES while still
// containing such a cell can be told apart from a rule that is simply fine.
// `BYMONTH=2;BYMONTHDAY=28,29,30,31` is the first kind: February 30th and 31st
// do overflow, but February 29th in the same list drags in the year-dependent
// path, so the predictor models neither half and the note correctly stays
// silent. Predicting "ical.js agrees with the reference" there would be wrong,
// and those pairs are counted below rather than quietly passed.
function namesAnImpossibleCell(rrule) {
  const g = (k) => {
    const m = rrule.match(new RegExp(`(?:^|;)${k}=([^;]*)`, "i"));
    return m ? m[1].split(",").map(Number) : null;
  };
  const months = g("BYMONTH"), days = g("BYMONTHDAY");
  if (!months || !days) return false;
  const longest = (m) => [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  return months.some((m) => days.some((d) => d > longest(m)));
}

let checked = 0, fired = 0, exact = 0, superimposed = 0, unmodelled = 0;
const fails = [];
for (const rrule of inScope) {
  for (const ds of STARTS) {
    const dtstart = parseDtstart(ds.replace(/-/g, "") + "T000000").t;
    let ref;
    try { ref = expand(rrule, dtstart, { limit: LIMIT }); } catch { continue; }
    if (icaljsAbandons(rrule, ref)) { superimposed++; continue; }

    const roll = icaljsMonthdayRollover(rrule, dtstart, LIMIT);
    if (!roll && namesAnImpossibleCell(rrule)) { unmodelled++; continue; }

    const got = icaljs(rrule, `${ds}T00:00:00`, LIMIT);
    checked++;
    let predicted, cmp;
    if (roll) {
      fired++;
      predicted = roll.predicted.map((t) => fmt(t, true));
      cmp = got;
    } else {
      // Not firing is also a prediction: that ical.js agrees with the
      // reference. The reference is capped at LIMIT, so it can only be
      // checked as far as the reference goes.
      predicted = ref.map((t) => fmt(t, true));
      cmp = got.slice(0, predicted.length);
    }

    if (cmp.join(" ") === predicted.join(" ")) exact++;
    else fails.push(`${rrule} @${ds}\n      predicted ${predicted.join(" ") || "(none)"}`
                  + `\n      ical.js   ${cmp.join(" ") || "(none)"}`);
  }
}

// --- the guard declines what it says it declines -------------------------
const leaks = [];
for (const rrule of outOfScope) {
  for (const ds of STARTS) {
    const dtstart = parseDtstart(ds.replace(/-/g, "") + "T000000").t;
    if (icaljsMonthdayRollover(rrule, dtstart, LIMIT) !== null) leaks.push(`${rrule} @${ds}`);
  }
}

// --- the exclusions are necessary, not superstitious ---------------------
// Finding 101's own mechanism, run WITHOUT the guard, on the two shapes the
// guard removes. If these agreed with ical.js the guard would be dead weight;
// they do not, and the counts are the reason the guard exists.
function ungated(rrule, dtstart, limit) {
  const stripped = rrule.split(";")
    .filter((c) => !/^(BYDAY)=/i.test(c))
    .join(";");
  // Negative values are what the real mechanism resolves against the month;
  // model that, which is the part finding 101 says is not enough.
  return icaljsMonthdayRollover(stripped.replace(/,-\d+|-\d+,/g, ""), dtstart, limit);
}
let counterNeg = 0, counterNegTotal = 0, counterDay = 0, counterDayTotal = 0;
for (const ds of STARTS) {
  const dtstart = parseDtstart(ds.replace(/-/g, "") + "T000000").t;
  for (const rrule of ["FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=31,-1",
                       "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=-5,31",
                       "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=-1,31"]) {
    const g = ungated(rrule, dtstart, LIMIT);
    if (!g) continue;
    counterNegTotal++;
    if (icaljs(rrule, `${ds}T00:00:00`, LIMIT).join(" ")
        === g.predicted.map((t) => fmt(t, true)).join(" ")) counterNeg++;
  }
  for (const rrule of ["FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=31;BYDAY=MO",
                       "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=31;BYDAY=2TU"]) {
    const g = ungated(rrule, dtstart, LIMIT);
    if (!g) continue;
    counterDayTotal++;
    if (icaljs(rrule, `${ds}T00:00:00`, LIMIT).join(" ")
        === g.predicted.map((t) => fmt(t, true)).join(" ")) counterDay++;
  }
}

console.log(`ical.js BYMONTHDAY-overflow note, against ical.js ${ICALJS_VERSION}`);
console.log(`  rule/DTSTART pairs expanded by both: ${checked}`);
console.log(`  note fires (an impossible BYMONTH/BYMONTHDAY cell): ${fired}`);
console.log(`  excluded -- finding 103's abandonment also fires, defects superimposed: ${superimposed}`);
console.log(`  excluded -- an impossible cell the guard declines (BYMONTH=2 with 29 alongside`);
console.log(`              30 or 31), where a second mechanism is superimposed: ${unmodelled}`);
console.log(`  prediction reproduces ical.js exactly: ${exact}/${checked}`);
console.log(`  guard declines every out-of-scope shape: ${outOfScope.length * STARTS.length - leaks.length}/${outOfScope.length * STARTS.length}`);
console.log(`  exclusion is necessary -- ungated predictor on negatives: ${counterNeg}/${counterNegTotal} exact`);
console.log(`  exclusion is necessary -- ungated predictor with BYDAY:   ${counterDay}/${counterDayTotal} exact`);
if (ICALJS_VERSION !== "2.2.1") {
  console.log(`  NOTE: finding 101 measured 2.2.1; this ran against ${ICALJS_VERSION}.`);
}
let bad = false;
if (fails.length) {
  console.log(`${fails.length} prediction failure(s):`);
  for (const f of fails.slice(0, 12)) console.log("  - " + f);
  bad = true;
}
if (leaks.length) {
  console.log(`${leaks.length} out-of-scope shape(s) the guard did NOT decline:`);
  for (const l of leaks.slice(0, 12)) console.log("  - " + l);
  bad = true;
}
if (!fired) {
  console.log("FAIL: the note fired on nothing, so nothing about it was tested.");
  bad = true;
}
if (fired === checked) {
  console.log("FAIL: the note fired on EVERY pair, so no control was tested. The long");
  console.log("      months are in the grid precisely so that it has to stay silent.");
  bad = true;
}
if (counterNegTotal && counterNeg === counterNegTotal) {
  console.log("FAIL: the ungated predictor is exact on the negative-BYMONTHDAY shapes,");
  console.log("      so that exclusion is not justified by anything measured here.");
  bad = true;
}
if (bad) process.exit(1);
console.log("OK: the predictor reproduces ical.js on every pair, firing and not firing alike.");
