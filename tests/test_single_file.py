"""web/rrule-debugger.html must be the same tool as web/, and must run from disk.

The multi-file page needs a web server: its modules load with
`<script type="module" src=...>`, and a browser opening index.html from a
file:// URL refuses the cross-file imports. The page then renders its form and
silently produces nothing -- no results and no error, which looks like a working
tool. So the single-file build exists for anyone who downloads the repository,
and it is worth nothing if it drifts from the sources or quietly stops working.

Two checks, and the second is the one that matters:

  * the built file is byte-identical to a fresh build from web/. That is what
    ties it to the rest of the suite -- the JavaScript inside it *is* the
    JavaScript in web/, which test_web_port.py scores against the full corpus.
  * the built file, loaded from a file:// URL, renders the same results as the
    multi-file page served over HTTP. A bundler can produce a file that is in
    sync, self-contained and still broken: the first version of the builder
    emitted app.js before the modules it destructures from, which passes every
    static check and dies in the browser. Only executing it catches that.

Skips, loudly, when no browser is installed -- but fails instead of skipping
under CI, where a check that quietly stops running is indistinguishable from one
that passes.
"""
import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
BUILT = os.path.join(WEB, "rrule-debugger.html")

BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")

# Cases chosen to reach the parts of the page that do real work: a plain
# expansion, a rule carrying a measured divergence note, a date-valued DTSTART,
# and a "why is this date missing" query.
CASES = [
    "rrule=FREQ%3DMONTHLY%3BBYDAY%3D-1FR&dtstart=20260130T090000&limit=12",
    "rrule=FREQ%3DWEEKLY%3BBYDAY%3DMO%2CTU%2CWE%2CTH%2CFR%3BBYSETPOS%3D1&dtstart=20260107T090000&limit=8",
    "rrule=FREQ%3DYEARLY%3BBYWEEKNO%3D53%3BBYDAY%3DMO&dtstart=20261228&limit=6",
    "rrule=FREQ%3DMONTHLY%3BBYMONTHDAY%3D31&dtstart=20260131T193000&limit=8&why=20260228",
]

fails = []


def browser():
    for b in BROWSERS:
        p = shutil.which(b)
        if p:
            return p
    return None


def dump(exe, url):
    out = subprocess.run(
        [exe, "--headless", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=5000",
         "--dump-dom", url],
        capture_output=True, text=True, timeout=120,
    ).stdout
    # Only the computed regions. Everything else legitimately differs: the
    # served page ends in <script src="app.js">, the single file in the whole
    # inlined module graph. Each region runs to the start of the next one, so
    # the match must not be greedy to end of document.
    marks = [(m.start(), m.group(1)) for m in
             re.finditer(r'<(?:div|section) id="(error|why-out|notes|result)"[^>]*>', out)]
    ends = [m.start() for m in re.finditer(r'</body|<script', out)] or [len(out)]
    got = {}
    for i, (pos, sec) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else min(e for e in ends if e > pos)
        body = out[out.index(">", pos) + 1:stop]
        got[sec] = re.sub(r"\s+", " ", body).strip()
    for sec in ("error", "why-out", "notes", "result"):
        got.setdefault(sec, "<MISSING>")
    return got


def main():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_single_file.py"), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("build: " + (r.stdout + r.stderr).strip())
        return  # every later check would be about a stale file

    html = open(BUILT).read()
    for pat, why in ((r'<script[^>]+src=', "an external script"),
                     (r'<link[^>]+stylesheet', "an external stylesheet"),
                     (r'^\s*import\s', "a leftover import statement"),
                     (r'^\s*export\s', "a leftover export statement")):
        if re.search(pat, html, re.M):
            fails.append("built file still references %s -- it is not self-contained" % why)

    exe = browser()
    if exe is None:
        # A skip is fine on a developer machine and not fine on CI: the whole
        # point of this file is the browser check, and a check that silently
        # stops running looks exactly like a check that passes.
        msg = "no browser found (%s); the file:// behaviour was NOT checked" % ", ".join(BROWSERS)
        if os.environ.get("CI"):
            fails.append(msg + " -- install one on the runner or this test is decorative")
        else:
            print("SKIP: " + msg)
        return

    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=WEB, **k))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    tmp = tempfile.mkdtemp()  # a bare copy, to prove it needs nothing beside it
    try:
        local = os.path.join(tmp, "rrule-debugger.html")
        shutil.copy(BUILT, local)
        for case in CASES:
            served = dump(exe, "http://127.0.0.1:%d/#%s" % (port, case))
            disk = dump(exe, "file://%s#%s" % (local, case))
            if disk["result"] in ("", "<MISSING>"):
                fails.append("#%s: the file:// page produced no result at all" % case)
                continue
            for sec in served:
                if served[sec] != disk[sec]:
                    fails.append("#%s: <%s> differs between the served page and the single file"
                                 % (case, sec))
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


main()
if fails:
    for f in fails:
        print("FAIL: %s" % f)
    sys.exit(1)
print("single-file build is in sync, self-contained, and matches the served page")
