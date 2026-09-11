// Emit the `weekly-bymonth-seed-limit` diagnostic's seed-limit expansion for
// each rule on stdin, so it can be checked against the independent Python
// reference implementation in findings/repro/022-seed-limit-reading.py.
//
// stdin:  one JSON object per line, {id, rrule, dtstart, limit}
// stdout: one JSON object per line, {id, occurrences, seedLimit|null, severity}
import { expand, parseDtstart, fmt } from "../src/naive.js";
import { analyze } from "../src/diagnostics.js";

let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { buf += d; });
process.stdin.on("end", () => {
  for (const line of buf.split("\n")) {
    if (!line.trim()) continue;
    const c = JSON.parse(line);
    const dtstart = parseDtstart(c.dtstart).t;
    const occurrences = expand(c.rrule, dtstart, { limit: c.limit });
    const notes = analyze({
      rrule: c.rrule, dtstart, dateOnly: true, occurrences, limit: c.limit,
    });
    const note = notes.find((n) => n.id === "weekly-bymonth-seed-limit");
    process.stdout.write(JSON.stringify({
      id: c.id,
      occurrences: occurrences.map((t) => fmt(t, true)),
      seedLimit: note ? note.compare.occurrences.slice(0, c.limit) : null,
      severity: note ? note.severity : null,
      dropsDtstart: note ? /DTSTART itself is not in it/.test(note.body) : null,
    }) + "\n");
  }
});
