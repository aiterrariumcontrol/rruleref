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

# The premise above stopped being true on 2026-09-11 without anything saying
# so: the Pages source was changed to main:/ , so this script has since been
# pushing to a branch nobody serves. Finding 068, standing rule 73 -- a premise
# that lives outside the repository needs a check, not a comment. Ask GitHub
# what it actually serves before doing any work.
if command -v gh >/dev/null 2>&1; then
  SRC_BRANCH=$(gh api repos/:owner/:repo/pages --jq .source.branch 2>/dev/null || echo "")
  SRC_PATH=$(gh api repos/:owner/:repo/pages --jq .source.path 2>/dev/null || echo "")
  if [ -n "$SRC_BRANCH" ] && [ "$SRC_BRANCH" != "gh-pages" ]; then
    echo "GitHub Pages serves ${SRC_BRANCH}:${SRC_PATH}, not gh-pages." >&2
    echo "Pushing gh-pages would change nothing a visitor can see." >&2
    echo "The live debugger is published by committing to ${SRC_BRANCH}." >&2
    echo "Re-run with FORCE_GH_PAGES=1 if you want the branch updated anyway." >&2
    [ "${FORCE_GH_PAGES:-0}" = "1" ] || exit 1
  fi
else
  echo "warning: gh is not installed; cannot confirm what Pages serves" >&2
fi

SRC=$(git rev-parse --short HEAD)
MSG=${1:-"publish web/ from $SRC"}
TMP=$(mktemp -d)      # the site contents
WT=$(mktemp -d)       # the gh-pages worktree, kept out of TMP so the copy
                      # below is not asked to copy a directory into itself
trap 'rm -rf "$TMP" "$WT"' EXIT

cp -R web/. "$TMP/"
rm -rf "$TMP/test"          # the conformance adapter is not part of the site
touch "$TMP/.nojekyll"      # serve files literally; nothing here is Jekyll
printf '%s\n' "$SRC" > "$TMP/COMMIT"

rm -rf "$WT"
git worktree add -q --detach "$WT"
cd "$WT"
git checkout -q --orphan gh-pages 2>/dev/null || git checkout -q gh-pages
git rm -rq --cached . 2>/dev/null || true
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$TMP"/. .
git add -A
git commit -q -m "$MSG" || echo "nothing changed"
git push -q origin gh-pages
cd "$ROOT"
git worktree remove --force "$WT"
echo "pushed gh-pages from $SRC"
