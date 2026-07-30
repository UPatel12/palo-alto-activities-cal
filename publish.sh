#!/usr/bin/env bash
# Publish the app to GitHub Pages.
#
# Builds gh-pages with git plumbing rather than checking the branch out, so
# your working tree and current branch are never touched.
#
#   ./publish.sh
set -euo pipefail

cd "$(dirname "$0")"

PY=${PY:-.venv/bin/python}
[ -x "$PY" ] || PY=python3

echo "Building standalone page..."
"$PY" generate_app.py --standalone --out output/index.html

BLOB=$(git hash-object -w output/index.html)
NOJEKYLL=$(printf '' | git hash-object -w --stdin)
TREE=$(printf '100644 blob %s\tindex.html\n100644 blob %s\t.nojekyll\n' \
       "$BLOB" "$NOJEKYLL" | git mktree)
COMMIT=$(git commit-tree "$TREE" -m "Update app — $(date +%Y-%m-%d)")

git branch -f gh-pages "$COMMIT"
git push --force --quiet origin gh-pages

echo "Pushed. Live in ~1 min at:"
echo "  https://upatel12.github.io/palo-alto-activities-cal/"
