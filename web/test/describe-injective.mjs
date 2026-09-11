// Can the English tell two different rules apart?
//
// A plain-English rendering of an RRULE is only worth showing if it is
// faithful. The failure mode that matters is not clumsy prose -- a reader can
// see that -- but a sentence that quietly omits the part which changes the
// answer, because the reader cannot see what is missing. rrule.js's toText()
// has exactly this problem: over this corpus it gives
// `FREQ=DAILY;BYHOUR=9,8` and `FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1` the same
// sentence, while declaring itself fully convertible.
//
// So two properties are checked here over every corpus case.
//
//   INJECTIVITY  Two rules that get the same sentence from the same DTSTART
//                must have the same expansion. Contrapositive: if they expand
//                differently, the English must differ somewhere.
//
//   COVERAGE     Every RRULE part present in the text is claimed by some
//                clause, and no clause claims a part that is not there.
//
// Neither says the English reads well. They say it is not lying by omission.
//
// Reads the corpus on stdin as JSON; prints a report and exits non-zero on
// any violation.
import { parseDtstart, parse, expand, fmt } from "../src/naive.js";
import { describe, presentParts } from "../src/describe.js";

const cases = JSON.parse(await new Promise((res) => {
  let s = ""; process.stdin.setEncoding("utf8");
  process.stdin.on("data", (d) => (s += d)); process.stdin.on("end", () => res(s));
}));

let checked = 0;
const fails = [];
const bySentence = new Map();

for (const c of cases) {
  let ds, r, d;
  try {
    ds = parseDtstart(c.dtstart);
    r = parse(c.rrule);
    d = describe(r, c.rrule, ds.t, { dateOnly: ds.dateOnly });
  } catch (e) {
    continue; // rules the parser itself rejects are not this module's problem
  }
  checked++;

  // --- coverage
  const present = presentParts(c.rrule);
  const covered = new Set(d.covered);
  const unmentioned = [...present].filter((k) => !covered.has(k));
  const invented = [...covered].filter((k) => !present.has(k) && k !== "FREQ");
  if (unmentioned.length) fails.push(`${c.rrule}: not accounted for by any clause: ${unmentioned.join(",")}`);
  if (invented.length) fails.push(`${c.rrule}: clause claims a part the rule does not state: ${invented.join(",")}`);

  // --- injectivity: group by (sentence, dtstart)
  const key = d.sentence + "  @" + c.dtstart;
  if (!bySentence.has(key)) bySentence.set(key, []);
  const g = bySentence.get(key);
  if (!g.some((x) => x.rrule === c.rrule)) g.push(c);
}

let collisions = 0, ambiguous = 0;
for (const [key, group] of bySentence) {
  if (group.length < 2) continue;
  collisions++;
  const sets = new Map();
  for (const c of group) {
    let occ;
    try { occ = expand(c.rrule, parseDtstart(c.dtstart).t, { limit: 60 }).map((t) => fmt(t)).join(","); }
    catch (e) { occ = "ERR:" + e.message; }
    if (!sets.has(occ)) sets.set(occ, []);
    sets.get(occ).push(c.rrule);
  }
  if (sets.size > 1) {
    ambiguous++;
    const which = [...sets.values()].map((v) => v[0]).slice(0, 3).join("  |  ");
    fails.push(`same sentence, different occurrences: ${which} -- sentence was: ${key}`);
  }
}

console.log(`describe(): ${checked} cases, ${bySentence.size} distinct (sentence, DTSTART) keys`);
console.log(`  sentences shared by more than one rule: ${collisions}`);
console.log(`  of those, sharing rules that expand differently: ${ambiguous}`);
if (fails.length) {
  console.log(`${fails.length} failure(s):`);
  for (const f of fails.slice(0, 25)) console.log("  - " + f);
  process.exit(1);
}
console.log("OK: no sentence is shared by two rules with different occurrences.");
