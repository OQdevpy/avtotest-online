#!/usr/bin/env bash
# Bog'liqliklarni faqat kerak bo'lganda o'rnatadi:  deploy/npm-deps.sh <papka>
#
# package-lock.json o'zgarmagan bo'lsa `npm ci` (serverda 8-10 daqiqa)
# o'tkazib yuboriladi — build bir necha soniyada tugaydi.
set -euo pipefail
cd "$1"
stamp="node_modules/.deploy-lock-hash"
want="$(sha256sum package-lock.json | cut -d' ' -f1)"

if [[ -f "$stamp" && "$(cat "$stamp")" == "$want" ]]; then
  echo "==> $1: bog'liqliklar o'zgarmagan — npm ci kerak emas"
  exit 0
fi
# Belgi hali yo'q, lekin node_modules to'liq va to'g'ri bo'lsa — qayta o'rnatilmaydi
if [[ ! -f "$stamp" && -d node_modules ]] && npm ls --depth=0 >/dev/null 2>&1; then
  echo "$want" > "$stamp"
  echo "==> $1: mavjud node_modules to'g'ri — npm ci kerak emas"
  exit 0
fi
echo "==> $1: npm ci (package-lock.json o'zgargan)"
npm ci --prefer-offline --include=dev --no-audit --no-fund
echo "$want" > "$stamp"
