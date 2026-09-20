// Reference adapter: ical.js (kewisch/ical.js), the Thunderbird calendaring
// library. Run from the repository root after tools/bootstrap.sh has
// npm-installed ical.js in js/.
//
//   node conformance/adapters/icaljs_adapter.js
//
// Unlike the rrule.js adapter this one needs no timezone trick: an ICAL.Time
// built from a bare date-time string carries the `floating` zone, which is
// exactly what the corpus is. Datetimes go in and come back out naive.
//
// WHY THIS ADAPTER IS TWO PROCESSES
//
// ical.js can enter an unbounded search inside a single iterator.next() call --
// see finding 070. It does not hang politely: it allocates until the Node heap
// is exhausted and the process aborts, which would take the whole corpus run
// down with it. So the work runs in a `--worker` child with a small heap and a
// per-case deadline, and the supervisor restarts the child and reports
// `error: timeout` for the case that killed it.
//
// The timeout is the adapter's, not the library's. It is reported as an error
// exactly as a parse refusal would be, and it asserts only that no answer
// arrived within the deadline -- not that no answer exists. Every other case in
// this corpus answers in well under a millisecond, so the deadline is three
// orders of magnitude of headroom and is not measuring machine load.
const path = require('path');
const readline = require('readline');

const CASE_TIMEOUT_MS = 2000;
const WORKER_HEAP_MB = 256;

function runWorker() {
  const ICAL = require(path.join(__dirname, '..', '..', 'js', 'node_modules', 'ical.js')).default;

  const pad = (n, w) => String(n).padStart(w, '0');
  const fmt = t => pad(t.year, 4) + pad(t.month, 2) + pad(t.day, 2)
    + 'T' + pad(t.hour, 2) + pad(t.minute, 2) + pad(t.second, 2);
  // "20260302T090000" -> the ISO form ICAL.Time.fromDateTimeString wants.
  const iso = s => s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8)
    + 'T' + s.slice(9, 11) + ':' + s.slice(11, 13) + ':' + s.slice(13, 15);

  readline.createInterface({ input: process.stdin, terminal: false }).on('line', line => {
    line = line.trim();
    if (!line) return;
    const c = JSON.parse(line);
    let out;
    try {
      const dtstart = ICAL.Time.fromDateTimeString(iso(c.dtstart));
      const it = ICAL.Recur.fromString(c.rrule).iterator(dtstart);
      // Nothing here checks that the occurrences ascend. An earlier draft did,
      // and it turned a plain wrong answer (ical.js emits BYHOUR in rule order,
      // not clock order) into an `error`, which is a different claim about an
      // implementation. The per-case deadline in the supervisor is the only
      // guard this adapter needs; everything else the library says is passed
      // through for the scorer to judge.
      const occ = [];
      while (occ.length < c.limit) {
        const t = it.next();
        if (!t) break;
        occ.push(fmt(t));
      }
      out = { id: c.id, occurrences: occ };
    } catch (e) {
      out = { id: c.id, error: String((e && e.message) || e) };
    }
    process.stdout.write(JSON.stringify(out) + '\n');
  });
}

function runSupervisor() {
  const { spawn } = require('child_process');
  const cases = [];
  readline.createInterface({ input: process.stdin, terminal: false })
    .on('line', l => { if (l.trim()) cases.push(l.trim()); })
    .on('close', () => drive(cases));

  function drive(cases) {
    let i = 0;
    let child = null;
    let timer = null;
    let rl = null;

    const start = () => {
      child = spawn(process.execPath, ['--max-old-space-size=' + WORKER_HEAP_MB, __filename, '--worker'],
        { stdio: ['pipe', 'pipe', 'ignore'] });
      // A worker that dies mid-case leaves `next()` unanswered; the deadline
      // below is what reports it, so nothing is needed here.
      child.on('error', () => {});
      rl = readline.createInterface({ input: child.stdout, terminal: false });
      rl.on('line', line => { clearTimeout(timer); process.stdout.write(line + '\n'); i++; step(); });
    };

    const restart = () => {
      if (rl) rl.close();
      if (child) child.kill('SIGKILL');
      start();
    };

    const step = () => {
      if (i >= cases.length) { if (child) child.kill('SIGKILL'); return; }
      const line = cases[i];
      timer = setTimeout(() => {
        const id = JSON.parse(line).id;
        process.stdout.write(JSON.stringify({ id, error: 'timeout: no answer in ' + CASE_TIMEOUT_MS + 'ms' }) + '\n');
        i++;
        restart();
        step();
      }, CASE_TIMEOUT_MS);
      child.stdin.write(line + '\n');
    };

    start();
    step();
  }
}

if (process.argv.includes('--worker')) runWorker(); else runSupervisor();
