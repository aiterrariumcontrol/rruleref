// Where implementations diverge, and what RFC 5545 says about it.
//
// Every entry here is backed by a finding in ../../findings/, each of which
// was produced by running the named implementations and comparing output --
// not by reading their source and guessing. Two rules govern what may be
// written here:
//
//   * A divergence is *computed* wherever computing it is possible. The
//     BYSETPOS, WKST and minority-reading notes below re-expand the user's own
//     rule under the other reading and show the actual difference, so they
//     appear only when that rule really is affected. They do not fire on a
//     syntactic shape that might or might not matter.
//   * Where a note names an implementation and a version, that pair was
//     measured. Where it cannot be computed from the rule alone, the note says
//     which implementations were tested and does not generalise past them.

import { expand, parse, parts, fmt, weekday, weekStart, fromOrd, toOrd, mk, daysInMonth, bydayMatches, DAYS } from "./naive.js";

const F = (name) => ({
  label: `finding ${name.slice(0, 3)}`,
  url: `https://github.com/aiterrariumcontrol/rruleref/blob/main/findings/${name}.md`,
});
const RFC5545 = (section, anchor) => ({
  label: `RFC 5545 ${section}`,
  url: `https://www.rfc-editor.org/rfc/rfc5545.html#section-${anchor}`,
});

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
const DAYNAMES = { MO: "Monday", TU: "Tuesday", WE: "Wednesday", TH: "Thursday",
                   FR: "Friday", SA: "Saturday", SU: "Sunday" };

/** Rebuild an RRULE string with one part set (or replaced). */
function withPart(rrule, key, value) {
  const kept = rrule.split(";").filter((c) => c && c.split("=")[0].trim().toUpperCase() !== key);
  kept.push(`${key}=${value}`);
  return kept.join(";");
}
function sameList(a, b) {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}
function tryExpand(rrule, dtstart, opts) {
  try { return expand(rrule, dtstart, opts); } catch { return null; }
}

/** Rebuild an RRULE string with the named parts removed. */
function withoutParts(rrule, keys) {
  return rrule.split(";")
    .filter((c) => c && !keys.includes(c.split("=")[0].trim().toUpperCase()))
    .join(";");
}

/**
 * Finding 022's *seed-limit* reading of RFC 5545 3.3.10, for FREQ=WEEKLY.
 *
 * 3.3.10 applies BYMONTH before BYDAY, and for FREQ=WEEKLY BYMONTH is a limit
 * while BYDAY is an expand -- so BYMONTH runs while "the current set of
 * evaluated occurrences" is still the single DTSTART-derived seed for the
 * week. Under that reading BYMONTH selects *weeks*, by the month of their
 * seed; a selected week is then expanded by BYDAY across the whole week,
 * including into months BYMONTH does not name.
 *
 * That is computed here by re-expanding the rule with BYMONTH deleted -- which
 * is exactly "the week, unrestricted, with BYSETPOS applied to it" -- and then
 * keeping only the occurrences whose week's seed falls in a named month.
 * COUNT and UNTIL are deleted first and reapplied afterwards, because they are
 * evaluated after BYSETPOS and would otherwise be spent on filtered-out weeks.
 */
function seedLimitWeekly(r, rrule, dtstart, limit) {
  if (!("BYMONTH" in r) || !("BYDAY" in r) || r.FREQ !== "WEEKLY") return null;
  const inner = Math.min(4000, limit * 12 + 60);
  const alt = tryExpand(withoutParts(rrule, ["BYMONTH", "COUNT", "UNTIL"]),
                        dtstart, { limit: inner });
  if (!alt) return null;
  const iv = r.INTERVAL, stride = 7 * iv;
  const dsOrd = parts(dtstart).ord;
  const dsWeek = weekStart(dsOrd, r.WKST);
  const months = new Set(r.BYMONTH);
  const kept = alt.filter((t) => {
    const n = Math.floor((weekStart(parts(t).ord, r.WKST) - dsWeek) / stride);
    return months.has(fromOrd(dsOrd + n * stride)[1]);
  });
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;
  return (until === null ? kept : kept.filter((t) => t <= until)).slice(0, cap);
}

/**
 * Finding 103's `ical.js` 2.2.1 abandonment bound, as a predictor.
 *
 * `recur_iterator.js` retries a `FREQ=YEARLY` expansion when a year yields
 * nothing, and at the 28th consecutive empty retry sets `completed` and
 * returns null -- 28 being the 14 year variations (365/366 days x 7 starting
 * weekdays) counted twice. No error is raised, so the caller sees a series
 * that simply ended. The search for the *first* occurrence runs through a
 * different path and is not bounded at all, which is why the same rule read
 * from a later DTSTART answers correctly.
 *
 * The bound is in ITERATIONS, not years: a 40-year hole is 39 empty retries at
 * INTERVAL=1 and only 19 at INTERVAL=2, and ical.js truncates on the first and
 * not the second. Both are checked in test/icaljs-yearly-abandon.mjs, which
 * requires this function to reproduce ical.js 2.2.1's real output byte for
 * byte wherever it fires and wherever it does not.
 *
 * Returns null when no >= 28-iteration empty run is visible in `occurrences`,
 * otherwise { keep, lastYear, nextYear, empties } where `keep` is how many of
 * `occurrences` ical.js returns before stopping.
 */
export function icaljsAbandons(rrule, occurrences) {
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "YEARLY" || occurrences.length < 2) return null;
  const iv = r.INTERVAL;
  const years = occurrences.map((t) => parts(t).y);
  for (let i = 1; i < years.length; i++) {
    if (years[i] === years[i - 1]) continue;
    const empties = (years[i] - years[i - 1]) / iv - 1;
    if (empties >= 28) {
      // Everything in the year before the hole is still returned.
      let keep = i;
      while (keep < years.length && years[keep] === years[i - 1]) keep++;
      return { keep, lastYear: years[i - 1], nextYear: years[i], empties };
    }
  }
  return null;
}

/**
 * Finding 101's `ical.js` 2.2.1 BYMONTHDAY overflow, as a predictor.
 *
 * `expand_year_days` resolves a NEGATIVE BYMONTHDAY against the month's
 * length and then assigns a POSITIVE one raw -- `t3.day = monthday` with no
 * range check -- and lets `dayOfYear()` normalise it. So February 31st does
 * not become "no date"; it becomes March 3rd. RFC 5545 3.3.10 is explicit
 * that an invalid recurrence instance MUST be ignored, and the control is in
 * the same function: its BYDAY branches *do* bounds-check, so
 * `BYMONTH=4;BYDAY=5SU` is dropped rather than overflowed.
 *
 * Predicting it is one line of arithmetic -- the cross product of BYMONTH and
 * BYMONTHDAY, each cell normalised by carrying the overflow into the next
 * month -- and that is what makes it worth asserting. The prediction is
 * required to reproduce ical.js's real output byte for byte in
 * test/icaljs-monthday-rollover.mjs.
 *
 * The scope below is narrow, and every exclusion was measured rather than
 * assumed (counts in that harness):
 *
 *   * A NEGATIVE BYMONTHDAY alongside a positive one superimposes a second
 *     mechanism. `next_year()` renormalises the rule list against the month
 *     of the LAST EMITTED occurrence -- which by then may be an invented one
 *     -- and a dedupe collision there deletes a value the user wrote. That is
 *     finding 101's follow-on; this predictor does not model it and scores
 *     18/48 where it applies.
 *   * BYDAY alongside turns the result empty (0/48), because the bounds-checked
 *     BYDAY branch and the overflowed BYMONTHDAY branch intersect to nothing.
 *     There is no fabricated date to warn about.
 *   * `BYMONTH=2;BYMONTHDAY=29` is excluded because February 29th is a real
 *     date in leap years, so "impossible" is not a property of the cell. It is
 *     the ONLY year-dependent cell that exists, and ical.js handles it by a
 *     third path.
 *   * BYMONTH is REQUIRED, following finding 101's rule 108. Without it,
 *     which months `FREQ=YEARLY;BYMONTHDAY=31` ranges over is a genuine field
 *     dispute, and a defect may not be built on a contested reading. Naming
 *     the month costs the user nothing and removes every competing reading.
 *
 * Returns null unless at least one (BYMONTH, BYMONTHDAY) cell is impossible,
 * otherwise { predicted, invented, cells } -- `predicted` being ical.js's
 * whole stream and `invented` the dates in it that are not occurrences of the
 * rule at all.
 */
export function icaljsMonthdayRollover(rrule, dtstart, limit) {
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "YEARLY") return null;
  if (!("BYMONTH" in r) || !("BYMONTHDAY" in r)) return null;
  for (const k of ["BYDAY", "BYWEEKNO", "BYYEARDAY", "BYSETPOS",
                   "BYHOUR", "BYMINUTE", "BYSECOND"]) {
    if (k in r) return null;
  }
  if (r.BYMONTHDAY.some((d) => d < 0)) return null;
  if (r.BYMONTH.includes(2) && r.BYMONTHDAY.includes(29)) return null;

  // Which cells can never be a date? February is 29 at its longest, so this
  // is a property of the cell and not of the year -- the one exception, (2,29),
  // is excluded above.
  const longest = (m) => (m === 2 ? 29 : daysInMonth(2001, m));
  const cells = [];
  for (const m of r.BYMONTH) {
    for (const d of r.BYMONTHDAY) if (d > longest(m)) cells.push([m, d]);
  }
  if (!cells.length) return null;

  const p0 = parts(dtstart);
  const iv = r.INTERVAL;
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;
  const predicted = [], invented = [];
  for (let y = p0.y; y <= p0.y + 400 && predicted.length < cap; y += iv) {
    // ical.js pushes day-of-year values, so two cells landing on the same day
    // collapse to one occurrence. A date a VALID cell also reaches is not
    // invented, however it was additionally arrived at.
    const seen = new Map();
    for (const m of r.BYMONTH) {
      for (const d of r.BYMONTHDAY) {
        let mo = m, day = d, over = false;
        while (day > daysInMonth(y, mo) && mo < 12) {
          day -= daysInMonth(y, mo); mo++; over = true;
        }
        if (day > daysInMonth(y, mo)) continue;   // unreachable: BYMONTHDAY <= 31
        const t = mk(y, mo, day, p0.h, p0.mi, p0.s);
        seen.set(t, (seen.get(t) ?? true) && over);
      }
    }
    for (const t of [...seen.keys()].sort((a, b) => a - b)) {
      if (t < dtstart || (until !== null && t > until)) continue;
      if (predicted.length >= cap) break;
      predicted.push(t);
      if (seen.get(t)) invented.push(t);
    }
  }
  if (!invented.length) return null;
  return { predicted, invented, cells };
}

/**
 * Finding 111: dmfs `lib-recur` 0.17.1 answers `BYWEEKNO=53` in a 52-week year
 * with December 32nd.
 *
 * ISO 8601 gives a year a 53rd week only when the year is long, and RFC 5545
 * 3.3.10 defines BYWEEKNO by that numbering, so `BYWEEKNO=53` must select
 * nothing in a short year. `ByWeekNoYearlyExpander.expand()` normalises the
 * requested week against `getWeeksPerYear(year)` and then, when the result is
 * LARGER than that count, does not skip it -- it adds an instance at December
 * 31st plus one day, with no year adjustment. Everything downstream works from
 * a day that does not exist.
 *
 * That phantom is invisible on its own: a rule with no BYDAY emits nothing in a
 * short year, because the sanity filter drops the impossible date. It becomes
 * visible when BYDAY expands around it, and what comes out is decided by an
 * asymmetry in the library's own day arithmetic, which this predictor models
 * rather than approximates:
 *
 *   * `ByDayWeeklyExpander` calls `setDayOfWeek(instance, weekday)`, whose
 *     delta is `((wkst - dow(instance) - 7) % 7) + ((weekday - wkst + 7) % 7)`,
 *     evaluated with the weekday of *December 32nd* -- i.e. of January 1st.
 *   * `prevDay(instance, n)` clamps the day of month to `daysInMonth + 1`, so
 *     32 survives and the negative deltas land on real December days.
 *   * `nextDay(instance, n)` clamps it to `daysInMonth`, so 32 becomes 31 and
 *     the positive deltas are counted from December 31st instead -- one day
 *     short, which is why the week that comes out has six days and not seven.
 *   * the weekday whose delta is exactly zero yields December 32nd unchanged
 *     and is DROPPED. That is the whole of finding 111's monotonicity break:
 *     with `BYDAY=MO` alone the Monday can be the dropped one, and adding
 *     `TU` makes a Monday appear.
 *
 * Only the overflow branch is modelled. Every exclusion below was measured in
 * tests/test_dmfs_weekno_overflow.py, which runs this predictor against the
 * real library:
 *
 *   * a BYWEEKNO that normalises to zero or less (`BYWEEKNO=-53` in a 52-week
 *     year) takes the sibling branch of the same `if`, which adds month 0 day
 *     0 -- a different phantom this does not model;
 *   * BYMONTH alongside routes the rule through a different expander
 *     (`ByWeekNoMonthly*`), where short years stop firing at all;
 *   * BYSETPOS, BYHOUR, BYMINUTE, BYSECOND, BYMONTHDAY and BYYEARDAY each
 *     transform the result set after this expansion;
 *   * an ordinal BYDAY (`1MO`) is rejected outright by lib-recur when
 *     BYWEEKNO is set, so there is no output to predict.
 *
 * Returns null when the shape is outside the model, otherwise
 * { predicted, phantom, years }: lib-recur's whole stream, the dates in it
 * that are not occurrences of the rule at all, and the years whose week count
 * the rule overshoots. `years` is empty on most rules, and the stream is still
 * predicted there, so the harness can check the silence as well as the note.
 */
const LR_WD = { SU: 0, MO: 1, TU: 2, WE: 3, TH: 4, FR: 5, SA: 6 };
const LR_MIN_DAYS = 4;          // minDaysInFirstWeek, ISO
/** lib-recur's getWeekDayOfFirstYearDay, verbatim. 0 = Sunday. */
function lrFirstYearDayWeekday(y) {
  const p = y - 1;
  return (1 + 5 * (p & 3) + 4 * (p % 100) + 6 * (p % 400)) % 7;
}
function lrDaysPerYear(y) { return toOrd(y + 1, 1, 1) - toOrd(y, 1, 1); }
/** lib-recur's getYearDayOfFirstWeekStart: may be <= 0, i.e. in the year before. */
function lrFirstWeekStart(y, ws) {
  const d = 1 + ws - lrFirstYearDayWeekday(y);
  if (d > LR_MIN_DAYS) return d - 7;
  if (d < LR_MIN_DAYS - 6) return d + 7;
  return d;
}
/** lib-recur's getWeeksPerYear. Honours WKST, unlike libical's (finding 112). */
function lrWeeksPerYear(y, ws) {
  const t = lrDaysPerYear(y) - lrFirstWeekStart(y, ws) + 1;
  return (7 - (t % 7)) >= LR_MIN_DAYS ? Math.trunc(t / 7) : Math.trunc(t / 7) + 1;
}
/** A year-day of `y`, which may be out of range in either direction. */
function lrYearDay(y, yd) { return fromOrd(toOrd(y, 1, 1) + yd - 1); }

export function dmfsWeeknoOverflow(rrule, dtstart, limit, opts = {}) {
  // `ungated` exists only for the harness, which runs the predictor on the
  // shapes the guard refuses in order to show the refusal was necessary. It is
  // never set by a caller that shows a note to anybody.
  const ungated = opts.ungated === true;
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "YEARLY") return null;
  if (!("BYWEEKNO" in r) || !("BYDAY" in r)) return null;
  if (!ungated) {
    for (const k of ["BYMONTH", "BYMONTHDAY", "BYYEARDAY", "BYSETPOS",
                     "BYHOUR", "BYMINUTE", "BYSECOND"]) {
      if (k in r) return null;
    }
    // An ordinal BYDAY with BYWEEKNO is refused by the library outright.
    if (r.BYDAY.some(([ord]) => ord !== null)) return null;
  }
  if (r.BYWEEKNO.some((v) => v === 0 || v > 53 || v < -53)) return null;

  const ws = LR_WD[r.WKST];
  const p0 = parts(dtstart);
  const iv = r.INTERVAL;
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;
  const byday = r.BYDAY.map(([, day]) => LR_WD[day]);
  const predicted = [], phantom = [], years = [];
  for (let y = p0.y; y <= p0.y + 400 && predicted.length < cap; y += iv) {
    const n = lrWeeksPerYear(y, ws);
    const days = new Map();          // timestamp -> is it from the phantom
    let overshot = false;
    for (const v of r.BYWEEKNO) {
      const wk = v >= 0 ? v : n + v + 1;
      if (wk <= 0) { if (ungated) continue; return null; }  // the month-0 day-0 branch
      if (wk <= n) {
        const base = lrFirstWeekStart(y, ws) + (wk - 1) * 7;
        for (const t of byday) {
          const [yy, mm, dd] = lrYearDay(y, base + ((t - ws + 7) % 7));
          const ts = mk(yy, mm, dd, p0.h, p0.mi, p0.s);
          days.set(ts, false);   // a real week reached it
        }
      } else {
        overshot = true;
        const p = lrDaysPerYear(y) + 1;                 // December 32nd
        const dowp = (lrFirstYearDayWeekday(y) + p - 1) % 7;
        const first = (ws - dowp - 7) % 7;              // -6 .. 0
        for (const t of byday) {
          const delta = first + ((t - ws + 7) % 7);
          if (delta === 0) continue;                    // December 32nd itself: dropped
          // prevDay tolerates the 32nd, nextDay clamps it to the 31st.
          const yd = delta < 0 ? p + delta : lrDaysPerYear(y) + delta;
          const [yy, mm, dd] = lrYearDay(y, yd);
          const ts = mk(yy, mm, dd, p0.h, p0.mi, p0.s);
          if (!days.has(ts)) days.set(ts, true);
        }
      }
    }
    if (overshot) years.push(y);
    for (const ts of [...days.keys()].sort((a, b) => a - b)) {
      if (ts < dtstart) continue;
      // lib-recur's iterator never goes backwards, and the phantom week of one
      // year can reach past the first real week of the next.
      if (predicted.length && ts <= predicted[predicted.length - 1]) continue;
      if (until !== null && ts > until) return finish();
      if (predicted.length >= cap) break;
      predicted.push(ts);
      if (days.get(ts)) phantom.push(ts);
    }
  }
  return finish();

  // `years` empty means the rule overshoots nothing in its own window, which
  // is the common case and is returned rather than nulled: the harness
  // byte-compares the whole stream on rules the note stays silent about too,
  // and silence that was never checked is not evidence of anything.
  function finish() { return { predicted, phantom, years }; }
}

/**
 * Finding 111 as a note. Like finding 101's, it lives outside `analyze` because
 * its headline case -- a rule that asks only for week 53 and a window with no
 * long year in it -- is a CORRECTLY EMPTY series, and `analyze` returns early
 * there (rule 121).
 */
function weeknoOverflowNote(rrule, dtstart, limit) {
  const o = dmfsWeeknoOverflow(rrule, dtstart, limit);
  if (!o || !o.years.length || !o.phantom.length) return null;
  const shortYears = o.years;
  const shown = o.phantom.slice(0, 4).map((t) => fmt(t, true)).join(", ");
  const allPhantom = o.phantom.length === o.predicted.length;
  const yearList = shortYears.slice(0, 6).join(", ") + (shortYears.length > 6 ? ", …" : "");
  return {
    id: "dmfs-weekno-overflow",
    severity: "diverges",
    title: "lib-recur answers the week this rule asks for with a day that does not exist",
    body:
      `ISO 8601 gives a year a 53rd week only when the year is long. ` +
      `${shortYears.length === 1 ? "The year" : "The years"} ${yearList} ` +
      `${shortYears.length === 1 ? "has" : "have"} fewer weeks than this rule asks for, ` +
      `so the correct answer there is nothing, and python-dateutil and rrule.js return ` +
      `nothing. dmfs lib-recur 0.17.1 instead adds an instance at December 31st plus one ` +
      `day — December 32nd — and lets BYDAY expand around it, emitting ` +
      `${shown}${o.phantom.length > 4 ? ", …" : ""}` +
      (allPhantom ? ". Every occurrence shown beside this note is one of those. " : ". ") +
      `The week that comes out has six days, never seven: the library's prevDay tolerates ` +
      `the 32nd and its nextDay clamps it to the 31st, so one day of the week is lost. The ` +
      `weekday whose offset is exactly zero is dropped as an impossible date, which is why ` +
      `BYDAY=MO alone can yield nothing in a year where BYDAY=MO,TU yields a Monday. ` +
      `Note that the phantom is invisible without BYDAY: the same rule with no BYDAY is ` +
      `answered correctly, because the impossible date is then the occurrence itself and ` +
      `the sanity filter drops it. Use BYWEEKNO=-1 if what you mean is the last week of ` +
      `the year.`,
    evidence: [F("111-december-the-thirty-second"),
               RFC5545("3.3.10", "3.3.10")],
    compare: { label: "dmfs lib-recur 0.17.1", occurrences: o.predicted },
  };
}

/**
 * Finding 112's defect B in `libical` master `4edd39a3`, ICU build, as a
 * predictor of that build's exact output.
 *
 * `expand_year_days()`'s BYWEEKNO+BYDAY branch sets the length of the
 * week-numbering year to
 *
 *     last_day = (7 * weeks_in_year(year)) - doy_offset - 1;
 *
 * and `expand_by_day()` then reads `last_day` as a COUNT of days starting at
 * `doy_offset + 1`. The count is already right at `7 * weeks_in_year(year)`,
 * so the subtraction moves the end of the period by `doy_offset + 1` days --
 * backwards in the years where `doy_offset` is positive, which truncates the
 * last days of the week year, and FORWARDS in the years where January's first
 * week reaches back into the previous year and `doy_offset` goes negative,
 * which lets the stride loop run past the end into a week the year does not
 * have.
 *
 * Both halves are modelled, so `fix: true` reproduces the patch-B build
 * instead and the difference between the two arms is exactly what the defect
 * costs or invents. Everything else here is libical's own arithmetic:
 * ICU's week-of-year under WKST with four minimal days, `weeks_in_year()`'s
 * week-start-blind ISO count, `get_start_of_week()` at January 1st, the
 * straddle probe in `icalrecur_iterator_new()`, and
 * `icalrecur_iterator_next()`'s loop that swallows a repeated instant.
 */
const LI_WD = { SU: 1, MO: 2, TU: 3, WE: 4, TH: 5, FR: 6, SA: 7 };
const LI_MIN_DAYS = 4;                      // UCAL_MINIMAL_DAYS_IN_FIRST_WEEK
const LI_MAX_YEAR = 20000;                  // MAX_TIME_T_YEAR, the ICU build
const liLeap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
const liYearLen = (y) => (liLeap(y) ? 366 : 365);
/** icaltime_day_of_week: 1 = Sunday .. 7 = Saturday. */
const liDow = (y, m, d) => (toOrd(y, m, d) % 7) + 1;
/** ICU Calendar::weekNumber, verbatim. */
function liWeekNumber(dayOfPeriod, dow, fdow) {
  let s = (dow - fdow - dayOfPeriod + 1) % 7;
  if (s < 0) s += 7;
  let w = Math.trunc((dayOfPeriod + s - 1) / 7);
  if (7 - s >= LI_MIN_DAYS) w++;
  return w;
}
/** UCAL_WEEK_OF_YEAR for a day-of-year of `y` that ICU is free to normalise. */
function liWeekOfYear(y, doy, fdow) {
  const [yy, mm, dd] = fromOrd(toOrd(y, 1, 1) + doy - 1);
  const d2 = toOrd(yy, mm, dd) - toOrd(yy, 1, 1) + 1;
  const dow = liDow(yy, mm, dd);
  const len = liYearLen(yy);
  const relDow = (dow - fdow + 7) % 7;
  let w = liWeekNumber(d2, dow, fdow);
  if (w === 0) return liWeekNumber(d2 + liYearLen(yy - 1), dow, fdow);
  if (d2 >= len - 5) {
    let lastRelDow = (relDow + len - d2) % 7;
    if (lastRelDow < 0) lastRelDow += 7;
    if (6 - lastRelDow >= LI_MIN_DAYS && d2 + 7 - relDow > len) w = 1;
  }
  return w;
}
/** libical's weeks_in_year(): ISO, and so blind to WKST -- that is defect A. */
function liWeeksInYear(y) {
  const dow = liDow(y, 1, 1);
  return 52 + (dow === 5 || (dow === 4 && liLeap(y)) ? 1 : 0);
}
/**
 * The week count ICU's own numbering implies for this week start -- what
 * weeks_in_year() would return if it had heard about WKST.  Defect A is
 * exactly the difference between this and liWeeksInYear().
 */
function liWeeksInYearTrue(y, ws) {
  const len = liYearLen(y);
  const w = liWeekOfYear(y, len, ws);
  return w > 1 ? w : liWeekOfYear(y, len - 7, ws);
}

/**
 * The BYWEEKNO-without-BYDAY branch of expand_year_days(), as day-of-year
 * numbers.  libical expands such a rule to ONE day per selected week -- the
 * next instance of DTSTART's weekday -- and the returned numbers may exceed
 * the length of `y`, which is how a week lands in the next calendar year.
 */
function liNoBydayDays(y, byweekno, ws, p0, fix) {
  const nweeks = fix ? liWeeksInYearTrue(y, ws) : liWeeksInYear(y);
  let start = 1;
  if (liWeekOfYear(y, 1, ws) > 1) start += 7;   // Jan 1 is in last year's week
  let k = (liDow(y, 1, 1) - ws) % 7;
  if (k < 0) k += 7;
  start += (1 - k) - 1;                         // get_start_of_week(Jan 1) - 1
  start += (liDow(p0.y, p0.mo, p0.d) - ws + 7) % 7;
  const bits = new Set();
  for (let w of byweekno) {
    if (w < 0) w += nweeks + 1;
    else if (w > nweeks) continue;
    bits.add(start + 7 * (w - 1));
  }
  return [...bits].sort((a, b) => a - b);
}

/** The year-day bitmask libical builds for one year, as day-of-year numbers. */
function liYearDays(y, byweekno, byday, ws, fix) {
  let doyOffset = liWeekOfYear(y, 1, ws) > 1 ? 7 : 0;
  let k = (liDow(y, 1, 1) - ws) % 7;
  if (k < 0) k += 7;
  doyOffset += 1 - k - 1;                   // get_start_of_week(Jan 1) - 1
  const nweeks = liWeeksInYear(y);
  const lastDay = fix ? 7 * nweeks : 7 * nweeks - doyOffset - 1;
  const firstDow = ws;
  const bits = new Set();
  for (const dow of byday) {
    let day = ((dow + 7 - firstDow) % 7) + 1;
    let weekno = doyOffset < 0 ? 1 : liWeekOfYear(y, day + doyOffset, ws);
    for (;;) {
      for (let w of byweekno) {
        if (w < 0) w += nweeks + 1;
        if (w === weekno) { bits.add(day + doyOffset); break; }
      }
      day += 7;
      if (day > lastDay) break;
      weekno++;
    }
  }
  return [...bits].sort((a, b) => a - b);
}

/**
 * icalrecur_iterator's year-by-year walk, shared by both BYWEEKNO defects.
 * `bitsOf(y)` supplies the day-of-year bitmask for one year; everything here
 * is the iterator around it, which is the same code for either branch of
 * expand_year_days().
 */
function liIterate(bitsOf, p0, start, iv, until, cap, ws) {
  // icalrecur_iterator_new()'s straddle probe: a January DTSTART sitting in
  // the previous year's last week takes that year's OVERFLOW bits only, and
  // a December one in week 1 takes the next year instead.
  const swn = liWeekOfYear(p0.y, start - toOrd(p0.y, 1, 1) + 1, ws);
  let firstYear = p0.y, firstMin = -4;
  if (swn > 5 && p0.mo === 1) {
    const len = liYearLen(p0.y - 1);
    if (bitsOf(p0.y - 1).some((b) => b > len)) { firstYear = p0.y - 1; firstMin = len + 1; }
  } else if (swn < 45 && p0.mo === 12) {
    if (bitsOf(p0.y + 1).length) firstYear = p0.y + 1;
  }
  const out = [];
  let prev = null, sawAny = false, expansions = 0;
  for (let y = firstYear, first = true; out.length < cap; y += iv, first = false) {
    // The Gregorian calendar repeats every 400 years and so does the mask,
    // so 400 expansions with nothing set proves there is no year to find.
    // That is the constructor's loop running to MAX_TIME_T_YEAR, which the
    // library reports as MALFORMEDDATA and not as an empty series.
    if (!sawAny && expansions >= 400) return { out, refused: true };
    if (y > LI_MAX_YEAR) break;
    const bits = bitsOf(y);
    expansions++;
    if (!bits.length) continue;
    sawAny = true;
    for (const b of bits) {
      if (first && b < firstMin) continue;
      const n = toOrd(y, 1, 1) + b - 1;
      if (n < start) continue;
      if (n === prev) continue;   // next() loops while the instant stands still
      prev = n;
      const [yy, mm, dd] = fromOrd(n);
      const t = mk(yy, mm, dd, p0.h, p0.mi, p0.s);
      if (until !== null && t > until) return { out, refused: false };
      if (out.length >= cap) break;
      out.push(t);
    }
  }
  return { out, refused: false };
}

/**
 * Returns null when the shape is outside the model, otherwise
 * { predicted, fixed, lost, phantom, refused, years }: the stream libical
 * 4edd39a3 emits, the stream the same build emits with the one-line patch B,
 * the dates the defect costs, the dates it invents, whether libical refuses
 * the rule outright, and the years the invented dates fall in.
 */
export function libicalWeekYearTruncated(rrule, dtstart, limit, opts = {}) {
  // `ungated` exists only for the harness, which runs the predictor on the
  // shapes the guard refuses in order to show the refusal was necessary.
  const ungated = opts.ungated === true;
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "YEARLY") return null;
  if (!("BYWEEKNO" in r) || !("BYDAY" in r)) return null;
  if (!ungated) {
    for (const k of ["BYMONTH", "BYMONTHDAY", "BYYEARDAY", "BYSETPOS",
                     "BYHOUR", "BYMINUTE", "BYSECOND"]) {
      if (k in r) return null;
    }
    if (r.BYDAY.some(([ord]) => ord !== null)) return null;
  }
  if (r.BYWEEKNO.some((v) => v === 0 || v > 53 || v < -53)) return null;
  if (!(r.WKST in LI_WD)) return null;

  const ws = LI_WD[r.WKST];
  const byday = r.BYDAY.map(([, day]) => LI_WD[day]);
  const p0 = parts(dtstart);
  const start = toOrd(p0.y, p0.mo, p0.d);
  const iv = r.INTERVAL;
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;

  const run = (fix) =>
    liIterate((y) => liYearDays(y, r.BYWEEKNO, byday, ws, fix),
              p0, start, iv, until, cap, ws);

  const a = run(false), b = run(true);
  if (a.refused) {
    return { predicted: [], fixed: b.out, lost: [], phantom: [], refused: true, years: [] };
  }
  // Compare only inside the window both streams certainly cover: past the
  // shorter one's last date neither is evidence about the other.
  const horizon = Math.min(a.out.length ? a.out[a.out.length - 1] : Infinity,
                           b.out.length ? b.out[b.out.length - 1] : Infinity);
  const A = new Set(a.out), B = new Set(b.out);
  const lost = b.out.filter((t) => !A.has(t) && t <= horizon);
  const phantom = a.out.filter((t) => !B.has(t) && t <= horizon);
  const years = [...new Set(phantom.map((t) => parts(t).y))];
  return { predicted: a.out, fixed: b.out, lost, phantom, refused: false, years };
}

/**
 * Finding 112's defect A, as a predictor.
 *
 * `weeks_in_year()` in `icalrecur.c` counts ISO weeks -- its own comment says
 * so, and ISO means `WKST=MO`.  The week *numbering* it is compared against
 * comes from ICU, which this build configures with four minimal days and the
 * first day of the week taken from the rule's `WKST`.  So the numbering
 * honours `WKST` and the count of weeks does not, and with any non-Monday
 * `WKST` they can disagree by one.  Two places consume the count:
 *
 *     if (weekno < 0) weekno += nweeks + 1;      // normalise a negative
 *     else if (weekno > nweeks) continue;        // the only overflow guard
 *
 * so a negative `BYWEEKNO` can be normalised to the wrong week, and a week the
 * year does have under its own numbering can be dropped -- or one it does not
 * have can be kept, and then it lands in the next calendar year.
 *
 * Returns null when the shape is outside the model, otherwise the same shape
 * as `libicalWeekYearTruncated`: the stream libical 4edd39a3 emits, the stream
 * the WKST-aware count would give, and the two differences.
 */
export function libicalWeeksInYearBlind(rrule, dtstart, limit, opts = {}) {
  const ungated = opts.ungated === true;
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "YEARLY") return null;
  // This is the BYWEEKNO branch libical takes when there is NO BYDAY; with
  // BYDAY it is finding 112's defect B and liYearDays() models it instead.
  if (!("BYWEEKNO" in r) || "BYDAY" in r) return null;
  if (!ungated) {
    // expand_year_days() raises UNIMPLEMENTED for the first three outright.
    for (const k of ["BYMONTH", "BYMONTHDAY", "BYYEARDAY", "BYSETPOS",
                     "BYHOUR", "BYMINUTE", "BYSECOND"]) {
      if (k in r) return null;
    }
  }
  if (r.BYWEEKNO.some((v) => v === 0 || v > 53 || v < -53)) return null;
  if (!(r.WKST in LI_WD)) return null;

  const ws = LI_WD[r.WKST];
  const p0 = parts(dtstart);
  const start = toOrd(p0.y, p0.mo, p0.d);
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;
  const run = (fix) =>
    liIterate((y) => liNoBydayDays(y, r.BYWEEKNO, ws, p0, fix),
              p0, start, r.INTERVAL, until, cap, ws);

  const a = run(false), b = run(true);
  if (a.refused) {
    return { predicted: [], fixed: b.out, lost: [], phantom: [], refused: true, years: [] };
  }
  const horizon = Math.min(a.out.length ? a.out[a.out.length - 1] : Infinity,
                           b.out.length ? b.out[b.out.length - 1] : Infinity);
  const A = new Set(a.out), B = new Set(b.out);
  const lost = b.out.filter((t) => !A.has(t) && t <= horizon);
  const phantom = a.out.filter((t) => !B.has(t) && t <= horizon);
  const years = [...new Set(phantom.map((t) => parts(t).y))];
  return { predicted: a.out, fixed: b.out, lost, phantom, refused: false, years };
}

/**
 * Finding 105's `ical.js` 2.2.1 month-rollover asymmetry, as a predictor.
 *
 * `recur_iterator.js`, `next_month()`, the BYDAY-without-BYMONTHDAY branch.
 * The in-month scan tests BOTH spellings of a set position:
 *
 *     if (!this.has_by_data("BYSETPOS") ||
 *         this.check_set_position(++setpos) ||
 *         this.check_set_position(setpos - setpos_total - 1)) {
 *
 * Twelve lines later the path that walks off the end of a month and lands on
 * day 1 of the next one tests only the POSITIVE spelling, `check_set_position(1)`,
 * and never computes `setpos_total` for the month it has just entered. Day 1,
 * when it is in the BYDAY set, is necessarily set position 1, so the hardcoded
 * `1` is right as far as it goes -- but a rule that names position 1 only as
 * `-n` for a set of size n falls through with `data_valid` left at 0, and that
 * occurrence is lost.
 *
 * Finding 105 described the symptom as a DROPPED MONTH, which is what it looks
 * like whenever position 1 is the month's only selection. Building the
 * predictor showed the mechanism is narrower and the finding's phrasing was a
 * special case: `BYSETPOS=-2,2` loses only the day-1 date and keeps the other
 * one. That is measured, not reasoned -- see the addendum on 105.
 *
 * Scope, every exclusion measured in test/icaljs-negative-bysetpos.mjs rather
 * than assumed:
 *
 *   * BYMONTH is excluded. ical.js's month filter interacts with the same
 *     rollover and the ungated predictor scores 0/15 there.
 *   * BYMONTHDAY is excluded: `_byDayAndMonthDay()` is a different branch
 *     entirely, which finding 105 explicitly did not probe. Ungated: 0/10.
 *   * BYHOUR/BYMINUTE/BYSECOND are excluded; they multiply each date and the
 *     predictor models dates only. Ungated: 0/5.
 *   * DTSTART must be the rule's own first occurrence. Otherwise finding 004's
 *     first-period truncation is superimposed -- ical.js emits an extra
 *     opening date -- and those pairs are counted, not quietly skipped.
 *
 * Returns null when nothing is lost, otherwise { predicted, lost, emptied }:
 * ical.js's whole stream, the dates it drops, and the subset of `lost` whose
 * month ends up with no occurrence at all.
 */
export function icaljsNegativeSetposRollover(rrule, dtstart, limit) {
  let r;
  try { r = parse(rrule); } catch { return null; }
  if (r.FREQ !== "MONTHLY") return null;
  if (!("BYDAY" in r) || !("BYSETPOS" in r)) return null;
  for (const k of ["BYMONTH", "BYMONTHDAY", "BYWEEKNO", "BYYEARDAY",
                   "BYHOUR", "BYMINUTE", "BYSECOND"]) {
    if (k in r) return null;
  }
  // The positive spelling of position 1 is the repair, so a rule that already
  // contains it is unaffected by construction.
  if (r.BYSETPOS.includes(1) || !r.BYSETPOS.some((p) => p < 0)) return null;
  // Finding 004 otherwise fires in the same stream; see the scope note above.
  const ref = tryExpand(rrule, dtstart, { limit });
  if (!ref || !ref.length || ref[0] !== dtstart) return null;

  const p0 = parts(dtstart);
  const until = "UNTIL" in r ? r.UNTIL : null;
  const cap = "COUNT" in r ? Math.min(limit, r.COUNT) : limit;
  const predicted = [], lost = [], emptied = [];
  for (let k = 0; predicted.length < cap && k < 1200; k++) {
    const mIdx = (p0.mo - 1) + k * r.INTERVAL;
    const y = p0.y + Math.floor(mIdx / 12), mo = (mIdx % 12) + 1;
    // S(M): the BYDAY-derived day set for this month, in date order. This is
    // the set BYSETPOS indexes, and |S| is the n that -n is measured against.
    const S = [];
    for (let d = 1, dim = daysInMonth(y, mo); d <= dim; d++) {
      if (bydayMatches(parts(mk(y, mo, d)), r.BYDAY, "MONTHLY", false)) S.push(d);
    }
    const n = S.length;
    if (!n) continue;
    const picked = S.filter((d, i) => r.BYSETPOS.includes(i + 1) || r.BYSETPOS.includes(i - n));
    // k > 0: day 1 of the DTSTART month is not reached by the rollover path.
    const dropsDay1 = k > 0 && S[0] === 1 && r.BYSETPOS.includes(-n);
    let kept = 0;
    for (const d of picked) {
      const t = mk(y, mo, d);
      if (t < dtstart) continue;
      if (until !== null && t > until) return { predicted, lost, emptied };
      if (dropsDay1 && d === 1) { lost.push(t); continue; }
      kept++;
      if (predicted.length < cap) predicted.push(t);
    }
    if (dropsDay1 && !kept && picked.includes(1)) emptied.push(mk(y, mo, 1));
  }
  if (!lost.length) return null;
  return { predicted, lost, emptied };
}

/**
 * Finding 101 as a note, built apart from `analyze` because the case that
 * matters most is the one `analyze` used to return early on: when every date
 * the rule names is impossible, the *correct* series is empty, and the "this
 * rule produces no occurrences" note was the last word. That note even gives
 * `BYMONTH=2` with `BYMONTHDAY=30` as its example cause -- while saying
 * nothing about the library that answers it with a March date every year.
 */
/**
 * Finding 112's defect B as a note. Like findings 101's and 111's it lives
 * outside `analyze` because libical can refuse the rule where the correct
 * series is a perfectly ordinary one, and because the rules this note is
 * about include some whose correct answer is empty -- where `analyze` returns
 * early (rule 121).
 */
function weekYearTruncatedNote(rrule, dtstart, limit) {
  const o = libicalWeekYearTruncated(rrule, dtstart, limit);
  if (!o) return null;
  if (!o.refused && !o.lost.length && !o.phantom.length) return null;
  const list = (ts) => ts.slice(0, 4).map((t) => fmt(t, true)).join(", ") +
                       (ts.length > 4 ? ", …" : "");
  let body =
    "`libical` sizes the week-numbering year by subtracting the offset of its first day " +
    "from a count that already allowed for it, so the period BYDAY is expanded over is " +
    "the wrong length by that offset plus one. The offset is fixed by which weekday " +
    "January 1st falls on, which is why this depends on the year and not on the rule. " +
    "Measured on master `4edd39a3` built with ICU; `3.0.20` was not partitioned and is " +
    "not claimed.";
  if (o.refused) {
    body = "`libical` master `4edd39a3` does not answer this rule at all: it reports " +
      "MALFORMEDDATA. The week this rule asks for is always in the part of the year the " +
      "library drops, so its constructor searches every year up to its maximum, finds " +
      "nothing, and fails rather than returning an empty series. The same build with the " +
      "one-line fix answers it" +
      (o.fixed.length ? ", starting " + list(o.fixed) + "." : ".") + " " + body;
  } else {
    const bits = [];
    if (o.lost.length) {
      bits.push("it drops " + (o.lost.length === 1 ? "an occurrence" : "occurrences") +
        " at the end of the week year — " + list(o.lost) + " — so a week this rule names " +
        "comes back with fewer days than it has");
    }
    if (o.phantom.length) {
      bits.push((o.lost.length ? "and in " : "in ") + (o.years.length === 1 ? "the year " : "the years ") +
        o.years.slice(0, 5).join(", ") + (o.years.length > 5 ? ", …" : "") +
        ", where January's first week reaches back into the previous year, the same " +
        "arithmetic runs one stride too FAR and invents " + list(o.phantom) +
        " in a week the year does not have");
    }
    body = "`libical` master `4edd39a3` answers this rule differently from every other " +
      "implementation here, and not by a reading of the spec: " + bits.join(", ") + ". " + body;
  }
  return {
    id: "libical-week-year-truncated",
    severity: "diverges",
    title: o.refused
      ? "libical rejects this rule as malformed, and the reason is a length bug"
      : "libical mis-sizes the week-numbering year this rule is expanded over",
    body,
    evidence: [F("112-the-week-start-the-helper-never-heard-about"),
               RFC5545("3.3.10", "3.3.10")],
    compare: o.refused
      ? { label: "libical 4edd39a3 + the one-line fix", occurrences: o.fixed }
      : { label: "libical master 4edd39a3 (ICU build)", occurrences: o.predicted },
  };
}

/**
 * Finding 112's defect A as a note. The sibling of `weekYearTruncatedNote`,
 * and in the other branch of `expand_year_days()`: BYWEEKNO with no BYDAY,
 * where libical expands to one day per selected week. Outside `analyze` for
 * the same two reasons (rule 121): libical can refuse a rule whose correct
 * answer is ordinary, and some of these rules correctly produce nothing.
 */
function weeksInYearBlindNote(rrule, dtstart, limit) {
  const o = libicalWeeksInYearBlind(rrule, dtstart, limit);
  if (!o) return null;
  if (!o.refused && !o.lost.length && !o.phantom.length) return null;
  const list = (ts) => ts.slice(0, 4).map((t) => fmt(t, true)).join(", ") +
                       (ts.length > 4 ? ", …" : "");
  const base =
    "The cause is one helper: `weeks_in_year()` counts ISO weeks — its own comment says " +
    "so, and ISO means `WKST=MO`. But the week *numbering* that count is checked against " +
    "is ICU's, which this build configures with the `WKST` from your rule. So the " +
    "numbering moves with `WKST` and the count does not, and for any non-Monday `WKST` " +
    "they can differ by one. That count is used in exactly two places: to turn a negative " +
    "`BYWEEKNO` into a positive one, and as the only check that the year has the week you " +
    "asked for. Measured on master `4edd39a3` built with ICU; `3.0.20` was not partitioned " +
    "and is not claimed.";
  let body;
  if (o.refused) {
    // NOT OBSERVED. Defect B reaches MALFORMEDDATA because the week it asks
    // for is always inside the part of the year that branch drops; here the
    // ISO count is 52 or 53 depending on the year, so a week survives in some
    // year eventually and negatives normalise into range. The sweep in
    // tests/test_libical_weeks_in_year_blind.py refused 0 of 3958 rules. This
    // arm is kept because the predictor can still produce it, not because any
    // rule is known to reach it.
    body = "`libical` master `4edd39a3` does not answer this rule at all: it reports " +
      "MALFORMEDDATA. Under its week-start-blind count no year ever has the week this " +
      "rule names, so the constructor searches every year up to its maximum, finds " +
      "nothing, and fails instead of returning an empty series. The same build with the " +
      "one-line fix answers it" +
      (o.fixed.length ? ", starting " + list(o.fixed) + "." : ".") + " " + base;
  } else {
    const bits = [];
    if (o.lost.length) {
      bits.push("it drops " + (o.lost.length === 1 ? "an occurrence" : "occurrences") +
        " — " + list(o.lost) + " — for a week the year does have once the week start is " +
        "taken into account");
    }
    if (o.phantom.length) {
      // What is certain by construction is that these dates are in libical's
      // stream and not in the WKST-aware one. Whether a given date also falls
      // outside the calendar year it was selected for depends on the rule, so
      // the note does not assert it.
      bits.push((o.lost.length ? "and it emits " : "it emits ") + list(o.phantom) +
        " instead" + (o.years.length ? " — in " +
          o.years.slice(0, 5).join(", ") + (o.years.length > 5 ? ", …" : "") : "") +
        " — which the WKST-aware count does not select: the week your rule names " +
        "resolves to a different week under the ISO count");
    }
    body = "`libical` master `4edd39a3` answers this rule differently from the other " +
      "implementations here: " + bits.join(", ") + ". " + base;
  }
  return {
    id: "libical-weeks-in-year-blind",
    severity: "diverges",
    title: o.refused
      ? "libical rejects this rule as malformed, because it counts the year's weeks without WKST"
      : "libical counts this year's weeks without the WKST it numbers them by",
    body,
    evidence: [F("112-the-week-start-the-helper-never-heard-about"),
               RFC5545("3.3.10", "3.3.10")],
    compare: o.refused
      ? { label: "libical 4edd39a3 + the one-line fix", occurrences: o.fixed }
      : { label: "libical master 4edd39a3 (ICU build)", occurrences: o.predicted },
  };
}

function monthdayRolloverNote(rrule, dtstart, limit) {
  const roll = icaljsMonthdayRollover(rrule, dtstart, limit);
  if (!roll) return null;
    const cellList = roll.cells
      .map(([m, d]) => `${MONTHS[m - 1]} ${d}`)
      .join(", ");
    const shown = roll.invented.slice(0, 4).map((t) => fmt(t, true)).join(", ");
    const allInvented = roll.invented.length === roll.predicted.length;
    return {
      id: "icaljs-monthday-rollover",
      severity: "diverges",
      title: "ical.js answers this rule with dates that are not in the month it names",
      body:
        `This rule asks for ${cellList} — ${roll.cells.length === 1 ? "a day that" : "days that"} ` +
        `cannot occur. RFC 5545 3.3.10 says a recurrence instance that is an invalid date ` +
        `MUST be ignored, so the correct answer ` +
        (allInvented
          ? `is the empty set, and python-dateutil, rrule.js and lib-recur all return nothing. `
          : `omits ${roll.cells.length === 1 ? "that cell" : "those cells"} entirely. `) +
        `ical.js 2.2.1 instead carries the overflow forward into the following month and ` +
        `emits ${shown}${roll.invented.length > 4 ? ", …" : ""} — ` +
        `${roll.invented.length === 1 ? "a date" : "dates"} in a month this rule does not name, ` +
        `once a year, indefinitely. Nothing is logged and no exception is thrown, so a ` +
        `mistyped day-of-month becomes a permanent recurring reminder on the wrong date ` +
        `rather than a rule that visibly produces nothing. ` +
        `The cause is a missing range check on positive BYMONTHDAY values in ` +
        `expand_year_days; the same function's BYDAY branches are bounds-checked, so ` +
        `BYMONTH=${roll.cells[0][0]};BYDAY=5SU is correctly dropped. ical.js is the ` +
        `library Thunderbird calendaring uses.`,
      evidence: [F("101-an-impossible-day-that-was-not-refused"),
                 RFC5545("3.3.10", "3.3.10")],
      compare: { label: "ical.js 2.2.1", occurrences: roll.predicted },
    };
}

/**
 * ctx: { rrule, dtstart, dateOnly, occurrences, limit }
 * returns [{ id, severity, title, body, evidence, compare }]
 *   severity: "error" | "diverges" | "note"
 *   compare (optional): { label, occurrences } -- an alternative expansion to
 *   show beside the main one.
 */
export function analyze(ctx) {
  const { rrule, dtstart, dateOnly, occurrences, limit } = ctx;
  const out = [];
  let r;
  try { r = parse(rrule); } catch { return out; }
  const has = (k) => k in r;
  const ds = parts(dtstart);
  const show = (ts) => ts.map((t) => fmt(t, dateOnly));

  // --- the rule does not fire at all ------------------------------------
  if (occurrences.length === 0) {
    out.push({
      id: "empty",
      severity: "error",
      title: "This rule produces no occurrences at all",
      body:
        "Within the window searched, nothing matches. The usual causes are a combination " +
        "that cannot be satisfied (BYMONTH=2 with BYMONTHDAY=30), or an ordinal BYDAY " +
        "under a FREQ that does not permit one. Note that implementations differ here: " +
        "some return an empty set, some raise, and some silently ignore the part they " +
        "cannot apply.",
      evidence: [],
    });
    const rn = monthdayRolloverNote(rrule, dtstart, limit);
    if (rn) out.push(rn);
    const wn = weeknoOverflowNote(rrule, dtstart, limit);
    if (wn) out.push(wn);
    const tn = weekYearTruncatedNote(rrule, dtstart, limit);
    if (tn) out.push(tn);
    const bn = weeksInYearBlindNote(rrule, dtstart, limit);
    if (bn) out.push(bn);
    return out;
  }

  // --- DTSTART is not the rule's own first occurrence -------------------
  // RFC 5545 3.8.5.3 declares the recurrence set undefined in this case, and
  // implementations then differ on whether DTSTART is emitted anyway. This is
  // computed, not guessed: the expansion simply does not begin at DTSTART.
  if (occurrences[0] !== dtstart) {
    out.push({
      id: "unsynchronized-dtstart",
      severity: "diverges",
      title: "DTSTART does not match this rule",
      body:
        `DTSTART is ${fmt(dtstart, dateOnly)}, but the first date this rule actually ` +
        `describes is ${fmt(occurrences[0], dateOnly)}. RFC 5545 3.8.5.3: “The ‘DTSTART’ ` +
        "property value SHOULD be synchronized with the recurrence rule, if specified. The " +
        "recurrence set generated with a ‘DTSTART’ property value not synchronized with the " +
        "recurrence rule is undefined.” Undefined means the answer is up to the library: " +
        "some emit DTSTART as an extra first occurrence, " +
        "some do not. This is one of the most common real causes of “the same rule " +
        "gives different results in two systems”. If you did not intend it, move " +
        "DTSTART onto a date the rule matches.",
      evidence: [RFC5545("3.8.5.3", "3.8.5.3"), F("020-synchronization-is-reading-dependent")],
    });
  }

  // --- BYSETPOS and the period containing DTSTART -----------------------
  if (has("BYSETPOS")) {
    const other = tryExpand(rrule, dtstart, { limit, truncateFirstPeriod: true });
    if (other && !sameList(other, occurrences)) {
      out.push({
        id: "bysetpos-first-period",
        severity: "diverges",
        title: "BYSETPOS: this rule's first occurrences depend on a contested reading",
        body:
          "When BYSETPOS selects from the period that contains DTSTART, does it index the " +
          "whole period, or the period cut short at DTSTART? RFC 5545 3.3.10 answers it: " +
          "“A set of recurrence instances starts at the beginning of the interval " +
          "defined by the FREQ rule part.” That is the whole-period reading, shown on " +
          "the left. python-dateutil and the implementations descended from it truncate the " +
          "first period at DTSTART instead, giving the answer on the right. Your rule is " +
          "affected — the two readings disagree on the dates below.",
        evidence: [
          F("021-bysetpos-first-interval-resolved"),
          F("004-bysetpos-first-period-truncation"),
          { label: "dateutil/dateutil#1398", url: "https://github.com/dateutil/dateutil/issues/1398" },
        ],
        compare: { label: "first period truncated at DTSTART (python-dateutil lineage)", occurrences: show(other) },
      });
    }
    const nr = icaljsNegativeSetposRollover(rrule, dtstart, limit);
    if (nr) {
      const shown = nr.lost.slice(0, 4).map((t) => fmt(t, dateOnly)).join(", ");
      const n = nr.lost.length;
      out.push({
        id: "icaljs-negative-bysetpos-rollover",
        severity: "diverges",
        title: "ical.js loses the first of the month when BYSETPOS names it only negatively",
        body:
          `This rule selects the first day of some months — ${shown}` +
          `${n > 4 ? `, … (${n} of them in the window shown)` : ""} — and names that ` +
          `position only negatively. ical.js 2.2.1 does not return ` +
          `${n === 1 ? "that date" : "those dates"}. ` +
          (nr.emptied.length
            ? (nr.emptied.length === n
                ? `In each of those months it is the only occurrence, so the month `
                : `In ${nr.emptied.length} of those months it is the only occurrence, so the month `) +
              `disappears from the series entirely, with the months either side correct — ` +
              `which is the shape this is usually noticed in. `
            : `The other occurrences in those months survive, so what you see is a single ` +
              `missing date rather than a gap. `) +
          `python-dateutil, rrule.js, sabre/vobject and dmfs lib-recur all return the full ` +
          `series. The cause is an asymmetry twelve lines wide in next_month(): the in-month ` +
          `scan tests a set position in both spellings, but the path that rolls over into ` +
          `the next month and lands on day 1 tests only the positive one, and never computes ` +
          `that month's set size, so it can never recognise −n. ` +
          `Adding the positive spelling repairs it without changing which dates the rule ` +
          `selects: for a set of size n, write BYSETPOS=1,−n rather than BYSETPOS=−n. ` +
          `ical.js is the library Thunderbird calendaring uses.`,
        evidence: [F("105-the-month-that-rolled-over"),
                   F("004-bysetpos-first-period-truncation")],
        compare: { label: "ical.js 2.2.1", occurrences: show(nr.predicted) },
      });
    }
    if (has("UNTIL")) {
      out.push({
        id: "bysetpos-until-order",
        severity: "note",
        title: "BYSETPOS with UNTIL: the order of the two matters",
        body:
          "RFC 5545 3.3.10 evaluates BYSETPOS first and only then COUNT and UNTIL. An " +
          "implementation that folds UNTIL into its search window instead applies it first, " +
          "which truncates the final period and can change which instance BYSETPOS selects " +
          "there. This is the last-period twin of the first-period question above.",
        evidence: [F("014-metamorphic-properties")],
      });
    }
    if (r.FREQ === "WEEKLY" && has("BYMONTH")) {
      out.push({
        id: "libical-weekly-bymonth-bysetpos",
        severity: "diverges",
        title: "FREQ=WEEKLY with BYMONTH and BYSETPOS: older libical drops occurrences",
        body:
          "In a week that straddles a BYMONTH boundary, libical loses occurrences that the " +
          "specification's reading produces. This was reported as libical issue 1374 and " +
          "fixed upstream on 2026-09-10 in commit 4edd39a; at that commit all eight of this " +
          "project's corpus cases pass, with no regression elsewhere. It is still present in " +
          "every released version, including the 3.0.20 in Debian trixie, where it is part " +
          "of a larger BYSETPOS failure class. So this depends on which libical you have, " +
          "and most deployed calendars still have an affected one. If your stack goes " +
          "through libical — evolution, and much of the C/C++ calendar world does — check " +
          "this rule against your build directly rather than against master.",
        evidence: [
          F("019-libical-weekly-bymonth-bysetpos"),
          { label: "libical/libical#1374", url: "https://github.com/libical/libical/issues/1374" },
        ],
      });
    }
  }

  // --- FREQ=WEEKLY: what does BYMONTH limit? ----------------------------
  // Finding 022. Computed, not syntactic: the seed-limit expansion is built
  // and compared, so this fires only on rules the reading actually changes.
  if (r.FREQ === "WEEKLY" && has("BYMONTH") && has("BYDAY")) {
    const alt = seedLimitWeekly(r, rrule, dtstart, limit);
    const k = alt ? Math.min(alt.length, occurrences.length) : 0;
    const differs = k > 0 && !sameList(alt.slice(0, k), occurrences.slice(0, k));
    if (differs) {
      const dropsDtstart = occurrences[0] === dtstart && alt[0] !== dtstart;
      const named = r.BYMONTH.map((m) => MONTHS[m - 1]).join(", ");
      out.push({
        id: "weekly-bymonth-seed-limit",
        severity: has("BYSETPOS") ? "diverges" : "note",
        title: "FREQ=WEEKLY with BYMONTH: two readings of what BYMONTH limits",
        body:
          "RFC 5545 3.3.10 applies BYMONTH before BYDAY, and under FREQ=WEEKLY BYMONTH " +
          "limits while BYDAY expands — so BYMONTH runs before the week has become days. " +
          "What it limits is not stated. On one reading it restricts the instants the week " +
          `finally yields, so nothing outside ${named} survives; that is the list above. On ` +
          "the other it applies to the single DTSTART-derived seed of each week, selecting " +
          "whole weeks, which BYDAY then expands across the week — " +
          `including into months outside ${named}. That is the list beside it.` +
          (has("BYSETPOS")
            ? " Your rule has BYSETPOS, which is where the readings have been seen to part " +
              "company in shipped code. python-dateutil 2.9.0.post0, rrule.js and dmfs " +
              "lib-recur 0.17.1 produce the list above. ical4j 4.1.1 and libical master do " +
              "not: on some rules of this shape each returns exactly the seed-limit list, " +
              "and on others a third list that is neither reading, so the alternative here " +
              "is not a prediction of what they will do with your rule. It is what the " +
              "other reading of 3.3.10 would cost, computed on your rule. This is a " +
              "separate question from the released-libical defect noted above, which is a " +
              "bug in versions rather than a disagreement about the text."
            : " Without BYSETPOS this is a reading question rather than a measured split: " +
              "all six implementations this project runs — including libical master and " +
              "ical4j 4.1.1 — produce the list above. The other reading is shown because it " +
              "was argued for on libical issue 1374 by a maintainer, and because the price " +
              "of it is visible beside your own rule rather than in the abstract.") +
          (dropsDtstart
            ? " Note what the seed-limit list costs here: DTSTART itself is not in it. " +
              "RFC 5545 3.8.5.3 says DTSTART defines the first instance of the recurrence " +
              "set, and excuses an implementation only when DTSTART is not synchronised " +
              "with the rule — which is itself decided by whichever reading you take."
            : ""),
        evidence: [
          F("022-weekly-bymonth-ordering"),
          RFC5545("3.3.10", "3.3.10"),
          { label: "libical/libical#1374", url: "https://github.com/libical/libical/issues/1374" },
        ],
        compare: {
          label: "seed-limit reading — BYMONTH selects whole weeks by the month of their seed",
          occurrences: show(alt),
        },
      });
    }
  }

  // --- BYDAY mixing signed and unsigned entries -------------------------
  if (has("BYDAY") && ["MONTHLY", "YEARLY"].includes(r.FREQ)) {
    const signed = r.BYDAY.filter(([n]) => n !== null);
    const plain = r.BYDAY.filter(([n]) => n === null);
    if (signed.length && plain.length) {
      out.push({
        id: "byday-mixed-signed",
        severity: "diverges",
        title: "BYDAY mixes a numbered weekday with a plain one",
        body:
          `Your BYDAY list contains both ${signed.map(([n, d]) => (n > 0 ? "+" : "") + n + d).join(", ")} ` +
          `and ${plain.map(([, d]) => d).join(", ")}. A BYDAY list is a union of its elements, ` +
          "so this means “the numbered day, and also every one of the plain days”. " +
          "python-dateutil 2.9.0.post0 returns no occurrences at all for such a list: it " +
          "splits BYDAY into a numbered and an unnumbered set and then requires a date to " +
          "satisfy both. Its own BYMONTHDAY handling, three lines away in the same condition, " +
          "gets the signed/unsigned union right.",
        evidence: [F("013-byday-mixed-signed-and-unsigned")],
      });
    }
  }

  // --- FREQ=YEARLY: expand over the year, or inherit from DTSTART? ------
  // RFC 5545 3.3.10's table classes BYMONTHDAY and BYWEEKNO as Expand for
  // YEARLY. Three implementations sharing no code (libical, ical4j 4.1.1, dmfs
  // lib-recur 0.17.1) instead inherit the unspecified component from DTSTART.
  // This was the largest single failure family in all three.
  //
  // This said "two" until 2026-09-11, which was written before libical was
  // adapted and never revisited. Finding 017 had already counted three: 41
  // BYMONTHDAY cases where all three agree against the corpus, and a check of
  // the BYWEEKNO branch adds 15 of 42. Undercounting mattered because the
  // whole point of the sentence is how much weight the other reading carries.
  if (r.FREQ === "YEARLY") {
    let pinKey = null, pinVal = null, what = null;
    if (has("BYMONTHDAY") && !has("BYMONTH")) {
      pinKey = "BYMONTH"; pinVal = ds.mo;
      what = `the month is not fixed, so the specification's table expands this over every month ` +
             `(the 15th of January, February, March, …). The other reading takes the month ` +
             `from DTSTART — ${MONTHS[ds.mo - 1]} — and yields one occurrence a year.`;
    } else if (has("BYWEEKNO") && !has("BYDAY")) {
      pinKey = "BYDAY"; pinVal = DAYS[weekday(ds.ord)];
      what = `the weekday is not fixed, so the specification's table expands this over all seven ` +
             `days of the named week. The other reading takes the weekday from DTSTART — ` +
             `${DAYNAMES[DAYS[weekday(ds.ord)]]} — and yields one occurrence a year.`;
    }
    if (pinKey) {
      const alt = tryExpand(withPart(rrule, pinKey, pinVal), dtstart, { limit });
      if (alt && alt.length && !sameList(alt, occurrences)) {
        out.push({
          id: "yearly-expand-vs-inherit",
          severity: "diverges",
          title: `FREQ=YEARLY with ${pinKey === "BYMONTH" ? "BYMONTHDAY" : "BYWEEKNO"}: two readings, and both are in use`,
          body:
            `Under FREQ=YEARLY, ${what} RFC 5545 3.3.10's table classifies this part as ` +
            "“Expand”, which is the left-hand answer. python-dateutil and rrule.js " +
            "produce it, but those two are one lineage: rrule.js is a documented port. " +
            "Three implementations that share no code with it or with each other — " +
            "libical, ical4j 4.1.1 and dmfs lib-recur 0.17.1 — produce the right-hand " +
            "answer instead, and a libical maintainer has argued in public for reading " +
            "these parts as limiting each other. Whether that is a defect in three " +
            "libraries or a widely-taken pragmatic reading of an awkward table is not " +
            `settled. If it matters to you, say so explicitly by adding ${pinKey} to the rule.`,
          evidence: [F("016-independent-lineage-results"), F("017-libical-third-lineage"),
                     RFC5545("3.3.10", "3.3.10")],
          compare: {
            label: `component inherited from DTSTART (the libical / ical4j / lib-recur reading, shown here by pinning ${pinKey}=${pinVal})`,
            occurrences: show(alt),
          },
        });
      }
    }
  }

  // --- BYWEEKNO ---------------------------------------------------------
  if (has("BYWEEKNO")) {
    const odd = r.BYWEEKNO.filter((v) => v === 53 || v === -53 || v < 0);
    out.push({
      id: "byweekno",
      severity: "diverges",
      title: "BYWEEKNO is the least reliably implemented part of RRULE",
      body:
        "Week numbering follows ISO 8601 generalised to your WKST: week 1 is the first week " +
        "with at least four days in the year, so early January can belong to the previous " +
        "year's last week and late December to the next year's first. python-dateutil " +
        "2.9.0.post0 gets the year boundary wrong; there is an open upstream fix " +
        "(dateutil/dateutil#1537). What a date's week number is when its week straddles a " +
        "year boundary and FREQ=YEARLY is asking about a single year is a genuine gap in " +
        "the specification, not just a bug." +
        (odd.length
          ? " Your rule uses " + odd.join(", ") +
            ". Note that most years have no week 53 — a rule asking for it fires only " +
            "in the years that have one, which is not the same as “the last week of the year” " +
            "(that is BYWEEKNO=-1)."
          : ""),
      evidence: [
        F("008-byweekno-previous-year-last-week"),
        F("002-byweekno-year-boundary"),
        { label: "dateutil/dateutil#1537", url: "https://github.com/dateutil/dateutil/pull/1537" },
      ],
    });
  }

  // --- does WKST change the answer? -------------------------------------
  // Computed by re-expanding under each of the seven values. WKST defaults to
  // MO and is very often left out of a rule that needs it.
  {
    const differ = [];
    for (const d of DAYS) {
      if (d === r.WKST) continue;
      const alt = tryExpand(withPart(rrule, "WKST", d), dtstart, { limit });
      if (alt && !sameList(alt, occurrences)) differ.push(d);
    }
    if (differ.length) {
      out.push({
        id: "wkst-sensitive",
        severity: "diverges",
        title: `This rule's answer changes with WKST (${differ.join(", ")} all differ from ${r.WKST})`,
        body:
          (rrule.toUpperCase().includes("WKST=")
            ? `Your rule sets WKST=${r.WKST}. `
            : "Your rule does not set WKST, so the default of MO applies. ") +
          "Changing it to " + differ.join(", ") + " gives a different set of dates. WKST is " +
          "the part most often dropped when a rule is copied between systems, and a calendar " +
          "that localises the first day of the week can supply a different default than the " +
          "one you tested against. If the answer matters, write WKST into the rule.",
        evidence: [RFC5545("3.3.10", "3.3.10")],
      });
    }
  }

  // --- the rule skips periods -------------------------------------------
  // BYMONTHDAY=31, BYYEARDAY=366, BYWEEKNO=53 and February 29 all produce
  // recurrences with holes. Computed from the expansion, so it says which
  // periods are actually missing rather than which parts look suspicious.
  {
    const unit = { YEARLY: "year", MONTHLY: "month" }[r.FREQ];
    if (unit && occurrences.length >= 2) {
      const key = (t) => (unit === "year" ? parts(t).y : parts(t).y * 12 + parts(t).mo - 1);
      const seen = [...new Set(occurrences.map(key))];
      const holes = [];
      for (let i = 1; i < seen.length; i++) {
        const gap = seen[i] - seen[i - 1];
        if (gap > r.INTERVAL) holes.push([seen[i - 1], seen[i], gap]);
      }
      if (holes.length) {
        const label = (k) => (unit === "year" ? String(k) : `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`);
        out.push({
          id: "skipped-periods",
          severity: "note",
          title: `This rule skips ${unit}s`,
          body:
            `It does not fire in every ${unit}. Between ${label(holes[0][0])} and ` +
            `${label(holes[0][1])} there is a gap of ${holes[0][2]} ${unit}s` +
            (holes.length > 1 ? `, and there are ${holes.length} such gaps in the dates shown` : "") +
            ". That is usually intended (a rule for the 31st cannot fire in a 30-day month), " +
            "but it is also what “the event silently disappeared for a year” looks " +
            "like. RFC 5545 3.3.10: “Recurrence rules may generate recurrence instances " +
            "with an invalid date (e.g., February 30) … Such recurrence instances MUST be " +
            "ignored and MUST NOT be counted as part of the recurrence set.”",
          evidence: [RFC5545("3.3.10", "3.3.10")],
        });
      }
    }
  }

  // --- DATE-valued DTSTART with time-of-day parts -----------------------
  if (dateOnly && ["BYHOUR", "BYMINUTE", "BYSECOND"].some(has)) {
    out.push({
      id: "date-value-with-time-parts",
      severity: "note",
      title: "A time-of-day BYxxx part with a DATE-valued DTSTART",
      body:
        "DTSTART here is a date with no time, as an all-day event has. RFC 5545 3.3.10 says " +
        "BYSECOND, BYMINUTE and BYHOUR MUST NOT be specified when DTSTART is a DATE value. " +
        "Implementations do not agree on what to do with such a rule; the dates below drop " +
        "the time-of-day parts.",
      evidence: [F("011-date-valued-dtstart"), RFC5545("3.3.10", "3.3.10")],
    });
  }

  // --- ical.js turns an impossible BYMONTHDAY into a date in the next month --
  {
    const rn = monthdayRolloverNote(rrule, dtstart, limit);
    if (rn) out.push(rn);
  }

  // --- lib-recur answers an overshot BYWEEKNO with December 32nd -----------
  {
    const wn = weeknoOverflowNote(rrule, dtstart, limit);
    if (wn) out.push(wn);
    const tn = weekYearTruncatedNote(rrule, dtstart, limit);
    if (tn) out.push(tn);
    const bn = weeksInYearBlindNote(rrule, dtstart, limit);
    if (bn) out.push(bn);
  }

  // --- ical.js abandons a long empty run and calls the series complete ----
  {
    const cut = icaljsAbandons(rrule, occurrences);
    if (cut) {
      out.push({
        id: "icaljs-yearly-abandon",
        severity: "diverges",
        title: "ical.js stops this series early, and reports no error",
        body:
          `This rule produces nothing for ${cut.empties} consecutive yearly ` +
          `iterations between ${cut.lastYear} and ${cut.nextYear}. ical.js 2.2.1 ` +
          `gives up after 28 such iterations and marks the series complete, so it ` +
          `returns ${cut.keep} occurrence${cut.keep === 1 ? "" : "s"} here and then ` +
          `stops at ${cut.lastYear}; ${fmt(occurrences[cut.keep], true)} and ` +
          `everything after it are silently missing. No exception is thrown and ` +
          `nothing distinguishes the result from a series that really did end. ` +
          `python-dateutil, rrule.js, lib-recur and ical4j 4.1.1 all return the ` +
          `full series. ical.js is the library Thunderbird calendaring uses. ` +
          `The bound is on iterations, not years, so raising INTERVAL can hide ` +
          `it; and because the search for the *first* occurrence is unbounded, ` +
          `the same rule evaluated from a DTSTART after ${cut.lastYear} is ` +
          `answered correctly.`,
        evidence: [F("103-the-year-the-iterator-gave-up")],
        compare: { label: "ical.js 2.2.1", occurrences: occurrences.slice(0, cut.keep) },
      });
    }
  }

  return out;
}
