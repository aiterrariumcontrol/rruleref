// What did that edit actually do to my schedule?
//
// The failure this answers is not hypothetical. Superset's schedule picker
// silently rewrote `FREQ=DAILY;BYHOUR=9,17` as `FREQ=DAILY;BYHOUR=9` when the
// user touched an unrelated field, turning a twice-daily job into a
// once-daily one with nothing on screen to show it (superset-sh/superset,
// issue 5670). The same shape recurs wherever a UI round-trips a rule through
// a simplified model: the rule that comes back is a different rule, and the
// difference is invisible because both render as reasonable-looking RRULEs.
//
// Two rules, one DTSTART, and the question is exactly: which dates did I
// lose, which did I gain, and which are unchanged.
//
// THE CAP IS NOT A PROPERTY OF THE RULES. Each expansion is truncated at the
// occurrence count the user asked for. Two truncated lists say nothing about
// what happens after the earlier of their two last occurrences, so the
// comparison is restricted to the window both lists cover and that window is
// stated on the page. Without this a rule that merely fires more often looks
// like a rule that drops every later date.
import { expand } from "./naive.js";

/**
 * Compare the recurrence sets of two parsed rules from one DTSTART.
 *
 * @param {object} a    parsed rule, as from parse()
 * @param {object} b    parsed rule
 * @param {number} dtstart
 * @param {{limit?: number, maxSteps?: number}} opts
 * @returns {{
 *   both: number[], onlyA: number[], onlyB: number[],
 *   same: boolean, complete: boolean, until: number|null,
 *   countA: number, countB: number
 * }}
 */
export function compareRules(a, b, dtstart, opts = {}) {
  const limit = opts.limit || 24;
  const maxSteps = opts.maxSteps || 8e6;
  const A = expand(a, dtstart, { limit, maxSteps });
  const B = expand(b, dtstart, { limit, maxSteps });

  // A list shorter than the cap is the whole recurrence set, and covers every
  // future date. A list at the cap was cut off, and covers nothing after its
  // own last occurrence.
  const horizon = (occ) => (occ.length < limit ? Infinity
                            : occ.length ? occ[occ.length - 1] : Infinity);
  const until = Math.min(horizon(A), horizon(B));
  const complete = until === Infinity;

  const inWindow = (occ) => occ.filter((t) => t <= until);
  const wa = inWindow(A), wb = inWindow(B);
  const sb = new Set(wb), sa = new Set(wa);

  const both = wa.filter((t) => sb.has(t));
  const onlyA = wa.filter((t) => !sb.has(t));
  const onlyB = wb.filter((t) => !sa.has(t));

  return {
    both, onlyA, onlyB,
    same: onlyA.length === 0 && onlyB.length === 0,
    complete,
    until: complete ? null : until,
    countA: wa.length,
    countB: wb.length,
  };
}

const n = (k, word) => `${k} ${word}${k === 1 ? "" : "s"}`;

/**
 * One sentence a reader can act on, plus the qualification that sentence
 * depends on. Kept apart from compareRules() so the facts can be checked by a
 * test without the prose.
 *
 * @param {ReturnType<typeof compareRules>} c
 * @param {(t: number) => string} fmtDate  renders one occurrence for display
 */
export function summarize(c, fmtDate) {
  const scope = c.complete
    ? "over the whole of both recurrence sets"
    : `up to ${fmtDate(c.until)}, which is as far as both lists reach`;

  let headline;
  if (c.same && c.countA === 0) {
    headline = "Neither rule produces any dates here.";
  } else if (c.same) {
    headline = "Both rules produce exactly the same dates.";
  } else if (c.onlyA.length && !c.onlyB.length) {
    headline = `The second rule drops ${n(c.onlyA.length, "date")} and adds none.`;
  } else if (c.onlyB.length && !c.onlyA.length) {
    headline = `The second rule adds ${n(c.onlyB.length, "date")} and drops none.`;
  } else {
    headline = `The second rule drops ${n(c.onlyA.length, "date")} and adds ` +
               `${n(c.onlyB.length, "date")}.`;
  }

  const notes = [];
  notes.push(c.same
    ? `Checked ${scope}.`
    : `${n(c.both.length, "date")} unchanged. Compared ${scope}.`);
  if (!c.complete) {
    notes.push("Both rules were cut off at the occurrence count you asked for, " +
               "so nothing here is a claim about dates after that. Raise the " +
               "count to compare further.");
  }
  return { headline, notes };
}
