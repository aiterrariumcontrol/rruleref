// The node half of finding 111's diagnostic harness.
//
// Unlike finding 101's and 103's predictors, this one models a JAVA library,
// so the real implementation cannot be reached from node at all. The division
// of labour is therefore: this script computes what
// `dmfsWeeknoOverflow` in ../src/diagnostics.js predicts, and
// tests/test_dmfs_weekno_overflow.py runs the same cases through the compiled
// DmfsAdapter and compares. Nothing here asserts anything -- the python side
// owns every judgement, so that the library and the predictor are never read
// by the same process.
//
// Reads one JSON object per line on stdin: { id, dtstart, rrule, limit }.
// Writes one JSON object per line on stdout:
//   { id, predicted: ["YYYYMMDDTHHMMSS", ...], phantom: [...], years: [...] }
// An input line may carry "ungated": true, which runs the predictor with the
// guard switched off so the python side can show each exclusion was necessary.
// or { id, declined: true } when the guard refuses the rule, which the python
// side treats as a measurable claim and not as a pass.
import { parseDtstart, parts } from "../src/naive.js";
import { dmfsWeeknoOverflow } from "../src/diagnostics.js";

const stamp = (t) => {
  const p = parts(t);
  const z = (n, w) => String(n).padStart(w, "0");
  return `${z(p.y, 4)}${z(p.mo, 2)}${z(p.d, 2)}T${z(p.h, 2)}${z(p.mi, 2)}${z(p.s, 2)}`;
};

let buf = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) buf += chunk;
const out = [];
for (const line of buf.split("\n")) {
  if (!line.trim()) continue;
  const c = JSON.parse(line);
  let o = null, err = null;
  try {
    const { t } = parseDtstart(c.dtstart);
    o = dmfsWeeknoOverflow(c.rrule, t, c.limit, { ungated: c.ungated === true });
  } catch (e) {
    err = String(e && e.message || e);
  }
  if (err) out.push({ id: c.id, error: err });
  else if (!o) out.push({ id: c.id, declined: true });
  else out.push({
    id: c.id,
    predicted: o.predicted.map(stamp),
    phantom: o.phantom.map(stamp),
    years: o.years,
  });
}
process.stdout.write(out.map((o) => JSON.stringify(o)).join("\n") + "\n");
