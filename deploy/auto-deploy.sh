#!/usr/bin/env bash
# Serverda avtomatik yangilanish: branch'ga yangi commit tushsa, shu skript
# o'zgargan qismlarni qayta yig'adi (backend, admin panel, web saytlar).
#
# Bir marta o'rnatiladi (root crontab, har 5 daqiqada):
#   ( crontab -l 2>/dev/null; echo '*/5 * * * * /root/avtotest/avtotest-online/deploy/auto-deploy.sh >> /var/log/avtotest-deploy.log 2>&1' ) | crontab -
#
# prava777 nusxasi uchun: DEPLOY_BRANCH=prava777 COMPOSE_PROJECT=prava777
# Qo'lda ishga tushirish ham mumkin; o'zgarish bo'lmasa hech narsa qilmaydi.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BRANCH="${DEPLOY_BRANCH:-master}"
COMPOSE=(docker compose)
[[ -n "${COMPOSE_PROJECT:-}" ]] && COMPOSE+=(-p "$COMPOSE_PROJECT")

# Bir vaqtda ikki nusxa ishlamasin (oldingi build hali tugamagan bo'lsa)
exec 9>"/tmp/auto-deploy-$(basename "$ROOT")-$BRANCH.lock"
flock -n 9 || exit 0

log() { echo "$(date '+%F %T') [$BRANCH] $*"; }

# Oxirgi muvaffaqiyatli o'rnatilgan commit .git ichida saqlanadi — kimdir
# qo'lda `git pull` qilsa ham o'rnatish o'tkazib yuborilmaydi.
STATE="$(git rev-parse --git-dir)/auto-deploy-$BRANCH"
DEPLOYED="$(cat "$STATE" 2>/dev/null || true)"

git fetch -q origin "$BRANCH"
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse FETCH_HEAD)" ]]; then
  if ! git merge --ff-only -q FETCH_HEAD; then
    log "XATO: serverdagi nusxada qo'lda o'zgarish bor (git status). Yangilanmadi."
    exit 1
  fi
fi
NEW="$(git rev-parse HEAD)"
[[ "$DEPLOYED" == "$NEW" ]] && exit 0

if [[ -n "$DEPLOYED" ]] && git cat-file -e "$DEPLOYED^{commit}" 2>/dev/null; then
  log "yangilanish: ${DEPLOYED:0:7} -> ${NEW:0:7}"
  CHANGED="$(git diff --name-only "$DEPLOYED" "$NEW")"
else
  # Birinchi ishga tushish — hammasi o'rnatiladi
  log "birinchi o'rnatish: ${NEW:0:7} (hammasi)"
  CHANGED=$'backend/\nadmin/\nweb/student/\nweb/teacher/'
fi
changed() { grep -qE "$1" <<<"$CHANGED"; }

if changed '^(backend/|docker-compose)'; then
  log "backend qayta yig'ilmoqda"
  "${COMPOSE[@]}" up -d --build
  # Migratsiya va gunicorn ko'tarilishini kutamiz (API kirishsiz 401 qaytaradi)
  port="$(grep -E '^API_PORT=' .env 2>/dev/null | cut -d= -f2 || true)"
  for _ in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port:-8010}/api/v1/content/version/" || true)"
    [[ "$code" == "401" || "$code" == "200" ]] && break
    sleep 3
  done
  log "backend javobi: ${code:-none}"
  if [[ "${code:-}" != "401" && "${code:-}" != "200" ]]; then
    "${COMPOSE[@]}" logs --tail 40 backend
    log "XATO: backend javob bermadi — keyingi safar qayta uriniladi"
    exit 1
  fi
fi

if changed '^admin/' && [[ -d admin ]]; then
  log "admin panel yig'ilmoqda"
  (cd admin && npm ci --no-audit --no-fund && npm run build)
fi

for app in student teacher; do
  if changed "^web/($app/|deploy\.sh)" && [[ -x web/deploy.sh ]]; then
    log "web/$app yig'ilmoqda"
    ./web/deploy.sh "$app"
  fi
done

echo "$NEW" > "$STATE"
log "tayyor"
