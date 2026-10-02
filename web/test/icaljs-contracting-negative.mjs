// Does the contracting-negative note predict ical.js, or merely resemble
// finding 070's description of it?
//
// Finding 070 measured one cause with two symptoms. ical.js 2.2.1's
// `check_contract_restriction` compares a stored BY value against the
// candidate date literally, so a negative BYMONTHDAY or an ordinal BYDAY in a
// part that *contracts* under the rule's own FREQ can never match. If some
// other value in the part still can, the user gets a wrong list with nothing
// logged. If none can, the `do ... while` in `next()` -- unbounded at
// SECONDLY, MINUTELY, HOURLY, DAILY and WEEKLY -- never terminates, and
// because the iterator allocates as it scans, the process dies.
//
// The note in diagnostics.js may not say either of those things about a user's
// rule unless that rule is really affected, and when it shows a stream it may
// not show dates the library does not emit. So it is backed by a PREDICTOR of
// ical.js's WHOLE ANSWER, and this harness requires that prediction to be
// right about ical.js 2.2.1 on every rule it is given, firing and not firing
// alike.
//
// HOW THE TRUTH IS OBTAINED, AND WHY IT IS A CHILD PROCESS
//
// A library that aborts the process cannot be contained in-process. Every case
// here therefore runs in its own `node --max-old-space-size=16` child, exactly
// as conformance/adapters/icaljs_adapter.js does for the corpus. A 16 MB heap
// is not a convenience: it turns the non-termination into a DEFINITE signal in
// about half a second -- SIGABRT with "JavaScript heap out of memory" on
// stderr -- instead of a deadline that a loaded machine could also produce.
// A case killed by the wall-clock deadline instead is reported separately and
// fails the harness, because "it did not answer in time" is a weaker claim
// than the note makes.
//
// The 16 MB heap is itself checked: every control here answers under it, so a
// heap death is evidence about the search and not about the budget.
//
// WHAT THE GUARDS COST
//
// The predictor declines three shapes, and for each this harness shows both
// halves -- that the guard really declines it, and that declining is necessary
// rather than superstitious (standing rule from finding 101's conversion):
//
//   * FREQ=WEEKLY, MONTHLY and YEARLY, where the same BY part expands (or is
//     refused at parse time) and the negative is normalised correctly;
//   * UNTIL at or before DTSTART, answered with the empty set before the loop
//     is entered;
//   * a rule with no negative or ordinal value at all.
//
// For the first two the harness shows the mechanism's own prediction would
// have been wrong, by running the real library on the rule AND on the rule
// with those values deleted and requiring the two answers to DIFFER. That
// equality is precisely what the note claims where it fires, so a difference
// is what makes the exclusion load-bearing.
import { createRequire } from "module";
import path from "path";
import { spawnSync } from "child_process";
import { parseDtstart, fmt, parse } from "../src/naive.js";
import { icaljsContractingNegative } from "../src/diagnostics.js";

const require = createRequire(import.meta.url);
const SELF = new URL(import.meta.url).pathname;
const ROOT = path.resolve(path.dirname(SELF), "..", "..");
const HEAP_MB = 16;
const DEADLINE_MS = 12000;
// The frequencies at which a heap abort is cheap enough to require.
const ABORTS_FAST = ["DAILY", "HOURLY"];
const SLOW_DEADLINE_MS = 3000;
const LIMIT = 12;

// --- the worker: one case, in its own process ----------------------------
if (process.argv[2] === "--one") {
  const ICAL = require(path.join(ROOT, "js", "node_modules", "ical.js")).default;
  const c = JSON.parse(process.argv[3]);
  const pad = (n, w) => String(n).padStart(w, "0");
  const f = (t) => pad(t.year, 4) + pad(t.month, 2) + pad(t.day, 2) + "T"
    + pad(t.hour, 2) + pad(t.minute, 2) + pad(t.second, 2);
  const d = c.dtstart;
  const iso = d.slice(0, 4) + "-" + d.slice(4, 6) + "-" + d.slice(6, 8) + "T"
    + d.slice(9, 11) + ":" + d.slice(11, 13) + ":" + d.slice(13, 15);
  try {
    const it = ICAL.Recur.fromString(c.rrule).iterator(ICAL.Time.fromDateTimeString(iso));
    const occ = [];
    while (occ.length < LIMIT) { const t = it.next(); if (!t) break; occ.push(f(t)); }
    process.stdout.write(JSON.stringify({ occ }));
  } catch (e) {
    process.stdout.write(JSON.stringify({ refused: String((e && e.message) || e) }));
  }
  process.exit(0);
}

function icaljs(rrule, dtstart, deadline = DEADLINE_MS) {
  const r = spawnSync(process.execPath,
    [`--max-old-space-size=${HEAP_MB}`, SELF, "--one", JSON.stringify({ rrule, dtstart })],
    { timeout: deadline, encoding: "utf8", maxBuffer: 1 << 24 });
  if (r.status === 0 && r.stdout) return JSON.parse(r.stdout);
  if (r.signal === "SIGABRT" && /heap out of memory/.test(r.stderr || "")) {
    return { heapDeath: true };
  }
  if (r.signal === "SIGTERM") return { deadline: true };
  return { unknown: `status=${r.status} signal=${r.signal} ${(r.stderr || "").slice(0, 160)}` };
}

// --- the corpus ----------------------------------------------------------
const STARTS = ["20240331T090000", "20240115T120000", "20250301T000000",
                "20240229T083000", "20230701T000000", "21000215T235959"];

// Every rule here is in scope: the four contracting frequencies, each of the
// two parts that can reach the check, with and without a value that still
// matches, and the time-of-day parts on both sides of the expand/limit line.
const inScope = [
  "FREQ=DAILY;BYMONTHDAY=-1",
  "FREQ=DAILY;BYMONTHDAY=-2,-15",
  "FREQ=HOURLY;BYMONTHDAY=-1",
  "FREQ=MINUTELY;BYMONTHDAY=-5",
  "FREQ=SECONDLY;BYMONTHDAY=-1",
  "FREQ=DAILY;BYDAY=-1MO",
  "FREQ=DAILY;BYDAY=5SA",
  // UNTIL is pinned to a DTSTART before it: an UNTIL at or before DTSTART is
  // a declined shape and is exercised in the control list instead.
  ["FREQ=DAILY;BYMONTHDAY=-1;UNTIL=20240401T000000", ["20240331T090000", "20240115T120000"]],
  "FREQ=DAILY;BYMONTHDAY=-1;COUNT=2",
  "FREQ=DAILY;BYMONTH=2;BYMONTHDAY=-1,30",
  "FREQ=DAILY;BYMONTHDAY=-1,15;BYDAY=-1MO",
  "FREQ=HOURLY;INTERVAL=5;BYDAY=-2FR",
  "FREQ=DAILY;BYMONTHDAY=-1,15",
  "FREQ=DAILY;BYMONTHDAY=15,-1",
  "FREQ=DAILY;BYMONTHDAY=-1,-15,10,20",
  "FREQ=DAILY;BYDAY=-1MO,TU",
  "FREQ=DAILY;BYDAY=-1SU,2MO,WE",
  "FREQ=DAILY;BYDAY=5SA,SU",
  "FREQ=HOURLY;BYMONTHDAY=-1,15",
  "FREQ=MINUTELY;BYMONTHDAY=-5,3",
  "FREQ=SECONDLY;BYMONTHDAY=-1,2",
  "FREQ=DAILY;BYMONTHDAY=-1,15;COUNT=4",
  "FREQ=DAILY;BYMONTHDAY=-1;COUNT=1",
  ["FREQ=DAILY;BYMONTHDAY=-1,15;UNTIL=20240901T000000", ["20240331T090000", "20240115T120000"]],
  "FREQ=DAILY;INTERVAL=2;BYMONTHDAY=-1,15",
  "FREQ=DAILY;BYMONTH=3,7;BYMONTHDAY=-1,15",
  "FREQ=DAILY;BYMONTHDAY=-1,15;BYDAY=MO",
  "FREQ=DAILY;BYHOUR=9,10;BYMONTHDAY=-1,15",
  "FREQ=HOURLY;BYHOUR=9;BYMONTHDAY=-1,15",
  "FREQ=DAILY;BYMINUTE=0,30;BYMONTHDAY=-1,15",
  "FREQ=MINUTELY;BYSECOND=0,30;BYMONTHDAY=-1,15",
  "FREQ=DAILY;BYMONTHDAY=-1,15;BYSETPOS=1",
  "FREQ=DAILY;BYMONTHDAY=-1,15;WKST=SU",
];

// Shapes the guard must DECLINE, kept here so a future widening cannot pass
// unnoticed. `differs` marks the ones where the harness also requires the
// library to disagree with the mechanism, which is what makes the exclusion
// necessary; `refused` marks the ones ical.js rejects at parse time.
// Each entry says what the mechanism WOULD have claimed here, so that the
// harness can require the library to contradict it:
//
//   "answers"  the part holds nothing but negatives, so the mechanism claims
//              the search never terminates. ical.js must answer.
//   "differs"  the part still holds a matchable value, so the mechanism
//              claims ical.js answers the rule exactly as it answers the rule
//              with the negatives deleted. The two must not agree.
//   "refused"  ical.js rejects the rule before the loop is reached.
//   "empty"    guard U. The mechanism claims either no answer or a stream
//              beginning at DTSTART; ical.js returns the empty set.
//   "silent"   no negative or ordinal value at all; nothing to be wrong about.
const outOfScope = [
  ["FREQ=MONTHLY;BYMONTHDAY=-1", null, "answers"],
  ["FREQ=YEARLY;BYMONTHDAY=-1", null, "answers"],
  ["FREQ=MONTHLY;BYDAY=-1MO", null, "answers"],
  ["FREQ=YEARLY;BYDAY=-1MO", null, "answers"],
  ["FREQ=WEEKLY;BYDAY=-1MO", null, "answers"],
  ["FREQ=MONTHLY;BYMONTHDAY=-1,15", null, "differs"],
  ["FREQ=YEARLY;BYMONTHDAY=-1,15", null, "differs"],
  ["FREQ=MONTHLY;BYDAY=-1MO,WE", null, "differs"],
  ["FREQ=WEEKLY;BYMONTHDAY=-1", null, "refused"],
  ["FREQ=DAILY;BYYEARDAY=-1", null, "refused"],
  ["FREQ=DAILY;BYMONTHDAY=-1,15;UNTIL=20240301T000000",
   ["20240331T090000", "20250301T000000", "21000215T235959"], "empty"],
  ["FREQ=DAILY;BYMONTHDAY=-1;UNTIL=20240301T000000",
   ["20240331T090000", "20250301T000000", "21000215T235959"], "empty"],
  ["FREQ=DAILY;BYMONTHDAY=15", null, "silent"],
  ["FREQ=DAILY;BYDAY=MO", null, "silent"],
  ["FREQ=DAILY;BYMONTHDAY=1,15;BYDAY=MO,TU", null, "silent"],
];

/** The rule with every negative BYMONTHDAY and ordinal BYDAY deleted. */
function stripNegatives(rrule) {
  const out = [];
  for (const c of rrule.split(";")) {
    if (!c) continue;
    const [k, v] = [c.split("=")[0].trim().toUpperCase(), c.slice(c.indexOf("=") + 1)];
    if (k === "BYMONTHDAY") {
      const keep = v.split(",").filter((x) => Number(x) > 0);
      if (keep.length) out.push(`BYMONTHDAY=${keep.join(",")}`);
    } else if (k === "BYDAY") {
      const keep = v.split(",").filter((x) => /^[A-Za-z]{2}$/.test(x.trim()));
      if (keep.length) out.push(`BYDAY=${keep.join(",")}`);
    } else out.push(c);
  }
  return out.join(";");
}

// --- run -----------------------------------------------------------------
const fail = [];
let nonterm = 0, drops = 0, controls = 0, deadlines = 0, slow = 0, ran = 0;

for (const entry of inScope) {
  const [rrule, starts] = Array.isArray(entry) ? entry : [entry, STARTS];
  for (const ds of starts) {
    const { t } = parseDtstart(ds);
    const p = icaljsContractingNegative(rrule, t, LIMIT);
    if (!p) { fail.push(`${rrule} @ ${ds}: the note is silent on an in-scope rule`); continue; }
    const freq = parse(rrule).FREQ;
    const slowArm = p.kind === "nonterminating" && !ABORTS_FAST.includes(freq);
    const truth = icaljs(rrule, ds, slowArm ? SLOW_DEADLINE_MS : DEADLINE_MS);
    if (slowArm) {
      // The weaker arm. "No answer in SLOW_DEADLINE_MS" only means anything
      // beside a control that does answer in it.
      slow++;
      if (truth.occ) {
        fail.push(`${rrule} @ ${ds}: predicted no answer, ical.js returned ${JSON.stringify(truth.occ)}`);
        continue;
      }
      if (truth.unknown) { fail.push(`${rrule} @ ${ds}: ${truth.unknown}`); continue; }
      const bare = icaljs(stripNegatives(rrule), ds, SLOW_DEADLINE_MS);
      if (!bare.occ) {
        fail.push(`${rrule} @ ${ds}: the control ${stripNegatives(rrule)} also failed to answer in ${SLOW_DEADLINE_MS} ms, so the silence is not evidence`);
      }
      continue;
    }
    if (truth.deadline) { deadlines++; fail.push(`${rrule} @ ${ds}: killed by the ${DEADLINE_MS} ms deadline rather than answering or dying of the heap`); continue; }
    if (truth.unknown) { fail.push(`${rrule} @ ${ds}: ${truth.unknown}`); continue; }
    if (p.kind === "nonterminating") {
      nonterm++;
      if (!truth.heapDeath) {
        fail.push(`${rrule} @ ${ds}: predicted no answer, ical.js returned ${JSON.stringify(truth.occ || truth.refused)}`);
      }
    } else {
      drops++;
      const want = p.predicted.map((x) => fmt(x, false));
      if (truth.heapDeath) { fail.push(`${rrule} @ ${ds}: predicted ${want.length} occurrences, ical.js died of the heap`); continue; }
      if (!truth.occ || JSON.stringify(truth.occ) !== JSON.stringify(want)) {
        fail.push(`${rrule} @ ${ds}:\n    predicted ${JSON.stringify(want)}\n    ical.js   ${JSON.stringify(truth.occ || truth.refused)}`);
      }
    }
  }
}

const counterexamples = [];
for (const [rrule, starts, why] of outOfScope) {
  for (const ds of starts || STARTS) {
    const { t } = parseDtstart(ds);
    if (icaljsContractingNegative(rrule, t, LIMIT) !== null) {
      fail.push(`${rrule} @ ${ds}: the guard should decline this (${why}) and does not`);
      continue;
    }
    controls++;
    if (why === "silent") continue;              // nothing to be wrong about
    ran++;
    const truth = icaljs(rrule, ds);
    if (truth.deadline || truth.unknown) {
      fail.push(`${rrule} @ ${ds}: a declined control did not answer under a ${HEAP_MB} MB heap (${truth.unknown || "deadline"})`);
      continue;
    }
    if (truth.heapDeath && why !== "refused") {
      fail.push(`${rrule} @ ${ds}: a declined control died of the heap, so the ${HEAP_MB} MB budget is too small to be evidence`);
      continue;
    }
    const first = ds === (starts || STARTS)[0];
    if (why === "refused") {
      if (!truth.refused) fail.push(`${rrule} @ ${ds}: expected a parse refusal, got ${JSON.stringify(truth.occ)}`);
      else if (first) counterexamples.push(`  ${rrule.padEnd(46)} refused: ${truth.refused}`);
    } else if (why === "answers") {
      if (!truth.occ || !truth.occ.length) {
        fail.push(`${rrule} @ ${ds}: declined, but ical.js produced no answer either -- the exclusion may be unnecessary`);
      } else if (first) {
        counterexamples.push(`  ${rrule.padEnd(46)} answers normally: ${JSON.stringify(truth.occ.slice(0, 3))}`);
      }
    } else if (why === "empty") {
      if (!truth.occ || truth.occ.length) {
        fail.push(`${rrule} @ ${ds}: expected the empty set, got ${JSON.stringify(truth.occ || truth.refused)}`);
      } else if (first) {
        counterexamples.push(`  ${rrule.padEnd(46)} empty set, before the loop is entered`);
      }
    } else {
      const bare = icaljs(stripNegatives(rrule), ds);
      const same = bare.occ && truth.occ && JSON.stringify(bare.occ) === JSON.stringify(truth.occ);
      if (same) {
        fail.push(`${rrule} @ ${ds}: declined, but ical.js answers it exactly as it answers ${stripNegatives(rrule)} -- the exclusion may be unnecessary`);
      } else if (first) {
        // Show the first position where they part company, not the first
        // three -- these rules often agree for a while.
        const i = Math.max(0, (truth.occ || []).findIndex((x, j) => x !== (bare.occ || [])[j]));
        counterexamples.push(
          `  ${rrule.padEnd(46)} differ from occurrence ${i + 1}\n` +
          `  ${"".padEnd(46)} ical.js: ${JSON.stringify((truth.occ || []).slice(i, i + 2))}\n` +
          `  ${"".padEnd(46)} without the negatives: ${JSON.stringify((bare.occ || []).slice(i, i + 2))}`);
      }
    }
  }
}

console.log(`ical.js ${require(path.join(ROOT, "js", "node_modules", "ical.js", "package.json")).version}, ` +
            `one child per case at ${HEAP_MB} MB`);
console.log(`in scope:   ${nonterm + drops + slow} predictions`);
console.log(`  ${String(drops).padStart(4)} of an exact stream, reproduced byte for byte`);
console.log(`  ${String(nonterm).padStart(4)} of no answer at all, shown by the heap abort itself (${ABORTS_FAST.join(", ")})`);
console.log(`  ${String(slow).padStart(4)} of no answer at all at MINUTELY/SECONDLY, shown only by silence for`);
console.log(`       ${SLOW_DEADLINE_MS} ms beside a control that answers in it -- a weaker observation`);
console.log(`controls:   ${controls} declined by the guard, ${ran} of them run against the library`);
console.log(`deadlines:  ${deadlines}`);
console.log("\nwhy the exclusions are not superstition:");
for (const c of counterexamples) console.log(c);

if (fail.length) {
  console.log(`\n${fail.length} FAILURE${fail.length === 1 ? "" : "S"}:`);
  for (const f of fail.slice(0, 25)) console.log(`  ${f}`);
  process.exit(1);
}
console.log(`\nOK: ${nonterm + drops + slow} predictions held against ical.js, ` +
            `${controls} declined shapes left alone`);
