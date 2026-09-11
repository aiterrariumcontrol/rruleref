// "Is this what you meant?" -- an RRULE rendered as one English sentence.
//
// Why this exists, and why it is not the same as the ones that already exist.
//
// On libical/libical#1374, when two readings of BYSETPOS were being weighed
// against each other, CMendia reached for exactly this: translate the rule
// into plain English and see which reading the English matches. That is a
// reasonable instinct, and it is what the rendering has to be good enough for.
//
// It is not good enough today. rrule.js ships `toText()` and an
// `isFullyConvertibleToText()` guard. Over the 1613 distinct rules in this
// repository's corpus the guard says 1583 are fully convertible -- and among
// those, 301 rules fall into 35 groups where two rules with *different*
// occurrence sets are given the identical sentence. For instance
//
//   FREQ=DAILY;BYHOUR=9,8               -> "every day at 9 and 8"
//   FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1   -> "every day at 9 and 8"
//
// which fire twice a day and once a day respectively. A sentence that cannot
// tell those apart cannot settle an argument about BYSETPOS.
//
// So the property this module is built around, and which tests/test_describe.py
// checks over the whole corpus, is:
//
//   INJECTIVITY -- if two rules get the same sentence, they must have the
//   same expansion from the same DTSTART.
//
// plus the weaker but cheaper:
//
//   COVERAGE -- every RRULE part present in the input is accounted for by
//   some clause, and no clause is emitted without a part behind it.
//
// Neither property says the English is *well written*; a human has to judge
// that. What they do say is that it is not quietly dropping the part that
// changes the answer, which is the failure mode that makes a description
// worse than none at all.
//
// Every clause records the RRULE parts it speaks for, so the page can show
// which words came from which part of the rule.

import {
  DAYS, parts, weekday, daysInMonth, fmt, pinned, finer,
} from "./naive.js";

const DAYNAMES = { MO: "Monday", TU: "Tuesday", WE: "Wednesday", TH: "Thursday",
                   FR: "Friday", SA: "Saturday", SU: "Sunday" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
const PERIOD = { YEARLY: "year", MONTHLY: "month", WEEKLY: "week", DAILY: "day",
                 HOURLY: "hour", MINUTELY: "minute", SECONDLY: "second" };
const PLURAL = { YEARLY: "years", MONTHLY: "months", WEEKLY: "weeks", DAILY: "days",
                 HOURLY: "hours", MINUTELY: "minutes", SECONDLY: "seconds" };

const pad = (n) => String(n).padStart(2, "0");

export function ordinal(n) {
  const a = Math.abs(n);
  const t = a % 100;
  const suffix = t >= 11 && t <= 13 ? "th" : ["th", "st", "nd", "rd"][a % 10] || "th";
  return `${a}${suffix}`;
}

/** "a, b and c" -- the serial comma is deliberate; "1, 2 and 3" reads as a set. */
function and(xs) {
  if (xs.length <= 1) return xs.join("");
  if (xs.length === 2) return `${xs[0]} and ${xs[1]}`;
  return `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;
}

/** Which BY* keys the raw rule text actually carries. Defaults do not count. */
export function presentParts(rrule) {
  let s = String(rrule).trim();
  if (s.toUpperCase().startsWith("RRULE:")) s = s.slice(6);
  const out = new Set();
  for (const p of s.split(";")) {
    if (!p.trim()) continue;
    const k = p.split("=")[0].trim().toUpperCase();
    if (k) out.add(k);
  }
  return out;
}

// --- the pieces that name a value ----------------------------------------

function monthday(n) {
  if (n === -1) return "the last day of the month";
  if (n < 0) return `the ${ordinal(n)}-to-last day of the month`;
  return `the ${ordinal(n)}`;
}
function yearday(n) {
  if (n === -1) return "the last day of the year";
  if (n < 0) return `the ${ordinal(n)}-to-last day of the year`;
  return `day ${n} of the year`;
}
function bydayTerm([ord, day], freq, hasBymonth) {
  const name = DAYNAMES[day];
  if (ord === null) return name;
  // An ordinal BYDAY counts inside the month when the rule is monthly, or
  // yearly with BYMONTH; inside the year when it is yearly without. Anywhere
  // else RFC 5545 3.3.10 calls it an error, and the expander treats it as
  // unmatchable rather than silently ignoring it -- so say that.
  let span;
  if (freq === "MONTHLY" || (freq === "YEARLY" && hasBymonth)) span = "of the month";
  else if (freq === "YEARLY") span = "of the year";
  else return `${name} with the ordinal ${ord >= 0 ? "+" : ""}${ord}, which FREQ=${freq} gives no span to count in, so it can never match`;
  const which = ord === -1 ? "last" : ord < 0 ? `${ordinal(ord)}-to-last` : ordinal(ord);
  return `the ${which} ${name} ${span}`;
}
function setposTerm(n) {
  if (n === -1) return "the last";
  if (n < 0) return `the ${ordinal(n)} from the end`;
  return `the ${ordinal(n)}`;
}

/** Is WKST capable of changing this rule's expansion at all? */
export function wkstMatters(r, present) {
  if (present.has("BYWEEKNO")) return true;
  if (r.FREQ !== "WEEKLY") return false;
  return r.INTERVAL > 1 || present.has("BYSETPOS");
}

// --- the description ------------------------------------------------------

/**
 * Describe `r` (a parsed rule) as clauses and one sentence.
 *
 * `rrule` is the raw text, used only to tell a stated part from a default.
 * `dtstart` may be omitted; without it the clauses that quote DTSTART's own
 * values are left out, and the sentence says so rather than inventing them.
 *
 * Returns { sentence, clauses: [{ text, parts: [KEY...] }], covered: [KEY...] }.
 */
export function describe(r, rrule, dtstart = null, opts = {}) {
  const dateOnly = !!opts.dateOnly;
  const present = presentParts(rrule);
  const freq = r.FREQ;
  const clauses = [];
  const add = (kind) => (text, ...keys) => clauses.push({ text, kind, parts: keys });
  const base = add("base"), restrict = add("restrict"), time = add("time"), setpos = add("setpos");
  const note = (text, ...keys) => clauses.push({ text, kind: "note", parts: keys });

  if (!freq) {
    const t = "This rule has no FREQ, so it describes nothing; RFC 5545 requires one.";
    return { sentence: t, headline: t, clauses: [], covered: [] };
  }

  // 1. how often
  const every = r.INTERVAL === 1
    ? `Every ${PERIOD[freq]}`
    : `Every ${r.INTERVAL} ${PLURAL[freq]}`;
  base(every, "FREQ", ...(present.has("INTERVAL") ? ["INTERVAL"] : []));
  if (r.INTERVAL > 1 && dtstart) {
    note(`The ${PLURAL[freq]} are counted from the one containing DTSTART, not from any calendar boundary.`, "INTERVAL");
  }

  // 2. the limits, in the order RFC 5545 3.3.10 evaluates them
  if (present.has("BYMONTH")) {
    restrict(`in ${and(r.BYMONTH.map((m) => MONTHS[m - 1] || `month ${m}`))}`, "BYMONTH");
  }
  if (present.has("BYWEEKNO")) {
    // The week numbering needs a week start, and the rule may not state one.
    // Naming Monday without saying where it came from reads as if the rule
    // said so; RFC 5545 3.3.10 is where it actually comes from.
    const start = present.has("WKST")
      ? `starting on ${DAYNAMES[r.WKST]}`
      : `starting on Monday, the RFC 5545 default, since this rule has no WKST`;
    restrict(`in ${and(r.BYWEEKNO.map((w) => w < 0 ? `the ${ordinal(w)}-to-last week of the year` : `week ${w}`))}`
           + ` (weeks numbered ISO-style, ${start})`,
           "BYWEEKNO", ...(present.has("WKST") ? ["WKST"] : []));
  }
  if (present.has("BYYEARDAY")) {
    restrict(`on ${and(r.BYYEARDAY.map(yearday))}`, "BYYEARDAY");
  }
  if (present.has("BYMONTHDAY")) {
    restrict(`on ${and(r.BYMONTHDAY.map(monthday))}`, "BYMONTHDAY");
  }
  if (present.has("BYDAY")) {
    restrict(`on ${and(r.BYDAY.map((v) => bydayTerm(v, freq, present.has("BYMONTH"))))}`, "BYDAY");
  } else if (freq === "WEEKLY" && dtstart) {
    // The rule pins the weekday even though it never mentions one.
    restrict(`on ${DAYNAMES[DAYS[weekday(parts(dtstart).ord)]]}`, "FREQ");
    note("The weekday is not in the rule: FREQ=WEEKLY with no BYDAY takes it from DTSTART.", "FREQ");
  }
  for (const [key, noun, fmtv] of [
    ["BYHOUR", "hour", (v) => `${pad(v)}:00`],
    ["BYMINUTE", "minute", (v) => `minute ${pad(v)}`],
    ["BYSECOND", "second", (v) => `second ${pad(v)}`],
  ]) {
    if (present.has(key)) time(`${and(r[key].map(fmtv))}`, key);
    else void noun;
  }

  // 3. what the unstated finer components inherit. This is the clause no
  //    other renderer has, and it is the answer to "why does my monthly rule
  //    not fire on every day of the month".
  if (dtstart) {
    const pin = pinned(r, freq);
    const ds = parts(dtstart);
    const NOUN = { mo: ["month", (p) => MONTHS[p.mo - 1]],
                   d: ["day of the month", (p) => `the ${ordinal(p.d)}`],
                   h: ["hour", (p) => pad(p.h)],
                   mi: ["minute", (p) => pad(p.mi)],
                   s: ["second", (p) => pad(p.s)] };
    const inherited = finer(freq).filter((c) => !pin.has(c))
      .filter((c) => !(dateOnly && (c === "h" || c === "mi" || c === "s")));
    if (inherited.length) {
      const bits = inherited.map((c) => `${NOUN[c][0]} ${NOUN[c][1](ds)}`);
      note(`Nothing in the rule fixes the ${and(inherited.map((c) => NOUN[c][0]))}, so ${inherited.length === 1 ? "it stays" : "they stay"} at DTSTART's: ${and(bits)}.`,
           "FREQ");
    }
  }

  // 4. BYSETPOS last, because it selects from what everything above produced,
  //    and name the period it selects within -- that is the whole of the
  //    disagreement it usually causes.
  if (present.has("BYSETPOS")) {
    setpos(`and then only ${and(r.BYSETPOS.map(setposTerm))} of the times that ${PERIOD[freq]} produces`,
           "BYSETPOS");
  }

  // 5. WKST, but only when it can change the answer. Saying "weeks start on
  //    Monday" about a rule where the week boundary is never consulted is
  //    true and misleading.
  if (present.has("WKST") && !present.has("BYWEEKNO")) {
    if (wkstMatters(r, present)) {
      note(`Weeks start on ${DAYNAMES[r.WKST]}, which moves the ${PERIOD[freq]} boundaries this rule counts in.`, "WKST");
    } else {
      note(`WKST=${r.WKST} is stated but cannot change this rule's occurrences.`, "WKST");
    }
  }

  // 6. the stop condition
  // 6. the stop condition, as its own sentence -- it is a separate fact about
  //    the rule, and burying it in a comma list is how it gets skimmed past.
  const stop = [];
  if (present.has("COUNT")) stop.push({ text: `Stops after ${r.COUNT} occurrence${r.COUNT === 1 ? "" : "s"} in total.`, parts: ["COUNT"] });
  if (present.has("UNTIL")) stop.push({ text: `No occurrences after ${fmt(r.UNTIL, dateOnly)}.`, parts: ["UNTIL"] });
  if (!stop.length) stop.push({ text: "Repeats forever.", parts: ["FREQ"] });
  for (const st of stop) clauses.push({ ...st, kind: "stop" });

  const pick = (k) => clauses.filter((c) => c.kind === k).map((c) => c.text);
  const times = pick("time"), restricts = pick("restrict"), sp = pick("setpos");
  let head = pick("base")[0];
  if (times.length) head += ` at ${times.join(", ")}`;
  if (restricts.length) head += `, but only ${restricts.join(", ")}`;
  if (sp.length) head += `, ${sp.join(", ")}`;
  head += ".";
  const sentence = [head, ...pick("note"), ...pick("stop")].join(" ");
  const covered = [...new Set(clauses.flatMap((c) => c.parts))];
  return { sentence, headline: head, clauses, covered: covered.sort() };
}
