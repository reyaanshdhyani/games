#!/bin/bash
# Double-click this file to publish new/updated games to the live site.
# It rebuilds the menu, commits everything, and pushes to GitHub.
# GitHub Pages then redeploys automatically (~1 minute).

cd "$(dirname "$0")" || exit 1

echo "🎮 Publishing the arcade..."

# Rebuild the menu locally so it looks right even before the Action runs.
if command -v python3 >/dev/null 2>&1; then
  python3 build_index.py
fi

git add -A

if git diff --cached --quiet; then
  echo "Nothing new to publish — everything is already up to date."
else
  git commit -m "Update games ($(date '+%Y-%m-%d %H:%M'))"
  if git push; then
    echo "✅ Pushed! Your site will update in about a minute."
  else
    echo "❌ Push failed. Make sure the repo is connected (see README) and you're signed in to GitHub."
  fi
fi

echo
read -n 1 -s -r -p "Done. Press any key to close."
echo
