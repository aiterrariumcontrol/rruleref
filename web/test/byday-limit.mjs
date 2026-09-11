// Does the sentence tell the reader that BYDAY is subtracting, not adding?
//
// RFC 5545 3.3.10's table gives BYDAY as an expanding part, with two
// exceptions in its footnotes: Note 1 makes it a limit for MONTHLY when
// BYMONTHDAY is present, Note 2 for YEARLY when BYYEARDAY or BYMONTHDAY is.
// Those two footnotes are the most-missed lines in the specification. Read as
// a union instead of an intersection, `FREQ=MONTHLY;BYMONTHDAY=13;BYDAY=FR`
// stops meaning Friday the 13th and starts meaning every Friday -- which is a
// bug people actually file against shipped calendars.
//
// describe() emits a note for exactly that combination. Two properties here.
//
//   CONDITION  The note appears on exactly the rules the two footnotes name,
//              and on no others. Checked against the rule text directly.
//
//   TRUTH      Where the note appears, its claim holds: BYDAY contributes no
//              dates of its own. The expansion must be a subset of the same
//              rule with BYDAY deleted.
//
//              Only inside the window both expansions cover. Dropping BYDAY
//              makes a rule fire more often, so its Nth occurrence is earlier;
//              comparing past that point reports dates as "added by BYDAY"
//              when they are merely beyond where the other list stopped.
//
//              BYSETPOS selects from whatever the other parts leave, so
//              deleting BYDAY there moves which member is picked rather than
//              only removing members -- six corpus rules showed this. The
//              claim is about the candidate set, so for those rules BYSETPOS
//              is deleted from both sides before comparing.
//
// Prints, as evidence that the subset check can fail at all, how many of the
// rules where BYDAY *expands* violate it.
//
// Reads the corpus on stdin as JSON; exits non-zero on any violation.
import { parseDtstart, parse, expand, fmt } from "../src/naive.js";
import { describe, presentParts } from "../src/describe.js";

const cases = JSON.parse(await new Promise((res) => {
  let s = ""; process.stdin.setEncoding("utf8");
  process.stdin.on("data", (d) => (s += d)); process.stdin.on("end", () => res(s));
}));

const MARK = "BYDAY narrows here";
const without = (s, re) => s.split(";").filter((p) => !re.test(p)).join(";");
const BYDAY = /^BYDAY=/i, BYSETPOS = /^BYSETPOS=/i;

let checked = 0, fired = 0, tested = 0, expandingChecked = 0, expandingViolations = 0;
const fails = [];

const occ = (rrule, t, limit) => expand(rrule, t, { limit }).map((x) => Number(x));

for (const c of cases) {
  let ds, r, d, present;
  try {
    ds = parseDtstart(c.dtstart);
    r = parse(c.rrule);
    present = presentParts(c.rrule);
    d = describe(r, c.rrule, ds.t, { dateOnly: ds.dateOnly });
  } catch (e) {
    continue;
  }
  checked++;

  // --- CONDITION, restated from the RFC footnotes rather than from the code
  const limitedByFootnote = present.has("BYDAY") && (
    ((r.FREQ === "MONTHLY" || r.FREQ === "YEARLY") && present.has("BYMONTHDAY")) ||
    (r.FREQ === "YEARLY" && present.has("BYYEARDAY")));
  const said = d.sentence.includes(MARK);
  if (said !== limitedByFootnote) {
    fails.push(`${c.rrule}: note ${said ? "present" : "absent"} but 3.3.10 says BYDAY `
             + `${limitedByFootnote ? "limits" : "expands"} here`);
    continue;
  }

  // --- TRUTH, for the rules the note fires on
  if (!present.has("BYDAY")) continue;
  const base = without(c.rrule, BYSETPOS);   // candidate set, before selection
  let a, b;
  try {
    a = occ(base, ds.t, 40);
    b = occ(without(base, BYDAY), ds.t, 4000);
  } catch (e) { continue; }
  if (!a.length || !b.length) continue;
  const window = Math.min(a[a.length - 1], b[b.length - 1]);
  const inB = new Set(b);
  const added = a.filter((x) => x <= window && !inB.has(x));

  if (limitedByFootnote) {
    fired++; tested++;
    if (added.length) {
      fails.push(`${c.rrule} @${c.dtstart}: note claims BYDAY only removes, but it adds `
               + `${added.length} date(s) the rule without BYDAY does not produce, `
               + `first ${fmt(added[0])}`);
    }
  } else {
    expandingChecked++;
    if (added.length) expandingViolations++;
  }
}

console.log(`BYDAY limit note: ${checked} corpus cases parsed`);
console.log(`  3.3.10 Note 1/Note 2 applies, note emitted: ${fired}`);
console.log(`  subset-of-BYDAY-less property checked on: ${tested}`);
console.log(`  control -- rules where BYDAY expands: ${expandingChecked}, of which `
          + `${expandingViolations} do add dates (the property can fail)`);
if (fails.length) {
  console.log(`${fails.length} failure(s):`);
  for (const f of fails.slice(0, 25)) console.log("  - " + f);
  process.exit(1);
}
console.log("OK: the note fires on exactly 3.3.10's two footnotes, and its claim holds on every one.");
