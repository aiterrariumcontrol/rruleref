import { expand, parse, parseDtstart, parts, fmt, weekday, daysInMonth, toOrd, DAYS, Budget } from "./src/naive.js";
import { violations, NOT_CHECKED } from "./src/validity.js";
import { analyze } from "./src/diagnostics.js";
import { parseInput } from "./src/icalinput.js";
import { why, parseQuery, resolveQuery } from "./src/why.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
const DAYNAMES = { MO: "Mon", TU: "Tue", WE: "Wed", TH: "Thu", FR: "Fri", SA: "Sat", SU: "Sun" };
const MAX_GRIDS = 14;

// --- shareable state in the URL fragment ---------------------------------
// A developer debugging this with a colleague wants to send them the case,
// not a screenshot. Everything needed is in the fragment, which never leaves
// the browser.
function readHash() {
  const p = new URLSearchParams(location.hash.replace(/^#/, ""));
  if (p.get("rrule")) $("rrule").value = p.get("rrule");
  if (p.get("dtstart")) $("dtstart").value = p.get("dtstart");
  if (p.get("limit")) $("limit").value = p.get("limit");
  if (p.get("why")) $("why").value = p.get("why");
}
function writeHash() {
  const fields = {
    rrule: $("rrule").value.trim(),
    dtstart: $("dtstart").value.trim(),
    limit: $("limit").value,
  };
  // Only carried when it is asked, so an ordinary expansion still shares as a
  // short link.
  if ($("why").value.trim()) fields.why = $("why").value.trim();
  const p = new URLSearchParams(fields);
  history.replaceState(null, "", "#" + p.toString());
}

// --- rendering ------------------------------------------------------------

function occurrenceList(occ, dateOnly, dtstart) {
  const wrap = el("div", "occ-list");
  let prev = null;
  for (const t of occ) {
    const p = parts(t);
    const line = el("div", "occ");
    line.appendChild(el("span", "occ-day", DAYNAMES[DAYS[weekday(p.ord)]]));
    line.appendChild(el("span", "occ-date", `${p.y}-${String(p.mo).padStart(2, "0")}-${String(p.d).padStart(2, "0")}`));
    if (!dateOnly) {
      line.appendChild(el("span", "occ-time",
        `${String(p.h).padStart(2, "0")}:${String(p.mi).padStart(2, "0")}:${String(p.s).padStart(2, "0")}`));
    }
    if (prev !== null) {
      const days = Math.floor(t / 86400) - Math.floor(prev / 86400);
      line.appendChild(el("span", "occ-gap", days === 0 ? "same day" : `+${days}d`));
    } else if (t === dtstart) {
      line.appendChild(el("span", "occ-tag", "DTSTART"));
    }
    if (prev !== null && t === dtstart) line.appendChild(el("span", "occ-tag", "DTSTART"));
    prev = t;
    wrap.appendChild(line);
  }
  return wrap;
}

function monthGrids(occ, dtstart, wkst) {
  const days = new Set(occ.map((t) => Math.floor(t / 86400)));
  const months = [];
  const seen = new Set();
  for (const t of occ) {
    const p = parts(t);
    const key = p.y * 12 + p.mo - 1;
    if (!seen.has(key)) { seen.add(key); months.push([p.y, p.mo]); }
  }
  const shown = months.slice(0, MAX_GRIDS);
  const wrap = el("div", "grids");
  const order = [];
  const start = DAYS.indexOf(wkst) < 0 ? 0 : DAYS.indexOf(wkst);
  for (let i = 0; i < 7; i++) order.push(DAYS[(start + i) % 7]);

  for (const [y, mo] of shown) {
    const box = el("section", "month");
    box.appendChild(el("h3", null, `${MONTHS[mo - 1]} ${y}`));
    const grid = el("div", "grid");
    for (const d of order) grid.appendChild(el("div", "dow", DAYNAMES[d]));
    const first = toOrd(y, mo, 1);
    const lead = (weekday(first) - start + 7) % 7;
    for (let i = 0; i < lead; i++) grid.appendChild(el("div", "pad"));
    for (let d = 1; d <= daysInMonth(y, mo); d++) {
      const ord = toOrd(y, mo, d);
      const cell = el("div", "cell", String(d));
      if (days.has(ord)) cell.classList.add("hit");
      if (ord === Math.floor(dtstart / 86400)) cell.classList.add("start");
      grid.appendChild(cell);
    }
    box.appendChild(grid);
    wrap.appendChild(box);
  }
  if (months.length > shown.length) {
    wrap.appendChild(el("p", "more", `…and ${months.length - shown.length} more months in the list above.`));
  }
  return wrap;
}

function noteBox(note) {
  const box = el("article", `note note-${note.severity}`);
  const head = el("h3");
  head.appendChild(el("span", "badge",
    note.severity === "error" ? "problem" : note.severity === "diverges" ? "implementations disagree" : "worth knowing"));
  head.appendChild(document.createTextNode(note.title));
  box.appendChild(head);
  box.appendChild(el("p", null, note.body));
  if (note.compare) {
    const cmp = el("div", "compare");
    cmp.appendChild(el("h4", null, note.compare.label));
    const list = el("div", "compare-dates");
    for (const s of note.compare.occurrences.slice(0, 12)) list.appendChild(el("code", null, s));
    cmp.appendChild(list);
    box.appendChild(cmp);
  }
  if (note.evidence && note.evidence.length) {
    const ev = el("p", "evidence");
    ev.appendChild(document.createTextNode("Evidence: "));
    note.evidence.forEach((e, i) => {
      if (i) ev.appendChild(document.createTextNode(" · "));
      const a = el("a", null, e.label);
      a.href = e.url; a.rel = "noopener"; a.target = "_blank";
      ev.appendChild(a);
    });
    box.appendChild(ev);
  }
  return box;
}

// --- the date explainer ---------------------------------------------------

function whyBox(w) {
  const box = el("article", "why " + (w.status === "occurrence" ? "yes"
    : w.status === "inconsistent" ? "broken" : "no"));
  box.appendChild(el("h3", null, w.headline));
  if (w.body) box.appendChild(el("p", null, w.body));
  if (w.checks && w.checks.length) {
    const ul = el("ul", "checks");
    for (const c of w.checks) {
      const li = el("li", c.ok === false ? "check-no" : "check-yes");
      li.appendChild(el("span", "mark", c.ok === false ? "\u2717" : "\u2713"));
      const text = el("span");
      // Rule parts are set in code type; the checks that are prose ("the
      // minute comes from DTSTART") are a sentence, not a token, and reading
      // them as code makes them look like something the user could have typed.
      text.appendChild(el("span", /^(FREQ|INTERVAL|BY)/.test(c.title) ? "check-part" : "check-name", c.title));
      text.appendChild(document.createTextNode(" \u2014 "));
      text.appendChild(el("span", "check-detail", c.detail));
      li.appendChild(text);
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
  if (w.evidence && w.evidence.length) {
    const ev = el("p", "evidence");
    ev.appendChild(document.createTextNode("Evidence: "));
    w.evidence.forEach((e, i) => {
      if (i) ev.appendChild(document.createTextNode(" \u00b7 "));
      const a = el("a", null, e.label);
      a.href = e.url; a.rel = "noopener"; a.target = "_blank";
      ev.appendChild(a);
    });
    box.appendChild(ev);
  }
  return box;
}

// The answer goes ABOVE the divergence notes and the dates. Someone who typed
// a date into this box asked one question, and it is the only thing on the
// page they are looking for.
function runWhy(rrule, ds, r) {
  const box = $("why-out");
  box.textContent = "";
  const raw = $("why").value.trim();
  if (!raw) return;
  let q;
  try {
    q = parseQuery(raw, ds.dateOnly);
  } catch (e) {
    box.appendChild(whyBox({ status: "inconsistent", headline: String(e.message || e),
      body: "Dates go in as 20260227 or 20260227T090000; a hyphenated 2026-02-27 works too.",
      checks: [], evidence: [] }));
    return;
  }
  // A DATE-valued DTSTART has no time of day to compare against, so a time
  // typed here would be measured against a midnight that is an artefact of
  // the value type rather than anything the user wrote.
  const dropped = ds.dateOnly && q.hadTime;
  let w, resolved;
  try {
    resolved = resolveQuery(r, ds.t, { ...q, t: ds.dateOnly ? Math.floor(q.t / 86400) * 86400 : q.t },
                            ds.dateOnly);
    w = why(r, ds.t, resolved.t, { dateOnly: ds.dateOnly, maxSteps: 2e6 });
  } catch (e) {
    box.appendChild(whyBox({ status: "inconsistent", headline: String(e.message || e),
      checks: [], evidence: [] }));
    return;
  }
  if (resolved.note) w = { ...w, body: `${resolved.note} ${w.body || ""}`.trim() };
  if (dropped) {
    w = { ...w, body: (w.body || "") + " (DTSTART is a DATE, with no time of day, so the time " +
          "you typed was not used \u2014 this rule can only produce whole dates.)" };
  }
  box.appendChild(whyBox(w));
}

// --- the run --------------------------------------------------------------

// DTSTART is derived-and-overridable: a paste that carries one fills the box,
// but a value the user typed there themselves survives further typing in the
// paste area. `lastDerived` is how the two are told apart -- if the box still
// holds exactly what the last paste put there, the paste still owns it.
let lastDerived = null;

function run() {
  const input = parseInput($("rrule").value);
  const rrule = (input.rrule || "").replace(/^RRULE:/i, "");
  if (input.dtstart && input.dtstart !== lastDerived &&
      ($("dtstart").value.trim() === (lastDerived || "") || !$("dtstart").value.trim())) {
    $("dtstart").value = input.dtstart;
    lastDerived = input.dtstart;
  }
  const dtstartRaw = $("dtstart").value.trim();
  const limit = Math.max(1, Math.min(500, parseInt($("limit").value, 10) || 24));
  const errBox = $("error"), notes = $("notes"), result = $("result");
  errBox.hidden = true; errBox.textContent = "";
  notes.textContent = ""; result.textContent = ""; $("why-out").textContent = "";

  // Anything the input parser read and set aside is said before the dates, not
  // after them. A caveat under the answer is a caveat the reader has already
  // acted on.
  for (const n of input.notes || []) {
    notes.appendChild(noteBox({
      severity: n.level === "error" ? "error" : "info",
      title: n.title || "About this input",
      body: n.text,
    }));
  }
  if (!rrule) { writeHash(); return; }
  writeHash();

  // Validity is checked first and independently of the expander: a rule can
  // violate a MUST NOT of 3.3.10 and still expand to something.
  let vios = [];
  try { vios = violations(rrule); } catch { /* reported by the parser below */ }
  for (const v of vios) {
    notes.appendChild(noteBox({
      severity: "error",
      title: `${v.part}: ${v.detail}`,
      body: `RFC 5545 §3.3.10: “${v.rfc}” Implementations differ on what they do with a rule ` +
            "that breaks this — some reject it, some silently ignore the offending part, " +
            "some apply it anyway. The dates below are one reading, not an authority.",
      evidence: [{ label: "RFC 5545 §3.3.10", url: "https://www.rfc-editor.org/rfc/rfc5545.html#section-3.3.10" }],
    }));
  }

  let ds, occ, r;
  try {
    ds = parseDtstart(dtstartRaw);
    r = parse(rrule);
    occ = expand(r, ds.t, { limit, maxSteps: 8e6 });
  } catch (e) {
    errBox.hidden = false;
    errBox.textContent = e instanceof Budget
      ? `This rule is too sparse to expand here: ${e.message}. The expander is a brute force ` +
        "over candidate times, which is what makes it easy to check against the specification " +
        "and slow on rules that almost never fire. Try a nearer DTSTART or fewer occurrences."
      : String(e.message || e);
    return;
  }

  runWhy(rrule, ds, r);

  // Count what is on the page before the divergence notes, so the "nothing
  // applies" box below is decided by whether *analyze* said anything -- not by
  // whether the page happens to be empty, which input notes now also affect.
  const beforeDiagnostics = notes.children.length;
  // ...and whether the input itself was reported as a problem. The "nothing
  // applies" box is about *measured divergences between implementations*,
  // which is a different axis from "your TZID was dropped". Printing the
  // reassurance directly under a red box reads as withdrawing it.
  const inputProblem = (input.notes || []).some((n) => n.level === "error");
  for (const note of analyze({ rrule, dtstart: ds.t, dateOnly: ds.dateOnly, occurrences: occ, limit })) {
    notes.appendChild(noteBox(note));
  }
  if (notes.children.length === beforeDiagnostics && !inputProblem) {
    const ok = el("article", "note note-clear");
    ok.appendChild(el("h3", null, "No known divergence applies to this rule."));
    ok.appendChild(el("p", null,
      "Nothing this tool knows about affects it: no MUST NOT of §3.3.10 is broken, DTSTART is " +
      "the rule's own first occurrence, and the answer does not change under any reading or " +
      "WKST value this tool checks. That is not a proof of agreement — it is the absence of " +
      "the specific disagreements listed in the findings."));
    notes.appendChild(ok);
  }

  if (occ.length) {
    const h = el("h2", null, `${occ.length} occurrence${occ.length === 1 ? "" : "s"}`);
    if (occ.length < limit) h.appendChild(el("span", "hint", " — the whole recurrence set"));
    result.appendChild(h);
    result.appendChild(occurrenceList(occ, ds.dateOnly, ds.t));
    result.appendChild(monthGrids(occ, ds.t, r.WKST));
  }

  const caveat = el("details", "caveat");
  caveat.appendChild(el("summary", null, "What this tool does not check"));
  const ul = el("ul");
  for (const s of NOT_CHECKED) ul.appendChild(el("li", null, s));
  ul.appendChild(el("li", null,
    "time zones and DST — every date here is floating local time, exactly as typed"));
  ul.appendChild(el("li", null,
    "EXDATE, RDATE and EXRULE, and any other component of the recurrence set besides this one RRULE"));
  ul.appendChild(el("li", null,
    "anything more than about thirty years after DTSTART \u2014 the list stops there even when " +
    "fewer occurrences than you asked for have been found. \u201cExplain one date\u201d is not " +
    "bounded that way and will answer past it."));
  ul.appendChild(el("li", null,
    "divergences that no finding has measured yet. Absence of a note is not agreement."));
  caveat.appendChild(ul);
  result.appendChild(caveat);
}

// --- wiring ---------------------------------------------------------------
let timer = null;
const schedule = () => { clearTimeout(timer); timer = setTimeout(run, 120); };
const autosize = () => {
  const t = $("rrule");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight + 2, 340) + "px";
};
for (const id of ["rrule", "dtstart", "limit", "why"]) $(id).addEventListener("input", schedule);
$("rrule").addEventListener("input", autosize);
$("form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
for (const b of document.querySelectorAll(".ex")) {
  b.addEventListener("click", () => {
    $("rrule").value = b.dataset.r;
    $("dtstart").value = b.dataset.d;
    // An example may carry the question it is an example of; otherwise a
    // question about the previous rule is not about this one.
    $("why").value = b.dataset.w || "";
    lastDerived = null;      // the example owns both boxes now
    run();
    autosize();
  });
}
window.addEventListener("hashchange", () => { readHash(); run(); autosize(); });
readHash();
run();
autosize();
