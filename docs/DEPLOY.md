# Deploy va ko'chirish eslatmalari

Bu fayl backend'ni jonli tizimga chiqarishdagi nozik joylarni yig'adi. Ishga
tushirish buyruqlari `README.md` da.

## 1. Do'kondagi mobil ilova hech qachon yangilanmaydi

Ilovaning ichida server manzili qotib qolgan: `https://mobile.avtotest-tayyorlov.uz`
(`mobil/src/api/config.ts`). Uni o'zgartirish faqat yangi versiya chiqarish bilan
mumkin, o'rnatilgan nusxalarga esa u yetib bormaydi.

**Shuning uchun ko'chirish nginx darajasida qilinadi:** `mobile.avtotest-tayyorlov.uz`
hostini yangi backendga yo'naltiring. Ilova o'z manzilini o'zgartirmasdan yangi
tizimga tushadi.

Ilova ishlatadigan va **buzilmasligi shart** bo'lgan yo'llar:

| Yo'l | Izoh |
|---|---|
| `POST /api/v1/auth/login/` | `platform` yubormaydi — default `mobile` bo'ladi |
| `POST /api/v1/auth/token/refresh/` | Quyidagi 2-bandga qarang |
| `GET /api/v1/lessons/{id}/` | **O'rganish ekrani** — `?mode=study` yubormaydi, lekin to'g'ri javob, `explanation`, `audio_url` va `explanation_image_url` kerak |
| `GET /api/v1/exam/generate/?count=` | `deprecated`, lekin ishlaydi |
| `POST /api/v1/progress/exam-attempts/` | `deprecated`, lekin ishlaydi |
| `GET /api/v1/progress/saved/`, `mistakes/` | Javob kaliti bilan keladi — ilova shu bilan chizadi |

Bu yo'llarning javob shaklini o'zgartirishdan oldin `mobil/src/api/types.ts` ni
va tegishli ekranni o'qib chiqing.

## 2. Jonli sessiyalar

Baza eski mobil backupdan tiklanganda jonli refresh tokenlarning hech birida
`Device` yozuvi yo'q. `DeviceAwareTokenRefreshView` noma'lum `jti` uchun yozuvni
o'zi to'ldiradi (`grandfather_device`), shuning uchun foydalanuvchilar tizimdan
chiqib ketmaydi.

**Lekin `SECRET_KEY` o'zgarsa barcha JWT'lar yaroqsiz bo'ladi** va hamma qayta
kirishga majbur bo'ladi. Eski kalitni saqlab qolish yoki chiqib ketishni ataylab
qabul qilish — ongli qaror bo'lishi kerak.

## 3. Ma'lumot ko'chirish tartibi

```
1. backups/avtotest_mobile_*.sql  →  yangi baza
2. python manage.py migrate
3. python manage.py import_content --path ../../admin-panel/src/db --dry-run
   python manage.py import_content --path ../../admin-panel/src/db
4. python manage.py import_web --database-url <eski web bazasi> --dry-run
   python manage.py import_web --database-url <eski web bazasi>
5. python manage.py convert_images_to_webp
6. python manage.py setup_groups
```

Haqiqiy ma'lumotda tekshirilgan natija (`web/backend/db1.sqlite3`):
4 filial, 1757 foydalanuvchi yaratildi, 1 tasi mavjud hisobga bog'landi
(ikki eski yozuv bitta `+998…` raqamiga normallashdi), 6 tasi yaroqsiz raqam
sababli o'tkazildi, 22 to'lov, 31 hisobot. Ikkinchi ishlatishda hech narsa
qo'shilmaydi va balanslar o'zgarmaydi.

`import_web` o'tkazib yuborgan 6 yozuvni qo'lda ko'rib chiqing — ular
`stderr` ga yoziladi.

## 4. Nashr etilmagan savollar

`is_published=False` savol o'quvchiga hech qayerda ko'rinmaydi. Migratsiya
mavjud 1152 savolni `True` qiladi; API orqali yangi yaratilgani `False` bo'ladi.

Shef buni Django adminda ko'radi va almashtiradi: savollar ro'yxatida
`is_published` ustuni, filtr va ommaviy amallar ("Nashr etish" / "Nashrdan
olish") bor. Admin panel fronti ham bu maydonni ko'rsatishi kerak — aks holda
shef savol kiritadi-yu u hech qayerda chiqmaydi.

## 5. Sotilgan kirish muddati

Web va desktop sessiyalari 12 kundan keyin tugaydi (`settings.SESSION_DAYS`),
mobilda muddat yo'q. Kirish kodi bilan ochilgan sessiya kodning o'z muddatidan
uzoq yashamaydi. `platform` mijozdan olinmaydi — `login-code/` har doim desktop
tarifida ishlaydi.

Muddati o'tgan qurilmalarni tozalash uchun cron:

```
python manage.py prune_devices
```

## 6. Ijtimoiy kirish

`APPLE_BUNDLE_ID`, `GOOGLE_CLIENT_IDS` yoki `TELEGRAM_BOT_TOKEN` bo'sh bo'lsa
o'sha provayder orqali kirish **ochilmaydi**. Tekshiruvsiz ishlash imkoni yo'q.

`auth/social/` mijoz yuborgan telefon raqami bo'yicha hisob qidirmaydi —
hisob faqat tasdiqlangan provayder `uid` si bo'yicha topiladi. Telefonsiz
ijtimoiy hisobga o'rinbosar raqam beriladi; foydalanuvchi haqiqiy raqamini
keyin qo'shadi.

## 7. Mobil qurilma limiti

Mobilda limit 2 qurilma (`MAX_DEVICES_PER_PLATFORM`), lekin limit to'lganda
403 **qaytmaydi** — eng uzoq ishlatilmagan sessiya yopiladi
(`settings.DEVICE_EVICT_OLDEST = {"mobile"}`). Sabab: do'kondagi ilova chiqishda
`/auth/logout/` ni chaqirmaydi, slot hech qachon bo'shamaydi va foydalanuvchi
2 marta chiqib-kirgandan keyin butunlay bloklanib qolardi. Yopilgan telefon
keyingi token yangilashda 401 oladi va login ekraniga chiqadi. Web/desktopda
limit qat'iy (403) — u yerda kirish sotiladi.

## 8. Serverga deploy (Docker + tizim nginx'i)

Konteynerlar: `db` (Postgres), `redis` (OTP kodlari), `backend` (gunicorn),
`admin` (admin panel statikasi), `nginx` (admin panel + API, `WEB_PORT`),
`bot` (Telegram, `bot` profili — standart holatda ishga tushmaydi).

| Port | Nima | Kimga |
|---|---|---|
| `${WEB_PORT:-9005}` | admin panel + `/api/` + `/media/` | admin domeni |
| `127.0.0.1:${API_PORT:-8010}` | faqat backend (Django) | tizim nginx'i → `mobile.avtotest-tayyorlov.uz` |

Rasm/audio fayllar konteyner ichida emas — serverdagi `backend/media/`
papkasida (bind mount). Zaxira uchun shu papkani ko'chirish kifoya.

```
1. cp .env.example .env                  # DB_PASSWORD, WEB_PORT, API_PORT
   cp backend/.env.example backend/.env  # SECRET_KEY, ALLOWED_HOSTS, TELEGRAM_BOT_TOKEN
2. docker compose up -d --build
3. Ma'lumot ko'chirish — 3-bo'lim (docker compose exec backend python manage.py ...)
4. Rasmlar: eski mobil backenddagi media/ → backend/media/
5. Tizim nginx'i: mobile.avtotest-tayyorlov.uz → proxy_pass http://127.0.0.1:8010;
   (Host, X-Forwarded-For, X-Forwarded-Proto sarlavhalari shart — busiz rasm
   URL'lari http:// bo'lib qoladi va iOS ularni ochmaydi)
6. Eski mobil backend botini to'xtating, keyin:
   docker compose --profile bot up -d
```

Diqqat:

- **`SECRET_KEY`** — prod serverdagi eski mobil backend kaliti bilan bir xil
  bo'lsin (2-bo'lim), aks holda hamma tizimdan chiqadi. Kalitda `$` bo'lsa
  compose uni o'zgaruvchi deb o'qiydi — `$$` qilib yozing.
- **Bot bitta joyda** ishlashi shart — ikki jarayon bitta tokenda polling
  qilsa Telegram `Conflict` xatosini beradi.
- **443-port**: `web/` compose'idagi nginx ham 443 ni band qiladi va
  `mobile.` domenini o'zi uzatadi (`web/nginx/nginx.conf`). Tizim nginx'iga
  o'tishdan oldin u yerdagi `mobile.` blokini olib tashlang va portlarni
  kelishtiring.
- Login tezlik cheklovi (compose nginx'ida): IP uchun daqiqasiga 10 ta,
  `burst=5`. nginx `r/h` ni qabul qilmaydi.
