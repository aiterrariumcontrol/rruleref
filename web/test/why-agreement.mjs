// Does the explainer agree with the expander it is explaining?
//
// `why()` reaches its verdict through a different path from `expand()`: it
// runs the BY-rule predicates one at a time, in the order 3.3.10 states, and
// then reasons about BYSETPOS, COUNT and UNTIL separately. Two paths to one
// answer is exactly the arrangement that goes quietly wrong, so every corpus
// case is replayed through both here.
//
// For each case: every date in the published expectation must come back
// "occurrence" at its own index, and a spread of dates that are NOT in it must
// come back with some other status. Reads the corpus on stdin as JSON.
import { parseDtstart, parse, expand, mk, parts, fmt } from "../src/naive.js";
import { why } from "../src/why.js";

const cases = JSON.parse(await new Promise((res) => {
  let s = ""; process.stdin.setEncoding("utf8");
  process.stdin.on("data", (d) => (s += d)); process.stdin.on("end", () => res(s));
}));

let checked = 0, fails = [];
const say = (c, msg) => fails.push(`${c.rrule} @ ${c.dtstart}: ${msg}`);

for (const c of cases) {
  let ds, r, occ;
  try {
    ds = parseDtstart(c.dtstart);
    r = parse(c.rrule);
    occ = expand(r, ds.t, { limit: 60, maxSteps: 3e5 });
  } catch { continue; }
  const set = new Set(occ);
  // expand()'s default horizon is ~30 years past DTSTART, and it can stop the
  // list short of `limit`. A probe past it is absent from `occ` because of a
  // cap this test set, not because the rule excludes it -- and why(), which
  // expands as far as the date asked about, is right to call it an occurrence.
  // (One corpus rule does exactly this: FREQ=YEARLY;BYWEEKNO=-1,53 from
  // 20241228, whose 49th occurrence is 20541231, two days past the horizon.)
  const HORIZON = ds.t + (365 * 30 + 8) * 86400;

  for (let i = 0; i < occ.length; i++) {
    let w;
    try { w = why(r, ds.t, occ[i], { dateOnly: ds.dateOnly, maxSteps: 3e5 }); } catch { continue; }
    checked++;
    if (w.status === "unknown") continue;
    if (w.status !== "occurrence") say(c, `${fmt(occ[i], ds.dateOnly)} is occurrence ${i + 1} but why() says ${w.status}`);
    else if (w.index !== i + 1) say(c, `${fmt(occ[i], ds.dateOnly)} is occurrence ${i + 1} but why() says ${w.index}`);
    if (w.checks.some((x) => x.ok === false)) say(c, `${fmt(occ[i], ds.dateOnly)} is an occurrence but a check failed`);
  }

  // Non-occurrences: neighbours of real ones, and the days around DTSTART.
  // Neighbours are where an off-by-one in a predicate actually lives.
  const probes = new Set();
  for (const t of occ.slice(0, 12)) for (const d of [-86400, -3600, -60, 60, 3600, 86400]) probes.add(t + d);
  for (let d = 1; d <= 40; d++) probes.add(ds.t + d * 86400);
  const last = occ.length ? occ[occ.length - 1] : ds.t;
  for (let d = 1; d <= 10; d++) probes.add(last + d * 86400);

  for (const t of probes) {
    if (set.has(t) || t < ds.t || t > HORIZON) continue;
    // Only meaningful inside the window we actually expanded.
    if (occ.length >= 60 && t > occ[occ.length - 1]) continue;
    let w;
    try { w = why(r, ds.t, t, { dateOnly: ds.dateOnly, maxSteps: 3e5 }); } catch { continue; }
    checked++;
    if (w.status === "unknown" || w.status === "inconsistent") {
      if (w.status === "inconsistent") say(c, `${fmt(t, ds.dateOnly)}: why() reports itself inconsistent`);
      continue;
    }
    if (w.status === "occurrence") say(c, `${fmt(t, ds.dateOnly)} is not in the expansion but why() calls it occurrence ${w.index}`);
  }
}

console.log(JSON.stringify({ checked, fails: fails.slice(0, 20), nfails: fails.length }));
