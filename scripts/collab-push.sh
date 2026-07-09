#!/bin/bash
# collab-push.sh — One-command push for collaborators
#
# Usage:
#   ./scripts/collab-push.sh "my commit message"
#
# Does: stage → commit → rebase-pull → push to origin main
# No prompts once credentials are cached.

set -e
cd "$(dirname "$0")/.."

MSG="${1:-collab update $(date +%H:%M:%S)}"

NAME=$(git config user.name)
EMAIL=$(git config user.email)

echo "Pushing as: $NAME <$EMAIL>"
echo "Message:    $MSG"
echo ""

git status --short
git add -A

if git diff --cached --quiet; then
  echo "→ No changes to commit. Pulling latest..."
  git pull --rebase --autostash
  exit 0
fi

git commit -m "$MSG

Co-Authored-By: $NAME <$EMAIL>"

git pull --rebase --autostash
git push origin main

echo ""
echo "✓ Pushed to https://github.com/elham715/ICT_Fest_Hackathon_Preliminary"
