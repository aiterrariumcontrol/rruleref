// Reference adapter: rrule.js (jkbrzt/rrule). Run from the repository root
// after tools/bootstrap.sh has npm-installed rrule in js/.
//
//   node conformance/adapters/rrulejs_adapter.js
//
// rrule.js works in UTC internally; the corpus is naive local time, so the
// datetimes are fed and read back as UTC and never converted. Doing anything
// else here would be measuring the adapter, not the library.
const path = require('path');
const readline = require('readline');
const { RRule } = require(path.join(__dirname, '..', '..', 'js', 'node_modules', 'rrule'));

const pad = (n, w) => String(n).padStart(w, '0');
const fmt = d => pad(d.getUTCFullYear(), 4) + pad(d.getUTCMonth() + 1, 2) + pad(d.getUTCDate(), 2)
  + 'T' + pad(d.getUTCHours(), 2) + pad(d.getUTCMinutes(), 2) + pad(d.getUTCSeconds(), 2);
const parse = s => new Date(Date.UTC(
  +s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8),
  +s.slice(9, 11), +s.slice(11, 13), +s.slice(13, 15)));

readline.createInterface({ input: process.stdin, terminal: false }).on('line', line => {
  line = line.trim();
  if (!line) return;
  const c = JSON.parse(line);
  let out;
  try {
    const rule = RRule.fromString('DTSTART:' + c.dtstart + 'Z\nRRULE:' + c.rrule);
    const occ = [];
    rule.all((d, i) => { occ.push(fmt(d)); return occ.length < c.limit; });
    out = { id: c.id, occurrences: c.limit === 0 ? [] : occ.slice(0, c.limit) };
  } catch (e) {
    out = { id: c.id, error: String(e && e.message || e) };
  }
  process.stdout.write(JSON.stringify(out) + '\n');
});
