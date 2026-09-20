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

import { expand, parse, parts, fmt, weekday, weekStart, fromOrd, DAYS } from "./naive.js";

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

  return out;
}
