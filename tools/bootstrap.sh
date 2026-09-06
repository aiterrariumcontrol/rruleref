#!/bin/sh
# Provision everything rruleref's suite needs, into vendor/ and js/.
#
# Nothing here is required to *read* the corpus -- it is plain JSON. This is
# for re-running the checks, which is the only way to verify that the corpus
# says what it claims.
#
# Idempotent. Safe to re-run. Needs: python3, pip, curl; node/npm optional.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENDOR="$ROOT/vendor"
mkdir -p "$VENDOR"

# --- 1. The specification text, pinned by content, not by filename -----------
# Every expected value in the corpus traces back to these bytes. src/env.py
# re-checks the digest on each use; this only fetches them.
fetch_rfc() {
    num=$1
    want=$2
    out="$VENDOR/rfc$num.txt"
    if [ -f "$out" ]; then
        got=$(python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$out")
        if [ "$got" = "$want" ]; then
            echo "rfc$num.txt: present, sha256 ok"
            return 0
        fi
        echo "rfc$num.txt: present but sha256 $got != $want; refetching" >&2
    fi
    echo "rfc$num.txt: fetching https://www.rfc-editor.org/rfc/rfc$num.txt"
    curl -fsSL "https://www.rfc-editor.org/rfc/rfc$num.txt" -o "$out.tmp"
    got=$(python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$out.tmp")
    if [ "$got" != "$want" ]; then
        rm -f "$out.tmp"
        echo "rfc$num.txt: sha256 $got != pinned $want -- refusing" >&2
        exit 1
    fi
    mv "$out.tmp" "$out"
    echo "rfc$num.txt: fetched, sha256 ok"
}

fetch_rfc 5545 c256f809479d98aa23d71bbd1658b3800ea9f13f41ca56e59c8d2de1b31cbfcb
fetch_rfc 2445 21bfccbb1f8d658d355b8e530feb2bf15d74e0bd3d988f1733569bce9eeaa828

# --- 2. python-dateutil, pinned ---------------------------------------------
# Pinned because part of the suite records dateutil's *current* behaviour on
# purpose (tests/test_date_value_type.py), so the version is part of the claim.
if [ -d "$VENDOR/pylibs/dateutil" ]; then
    echo "pylibs: present"
else
    echo "pylibs: installing python-dateutil==2.9.0.post0 into vendor/pylibs"
    # pip is not always present even where python3 is (it was not on the
    # machine this repo was developed on); ensurepip is part of the stdlib.
    if ! python3 -m pip --version >/dev/null 2>&1; then
        python3 -m ensurepip --default-pip >/dev/null 2>&1 || true
    fi
    if python3 -m pip --version >/dev/null 2>&1; then
        python3 -m pip install --quiet --target "$VENDOR/pylibs" "python-dateutil==2.9.0.post0"
    else
        echo "pylibs: no pip available." >&2
        echo "  Install python-dateutil 2.9.0.post0 by any means and either make" >&2
        echo "  it importable, or point RRULEREF_PYLIBS at the directory holding it." >&2
        exit 1
    fi
fi

# --- 3. rrule.js, optional third witness ------------------------------------
# Its absence degrades rather than breaks: only the cross-check needs it.
if [ -d "$ROOT/js/node_modules/rrule" ]; then
    echo "rrule.js: present"
elif command -v npm >/dev/null 2>&1; then
    echo "rrule.js: npm install in js/"
    (cd "$ROOT/js" && npm install --silent --no-audit --no-fund)
else
    echo "rrule.js: npm not found -- skipping. The cross-check against the" >&2
    echo "  third implementation will be unavailable; everything else runs." >&2
fi

echo
echo "Bootstrap complete. Run the suite with: python3 tools/run_tests.py"
