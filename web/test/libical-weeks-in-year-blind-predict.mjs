// The node half of finding 112 defect A's diagnostic harness.
//
// libical is C, so the prediction and the implementation cannot share a
// process -- the same split finding 111's harness uses for a Java subject.
// This script computes what `libicalWeeksInYearBlind` in ../src/diagnostics.js
// predicts; tests/test_libical_weeks_in_year_blind.py runs the same cases through the
// compiled C adapter against two real builds -- pristine 4edd39a3 and the
// one-line patch A -- and compares. Nothing here
// asserts anything, so that the library and the predictor are never read by
// the same process.
//
// Reads one JSON object per line on stdin: { id, dtstart, rrule, limit }, with
// an optional "ungated": true that switches the guard off so the python side
// can show each exclusion was necessary.
// Writes one JSON object per line on stdout:
//   { id, predicted: [...], fixed: [...], lost: [...], phantom: [...],
//     refused: bool }
// or { id, declined: true } when the guard refuses the rule, which the python
// side treats as a measurable claim and not as a pass.
import { parseDtstart, parts } from "../src/naive.js";
import { libicalWeeksInYearBlind } from "../src/diagnostics.js";

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
    o = libicalWeeksInYearBlind(c.rrule, t, c.limit, { ungated: c.ungated === true });
  } catch (e) {
    err = String((e && e.message) || e);
  }
  if (err) out.push({ id: c.id, error: err });
  else if (!o) out.push({ id: c.id, declined: true });
  else out.push({
    id: c.id,
    predicted: o.predicted.map(stamp),
    fixed: o.fixed.map(stamp),
    lost: o.lost.map(stamp),
    phantom: o.phantom.map(stamp),
    refused: o.refused,
  });
}
process.stdout.write(out.map((o) => JSON.stringify(o)).join("\n") + "\n");
