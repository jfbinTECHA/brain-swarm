#!/usr/bin/env bash
set -euo pipefail

# Publishes a Helm chart repo to GitHub Pages (gh-pages branch)
# Assumes: you have chart sources under ./charts or ./brain-swarm and want to host at:
#   https://jfbinTECHA.github.io/kilo-charts
#
# Steps:
#  1) Package charts into ./.helm-repo
#  2) Generate index.yaml with --url pointing to your GH Pages URL
#  3) Commit & push to gh-pages

REPO_URL="https://jfbinTECHA.github.io/kilo-charts"
OUT_DIR=".helm-repo"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

if [ -d charts ]; then
  helm package charts/* -d "$OUT_DIR"
elif [ -d brain-swarm ]; then
  helm package brain-swarm -d "$OUT_DIR"
else
  echo "No charts/ or brain-swarm/ chart directory found under helm/"
  exit 1
fi

helm repo index "$OUT_DIR" --url "$REPO_URL"

git fetch origin gh-pages || true
git switch -c gh-pages origin/gh-pages 2>/dev/null || git checkout -b gh-pages
mkdir -p kilo-charts
cp -r "$OUT_DIR"/* kilo-charts/
git add kilo-charts
git commit -m "Publish Helm charts"
git push -u origin gh-pages

echo "Done. Ensure GitHub Pages is enabled for the repository and points to the gh-pages branch."