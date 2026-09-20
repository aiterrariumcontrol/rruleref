// Reproduce finding 070 with no corpus and no harness: two defects in ical.js
// 2.2.1, each demonstrated by a rule you can read.
//
//   node findings/repro/070-icaljs-contracting-negatives.js
//
// The hang cases are NOT run here -- they exhaust the Node heap and abort the
// process, which is the point. Each is printed with the one-line command that
// reproduces it on its own, so this script stays runnable end to end.
const path = require('path');
const ICAL = require(path.join(__dirname, '..', '..', 'js', 'node_modules', 'ical.js')).default;

const take = (rrule, dtstart, n) => {
  const it = ICAL.Recur.fromString(rrule).iterator(ICAL.Time.fromDateTimeString(dtstart));
  const o = []; let t;
  while (o.length < n && (t = it.next())) o.push(t.toString().slice(0, 16));
  return o;
};

let bad = 0;
const check = (label, rrule, dtstart, n, want) => {
  const got = take(rrule, dtstart, n).join(' ');
  const ok = got === want;
  if (!ok) bad++;
  console.log((ok ? 'ok   ' : 'FAIL ') + label);
  console.log('       ' + rrule + '  DTSTART:' + dtstart);
  console.log('       got  ' + got);
  if (!ok) console.log('       want ' + want);
};

console.log('ical.js ' + require(path.join(__dirname, '..', '..', 'js', 'node_modules', 'ical.js', 'package.json')).version + '\n');

console.log('--- A. a negative value in a BY part that CONTRACTS never matches ---\n');
// BYMONTHDAY expands under MONTHLY, so -1 is resolved against a known month.
check('MONTHLY: the control, and it is right',
  'FREQ=MONTHLY;BYMONTHDAY=-1', '2024-03-31T09:00:00', 3,
  '2024-03-31T09:00 2024-04-30T09:00 2024-05-31T09:00');
// Under DAILY it contracts, and the check compares -1 against a day 1..31.
// A positive value in the same list terminates the search, so this one answers
// -- with every last-of-month occurrence silently missing.
check('DAILY: -1 is dropped, 15 survives',
  'FREQ=DAILY;BYMONTHDAY=-1,15', '2024-03-31T09:00:00', 4,
  '2024-03-31T09:00 2024-04-30T09:00 2024-05-15T09:00 2024-06-15T09:00');

console.log('\n    With no positive value to end the search, the iterator never');
console.log('    returns. It does not hang politely: it allocates until the Node');
console.log('    heap is gone and the process aborts. Reproduce one at a time:\n');
for (const r of ['FREQ=DAILY;BYMONTHDAY=-1',
                 'FREQ=HOURLY;BYMONTHDAY=-1',
                 'FREQ=MINUTELY;BYMONTHDAY=-1',
                 'FREQ=DAILY;BYDAY=-1MO']) {
  console.log("      node --max-old-space-size=256 -e 'const I=require(\"ical.js\").default;" +
              "I.Recur.fromString(\"" + r + "\")" +
              ".iterator(I.Time.fromDateTimeString(\"2024-03-31T09:00:00\")).next()'");
}
console.log('\n    (FREQ=WEEKLY with BYMONTHDAY, and BYYEARDAY outside YEARLY, are');
console.log('     refused at parse time by RFC 5545 rules, so they never reach this.)');

console.log('\n--- B. BYHOUR/BYMINUTE/BYSECOND are iterated in rule order ---\n');
check('sorted list: right',
  'FREQ=DAILY;BYHOUR=8,9', '2026-03-02T09:00:00', 5,
  '2026-03-02T09:00 2026-03-03T08:00 2026-03-03T09:00 2026-03-04T08:00 2026-03-04T09:00');
check('same rule, listed 9,8: the set comes back out of order',
  'FREQ=DAILY;BYHOUR=9,8', '2026-03-02T09:00:00', 5,
  '2026-03-02T09:00 2026-03-03T08:00 2026-03-03T09:00 2026-03-04T08:00 2026-03-04T09:00');
check('BYMONTH, by contrast, IS sorted',
  'FREQ=YEARLY;BYMONTH=5,3', '2026-03-02T09:00:00', 4,
  '2026-03-02T09:00 2026-05-02T09:00 2027-03-02T09:00 2027-05-02T09:00');

console.log('\n' + bad + ' of 5 checks reproduce a defect.');
process.exit(0);
