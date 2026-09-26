#!/usr/bin/env python3
"""Finding 102's stored ledger still matches the producer that writes it.

Finding 109, rule 115. A repro script whose stdout is baselined in
tools/repro-drift.json is guarded in exactly one place: its stdout. The data
file it writes under `--write` is a separate artifact and nothing compared it
to anything. Those two drifted apart for four wakes -- findings 104 and 105
added themselves to 102's NAMED registry, the drift baseline was refreshed to
`RESIDUAL: 0`, and `findings/data/102-icaljs-residual-ledger.json` was left
saying `residual_n: 3` with the three ids 104 and 105 had just claimed. A reader
who took the artifact rather than rerunning the script got a figure that was
wrong by the whole of the last change to it.

The producer now has a `--check` mode that recomputes the ledger and diffs it
against the stored file. This test runs it. A failure here means somebody
changed 102's inputs -- most likely by adding a finding to NAMED -- and did not
rerun `--write`.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run([sys.executable, "findings/repro/102-residual-ledger.py",
                    "--check"], cwd=ROOT, capture_output=True, text=True)
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL findings/data/102-icaljs-residual-ledger.json is stale; "
          "rerun findings/repro/102-residual-ledger.py --write")
    sys.exit(1)
print("ok  102's stored ledger matches its producer")
