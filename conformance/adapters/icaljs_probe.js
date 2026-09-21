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

const CASE_TIMEOUT_MS = Number(process.env.RRULE_CASE_TIMEOUT_MS) || 2000;
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
    let caseStart = 0;

    const start = () => {
      const c = spawn(process.execPath, ['--max-old-space-size=' + WORKER_HEAP_MB, __filename, '--worker'],
        { stdio: ['pipe', 'pipe', 'ignore'] });
      child = c;
      c.on('error', () => {});
      // A worker that dies mid-case is NOT the deadline. It is the library
      // exhausting a 256 MB heap, which is a fact about ical.js and not about
      // this machine's clock. Report it separately so the error column can be
      // split into a deadline-dependent and a deadline-independent part
      // (rule 80). `c.intentional` marks the kills WE issue, and is per-child
      // on purpose: `exit` is asynchronous, so a flag shared across restarts is
      // cleared by the next start() before the old child's exit is delivered.
      c.on('exit', (code, signal) => {
        if (c.intentional || timer === null) return;
        clearTimeout(timer); timer = null;
        const t = Date.now() - caseStart;
        const id = JSON.parse(cases[i]).id;
        process.stdout.write(JSON.stringify({ id,
          error: 'worker aborted after ' + t + 'ms: ' + (signal ? 'signal ' + signal : 'exit ' + code) }) + '\n');
        i++;
        restart();
        step();
      });
      rl = readline.createInterface({ input: c.stdout, terminal: false });
      rl.on('line', line => {
        clearTimeout(timer); timer = null;
        process.stderr.write('ELAPSED ' + JSON.parse(cases[i]).id + ' ' + (Date.now() - caseStart) + '\n');
        process.stdout.write(line + '\n');
        i++; step();
      });
    };

    const stop = () => { if (child) { child.intentional = true; child.kill('SIGKILL'); } };

    const restart = () => { if (rl) rl.close(); stop(); start(); };

    const step = () => {
      if (i >= cases.length) { stop(); return; }
      const line = cases[i];
      caseStart = Date.now();
      timer = setTimeout(() => {
        timer = null;
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
