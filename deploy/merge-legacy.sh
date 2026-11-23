#!/usr/bin/env bash
# Eski avtotest bazasini prava777 bazasiga qo'shib birlashtiradi (serverda, root).
#
#   ./deploy/merge-legacy.sh
#
# 1. Ikkala bazaning zaxira nusxasi: ~/backups/
# 2. Eski baza prava777 Postgres'iga "avtotest_legacy" nomi bilan tiklanadi
# 3. Eski rasmlar prava777 media papkasiga (mavjudlari ustiga yozilmaydi)
# 4. prava777 backend yangi kod bilan qayta yig'iladi
# 5. Sinov (--dry-run) natijasi ko'rsatiladi va "ha" deb tasdiqlansa — birlashtiriladi
#
# prava777 bazasidagi hech narsa o'chirilmaydi. Qayta ishga tushirish xavfsiz:
# eski bazada keyin paydo bo'lganlar qo'shiladi, borlari takrorlanmaydi.
set -euo pipefail

OLD_DIR="${OLD_DIR:-$HOME/avtotest/avtotest-online}"
NEW_DIR="${NEW_DIR:-$HOME/prava777/avtotest-online}"
NEW_PROJECT="${NEW_PROJECT:-prava777}"
LEGACY_DB="avtotest_legacy"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUPS="$HOME/backups"

old() { (cd "$OLD_DIR" && docker compose "$@"); }
new() { (cd "$NEW_DIR" && docker compose -p "$NEW_PROJECT" "$@"); }
say() { echo; echo "==> $*"; }

[[ -d "$OLD_DIR" && -d "$NEW_DIR" ]] || { echo "Papka topilmadi: $OLD_DIR yoki $NEW_DIR"; exit 1; }
mkdir -p "$BACKUPS"

say "1/5 Zaxira nusxalar ($BACKUPS)"
old exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$BACKUPS/avtotest-$STAMP.dump"
new exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$BACKUPS/prava777-$STAMP.dump"
ls -lh "$BACKUPS/avtotest-$STAMP.dump" "$BACKUPS/prava777-$STAMP.dump"
[[ -s "$BACKUPS/avtotest-$STAMP.dump" && -s "$BACKUPS/prava777-$STAMP.dump" ]] || { echo "Zaxira bo'sh — to'xtatildi"; exit 1; }

say "2/5 Eski baza prava777 Postgres'iga ($LEGACY_DB)"
new exec -T db sh -c "dropdb -U \"\$POSTGRES_USER\" --if-exists $LEGACY_DB && createdb -U \"\$POSTGRES_USER\" $LEGACY_DB"
new exec -T db sh -c "pg_restore -U \"\$POSTGRES_USER\" -d $LEGACY_DB --no-owner --no-privileges" \
  < "$BACKUPS/avtotest-$STAMP.dump" || echo "(pg_restore ogohlantirish berdi — quyida tekshiriladi)"
count_old="$(old exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from accounts_user"')"
count_copy="$(new exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d $LEGACY_DB -Atc 'select count(*) from accounts_user'")"
echo "Eski bazada foydalanuvchi: $count_old, nusxada: $count_copy"
[[ -n "$count_old" && "$count_old" == "$count_copy" ]] || { echo "Nusxa to'liq emas — to'xtatildi"; exit 1; }

say "3/5 Rasmlar (eski media -> prava777 media, borlari ustiga yozilmaydi)"
mkdir -p "$NEW_DIR/backend/media"
cp -rn "$OLD_DIR/backend/media/." "$NEW_DIR/backend/media/" 2>/dev/null || true

say "4/5 prava777 kodini yangilash va backendni qayta yig'ish"
(cd "$NEW_DIR" && git pull --ff-only)
new up -d --build backend
for _ in $(seq 1 40); do
  new exec -T backend python manage.py help merge_legacy_db >/dev/null 2>&1 && break
  sleep 3
done

say "5/5 Sinov — nima qo'shilishi (hali hech narsa yozilmaydi)"
new exec -T backend python manage.py merge_legacy_db --legacy-db "$LEGACY_DB" --dry-run

echo
read -r -p "Birlashtirilsinmi? Davom etish uchun 'ha' deb yozing: " answer
if [[ "$answer" != "ha" ]]; then
  echo "To'xtatildi. Hech narsa o'zgarmadi."
  exit 0
fi
new exec -T backend python manage.py merge_legacy_db --legacy-db "$LEGACY_DB"
echo
echo "Tayyor. Zaxira: $BACKUPS/prava777-$STAMP.dump (orqaga qaytarish kerak bo'lsa)."
