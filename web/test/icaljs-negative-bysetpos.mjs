// Does the ical.js negative-BYSETPOS rollover note predict ical.js, or merely
// resemble finding 105's table?
//
// Finding 105 measured one defect in `ical.js` 2.2.1. `recur_iterator.js`,
// `next_month()`, the BYDAY-without-BYMONTHDAY branch: the in-month scan tests
// a set position in BOTH spellings, `check_set_position(++setpos)` and
// `check_set_position(setpos - setpos_total - 1)`, while the path twelve lines
// later that walks off the end of a month and lands on day 1 of the next one
// tests only `check_set_position(1)` and never computes that month's set size.
// So a rule naming position 1 only as `-n` loses the first-of-the-month date.
//
// A note in diagnostics.js may not say that about the user's own rule unless
// the user's own rule is affected, and it may not claim a date the library
// does not actually emit. So the note is backed by a PREDICTOR of ical.js's
// WHOLE STREAM -- each month's BYDAY-derived set rebuilt, BYSETPOS applied to
// it, and the day-1 member removed when only its negative spelling is named --
// and that prediction is required here to reproduce ical.js 2.2.1 BYTE FOR
// BYTE, on rules where the note fires and on rules where it does not. (Rule
// from finding 115: a predictor beats a pattern match.)
//
// BUILDING THE PREDICTOR CORRECTED THE FINDING. 105 called the symptom a
// dropped MONTH. The first model dropped the whole month and was exact on 70
// of 75 pairs, every miss a `BYSETPOS=-2,2` rule -- where ical.js keeps the
// position-2 date and loses only the day-1 one. The month-shaped symptom is
// the special case where position 1 is the month's only selection. Rule 122:
// a predictor exact everywhere except on one shape is describing a stage you
// have not modelled, not a defect in the subject. 105 carries an addendum.
//
// The four shapes the predictor does NOT model are excluded by the guard in
// `icaljsNegativeSetposRollover`, and this harness asserts both halves of each
// exclusion: that the guard really declines them, and -- in the
// COUNTEREXAMPLES section -- that the exclusion is necessary rather than
// superstitious, by showing the predictor would have been wrong there.
//
//   * BYMONTH, whose month filter interacts with the same rollover;
//   * BYMONTHDAY, which ical.js answers in `_byDayAndMonthDay()`, a different
//     branch that finding 105 explicitly did not probe;
//   * BYHOUR/BYMINUTE/BYSECOND, which multiply each date;
//   * an unsynchronized DTSTART, where finding 004's first-period truncation
//     is superimposed and ical.js emits an extra opening date.
import { createRequire } from "module";
import path from "path";
import { expand, parseDtstart, fmt } from "../src/naive.js";
import { icaljsNegativeSetposRollover } from "../src/diagnostics.js";

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
const iso = (t) => fmt(t, true).replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3") + "T00:00:00";

const LIMIT = 30;
// Seeds, not DTSTARTs. The rule's own first occurrence at or after each seed
// becomes the DTSTART, because the guard requires synchronization and an
// arbitrary seed would only exercise the exclusion.
const SEEDS = ["2023-01-01", "2024-03-15", "2025-11-02", "2027-01-01",
               "2030-06-11", "2000-02-29", "2100-01-01"];

// Two-token sets where day 1 can be the first member, three- and five-token
// sets, unordered sets, negative ordinals, and -- as controls -- sets where
// day 1 is never a member at all (2SA, 3FR alone) so the note must stay silent.
const DAYSETS = [["3FR", "1SA"], ["3FR", "1WE"], ["2FR", "1SA"], ["3FR", "2SA"],
                 ["1SA", "3FR"], ["MO", "TU"], ["MO", "WE", "FR"],
                 ["MO", "TU", "WE", "TH", "FR"], ["SA"], ["SU", "SA"],
                 ["1MO", "2MO"], ["-1FR", "1MO"], ["TH"], ["1TU", "3TH", "5SU"]];
// Positive-only sets are controls: the positive spelling of position 1 is the
// repair, so those must never fire. -1 in a large set is a control too.
const POSSETS = ["-1", "-2", "1", "2", "-2,2", "1,-2", "-3", "3", "-9", "-8",
                 "-13", "-20", "-1,-2", "2,-1", "-5"];

const inScope = [];
for (const d of DAYSETS) {
  for (const sp of POSSETS) inScope.push(`FREQ=MONTHLY;BYDAY=${d.join(",")};BYSETPOS=${sp}`);
}
// The rollover happens once per period, so INTERVAL must be exercised.
for (const iv of [2, 3, 4, 6]) inScope.push(`FREQ=MONTHLY;INTERVAL=${iv};BYDAY=3FR,1SA;BYSETPOS=-2`);
// COUNT and UNTIL are applied to ical.js's own SHORTENED stream, not to the
// correct one, so the predictor has to cap and cut the same way.
inScope.push("FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2;COUNT=7");
inScope.push("FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2;UNTIL=20280101T000000");
inScope.push("FREQ=MONTHLY;BYDAY=MO,TU;BYSETPOS=-9;COUNT=4");

// Shapes the guard must DECLINE, kept here so a future widening of the guard
// cannot pass unnoticed: each is asserted null.
const outOfScope = [
  "FREQ=MONTHLY;BYMONTH=1,4,7,10;BYDAY=3FR,1SA;BYSETPOS=-2",
  "FREQ=MONTHLY;BYMONTH=5;BYDAY=3FR,1SA;BYSETPOS=-2",
  "FREQ=MONTHLY;BYDAY=3FR,1SA;BYMONTHDAY=1,15,21;BYSETPOS=-2",
  "FREQ=MONTHLY;BYDAY=MO,TU;BYMONTHDAY=1,2,3,4,5;BYSETPOS=-2",
  "FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2;BYHOUR=9,17",
  "FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2;BYMINUTE=0,30",
  "FREQ=YEARLY;BYDAY=3FR,1SA;BYSETPOS=-2",
  "FREQ=WEEKLY;BYDAY=MO,TU;BYSETPOS=-2",
  "FREQ=MONTHLY;BYMONTHDAY=1,15;BYSETPOS=-2",
  "FREQ=MONTHLY;BYDAY=3FR,1SA",
];

// Does the rule's BYDAY set put day 1 in it, with the position named only
// negatively? Computed here independently of the guard, so that a rule the
// guard declines while still being affected can be told apart from one that is
// simply fine. Used only to classify the excluded pairs below.
function couldBeAffected(rrule, dtstart) {
  if (!/BYDAY=/i.test(rrule) || !/BYSETPOS=/i.test(rrule)) return false;
  const sp = /BYSETPOS=([^;]*)/i.exec(rrule)[1].split(",").map(Number);
  if (sp.includes(1) || !sp.some((p) => p < 0)) return false;
  const bare = rrule.split(";")
    .filter((c) => !/^(BYMONTH|BYMONTHDAY|BYHOUR|BYMINUTE|BYSECOND)=/i.test(c))
    .join(";");
  return icaljsNegativeSetposRollover(bare, dtstart, LIMIT) !== null;
}

let checked = 0, fired = 0, exact = 0, unsync = 0, emptyRule = 0, notFirst = 0;
const leaksSync = [];
const fails = [];
for (const rrule of inScope) {
  for (const seed of SEEDS) {
    const seedT = parseDtstart(seed.replace(/-/g, "") + "T000000").t;
    let first;
    try { first = expand(rrule, seedT, { limit: 1 }); } catch { emptyRule++; continue; }
    if (!first.length) { emptyRule++; continue; }
    const dtstart = first[0];
    let ref;
    try { ref = expand(rrule, dtstart, { limit: LIMIT }); } catch { emptyRule++; continue; }
    if (!ref.length || ref[0] !== dtstart) { notFirst++; continue; }

    const nr = icaljsNegativeSetposRollover(rrule, dtstart, LIMIT);
    const got = icaljs(rrule, iso(dtstart), LIMIT);
    checked++;
    let predicted, cmp;
    if (nr) {
      fired++;
      predicted = nr.predicted.map((t) => fmt(t, true));
      cmp = got;
    } else {
      // Not firing is also a prediction: that ical.js agrees with the
      // reference, as far as the reference reaches.
      predicted = ref.map((t) => fmt(t, true));
      cmp = got.slice(0, predicted.length);
    }
    if (cmp.join(" ") === predicted.join(" ")) exact++;
    else fails.push(`${rrule} @${fmt(dtstart, true)}\n      predicted ${predicted.join(" ") || "(none)"}`
                  + `\n      ical.js   ${cmp.join(" ") || "(none)"}`);
  }
}

// --- the unsynchronized-DTSTART exclusion is actually reached ------------
// The grid above derives every DTSTART from the rule itself, so it can only
// ever be synchronized. These pairs use the raw seed as DTSTART, which is what
// a user who edited the rule after setting the date has.
for (const rrule of inScope) {
  for (const seed of SEEDS) {
    const dtstart = parseDtstart(seed.replace(/-/g, "") + "T000000").t;
    let ref;
    try { ref = expand(rrule, dtstart, { limit: 2 }); } catch { continue; }
    if (!ref.length || ref[0] === dtstart) continue;
    if (icaljsNegativeSetposRollover(rrule, dtstart, LIMIT) !== null) {
      leaksSync.push(`${rrule} @${fmt(dtstart, true)}`);
    }
    unsync++;
  }
}

// --- the guard declines what it says it declines -------------------------
const leaks = [];
let declinedButAffected = 0;
for (const rrule of outOfScope) {
  for (const seed of SEEDS) {
    const seedT = parseDtstart(seed.replace(/-/g, "") + "T000000").t;
    let first;
    try { first = expand(rrule, seedT, { limit: 1 }); } catch { continue; }
    if (!first.length) continue;
    const dtstart = first[0];
    if (icaljsNegativeSetposRollover(rrule, dtstart, LIMIT) !== null) leaks.push(`${rrule} @${fmt(dtstart, true)}`);
    else if (couldBeAffected(rrule, dtstart)) declinedButAffected++;
  }
}

// --- the exclusions are necessary, not superstitious ---------------------
// The predictor run with the unmodelled part STRIPPED OUT of the rule it is
// given, but compared against ical.js on the WHOLE rule. That is what an
// ungated version of this note would have claimed. If these were exact the
// guard would be dead weight.
function ungated(rrule, dtstart, drop) {
  const stripped = rrule.split(";")
    .filter((c) => !new RegExp(`^(${drop.join("|")})=`, "i").test(c))
    .join(";");
  return icaljsNegativeSetposRollover(stripped, dtstart, LIMIT);
}
// DTSTART is taken from the rule WITHOUT the unmodelled part, because the
// predictor's own synchronization guard would otherwise decline these before
// the question being asked -- is the MODEL of the stream wrong? -- is reached.
function counter(rules, drop) {
  let ok = 0, total = 0;
  for (const rrule of rules) {
    const bare = rrule.split(";")
      .filter((c) => !new RegExp(`^(${drop.join("|")})=`, "i").test(c)).join(";");
    for (const seed of SEEDS) {
      const seedT = parseDtstart(seed.replace(/-/g, "") + "T000000").t;
      let first;
      try { first = expand(bare, seedT, { limit: 1 }); } catch { continue; }
      if (!first.length) continue;
      const dtstart = first[0];
      const g = ungated(rrule, dtstart, drop);
      if (!g) continue;
      total++;
      if (icaljs(rrule, iso(dtstart), LIMIT).join(" ")
          === g.predicted.map((t) => fmt(t, true)).join(" ")) ok++;
    }
  }
  return [ok, total];
}
const [cMonth, cMonthT] = counter(["FREQ=MONTHLY;BYMONTH=1,4,7,10;BYDAY=3FR,1SA;BYSETPOS=-2",
                                   "FREQ=MONTHLY;BYMONTH=5;BYDAY=3FR,1SA;BYSETPOS=-2",
                                   "FREQ=MONTHLY;BYMONTH=2,8;BYDAY=MO,TU;BYSETPOS=-9"], ["BYMONTH"]);
const [cMday, cMdayT] = counter(["FREQ=MONTHLY;BYDAY=3FR,1SA;BYMONTHDAY=1,15,21;BYSETPOS=-2",
                                 "FREQ=MONTHLY;BYDAY=MO,TU;BYMONTHDAY=1,2,3,4,5;BYSETPOS=-2"], ["BYMONTHDAY"]);
const [cHour, cHourT] = counter(["FREQ=MONTHLY;BYDAY=3FR,1SA;BYSETPOS=-2;BYHOUR=9,17"], ["BYHOUR"]);
// The DTSTART exclusion, measured differently: the predictor's own guard is
// what declines these, so the counterexample is the predictor's month-by-month
// model run against ical.js on an UNSYNCHRONIZED start. Finding 004's extra
// opening date is what it gets wrong.
let cSync = 0, cSyncT = 0;
for (const rrule of inScope) {
  for (const seed of SEEDS) {
    const dtstart = parseDtstart(seed.replace(/-/g, "") + "T000000").t;
    let ref;
    try { ref = expand(rrule, dtstart, { limit: LIMIT }); } catch { continue; }
    if (!ref.length || ref[0] === dtstart) continue;   // synchronized; not the case under test
    // Re-run the predictor from the rule's own first occurrence -- the dates
    // it predicts are right, but ical.js started at DTSTART and emitted one
    // more. Compare what an ungated note would have shown.
    const g = icaljsNegativeSetposRollover(rrule, ref[0], LIMIT);
    if (!g) continue;
    cSyncT++;
    if (icaljs(rrule, iso(dtstart), LIMIT).join(" ")
        === g.predicted.map((t) => fmt(t, true)).join(" ")) cSync++;
  }
}

console.log(`ical.js negative-BYSETPOS rollover note, against ical.js ${ICALJS_VERSION}`);
console.log(`  rule/DTSTART pairs expanded by both: ${checked}`);
console.log(`  note fires (day 1 selected, position named only negatively): ${fired}`);
console.log(`  controls where it must stay silent: ${checked - fired}`);
console.log(`  excluded -- the rule has no occurrence from that seed at all: ${emptyRule}`);
if (notFirst) console.log(`  excluded -- the derived DTSTART is not the rule's own first date: ${notFirst}`);
console.log(`  excluded -- DTSTART unsynchronized, finding 004 superimposed: ${unsync}` +
            `${leaksSync.length ? ` (${leaksSync.length} NOT declined)` : ""}`);
console.log(`  prediction reproduces ical.js exactly: ${exact}/${checked}`);
console.log(`  guard declines every out-of-scope shape: ${outOfScope.length * SEEDS.length - leaks.length} checks, ${leaks.length} leak(s)`);
console.log(`  of those, affected but declined (the exclusions cost real coverage): ${declinedButAffected}`);
console.log(`  exclusion is necessary -- ungated predictor with BYMONTH:     ${cMonth}/${cMonthT} exact`);
console.log(`  exclusion is necessary -- ungated predictor with BYMONTHDAY:  ${cMday}/${cMdayT} exact`);
console.log(`  exclusion is necessary -- ungated predictor with BYHOUR:      ${cHour}/${cHourT} exact`);
console.log(`     (those three take DTSTART from the rule without the excluded part)`);
console.log(`  exclusion is necessary -- ungated on unsynchronized DTSTART:  ${cSync}/${cSyncT} exact`);
if (ICALJS_VERSION !== "2.2.1") {
  console.log(`  NOTE: finding 105 measured 2.2.1; this ran against ${ICALJS_VERSION}.`);
}
let bad = false;
if (fails.length) {
  console.log(`${fails.length} prediction failure(s):`);
  for (const f of fails.slice(0, 12)) console.log("  - " + f);
  bad = true;
}
if (leaksSync.length) {
  console.log(`${leaksSync.length} unsynchronized pair(s) the guard did NOT decline:`);
  for (const l of leaksSync.slice(0, 8)) console.log("  - " + l);
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
  console.log("FAIL: the note fired on EVERY pair, so no control was tested. The positive");
  console.log("      BYSETPOS values and the 2SA-style day sets are in the grid precisely");
  console.log("      so that it has to stay silent.");
  bad = true;
}
if (!unsync) {
  console.log("FAIL: no pair exercised the unsynchronized-DTSTART exclusion, so the count");
  console.log("      reported above is not evidence of anything.");
  bad = true;
}
for (const [name, ok, total] of [["BYMONTH", cMonth, cMonthT], ["BYMONTHDAY", cMday, cMdayT],
                                 ["BYHOUR", cHour, cHourT], ["DTSTART", cSync, cSyncT]]) {
  if (!total) {
    console.log(`FAIL: the ${name} counterexample ran on nothing, so that exclusion is not`);
    console.log(`      justified by anything measured here.`);
    bad = true;
  } else if (ok === total) {
    console.log(`FAIL: the ungated predictor is exact on the ${name} shapes, so excluding`);
    console.log(`      them is not justified by anything measured here.`);
    bad = true;
  }
}
if (bad) process.exit(1);
console.log("OK: the predictor reproduces ical.js on every pair, firing and not firing alike.");
