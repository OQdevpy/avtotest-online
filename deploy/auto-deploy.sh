#!/usr/bin/env bash
# Serverda avtomatik yangilanish: branch'ga yangi commit tushsa, shu skript
# o'zgargan qismlarni qayta yig'adi (backend, admin panel, web saytlar).
#
# Bir marta o'rnatiladi (root crontab, har 5 daqiqada):
#   ( crontab -l 2>/dev/null; echo '*/5 * * * * /root/avtotest/avtotest-online/deploy/auto-deploy.sh >> /var/log/avtotest-deploy.log 2>&1' ) | crontab -
#
# prava777 nusxasi uchun: DEPLOY_BRANCH=prava777 COMPOSE_PROJECT=prava777
# Admin panel boshqa papkadan ochilsa: ADMIN_TARGET=/var/www/<admin papka>
# Qo'lda ishga tushirish ham mumkin; o'zgarish bo'lmasa hech narsa qilmaydi.
set -euo pipefail

# Cron juda qisqa PATH bilan ishga tushiradi (/usr/bin:/bin) — tizimdagi eski
# npm topilib, build yiqiladi. Terminaldagi kabi node topilsin: nvm va
# /usr/local/bin birinchi.
export PATH="/usr/local/bin:/usr/local/sbin:/snap/bin:$PATH"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  set +u
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh" >/dev/null 2>&1 || true
  set -u
fi

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

# Admin panel nginx boshqa papkadan ochilsa (ADMIN_TARGET) — yig'ilgan build
# o'sha yerga ko'chiriladi. Farq bo'lsa har safar tekshiriladi.
sync_admin() {
  local dist="admin/dist"
  [[ -n "${ADMIN_TARGET:-}" && -f "$dist/index.html" ]] || return 0
  [[ "$(realpath -m "$ADMIN_TARGET")" == "$(realpath -m "$dist")" ]] && return 0
  cmp -s "$dist/index.html" "$ADMIN_TARGET/index.html" 2>/dev/null && return 0
  log "admin panel $ADMIN_TARGET ga ko'chirilmoqda"
  mkdir -p "$ADMIN_TARGET"
  cp -r "$dist/." "$ADMIN_TARGET/"
  cp "$dist/index.html" "$ADMIN_TARGET/index.html"
}

if [[ "$DEPLOYED" == "$NEW" ]]; then
  sync_admin
  exit 0
fi

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

node_info() { log "node $(node -v 2>/dev/null || echo yo'q), npm $(npm -v 2>/dev/null || echo yo'q) ($(command -v npm || true))"; }

if changed '^admin/' && [[ -d admin ]]; then
  node_info
  log "admin panel yig'ilmoqda"
  (cd admin && npm ci --prefer-offline --include=dev --no-audit --no-fund && npm run build)
fi
sync_admin

for app in student teacher; do
  if changed "^web/($app/|deploy\.sh)" && [[ -x web/deploy.sh ]]; then
    log "web/$app yig'ilmoqda"
    node_info
    ./web/deploy.sh "$app"
  fi
done

echo "$NEW" > "$STATE"
log "tayyor"
