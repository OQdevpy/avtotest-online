#!/usr/bin/env bash
# Web saytlarni yig'ib, nginx papkalariga joylaydi (serverda ishlatiladi).
#
#   ./web/deploy.sh            — ikkalasi: web. va teacher.avtotest-tayyorlov.uz
#   ./web/deploy.sh student    — faqat o'quvchi sayti
#   ./web/deploy.sh teacher    — faqat o'qituvchi sayti
#
# Birinchi marta nginx va HTTPS sozlamasi kerak — qarang: web/README.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -eq 0 ]]; then APPS=(student teacher); else APPS=("$@"); fi

for app in "${APPS[@]}"; do
  case "$app" in
    student|teacher) ;;
    *) echo "Noma'lum ilova: $app (student yoki teacher)" >&2; exit 1 ;;
  esac
  target="/var/www/avtotest-web-$app"
  echo "==> $app: yig'ilmoqda"
  cd "$ROOT/$app"
  npm ci --no-audit --no-fund
  npm run build

  echo "==> $app: $target ga joylanmoqda"
  mkdir -p "$target"
  # Avval yangi fayllar, keyin eskilari o'chiriladi — sayt bir lahza ham bo'sh qolmaydi
  cp -r dist/. "$target/"
  find "$target/assets" -type f ! -newer dist/index.html -delete 2>/dev/null || true
  cp dist/index.html "$target/index.html"
done

echo "Tayyor. Brauzerda sahifani yangilang (Ctrl+F5)."
