#!/usr/bin/env bash
# Builds the static preview site deployed on Vercel: specification, design references and screen captures.
# The panel itself is local-only (127.0.0.1) and is NOT deployed; see OPERATIONS.md.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist && mkdir -p dist/design dist/captures
cp web-preview/index.html dist/index.html
cp design/*.png dist/design/
cp docs/captures/*.png dist/captures/
cp docs/painel-web.html dist/painel-web.html
cp docs/OneMoreShort-Painel-Web.pdf dist/OneMoreShort-Painel-Web.pdf
cp README.md dist/README.md
echo "site built in dist/ ($(ls dist/captures | wc -l) captures, $(ls dist/design | wc -l) references)"
