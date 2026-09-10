// Conformance adapter for web/src/naive.js -- the browser port of the
// reference expander. Protocol: conformance/PROTOCOL.md.
//
//   python3 conformance/score.py -- node web/test/adapter.mjs
//
// The port exists to run in a browser, where nothing checks it. This adapter
// is how it gets checked: it is scored against the same corpus, by the same
// scorer, as every other implementation in conformance/RESULTS.md.
import { createInterface } from "node:readline";
import { expand, parse, parseDtstart, fmt } from "../src/naive.js";

const rl = createInterface({ input: process.stdin });
const out = [];
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line);
  try {
    const ds = parseDtstart(c.dtstart);
    const occ = expand(parse(c.rrule), ds.t, { limit: c.limit, maxSteps: 5e7 });
    out.push(JSON.stringify({ id: c.id, occurrences: occ.map((t) => fmt(t, ds.dateOnly)) }));
  } catch (e) {
    out.push(JSON.stringify({ id: c.id, error: String(e && e.message || e) }));
  }
}
process.stdout.write(out.join("\n") + "\n");
