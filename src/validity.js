// A port of src/validity.py: RFC 5545 3.3.10 rule-validity checks, independent
// of any expander. Whether a rule is *valid* is a different question from
// whether DTSTART is synchronized with it, and both are different from whether
// implementations agree on its output.
//
// Every check quotes the sentence of RFC 5545 3.3.10 it enforces.
// Text: https://www.rfc-editor.org/rfc/rfc5545.txt
// sha256 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb

const WEEKDAYNUM = /^([+-]?\d{1,2})?(SU|MO|TU|WE|TH|FR|SA)$/;

export const RULES = {
  "byday-numeric-freq":
    "The BYDAY rule part MUST NOT be specified with a numeric value when the FREQ rule part is not set to MONTHLY or YEARLY.",
  "byday-numeric-byweekno":
    "Furthermore, the BYDAY rule part MUST NOT be specified with a numeric value with the FREQ rule part set to YEARLY when the BYWEEKNO rule part is specified.",
  "bymonthday-weekly":
    "The BYMONTHDAY rule part MUST NOT be specified when the FREQ rule part is set to WEEKLY.",
  "byyearday-freq":
    "The BYYEARDAY rule part MUST NOT be specified when the FREQ rule part is set to DAILY, WEEKLY, or MONTHLY.",
  "byweekno-freq":
    "This rule part MUST NOT be used when the FREQ rule part is set to anything other than YEARLY.",
  "bysetpos-needs-byxxx": "It MUST only be used in conjunction with another BYxxx rule part.",
  "freq-required": "The FREQ rule part ... MUST be specified in the recurrence rule.",
  "count-until-exclusive":
    "The UNTIL or COUNT rule parts are OPTIONAL, but they MUST NOT occur in the same 'recur'.",
  "value-range": "Valid values are as stated per rule part in RFC 5545 3.3.10.",
  "freq-value":
    'freq = "SECONDLY" / "MINUTELY" / "HOURLY" / "DAILY" / "WEEKLY" / "MONTHLY" / "YEARLY"',
  "part-repeated": "The other rule parts are OPTIONAL, but MUST NOT occur more than once.",
  "count-zero":
    'COUNT = 1*DIGIT, and "The COUNT rule part defines the number of occurrences at which to range-bound the recurrence. The DTSTART property value always counts as the first occurrence." COUNT=0 is syntactically well-formed but cannot describe a recurrence whose first occurrence is DTSTART.',
};

/** What violations() does NOT check. An empty result means "no violation of
 *  the checks below was detected", never "this rule is valid". */
export const NOT_CHECKED = [
  "BYSECOND/BYMINUTE/BYHOUR with a DATE-valued DTSTART",
  "UNTIL value-type and UTC agreement with DTSTART",
  "whether the rule is satisfiable at all (e.g. BYMONTHDAY=30;BYMONTH=2)",
  "RRULE-vs-RECUR framing: property parameters, folding, escaping",
];

const RANGES = {
  BYSECOND: [0, 60, false], BYMINUTE: [0, 59, false], BYHOUR: [0, 23, false],
  BYMONTH: [1, 12, false], BYMONTHDAY: [1, 31, true], BYYEARDAY: [1, 366, true],
  BYWEEKNO: [1, 53, true], BYSETPOS: [1, 366, true],
};
const BYXXX = ["BYSECOND", "BYMINUTE", "BYHOUR", "BYDAY", "BYMONTHDAY",
               "BYYEARDAY", "BYWEEKNO", "BYMONTH"];
const FREQS = ["SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"];

function rawParts(rule) {
  const out = {}, seen = new Set(), dup = [];
  for (const chunk of String(rule).trim().split(";")) {
    if (!chunk || !chunk.includes("=")) continue;
    const i = chunk.indexOf("=");
    const k = chunk.slice(0, i).trim().toUpperCase();
    if (seen.has(k)) dup.push(k);
    seen.add(k);
    out[k] = chunk.slice(i + 1).trim();
  }
  return { p: out, dup };
}

/** [{rule, part, detail, rfc}]. Empty means no checked 3.3.10 violation was found. */
export function violations(rule) {
  const { p, dup } = rawParts(rule);
  const out = [];
  const bad = (id, part, detail) => out.push({ rule: id, part, detail, rfc: RULES[id] });

  const freq = p.FREQ ? p.FREQ.toUpperCase() : undefined;
  if (!p.FREQ) bad("freq-required", "FREQ", "FREQ is absent");
  else if (!FREQS.includes(freq)) bad("freq-value", "FREQ", `${JSON.stringify(p.FREQ)} is not one of ${FREQS.join(", ")}`);

  for (const k of dup) bad("part-repeated", k, `${k} occurs more than once`);
  if ("COUNT" in p && "UNTIL" in p) bad("count-until-exclusive", "COUNT/UNTIL", "both present");

  if ("COUNT" in p) {
    if (!/^[+-]?\d+$/.test(p.COUNT)) bad("value-range", "COUNT", `unreadable ${JSON.stringify(p.COUNT)}`);
    else {
      const c = parseInt(p.COUNT, 10);
      if (c < 0) bad("value-range", "COUNT", `COUNT = 1*DIGIT, ${c} is negative`);
      else if (c === 0) bad("count-zero", "COUNT", "COUNT=0");
    }
  }

  if ("BYDAY" in p) {
    const numeric = [];
    for (const tok of p.BYDAY.split(",")) {
      const t = tok.trim().toUpperCase();
      const m = WEEKDAYNUM.exec(t);
      if (!m) { bad("value-range", "BYDAY", `unreadable weekdaynum ${JSON.stringify(tok)}`); continue; }
      if (m[1] !== undefined) {
        const n = Math.abs(parseInt(m[1], 10));
        if (n < 1 || n > 53) bad("value-range", "BYDAY", `ordwk ${m[1]} out of range 1..53 in ${JSON.stringify(t)}`);
        numeric.push(t);
      }
    }
    if (numeric.length) {
      if (freq !== "MONTHLY" && freq !== "YEARLY")
        bad("byday-numeric-freq", "BYDAY", `numeric ${numeric.join(", ")} with FREQ=${freq}`);
      else if (freq === "YEARLY" && "BYWEEKNO" in p)
        bad("byday-numeric-byweekno", "BYDAY", `numeric ${numeric.join(", ")} with FREQ=YEARLY and BYWEEKNO=${p.BYWEEKNO}`);
    }
  }

  if ("BYMONTHDAY" in p && freq === "WEEKLY") bad("bymonthday-weekly", "BYMONTHDAY", "with FREQ=WEEKLY");
  if ("BYYEARDAY" in p && ["DAILY", "WEEKLY", "MONTHLY"].includes(freq))
    bad("byyearday-freq", "BYYEARDAY", `with FREQ=${freq}`);
  if ("BYWEEKNO" in p && freq !== "YEARLY") bad("byweekno-freq", "BYWEEKNO", `with FREQ=${freq}`);
  if ("BYSETPOS" in p && !BYXXX.some((b) => b in p)) bad("bysetpos-needs-byxxx", "BYSETPOS", "no other BYxxx rule part");

  for (const [part, [lo, hi, mirror]] of Object.entries(RANGES)) {
    if (!(part in p)) continue;
    for (const tok of p[part].split(",")) {
      const t = tok.trim();
      if (!/^[+-]?\d+$/.test(t)) { bad("value-range", part, `unreadable ${JSON.stringify(p[part])}`); break; }
      const v = parseInt(t, 10);
      if (!((v >= lo && v <= hi) || (mirror && v >= -hi && v <= -lo)))
        bad("value-range", part, `${v} out of range`);
    }
  }

  if ("INTERVAL" in p) {
    if (!/^[+-]?\d+$/.test(p.INTERVAL)) bad("value-range", "INTERVAL", `unreadable ${JSON.stringify(p.INTERVAL)}`);
    else if (parseInt(p.INTERVAL, 10) < 1) bad("value-range", "INTERVAL", `${p.INTERVAL} < 1`);
  }
  return out;
}
