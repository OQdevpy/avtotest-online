#!/usr/bin/env bash
# Butun loyihani bitta buyruq bilan lokal ishga tushirish.
#
#   ./dev.sh        — backend (docker: db + redis + backend + nginx) va
#                     uchala frontni (vite dev) ko'taradi
#   ./dev.sh stop   — docker konteynerlarni to'xtatadi
#
# Manzillar:
#   backend / nginx  http://localhost:9005   (Swagger: /api/docs/)
#   frontend         http://localhost:5173   (o'quvchi sayti)
#   admin            http://localhost:5174
#   teacher          http://localhost:5175   (Avto Teacher)
#
# Ctrl+C — frontlarni to'xtatadi; docker fonda qoladi (`./dev.sh stop`).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "stop" ]]; then
  docker compose down
  exit 0
fi

# --- 1. Muhit fayllari ---------------------------------------------------------
[[ -f .env ]] || { cp .env.example .env; echo ".env yaratildi — DB_PASSWORD ni to'ldiring."; exit 1; }
[[ -f backend/.env ]] || { cp backend/.env.example backend/.env; echo "backend/.env yaratildi — SECRET_KEY va boshqalarni to'ldiring."; exit 1; }
grep -qE '^DB_PASSWORD=.+' .env || { echo ".env da DB_PASSWORD bo'sh."; exit 1; }

# --- 2. Backend (docker) -------------------------------------------------------
docker info >/dev/null 2>&1 || { echo "Docker ishlamayapti — Docker Desktop'ni oching."; exit 1; }
docker compose up -d --build || {
  echo "Build o'xshamadi (tarmoq?) — mavjud image'lar bilan ko'tarilmoqda."
  docker compose up -d
}

WEB_PORT="$(grep -E '^WEB_PORT=' .env | cut -d= -f2)"
BACKEND="http://127.0.0.1:${WEB_PORT:-9005}"
echo "Backend kutilmoqda: $BACKEND ..."
for _ in $(seq 1 60); do
  curl -s -o /dev/null "$BACKEND/api/schema/" && break
  sleep 2
done

# --- 3. Frontlar (vite dev) ----------------------------------------------------
for d in frontend admin teacher; do
  [[ -d "$d/node_modules" ]] || (cd "$d" && npm install)
done

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

run() {  # run <nom> <papka> <port>
  # API_URL to'liq bo'lishi shart (client.js `new URL` qiladi); so'rov vite proxy orqali ketadi
  (cd "$2" && DEV_BACKEND_URL="$BACKEND" VITE_API_URL="http://localhost:$3/api/v1" VITE_MEDIA_BASE_URL= \
     npx vite --port "$3" --strictPort 2>&1 | sed -u "s/^/[$1] /") &
  pids+=($!)
}
run frontend frontend 5173
run teacher  teacher  5175
# admin o'z .env'idagi VITE_API_URL (bo'sh → proxy) dan foydalanadi
(cd admin && DEV_BACKEND_URL="$BACKEND" npx vite --port 5174 --strictPort 2>&1 | sed -u "s/^/[admin] /") &
pids+=($!)

wait
