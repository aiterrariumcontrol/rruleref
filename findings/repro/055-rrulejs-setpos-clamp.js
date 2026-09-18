// Finding 055. rrule.js clamps an out-of-range NEGATIVE BYSETPOS to the first
// element of the set instead of selecting nothing. Positive out-of-range is
// handled correctly. Run from the repository root:
//   node findings/repro/055-rrulejs-setpos-clamp.js
const path = require('path');
const { rrulestr } = require(path.join(__dirname, '..', '..', 'js', 'node_modules', 'rrule'));
const pad = (n, w) => String(n).padStart(w, '0');
const fmt = d => pad(d.getUTCFullYear(), 4) + pad(d.getUTCMonth() + 1, 2) + pad(d.getUTCDate(), 2)
  + 'T' + pad(d.getUTCHours(), 2) + pad(d.getUTCMinutes(), 2) + pad(d.getUTCSeconds(), 2);
for (const pos of [-1, -2, -3, -5, 1, 2, 3, 5]) {
  const s = `DTSTART:20260601T090000Z\nRRULE:FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=${pos}`;
  const got = rrulestr(s).all((d, i) => i < 6).map(fmt);
  console.log(String(pos).padStart(3), got.join(' ') || '(empty)');
}
// Each week of June 2026 holds two occurrences {MO, WE}. The week of 2026-06-29
// holds only one inside June -- Mon the 29th, because that Wednesday is 1 July.
// BYSETPOS=-2 and -3 have no answer for that week. rrule.js answers 20260629.
