#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/validate_site.py
if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Commit the reviewed source state before publishing.\n' >&2
  exit 1
fi
git push origin main
pages_commit=$(git subtree split --prefix public main)
git push origin "$pages_commit:refs/heads/gh-pages"
printf 'Published static branch. Check the GitHub Pages build before reporting success.\n'
