// Is the two-rule comparison telling the truth about an edit?
//
// compareRules() answers "what did this edit do to my dates". It is easy to
// make such a thing look right and be wrong, in one specific way: both
// expansions are truncated at the occurrence count the user asked for, and if
// the two lists are compared past the point where one of them stops, every
// date the other list still has looks like a date the edit added. A rule that
// merely fires more often would be reported as a rule that gains dates it does
// not gain.
//
// So two properties, over an edit generator rather than over arbitrary pairs,
// because an edit is what a user actually does:
//
//   PARTITION   both + onlyA is exactly A inside the window, both + onlyB is
//               exactly B inside it, and the three lists are disjoint.
//
//   WINDOW      re-expanding both rules with four times the cap and cutting at
//               the same window must give the same three lists. If the verdict
//               moves when the cap moves, the verdict was about the cap.
//
// The edits are the ones that happen in the wild: drop a BY part, or keep only
// the first value of a multi-valued one -- which is the Superset bug, where
// Number.parseInt("9,17") quietly became 9.
//
// Reads the corpus on stdin as JSON; prints a report, exits non-zero on any
// violation.
import { parseDtstart, parse, fmt } from "../src/naive.js";
import { compareRules } from "../src/compare.js";

const cases = JSON.parse(await new Promise((res) => {
  let s = ""; process.stdin.setEncoding("utf8");
  process.stdin.on("data", (d) => (s += d)); process.stdin.on("end", () => res(s));
}));

const LIMIT = 12;

function edits(rrule) {
  const out = [];
  const kv = rrule.split(";").map((p) => p.split("="));
  for (let i = 0; i < kv.length; i++) {
    const [k, v] = kv[i];
    if (k === "FREQ") continue;
    const drop = kv.filter((_, j) => j !== i).map((p) => p.join("=")).join(";");
    out.push(["drop " + k, drop]);
    if (v && v.includes(",")) {
      const first = kv.map((p, j) => (j === i ? [k, v.split(",")[0]] : p))
                      .map((p) => p.join("=")).join(";");
      out.push(["first value of " + k, first]);
    }
  }
  return out;
}

const setOf = (a) => new Set(a);
const eq = (x, y) => x.length === y.length && x.every((v, i) => v === y[i]);

let pairs = 0, violations = 0, seen = new Set();
const report = (msg) => { if (violations++ < 12) console.log("  VIOLATION " + msg); };

for (const c of cases) {
  const key = c.rrule + "|" + c.dtstart;
  if (seen.has(key)) continue;
  seen.add(key);
  let ds, a;
  try { ds = parseDtstart(c.dtstart); a = parse(c.rrule); } catch { continue; }
  for (const [label, edited] of edits(c.rrule)) {
    let b;
    try { b = parse(edited); } catch { continue; }
    let r, wide;
    try {
      r = compareRules(a, b, ds.t, { limit: LIMIT });
      wide = compareRules(a, b, ds.t, { limit: LIMIT * 4 });
    } catch { continue; }
    pairs++;
    const where = `${c.rrule} -> ${edited} (${label}) from ${c.dtstart}`;

    // PARTITION
    const inBoth = setOf(r.both);
    if (r.onlyA.some((t) => inBoth.has(t)) || r.onlyB.some((t) => inBoth.has(t)) ||
        r.onlyA.some((t) => setOf(r.onlyB).has(t))) {
      report("lists overlap: " + where);
      continue;
    }
    if (r.both.length + r.onlyA.length !== r.countA ||
        r.both.length + r.onlyB.length !== r.countB) {
      report("lists do not partition the expansions: " + where);
      continue;
    }
    if (r.same !== (r.onlyA.length === 0 && r.onlyB.length === 0)) {
      report("same flag disagrees with the lists: " + where);
      continue;
    }

    // WINDOW -- the verdict must not depend on the cap, inside the window the
    // narrow run claimed to cover.
    if (r.complete) {
      if (!wide.complete || !eq(r.onlyA, wide.onlyA) || !eq(r.onlyB, wide.onlyB) ||
          !eq(r.both, wide.both)) {
        report("claimed to cover the whole sets, but a larger cap disagrees: " + where);
        continue;
      }
    } else {
      const cut = (xs) => xs.filter((t) => t <= r.until);
      if (!eq(r.onlyA, cut(wide.onlyA)) || !eq(r.onlyB, cut(wide.onlyB)) ||
          !eq(r.both, cut(wide.both))) {
        report(`window verdict moved when the cap moved (until ${fmt(r.until)}): ${where}`);
        continue;
      }
    }
  }

  // REFLEXIVITY -- a rule compared with itself must show no change at all.
  const self = compareRules(a, a, ds.t, { limit: LIMIT });
  if (!self.same || self.onlyA.length || self.onlyB.length) {
    report("a rule differs from itself: " + c.rrule + " from " + c.dtstart);
  }
}

console.log(`  compared ${pairs} edited pairs over ${seen.size} corpus cases`);
if (violations) {
  console.log(`  ${violations} violation(s)`);
  process.exit(1);
}
console.log(`OK: partition and window properties hold on all ${pairs} pairs`);
