#!/usr/bin/env bash
# Build the site and publish .pages-dist/ to the gh-pages branch (no Actions needed).
# Usage: scripts/deploy_gh_pages.sh [remote-url]   (defaults to origin)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/build_site.py --out .pages-dist --base /atlas-of-judgment/ --site https://lauorie.github.io
REMOTE="${1:-$(git remote get-url origin)}"
TMP="$(mktemp -d)"
cp -r .pages-dist/. "$TMP"/
git -C "$TMP" init -q -b gh-pages
git -C "$TMP" add -A
git -C "$TMP" -c user.name="deploy" -c user.email="deploy@localhost" commit -q -m "site build $(date -u +%Y-%m-%dT%H:%MZ)"
git -C "$TMP" push -f "$REMOTE" gh-pages:gh-pages
rm -rf "$TMP"
echo "published gh-pages"
