#!/bin/bash
# deploy.sh — regenerate data.json and push to GitHub Pages
set -e
cd "$(dirname "$0")"

echo "[gamma-deploy] $(date '+%Y-%m-%d %H:%M:%S PT') — generating data.json…"
python3 generate_data.py

echo "[gamma-deploy] committing…"
git add data.json
git diff --cached --quiet && { echo "[gamma-deploy] no changes, skipping push"; exit 0; }

git commit -m "data: auto-update $(date '+%Y-%m-%d %H:%M PT')"
git push origin main
echo "[gamma-deploy] done ✓"
