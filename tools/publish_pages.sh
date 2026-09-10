#!/bin/sh
# Sync web/ onto the gh-pages branch, whose root is what GitHub Pages serves.
#
# Why a branch and not .github/workflows/pages.yml: the Actions deploy path is
# the tidier one, but pushing a workflow file needs a token with `workflow`
# scope, which this agent's token does not have. Pages' "deploy from a branch"
# source needs no workflow, no extra scope, and serves the branch root -- so
# web/ is copied there rather than published in place. The cost is that this
# script has to be run after any change under web/; tools/run_tests.py is what
# says whether that change is safe to publish.
#
# Usage: tools/publish_pages.sh [commit message]
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

if [ -n "$(git status --porcelain)" ]; then
  echo "working tree is dirty; commit or stash first" >&2
  exit 1
fi

SRC=$(git rev-parse --short HEAD)
MSG=${1:-"publish web/ from $SRC"}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cp -R web/. "$TMP/"
rm -rf "$TMP/test"          # the conformance adapter is not part of the site
touch "$TMP/.nojekyll"      # serve files literally; nothing here is Jekyll
printf '%s\n' "$SRC" > "$TMP/COMMIT"

git worktree add -q --detach "$TMP/.wt"
cd "$TMP/.wt"
git checkout -q --orphan gh-pages 2>/dev/null || git checkout -q gh-pages
git rm -rq --cached . 2>/dev/null || true
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$TMP"/. .
rm -rf ./.wt
git add -A
git commit -q -m "$MSG" || echo "nothing changed"
git push -q origin gh-pages
cd "$ROOT"
git worktree remove --force "$TMP/.wt"
echo "pushed gh-pages from $SRC"
