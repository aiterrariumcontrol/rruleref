// "Why is this date not in my list?" -- part-by-part, for one date.
//
// The commonest question about a recurrence rule is not what it expands to.
// It is why one particular date the user expected is missing, or why one they
// did not expect is there. See jkbrzt/rrule#621, where the reporter's whole
// description of the bug is "it skips the correct one and gives me the one
// after": the rule and the dates were both in front of them, and neither said
// which rule part did it.
//
// This module answers that for a single date. It deliberately does NOT
// re-decide whether the date is an occurrence -- `naive.js` decides that, the
// same code that produced the list on the page. Every predicate below is
// imported from the expander rather than rewritten, and the assembled verdict
// is compared against `matches()` and against membership of the real expansion
// before it is shown. If they ever disagree the answer says so instead of
// picking one; `tests/test_why.py` replays the corpus through both.
//
// Order of the checks follows RFC 5545 3.3.10, which fixes it.

import {
  parse, parts, fmt, mk, toOrd, fromOrd, weekday, daysInMonth, weekNumber,
  periodIndex, periodStart, matches, expand, Budget,
  monthdayMatches, yeardayMatches, weeknoMatches, bydayMatches, pinned, finer,
  DAYS, FREQS,
} from "./naive.js";

const RFC = (section, anchor) => ({
  label: `RFC 5545 ${section}`,
  url: `https://www.rfc-editor.org/rfc/rfc5545.html#section-${anchor}`,
});
const S3310 = RFC("§3.3.10", "3.3.10");
const S3853 = RFC("§3.8.5.3", "3.8.5.3");

const DAYNAMES = { MO: "Monday", TU: "Tuesday", WE: "Wednesday", TH: "Thursday",
                   FR: "Friday", SA: "Saturday", SU: "Sunday" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
const COMP = {
  mo: { noun: "month", of: (p) => `${MONTHS[p.mo - 1]}`, rules: "BYMONTH" },
  d: { noun: "day of the month", of: (p) => `the ${ordinal(p.d)}`,
       rules: "BYMONTHDAY, BYDAY, BYYEARDAY or BYWEEKNO" },
  h: { noun: "hour", of: (p) => `${pad(p.h)}`, rules: "BYHOUR" },
  mi: { noun: "minute", of: (p) => `${pad(p.mi)}`, rules: "BYMINUTE" },
  s: { noun: "second", of: (p) => `${pad(p.s)}`, rules: "BYSECOND" },
};
const pad = (n) => String(n).padStart(2, "0");
function ordinal(n) {
  const t = n % 100;
  if (t >= 11 && t <= 13) return `${n}th`;
  return `${n}${["th", "st", "nd", "rd"][n % 10] || "th"}`;
}
function human(t, dateOnly) {
  const p = parts(t);
  const day = DAYNAMES[DAYS[weekday(p.ord)]];
  const date = `${day} ${p.y}-${pad(p.mo)}-${pad(p.d)}`;
  return dateOnly ? date : `${date} at ${pad(p.h)}:${pad(p.mi)}:${pad(p.s)}`;
}
const list = (xs) => xs.join(", ");

/**
 * Read the date the user is asking about. Accepts the same shapes as DTSTART,
 * plus the ISO-ish forms a person types by hand.
 */
export function parseQuery(v, dateOnly) {
  let t = String(v).trim().replace(/^DTSTART[^:]*:/i, "").trim().replace(/Z$/i, "");
  t = t.replace(/[/.]/g, "-");
  let m = /^(\d{4})-?(\d{2})-?(\d{2})[T ]?(\d{2}):?(\d{2})(?::?(\d{2}))?$/.exec(t);
  if (m) return { t: mk(+m[1], +m[2], +m[3], +m[4], +m[5], +(m[6] || 0)), hadTime: true };
  m = /^(\d{4})-?(\d{2})-?(\d{2})$/.exec(t);
  if (m) return { t: mk(+m[1], +m[2], +m[3]), hadTime: false };
  throw new Error(`cannot read ${JSON.stringify(v)} as a date; try 20260130 or 20260130T090000`);
}

// --- the part-by-part checks ---------------------------------------------
//
// Each returns { id, ok, title, detail, evidence }. `ok: null` means the check
// does not apply to this rule and is not shown as a hurdle the date cleared.

function byChecks(t, r, dtstart, dateOnly) {
  const p = parts(t), ds = parts(dtstart);
  const freq = r.FREQ, wkst = r.WKST;
  const out = [];
  const add = (id, ok, title, detail, evidence = [S3310]) =>
    out.push({ id, ok, title, detail, evidence });

  // FREQ + INTERVAL: is the date even in a period the rule visits?
  const n = periodIndex(t, freq, wkst) - periodIndex(dtstart, freq, wkst);
  if (r.INTERVAL === 1) {
    add("interval", true, `FREQ=${freq}`,
        `Every ${periodNoun(freq)} is visited (INTERVAL is 1, its default), and this date is ` +
        `${n === 0 ? "in the same" : `${Math.abs(n)} ${periodNoun(freq)}${Math.abs(n) === 1 ? "" : "s"} ` +
          (n > 0 ? "after the" : "before the")} ${periodNoun(freq)} DTSTART is in.`);
  } else {
    const ok = n % r.INTERVAL === 0;
    add("interval", ok, `FREQ=${freq};INTERVAL=${r.INTERVAL}`,
        `Number the ${periodNoun(freq)}s from DTSTART's, which is 0. This date is in ${periodNoun(freq)} ` +
        `${n}. The rule visits every ${r.INTERVAL}${nth(r.INTERVAL)} one, so it reaches ${n} only if ` +
        `${n} is a multiple of ${r.INTERVAL}` +
        (ok ? `, and it is.` : `. It is not: ${n} = ${r.INTERVAL}×${Math.trunc(n / r.INTERVAL)} + ` +
          `${((n % r.INTERVAL) + r.INTERVAL) % r.INTERVAL}.`));
  }

  if ("BYMONTH" in r) {
    add("BYMONTH", r.BYMONTH.includes(p.mo), `BYMONTH=${list(r.BYMONTH)}`,
        `This date is in ${MONTHS[p.mo - 1]} (month ${p.mo}).`);
  }
  if ("BYWEEKNO" in r) {
    const got = weekNumber(p.ord, wkst);
    add("BYWEEKNO", weeknoMatches(p, r.BYWEEKNO, wkst), `BYWEEKNO=${list(r.BYWEEKNO)}`,
        got === null
          ? `This date falls before week 1 of its own year under WKST=${wkst}, so it is in no ` +
            `week of it. Week numbering here is ISO 8601's, which WKST moves: week 1 is the first ` +
            `week with at least four days in the year.`
          : `Under WKST=${wkst} this date is in week ${got[1]} of ${got[0]}` +
            (got[0] !== p.y ? ` — a different year from the date's own, which is what week ` +
              `numbering does at a year boundary.` : `.`));
  }
  if ("BYYEARDAY" in r) {
    const doy = p.ord - toOrd(p.y, 1, 1) + 1;
    add("BYYEARDAY", yeardayMatches(p, r.BYYEARDAY), `BYYEARDAY=${list(r.BYYEARDAY)}`,
        `This date is day ${doy} of ${p.y}, and day ${doy - (isLeapYear(p.y) ? 366 : 365) - 1} ` +
        `counting back from the end.`);
  }
  if ("BYMONTHDAY" in r) {
    const last = daysInMonth(p.y, p.mo);
    add("BYMONTHDAY", monthdayMatches(p, r.BYMONTHDAY), `BYMONTHDAY=${list(r.BYMONTHDAY)}`,
        `This date is the ${ordinal(p.d)} of a ${last}-day month, so it is also ` +
        `${p.d - last - 1} counting back from the end.`);
  }
  if ("BYDAY" in r) {
    const wd = DAYS[weekday(p.ord)];
    const spans = bydaySpan(p, freq, "BYMONTH" in r);
    add("BYDAY", bydayMatches(p, r.BYDAY, freq, "BYMONTH" in r),
        `BYDAY=${r.BYDAY.map(([o, d]) => (o === null ? "" : (o > 0 ? `+${o}` : o)) + d).join(",")}`,
        `This date is a ${DAYNAMES[wd]}` + (spans ? `, and the ${ordinal(spans[0])} ${DAYNAMES[wd]} ` +
          `of ${spans[2]} — also the ${ordinal(spans[1] - spans[0] + 1)} from its end.` : `. Under ` +
          `FREQ=${freq} a number in front of a weekday has no period to count within, so this rule ` +
          `part can select only bare weekdays.`));
  }
  for (const [key, comp, noun] of [["BYHOUR", "h", "hour"], ["BYMINUTE", "mi", "minute"],
                                   ["BYSECOND", "s", "second"]]) {
    if (!(key in r)) continue;
    add(key, r[key].includes(p[comp]), `${key}=${list(r[key])}`,
        `This time's ${noun} is ${p[comp]}.`);
  }

  // FREQ=WEEKLY with no BYDAY: the weekday comes from DTSTART.
  if (freq === "WEEKLY" && !("BYDAY" in r)) {
    const ok = weekday(p.ord) === weekday(ds.ord);
    add("weekly-weekday", ok, "the weekday comes from DTSTART",
        `The rule names no BYDAY, so the only weekday it can mean is DTSTART's, which is ` +
        `${DAYNAMES[DAYS[weekday(ds.ord)]]}. This date is a ${DAYNAMES[DAYS[weekday(p.ord)]]}.`,
        [S3853]);
  }

  // Everything finer than FREQ that no BY rule pins down is inherited from
  // DTSTART. This is the one that surprises people: setting BYHOUR does not
  // free the minutes, and a MONTHLY rule does not fire on all 31 days.
  const pin = pinned(r, freq);
  for (const comp of finer(freq)) {
    if (pin.has(comp)) continue;
    const c = COMP[comp];
    const ok = p[comp] === ds[comp];
    add(`inherit-${comp}`, ok, `the ${c.noun} comes from DTSTART`,
        `FREQ=${freq} does not fix the ${c.noun}, and no ${c.rules} in this rule does either, so ` +
        `it stays at DTSTART's: ${c.of(ds)}. This date's is ${c.of(p)}.`, [S3853]);
  }
  return out;
}

function isLeapYear(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }
function nth(n) { return n === 2 ? "nd" : n === 3 ? "rd" : "th"; }
function periodNoun(freq) {
  return { YEARLY: "year", MONTHLY: "month", WEEKLY: "week", DAILY: "day",
           HOURLY: "hour", MINUTELY: "minute", SECONDLY: "second" }[freq];
}
/** [nth of its weekday in the span, how many there are, name of the span] */
function bydaySpan(p, freq, hasBymonth) {
  let lo, hi, name;
  if (freq === "MONTHLY" || (freq === "YEARLY" && hasBymonth)) {
    lo = toOrd(p.y, p.mo, 1); hi = toOrd(p.y, p.mo, daysInMonth(p.y, p.mo));
    name = `${MONTHS[p.mo - 1]} ${p.y}`;
  } else if (freq === "YEARLY") {
    lo = toOrd(p.y, 1, 1); hi = toOrd(p.y, 12, 31); name = String(p.y);
  } else {
    return null;
  }
  const first = lo + ((weekday(p.ord) - weekday(lo) + 7) % 7);
  return [Math.floor((p.ord - first) / 7) + 1, Math.floor((hi - first) / 7) + 1, name];
}

/**
 * Which instant did the user mean?
 *
 * A DTSTART with a time of day makes every occurrence an instant, but people
 * type a bare date -- "why is 2026-01-29 not in there?" -- and mean the day.
 * Answering about midnight on that day is true and useless: it explains a
 * date they never asked about, and the failing check is always the inherited
 * hour.
 *
 * So a time-less question about a rule with times is resolved to a time on
 * that day: the one the rule actually produces there if it produces one,
 * otherwise DTSTART's own time of day. Either way the caller is told, because
 * the answer is then about an instant the user did not type.
 *
 * The candidate times below mirror the expander's own; this is only a reading
 * of the *question*, though. Whatever instant comes out is still put through
 * why(), and through matches(), before anything is claimed about it.
 */
export function resolveQuery(r, dtstart, q, dateOnly) {
  if (dateOnly || q.hadTime) return { t: q.t, note: null };
  const ds = parts(dtstart);
  const day = Math.floor(q.t / 86400) * 86400;
  const seq = (n) => Array.from({ length: n }, (_, i) => i);
  const freq = r.FREQ;
  const hours = "BYHOUR" in r ? r.BYHOUR
    : (["HOURLY", "MINUTELY", "SECONDLY"].includes(freq) ? seq(24) : [ds.h]);
  const mins = "BYMINUTE" in r ? r.BYMINUTE
    : (["MINUTELY", "SECONDLY"].includes(freq) ? seq(60) : [ds.mi]);
  const secs = "BYSECOND" in r ? r.BYSECOND : (freq === "SECONDLY" ? seq(60) : [ds.s]);
  const hit = [];
  for (const h of hours) for (const mi of mins) for (const s of secs) {
    const t = day + h * 3600 + mi * 60 + s;
    if (t >= dtstart && matches(t, r, dtstart)) hit.push(t);
  }
  hit.sort((a, b) => a - b);
  if (hit.length) {
    return {
      t: hit[0],
      // "the time the rule's parts point at", not "the time it produces":
      // BYSETPOS can still drop this instant, and the verdict below may say
      // exactly that.
      note: `You asked about a date, and this rule works in times of day. Taking the ` +
            (hit.length === 1 ? `one time of day its parts point at there` :
             `first of the ${hit.length} times of day its parts point at there`) +
            `: ${fmt(hit[0])}.`,
    };
  }
  const t = day + ds.h * 3600 + ds.mi * 60 + ds.s;
  return {
    t,
    note: `You asked about a date, and this rule works in times of day. Its parts point at no time ` +
          `at all on that day, so the question is answered at DTSTART's own time of day, ${fmt(t)}.`,
  };
}

// --- the verdict ----------------------------------------------------------

/**
 * Why is `t` in, or not in, the recurrence set of `rrule` from `dtstart`?
 *
 * Returns { status, headline, checks, index, evidence, compare }.
 * status: "occurrence" | "before-dtstart" | "rule" | "bysetpos" | "until"
 *       | "count" | "unknown" | "inconsistent"
 */
export function why(rrule, dtstart, t, opts = {}) {
  const dateOnly = !!opts.dateOnly;
  const r = typeof rrule === "string" ? parse(rrule) : rrule;
  if (!FREQS.includes(r.FREQ)) throw new Error(`FREQ: ${JSON.stringify(r.FREQ)} is not a frequency`);
  const said = human(t, dateOnly);

  if (t < dtstart) {
    return {
      status: "before-dtstart", index: null, checks: [],
      headline: `No — ${said} is before DTSTART, so no rule part can put it in the set.`,
      body: "A recurrence rule never generates anything earlier than DTSTART: RFC 5545 §3.8.5.3 " +
            "says “The ‘DTSTART’ property defines the first instance in the recurrence set.” " +
            "If this date should be in the event, DTSTART is what has to move — or it belongs in " +
            "an RDATE, which this tool does not expand.",
      evidence: [S3853],
    };
  }

  const checks = byChecks(t, r, dtstart, dateOnly);
  const failed = checks.filter((c) => c.ok === false);
  const agrees = matches(t, r, dtstart);
  if (agrees !== (failed.length === 0)) {
    return {
      status: "inconsistent", index: null, checks,
      headline: "This tool cannot explain this date.",
      body: "The part-by-part check above and the expander that produced the list disagree about " +
            "this date. That is a bug in this tool, not in your rule. Please report it with the " +
            "link in the address bar — a case that breaks it is the most useful thing to send.",
      evidence: [],
    };
  }

  if (failed.length) {
    const first = failed[0];
    return {
      status: "rule", index: null, checks,
      headline: `No — ${said} is not what this rule describes.`,
      body: failed.length === 1
        ? `One rule part rules it out: ${first.title}.`
        : `${failed.length} of the rule's parts rule it out; the first, in the order §3.3.10 ` +
          `applies them, is ${first.title}.`,
      evidence: [S3310],
    };
  }

  // It matches the pattern. What is left is the machinery that runs *after*
  // the BYxxx parts: BYSETPOS selects within a period, and COUNT and UNTIL cut
  // the sequence. §3.3.10 fixes that order.
  let plain;
  const bare = { ...r };
  delete bare.COUNT; delete bare.UNTIL;
  try {
    plain = expand(bare, dtstart, { horizon: t, limit: 1e9, maxSteps: opts.maxSteps ?? 2e6 });
  } catch (e) {
    if (!(e instanceof Budget)) throw e;
    return {
      status: "unknown", index: null, checks,
      headline: `${said} matches every part of this rule, but this tool could not count that far.`,
      body: `Deciding whether it is actually in the set means expanding the rule from DTSTART up ` +
            `to it, and that ${e.message}. Every rule part above still holds. Try a DTSTART ` +
            `nearer the date you are asking about.`,
      evidence: [],
    };
  }

  const idx = plain.indexOf(t);
  if (idx < 0) {
    // Only BYSETPOS can drop a date that matched every BYxxx part.
    const info = setposDetail(r, dtstart, t, dateOnly);
    return {
      status: "bysetpos", index: null, checks,
      headline: `No — ${said} matches every part of the rule, and then BYSETPOS drops it.`,
      body: info,
      evidence: [S3310],
    };
  }
  if ("UNTIL" in r && t > r.UNTIL) {
    return {
      status: "until", index: null, checks,
      headline: `No — ${said} is what the rule describes, but it is past UNTIL.`,
      body: `UNTIL is ${fmt(r.UNTIL, dateOnly)}, and §3.3.10 says “The UNTIL rule part defines a ` +
            `DATE or DATE-TIME value that bounds the recurrence rule in an inclusive manner.” ` +
            `Inclusive: a date exactly equal to UNTIL is still in. This one is later. Without ` +
            `UNTIL it would have been occurrence ${idx + 1}.`,
      evidence: [S3310],
    };
  }
  if ("COUNT" in r && idx + 1 > r.COUNT) {
    return {
      status: "count", index: null, checks,
      headline: `No — ${said} is what the rule describes, but COUNT has already run out.`,
      body: `It would be occurrence ${idx + 1}, and COUNT is ${r.COUNT}. §3.3.10: “The ` +
            `‘DTSTART’ property value always counts as the first occurrence.” So a ` +
            `COUNT of ${r.COUNT} reaches ${fmt(plain[r.COUNT - 1], dateOnly)} and stops.`,
      evidence: [S3310],
    };
  }
  return {
    status: "occurrence", index: idx + 1, checks,
    headline: idx === 0
      ? `Yes — ${said} is the first occurrence. It is DTSTART.`
      : `Yes — ${said} is occurrence ${idx + 1}.`,
    body: checks.length
      ? `Every part of the rule holds for it:`
      : `The rule has nothing to check beyond its frequency.`,
    evidence: [],
  };
}

/** What BYSETPOS saw in this date's period, and why it did not pick this one. */
function setposDetail(r, dtstart, t, dateOnly) {
  const start = periodStart(t, r.FREQ, r.WKST);
  const key = periodIndex(t, r.FREQ, r.WKST);
  const bare = { ...r };
  delete bare.BYSETPOS; delete bare.COUNT; delete bare.UNTIL;
  let inPeriod;
  try {
    inPeriod = expand(bare, start < dtstart ? dtstart : start, {
      horizon: t + 400 * 86400, limit: 400, maxSteps: 2e6,
    }).filter((x) => periodIndex(x, r.FREQ, r.WKST) === key);
  } catch {
    return `BYSETPOS=${list(r.BYSETPOS)} selects only some of the dates the rest of the rule ` +
           `matches in each ${periodNoun(r.FREQ)}, and this date is not among the selected ones.`;
  }
  const pos = inPeriod.indexOf(t) + 1;
  const shown = inPeriod.map((x) => fmt(x, dateOnly));
  return `§3.3.10: “BYSETPOS operates on a set of recurrence instances in one interval of the ` +
         `recurrence rule.” The interval here is one ${periodNoun(r.FREQ)}, and in it the rest of ` +
         `the rule matches ${inPeriod.length} date${inPeriod.length === 1 ? "" : "s"}: ` +
         `${abridge(shown)}. This date is ${pos > 0 ? `number ${pos} of ${inPeriod.length} ` +
         `(also ${pos - inPeriod.length - 1} counting back)` : "not in that set"}, and ` +
         `BYSETPOS=${list(r.BYSETPOS)} does not name it.`;
}

/** A set of dates a reader can take in: the ends, and a count for the middle. */
function abridge(xs, keep = 3) {
  if (xs.length <= keep * 2 + 1) return xs.join(", ");
  return `${xs.slice(0, keep).join(", ")}, … (${xs.length - keep * 2} more) …, ` +
         `${xs.slice(-keep).join(", ")}`;
}
