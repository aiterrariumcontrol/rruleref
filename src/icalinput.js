// Read what people actually have, instead of what the expander wants.
//
// Nobody has a bare RRULE string. They have a .ics file, or the fragment of
// one that a colleague or a bug tracker pasted at them. Before this file, the
// tool required them to split DTSTART out by hand into a second box -- which
// is precisely the step where a TZID or a VALUE=DATE gets dropped, and
// dropping either one changes the answer. That made the user do, unaided, a
// piece of the parsing this tool exists to do.
//
// parseInput(text) accepts:
//   * a bare rule            FREQ=MONTHLY;BYDAY=-1FR
//   * a prefixed rule        RRULE:FREQ=MONTHLY;BYDAY=-1FR
//   * loose content lines    DTSTART;TZID=Europe/Paris:...  + RRULE:...
//   * a whole VEVENT or VCALENDAR
//
// and returns { rrule, dtstart, notes[] }. It never silently discards a line:
// anything recognised and not used produces a note, because the failure mode
// of a tool like this is looking like it considered something it ignored.

const WANTED = new Set(["RRULE", "DTSTART"]);

// Properties that change the recurrence set but that this tool does not
// implement. Each maps to what its presence means for the answer shown.
const AFFECTS_THE_ANSWER = {
  EXDATE: "removes occurrences from the set. The dates below do not have them removed.",
  RDATE: "adds occurrences to the set. The dates below do not include them.",
  EXRULE: "removes occurrences from the set (RFC 2445; dropped in RFC 5545). " +
          "The dates below do not have them removed.",
};

// Properties that are simply not this tool's subject. Worth naming so the
// user can see they were read and set aside, rather than wonder.
const NOT_OUR_SUBJECT = new Set([
  "DTEND", "DURATION", "SUMMARY", "DESCRIPTION", "LOCATION", "UID", "ORGANIZER",
  "ATTENDEE", "STATUS", "SEQUENCE", "CREATED", "LAST-MODIFIED", "DTSTAMP",
  "TRANSP", "CLASS", "CATEGORIES", "PRIORITY", "URL", "RECURRENCE-ID",
]);

/** RFC 5545 3.1: undo line folding before anything else looks at the text. */
export function unfold(text) {
  return String(text).replace(/\r\n|\r/g, "\n").replace(/\n[ \t]/g, "");
}

/** Split one content line into { name, params, value }. */
export function contentLine(line) {
  // The colon that ends the name+params is the first one not inside a quoted
  // parameter value: TZID="A:B":20260101T000000 is legal.
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') inQuote = !inQuote;
    else if (c === ":" && !inQuote) {
      const head = line.slice(0, i);
      const value = line.slice(i + 1);
      const segs = [];
      let cur = "", q = false;
      for (const ch of head) {
        if (ch === '"') { q = !q; cur += ch; }
        else if (ch === ";" && !q) { segs.push(cur); cur = ""; }
        else cur += ch;
      }
      segs.push(cur);
      const params = {};
      for (const s of segs.slice(1)) {
        const eq = s.indexOf("=");
        if (eq > 0) params[s.slice(0, eq).toUpperCase()] = s.slice(eq + 1).replace(/^"|"$/g, "");
      }
      return { name: segs[0].trim().toUpperCase(), params, value: value.trim() };
    }
  }
  return null;
}

function looksLikeBareRule(text) {
  // A bare rule is one line of KEY=VALUE pairs. This is also the format the
  // shared-link fragment carries, so it must keep working untouched.
  return !text.includes("\n") && !/^\s*(RRULE|DTSTART|BEGIN)\b[;:]/i.test(text) &&
         /^\s*[A-Z-]+=/i.test(text);
}

export function parseInput(text) {
  const notes = [];
  const raw = String(text == null ? "" : text).trim();
  if (!raw) return { rrule: "", dtstart: "", notes };

  if (looksLikeBareRule(raw)) return { rrule: raw, notes };

  const lines = unfold(raw).split("\n").map((l) => l.trim()).filter(Boolean);

  // Track the component stack. This matters more than it looks: a real
  // VCALENDAR usually carries a VTIMEZONE, and its STANDARD and DAYLIGHT
  // subcomponents each hold their own DTSTART *and their own RRULE* -- the
  // daylight-saving transition rules. Taking "the first RRULE in the text"
  // would hand the user the timezone's DST rule and call it their event.
  const stack = [];
  const EVENTISH = new Set(["VEVENT", "VTODO", "VJOURNAL"]);
  const found = { RRULE: [], DTSTART: [] };
  const ignored = new Map();       // name -> count, from event scope only
  let eventCount = 0, sawTimezone = false, sawComponent = false;

  for (const line of lines) {
    const cl = contentLine(line);
    if (!cl) continue;
    if (cl.name === "BEGIN") {
      stack.push(cl.value.toUpperCase());
      sawComponent = true;
      if (EVENTISH.has(cl.value.toUpperCase())) eventCount++;
      if (cl.value.toUpperCase() === "VTIMEZONE") sawTimezone = true;
      continue;
    }
    if (cl.name === "END") { stack.pop(); continue; }

    const inTimezone = stack.includes("VTIMEZONE");
    if (inTimezone) continue;      // its RRULEs are the zone's, not the user's
    // Outside any component (loose pasted lines) counts as event scope.
    const inEvent = stack.length === 0 || EVENTISH.has(stack[stack.length - 1]);
    if (!inEvent) continue;

    if (WANTED.has(cl.name)) { found[cl.name].push(cl); continue; }
    if (cl.name in AFFECTS_THE_ANSWER || !NOT_OUR_SUBJECT.has(cl.name)) {
      if (!/^X-/.test(cl.name) && cl.name in AFFECTS_THE_ANSWER)
        ignored.set(cl.name, (ignored.get(cl.name) || 0) + 1);
    }
  }

  if (eventCount > 1) {
    return {
      rrule: "", dtstart: "",
      notes: [{ level: "error", title: "More than one event in this paste", text:
        `This paste contains ${eventCount} components with their own recurrence ` +
        "(VEVENT/VTODO/VJOURNAL). This tool debugs one rule at a time and will not " +
        "guess which one you meant. Paste a single event." }],
    };
  }
  if (sawComponent && eventCount === 0 && !found.RRULE.length) {
    const what = sawTimezone ? "only a VTIMEZONE, whose RRULEs describe the zone's " +
      "daylight-saving transitions rather than any event" : "no VEVENT, VTODO or VJOURNAL";
    return { rrule: "", dtstart: "",
             notes: [{ level: "error", title: "No event to expand", text:
               `This paste contains ${what}. Nothing to expand.` }] };
  }

  if (!found.RRULE.length) {
    return { rrule: "", dtstart: "",
             notes: [{ level: "error", title: "No RRULE in this paste", text:
               "No RRULE line found. Paste an event that has one, or type the rule itself " +
               "(FREQ=...)." }] };
  }
  if (found.RRULE.length > 1) {
    notes.push({ level: "warn", title: "More than one RRULE", text:
      `This event has ${found.RRULE.length} RRULE lines; only the first is expanded below. ` +
      "RFC 5545 3.6.1 allows at most one RRULE in a VEVENT, and implementations differ on " +
      "what they do with more." });
  }

  const rrule = found.RRULE[0].value.trim();
  let dtstart = "", dsNotes = [];
  if (found.DTSTART.length) {
    const d = found.DTSTART[0];
    dtstart = d.value.trim();
    dsNotes = dtstartNotes(d, rrule);
  } else {
    notes.push({ level: "warn", title: "No DTSTART in the paste", text:
      "No DTSTART line in the paste, so the DTSTART box was left as it was. Every answer " +
      "this tool gives depends on it: RFC 5545 3.8.5.3 says “The ‘DTSTART’ " +
      "property defines the first instance in the recurrence set.”" });
  }
  notes.push(...dsNotes);

  for (const [name, n] of ignored) {
    notes.push({ level: "warn", title: `${name} was not applied`, text:
      `${name}${n > 1 ? ` (×${n})` : ""} is present and was not applied. It ` +
      AFFECTS_THE_ANSWER[name] });
  }

  return { rrule, dtstart, notes };
}

/** What a DTSTART's parameters mean for an expander that has no timezone data. */
function dtstartNotes(d, rrule) {
  const out = [];
  const tzid = d.params.TZID;
  const isUtc = /Z$/i.test(d.value);
  const valueDate = (d.params.VALUE || "").toUpperCase() === "DATE";

  if (valueDate && /T/i.test(d.value)) {
    out.push({ level: "warn", title: "VALUE=DATE disagrees with the value", text:
      "DTSTART says VALUE=DATE but its value carries a time. They disagree; the value was " +
      "used as written." });
  }
  if (tzid) {
    // Deliberately not a refusal. A recurrence rule is evaluated against the
    // local time of DTSTART, so the wall-clock dates below are the right
    // wall-clock dates for that zone -- this tool just never converts them to
    // instants. The place it can actually be wrong is UNTIL, and DST.
    let text = `DTSTART carries TZID=${tzid}. This tool has no timezone database: it expands ` +
      "in wall-clock time, which is what the rule is evaluated against, so the dates below " +
      "are the local dates in that zone. It does not convert them to UTC instants.";
    if (/(^|;)UNTIL=/i.test(rrule)) {
      text += " This rule also has an UNTIL, and that is where the omission bites: RFC 5545 " +
        "3.3.10 says “If the ‘DTSTART’ property is specified as a date with " +
        "UTC time or a date with local time and time zone reference, then the UNTIL rule " +
        "part MUST be specified as a date with UTC time.” So UNTIL is an instant in UTC " +
        "while the occurrences are local, and this tool compares them directly. The last " +
        "occurrence or two may be wrong by the zone's offset.";
      out.push({ level: "error", title: `UNTIL is UTC but DTSTART is in ${tzid}`, text });
      return out;
    }
    out.push({ level: "warn", title: `TZID=${tzid} was read but not applied`, text });
  } else if (isUtc) {
    out.push({ level: "info", title: "DTSTART is UTC", text:
      "DTSTART is in UTC (trailing Z). The dates below are UTC." });
  }
  return out;
}
