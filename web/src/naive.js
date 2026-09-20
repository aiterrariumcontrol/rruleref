// A port of src/naive.py -- the deliberately naive, spec-derived RFC 5545
// RRULE expander -- to dependency-free ES modules for the browser.
//
// The Python original is the reference. tests: web/test/parity.mjs replays
// corpus cases through both and requires identical output; any change here
// must keep that at zero mismatches.
//
// Dates are proleptic-Gregorian *civil* values with no time zone. A datetime
// is a single integer: dayNumber * 86400 + secondsOfDay, where dayNumber
// matches Python's date.toordinal() (0001-01-01 == 1). That makes ordering a
// numeric comparison and keeps every arithmetic step exact in a double
// (max ~3.2e10, well inside 2^53).

export const FREQS = ["SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"];
export const DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

const DIM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

export function isLeap(y) {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}
export function daysInMonth(y, m) {
  return m === 2 && isLeap(y) ? 29 : DIM[m - 1];
}
function daysBeforeYear(y) {
  const n = y - 1;
  return n * 365 + Math.floor(n / 4) - Math.floor(n / 100) + Math.floor(n / 400);
}
function daysBeforeMonth(y, m) {
  let t = 0;
  for (let i = 1; i < m; i++) t += daysInMonth(y, i);
  return t;
}
/** Python date.toordinal(). */
export function toOrd(y, m, d) {
  return daysBeforeYear(y) + daysBeforeMonth(y, m) + d;
}
/** Python date.fromordinal(). Returns [y, m, d]. */
export function fromOrd(n) {
  let y = Math.floor(n / 366) + 1;
  while (daysBeforeYear(y + 1) < n) y++;
  let rest = n - daysBeforeYear(y);
  let m = 1;
  while (rest > daysInMonth(y, m)) { rest -= daysInMonth(y, m); m++; }
  return [y, m, rest];
}
/** Python date.weekday(): Monday == 0. Ordinal 1 (0001-01-01) is a Monday. */
export function weekday(ord) {
  return (ord - 1) % 7;
}
/** Day-of-year, 1-based. */
function yearDay(y, m, d) {
  return daysBeforeMonth(y, m) + d;
}

// --- the datetime integer -------------------------------------------------

export function mk(y, mo, d, h = 0, mi = 0, s = 0) {
  return toOrd(y, mo, d) * 86400 + h * 3600 + mi * 60 + s;
}
export function parts(t) {
  const ord = Math.floor(t / 86400);
  let rest = t - ord * 86400;
  const [y, mo, d] = fromOrd(ord);
  const h = Math.floor(rest / 3600); rest -= h * 3600;
  const mi = Math.floor(rest / 60);
  return { y, mo, d, h, mi, s: rest - mi * 60, ord };
}
export function fmt(t, dateOnly = false) {
  const p = parts(t);
  const z = (n, w = 2) => String(n).padStart(w, "0");
  const day = `${z(p.y, 4)}${z(p.mo)}${z(p.d)}`;
  return dateOnly ? day : `${day}T${z(p.h)}${z(p.mi)}${z(p.s)}`;
}

// --- parsing --------------------------------------------------------------

export function parse(rrule) {
  let s = String(rrule).trim();
  if (s.toUpperCase().startsWith("RRULE:")) s = s.slice(6);
  const out = {};
  for (const part of s.split(";")) {
    if (!part) continue;
    const i = part.indexOf("=");
    const k = (i < 0 ? part : part.slice(0, i)).trim().toUpperCase();
    const v = i < 0 ? "" : part.slice(i + 1).trim();
    if (k === "FREQ" || k === "WKST") out[k] = v.toUpperCase();
    else if (k === "INTERVAL" || k === "COUNT") out[k] = intOrThrow(v, k);
    else if (k === "UNTIL") out[k] = parseUntil(v);
    else if (k === "BYDAY") out[k] = v.split(",").map(parseByday);
    else out[k] = v.split(",").map((x) => intOrThrow(x, k));
  }
  if (out.FREQ === undefined) out.FREQ = null;
  if (out.INTERVAL === undefined) out.INTERVAL = 1;
  if (out.WKST === undefined) out.WKST = "MO";
  return out;
}
function intOrThrow(v, k) {
  const t = v.trim();
  if (!/^[+-]?\d+$/.test(t)) throw new Error(`${k}: cannot read ${JSON.stringify(v)} as an integer`);
  return parseInt(t, 10);
}
function parseUntil(v) {
  const t = v.trim().replace(/Z$/i, "");
  let m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$/.exec(t);
  if (m) return mk(+m[1], +m[2], +m[3], +m[4], +m[5], +m[6]);
  m = /^(\d{4})(\d{2})(\d{2})$/.exec(t);
  if (m) return mk(+m[1], +m[2], +m[3]);
  throw new Error(`UNTIL: cannot read ${JSON.stringify(v)} as a DATE or DATE-TIME`);
}
function parseByday(tok) {
  const t = tok.trim().toUpperCase();
  const day = t.slice(-2);
  const ord = t.slice(0, -2);
  if (!DAYS.includes(day)) throw new Error(`BYDAY: ${JSON.stringify(tok)} does not end in a weekday`);
  if (ord === "" || ord === "+" || ord === "-") return [null, day];
  if (!/^[+-]?\d+$/.test(ord)) throw new Error(`BYDAY: cannot read the ordinal in ${JSON.stringify(tok)}`);
  return [parseInt(ord, 10), day];
}

/** DTSTART, as either "YYYYMMDD" or "YYYYMMDDTHHMMSS" (optionally "DTSTART:"-prefixed). */
export function parseDtstart(v) {
  let t = String(v).trim();
  t = t.replace(/^DTSTART[^:]*:/i, "").trim().replace(/Z$/i, "");
  let m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$/.exec(t);
  if (m) return { t: mk(+m[1], +m[2], +m[3], +m[4], +m[5], +m[6]), dateOnly: false };
  m = /^(\d{4})(\d{2})(\d{2})$/.exec(t);
  if (m) return { t: mk(+m[1], +m[2], +m[3]), dateOnly: true };
  throw new Error(`DTSTART: cannot read ${JSON.stringify(v)}; expected YYYYMMDD or YYYYMMDDTHHMMSS`);
}

// --- period arithmetic ----------------------------------------------------

function weekIndex(ord, wkst) {
  const shift = DAYS.indexOf(wkst);
  return Math.floor((ord - 1 - shift) / 7);
}
export function periodIndex(t, freq, wkst) {
  const p = parts(t);
  switch (freq) {
    case "YEARLY": return p.y;
    case "MONTHLY": return p.y * 12 + (p.mo - 1);
    case "WEEKLY": return weekIndex(p.ord, wkst);
    case "DAILY": return p.ord;
    case "HOURLY": return p.ord * 24 + p.h;
    case "MINUTELY": return (p.ord * 24 + p.h) * 60 + p.mi;
    case "SECONDLY": return ((p.ord * 24 + p.h) * 60 + p.mi) * 60 + p.s;
    default: throw new Error(`FREQ: ${JSON.stringify(freq)} is not a frequency`);
  }
}

// --- BY-rule predicates ---------------------------------------------------

export function monthdayMatches(p, vals) {
  const last = daysInMonth(p.y, p.mo);
  for (const v of vals) {
    if (v > 0 && p.d === v) return true;
    if (v < 0 && p.d === last + 1 + v) return true;
  }
  return false;
}
export function yeardayMatches(p, vals) {
  const n = isLeap(p.y) ? 366 : 365;
  const doy = yearDay(p.y, p.mo, p.d);
  for (const v of vals) {
    if (v > 0 && doy === v) return true;
    if (v < 0 && doy === n + 1 + v) return true;
  }
  return false;
}
export function weekStart(ord, wkst) {
  const shift = (weekday(ord) - DAYS.indexOf(wkst) + 7) % 7;
  return ord - shift;
}
function firstWeekStart(year, wkst) {
  const jan1 = toOrd(year, 1, 1);
  const first = weekStart(jan1, wkst);
  return first + 6 - jan1 >= 3 ? first : first + 7;
}
function weeksInYear(year, wkst) {
  return (firstWeekStart(year + 1, wkst) - firstWeekStart(year, wkst)) / 7;
}
/** [owning year, week number], or null if the date falls before week 1 of its own year. */
export function weekNumber(ord, wkst) {
  const [y] = fromOrd(ord);
  for (const yy of [y + 1, y, y - 1]) {
    const start = firstWeekStart(yy, wkst);
    if (start <= ord && ord < firstWeekStart(yy + 1, wkst)) {
      return [yy, Math.floor((ord - start) / 7) + 1];
    }
  }
  return null;
}
export function weeknoMatches(p, vals, wkst) {
  const got = weekNumber(p.ord, wkst);
  if (got === null) return false;
  const total = weeksInYear(got[0], wkst);
  for (const v of vals) {
    if (v > 0 && got[1] === v) return true;
    if (v < 0 && got[1] === total + 1 + v) return true;
  }
  return false;
}
function nthInSpan(ord, lo, hi) {
  const first = lo + ((weekday(ord) - weekday(lo) + 7) % 7);
  return [Math.floor((ord - first) / 7) + 1, Math.floor((hi - first) / 7) + 1];
}
export function bydayMatches(p, vals, freq, hasBymonth) {
  const wd = DAYS[weekday(p.ord)];
  for (const [ordinal, day] of vals) {
    if (day !== wd) continue;
    if (ordinal === null) return true;
    let n, total;
    if (freq === "MONTHLY" || (freq === "YEARLY" && hasBymonth)) {
      [n, total] = nthInSpan(p.ord, toOrd(p.y, p.mo, 1), toOrd(p.y, p.mo, daysInMonth(p.y, p.mo)));
    } else if (freq === "YEARLY") {
      [n, total] = nthInSpan(p.ord, toOrd(p.y, 1, 1), toOrd(p.y, 12, 31));
    } else {
      // The spec calls an ordinal here an error; treat it as unmatchable
      // rather than silently ignoring the ordinal.
      continue;
    }
    if (ordinal > 0 && n === ordinal) return true;
    if (ordinal < 0 && n === total + 1 + ordinal) return true;
  }
  return false;
}

// --- the occurrence predicate --------------------------------------------

const FINER_ORDER = ["YEARLY", "MONTHLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY"];
const FINER_COMP = { YEARLY: "mo", MONTHLY: "d", DAILY: "h", HOURLY: "mi", MINUTELY: "s" };

export function finer(freq) {
  if (freq === "WEEKLY") return ["h", "mi", "s"];
  const i = FINER_ORDER.indexOf(freq);
  const out = [];
  for (let j = i; j < FINER_ORDER.length - 1; j++) out.push(FINER_COMP[FINER_ORDER[j]]);
  return out;
}
export function pinned(r, freq) {
  const out = new Set();
  if ("BYMONTH" in r) out.add("mo");
  if (["BYMONTHDAY", "BYYEARDAY", "BYDAY", "BYWEEKNO"].some((k) => k in r)) {
    out.add("d");
    // Under YEARLY the day-level rules expand over the whole year, so they
    // pick the month too. Under MONTHLY they only pick a day inside it.
    if (freq === "YEARLY") out.add("mo");
  }
  if ("BYHOUR" in r) out.add("h");
  if ("BYMINUTE" in r) out.add("mi");
  if ("BYSECOND" in r) out.add("s");
  return out;
}

/** Is `t` an occurrence of rule `r`, ignoring BYSETPOS/COUNT/UNTIL? */
export function matches(t, r, dtstart) {
  const freq = r.FREQ, wkst = r.WKST;
  if ((periodIndex(t, freq, wkst) - periodIndex(dtstart, freq, wkst)) % r.INTERVAL !== 0) return false;

  const p = parts(t);
  if ("BYMONTH" in r && !r.BYMONTH.includes(p.mo)) return false;
  if ("BYWEEKNO" in r && !weeknoMatches(p, r.BYWEEKNO, wkst)) return false;
  if ("BYYEARDAY" in r && !yeardayMatches(p, r.BYYEARDAY)) return false;
  if ("BYMONTHDAY" in r && !monthdayMatches(p, r.BYMONTHDAY)) return false;
  if ("BYDAY" in r && !bydayMatches(p, r.BYDAY, freq, "BYMONTH" in r)) return false;
  if ("BYHOUR" in r && !r.BYHOUR.includes(p.h)) return false;
  if ("BYMINUTE" in r && !r.BYMINUTE.includes(p.mi)) return false;
  if ("BYSECOND" in r && !r.BYSECOND.includes(p.s)) return false;

  const ds = parts(dtstart);
  if (freq === "WEEKLY" && !("BYDAY" in r) && weekday(p.ord) !== weekday(ds.ord)) return false;

  // Components finer than FREQ that no BY rule pins down inherit DTSTART's
  // value. This is what stops FREQ=MONTHLY from firing on all 31 days.
  const pin = pinned(r, freq);
  for (const comp of finer(freq)) {
    if (pin.has(comp)) continue;
    if (p[comp] !== ds[comp]) return false;
  }
  return true;
}

// --- expansion ------------------------------------------------------------

const DAY = 86400;
const SPAN = { YEARLY: 400 * DAY, MONTHLY: 40 * DAY, WEEKLY: 10 * DAY, DAILY: 2 * DAY,
               HOURLY: 2 * 3600, MINUTELY: 120, SECONDLY: 2 };

export function periodStart(t, freq, wkst) {
  const p = parts(t);
  const tod = t - p.ord * DAY;
  if (freq === "YEARLY") return toOrd(p.y, 1, 1) * DAY + tod;
  if (freq === "MONTHLY") return toOrd(p.y, p.mo, 1) * DAY + tod;
  if (freq === "WEEKLY") return weekStart(p.ord, wkst) * DAY + tod;
  return t;
}

function* candidates(r, dtstart, horizon, wholePeriod) {
  const freq = r.FREQ;
  const seq = (n) => Array.from({ length: n }, (_, i) => i);
  const ds = parts(dtstart);
  const hours = "BYHOUR" in r ? [...r.BYHOUR].sort((a, b) => a - b)
    : (["HOURLY", "MINUTELY", "SECONDLY"].includes(freq) ? seq(24) : [ds.h]);
  const mins = "BYMINUTE" in r ? [...r.BYMINUTE].sort((a, b) => a - b)
    : (["MINUTELY", "SECONDLY"].includes(freq) ? seq(60) : [ds.mi]);
  const secs = "BYSECOND" in r ? [...r.BYSECOND].sort((a, b) => a - b)
    : (freq === "SECONDLY" ? seq(60) : [ds.s]);

  const begin = wholePeriod ? periodStart(dtstart, freq, r.WKST) : dtstart;
  let ord = Math.floor(begin / DAY);
  const end = Math.floor(horizon / DAY);
  for (; ord <= end; ord++) {
    const base = ord * DAY;
    for (const h of hours) for (const mi of mins) for (const s of secs) {
      yield base + h * 3600 + mi * 60 + s;
    }
  }
}

export class Budget extends Error {
  constructor(steps) {
    super(`gave up after examining ${steps.toLocaleString()} candidate times`);
    this.name = "Budget";
    this.steps = steps;
  }
}

/**
 * The default expansion horizon, in days.
 *
 * This is a SECOND COPY of `src/naive.py`'s `HORIZON_DAYS`, and it has to be:
 * the two run in different languages and nothing links them at run time. What
 * keeps them from drifting is `tests/test_web_port.py`, which fails if these
 * two numbers disagree.
 *
 * It drifted once. Finding 064 found `HORIZON_DAYS` declared in two Python
 * modules and repaired it to one definition; this third copy, in another
 * language, was not in that repair's field of view. When 066 raised the Python
 * horizon from 10958 to 109500 this file kept 10958, and the port silently
 * stopped agreeing with the corpus on 95 cases -- every one of them a proper
 * prefix of the right answer, which is exactly the signature of a short
 * window. Standing rule 66 is about definitions, not about modules.
 */
export const HORIZON_DAYS = 109500;

/**
 * Occurrences at or after dtstart, in order, as datetime integers.
 *
 * opts: { limit, horizon, truncateFirstPeriod, maxSteps }
 *
 * `truncateFirstPeriod` selects the *other* reading of finding 004: the period
 * containing DTSTART is cut at DTSTART before BYSETPOS selects from it. RFC
 * 5545 3.3.10 settles this in favour of the default (finding 021); the flag
 * exists so the UI can show a user what the other reading -- the one most
 * libraries implement -- would produce.
 */
export function expand(rrule, dtstart, opts = {}) {
  const r = typeof rrule === "string" ? parse(rrule) : rrule;
  const limit = opts.limit ?? 1000;
  const maxSteps = opts.maxSteps ?? 5e6;
  const freq = r.FREQ;
  if (!FREQS.includes(freq)) throw new Error(`FREQ: ${JSON.stringify(freq)} is not a frequency`);
  if (!Number.isInteger(r.INTERVAL) || r.INTERVAL < 1) throw new Error("INTERVAL must be a positive integer");
  if (!DAYS.includes(r.WKST)) throw new Error(`WKST: ${JSON.stringify(r.WKST)} is not a weekday`);

  let horizon = opts.horizon ?? dtstart + HORIZON_DAYS * DAY;
  const out = [];
  const setpos = "BYSETPOS" in r;
  const until = "UNTIL" in r ? r.UNTIL : null;

  // RFC 5545 3.3.10 fixes the order: BYSETPOS runs before COUNT and UNTIL.
  // Folding UNTIL into the candidate horizon would evaluate it first, which
  // truncates the final period and can change which instance BYSETPOS picks.
  // Without BYSETPOS the two orders coincide and clipping is a large speedup.
  if (until !== null && !setpos && until < horizon) horizon = until;
  const stop = horizon;
  const scan = setpos ? horizon + SPAN[freq] : horizon;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;

  const flush = (got) => {
    got.sort((a, b) => a - b);
    const picked = new Set();
    for (const pos of r.BYSETPOS) {
      if (pos > 0 && pos <= got.length) picked.add(got[pos - 1]);
      else if (pos < 0 && -pos <= got.length) picked.add(got[got.length + pos]);
    }
    for (const x of [...picked].sort((a, b) => a - b)) {
      if (x >= dtstart && x <= stop && (until === null || x <= until)) out.push(x);
    }
  };

  // BYSETPOS needs a whole period before it can select from it, so matches are
  // buffered per period and flushed as soon as the candidate stream leaves it.
  let curKey = null, cur = [], steps = 0;
  for (const t of candidates(r, dtstart, scan, setpos)) {
    if (++steps > maxSteps) throw new Budget(steps - 1);
    if (t > scan || ((!setpos || opts.truncateFirstPeriod) && t < dtstart)) continue;
    if (setpos) {
      const key = periodIndex(t, freq, r.WKST);
      if (key !== curKey) {
        if (curKey !== null) {
          flush(cur);
          if (out.length >= cap) return out.slice(0, cap);
        }
        if (t > stop || (until !== null && t > until)) return out.slice(0, cap);
        curKey = key; cur = [];
      }
      if (matches(t, r, dtstart)) cur.push(t);
    } else if (matches(t, r, dtstart)) {
      out.push(t);
      if (out.length >= cap) return out.slice(0, cap);
    }
  }
  if (setpos && curKey !== null) flush(cur);
  return out.slice(0, cap);
}
