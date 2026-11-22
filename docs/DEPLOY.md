# Deploy va ko'chirish eslatmalari

Bu fayl backend'ni jonli tizimga chiqarishdagi nozik joylarni yig'adi. Ishga
tushirish buyruqlari `README.md` da.

## 1. Do'kondagi mobil ilova hech qachon yangilanmaydi

Ilovaning ichida server manzili qotib qolgan: `https://mobile.prava777.uz`
(`mobil/src/api/config.ts`). Uni o'zgartirish faqat yangi versiya chiqarish bilan
mumkin, o'rnatilgan nusxalarga esa u yetib bormaydi.

**Shuning uchun ko'chirish nginx darajasida qilinadi:** `mobile.prava777.uz`
hostini yangi backendga yo'naltiring. Ilova o'z manzilini o'zgartirmasdan yangi
tizimga tushadi.

> **Domen almashdi (2026-11):** `avtotest-tayyorlov.uz` → `prava777.uz`. Yangi
> build'lar `mobile.prava777.uz` ga ulanadi, ammo ilgari o'rnatilgan nusxalar hali
> ham `mobile.avtotest-tayyorlov.uz` ga murojaat qiladi. Ular ishlashda davom
> etishi uchun eski domen DNS'ini o'chirmang: nginx'da uni ham shu backendga
> proksi qiling (yoki 308 bilan yangi domenga yo'naltiring — POST so'rovlar ham
> saqlanadi) va `ALLOWED_HOSTS` ga ikkala hostni yozing.

Ilova ishlatadigan va **buzilmasligi shart** bo'lgan yo'llar:

| Yo'l | Izoh |
|---|---|
| `POST /api/v1/auth/token/refresh/` | Quyidagi 2-bandga qarang — kirgan foydalanuvchilar chiqib ketmaydi |
| `GET /api/v1/lessons/{id}/` | **O'rganish ekrani** — `?mode=study` yubormaydi, lekin to'g'ri javob, `explanation`, `audio_url` va `explanation_image_url` kerak |
| `GET /api/v1/exam/generate/?count=` | `deprecated`, lekin ishlaydi |
| `POST /api/v1/progress/exam-attempts/` | `deprecated`, lekin ishlaydi |
| `GET /api/v1/progress/saved/`, `mistakes/` | Javob kaliti bilan keladi — ilova shu bilan chizadi |

Bu yo'llarning javob shaklini o'zgartirishdan oldin `mobil/src/api/types.ts` ni
va tegishli ekranni o'qib chiqing.

> **Parol bilan kirish yopildi (2026-11).** Kirish faqat Telegram orqali
> (`auth/telegram/claim/`). Eski ilova `auth/login/`, `register/` va parol
> tiklashda `400 update_required` oladi — bunday foydalanuvchi ilovani
> yangilashi kerak. Allaqachon kirib turganlar refresh token bilan ishlashda
> davom etadi. Qoraqalpoq tili (`qq`) ham olib tashlandi: migratsiya
> `language=qq` ni `uz` qiladi, eski ilovaning `?lang=qq` so'rovlari `uz` kontent
> oladi.

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

## 6. Telegram orqali kirish

Yagona kirish yo'li (mobil va React admin panel). `TELEGRAM_BOT_TOKEN` va
`TELEGRAM_BOT_USERNAME` (token egasi bo'lgan bot) to'ldirilgan bo'lishi va bot
(`docker compose --profile bot up -d`) ishlab turishi **shart** — bot to'xtasa
hech kim kira olmaydi (mehmon rejimidan tashqari). Sessiyalar Redis'da.

Bot faqat yuboruvchining o'z kontaktini va faqat `+998` raqamini qabul qiladi.
Shef React panelga ham Telegram bilan kiradi — uning raqami bazada `admin`
rolida bo'lishi kerak. Apple/Google orqali kirish olib tashlandi (`SocialAccount`
jadvali saqlangan).

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
`nginx` (`/api/`, `/admin/`, `/media/` — `WEB_PORT`), `bot` (Telegram, `bot`
profili — standart holatda ishga tushmaydi). Admin panel compose'da **yo'q** —
u `npm run build` qilinib, tizim nginx'i orqali uzatiladi (pastda).

| Port | Nima | Kimga |
|---|---|---|
| `${WEB_PORT:-9005}` | `/api/` + `/admin/` + `/media/` (login tezlik cheklovi bilan) | ixtiyoriy; lokal `npm run dev` shu yerga proxy qiladi |
| `127.0.0.1:${API_PORT:-8010}` | faqat backend (Django) | tizim nginx'i → admin, `mobile.`, `api.` domenlari |

### Admin panel (`npm run build` + tizim nginx'i)

```
cd admin
cp .env.example .env      # VITE_API_URL bo'sh — admin va API bitta domenda
npm ci && npm run build   # → admin/dist/  (har yangilanishda qayta build)
```

```nginx
server {
    server_name admin.prava777.uz;   # + listen 443 ssl / certbot
    client_max_body_size 50M;                  # rasm/audio yuklash

    root /yo'l/avtotest-online/admin/dist;
    location / { try_files $uri /index.html; }

    location /api/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /media/ {
        alias /yo'l/avtotest-online/backend/media/;
        expires 30d;
    }
}
```

`VITE_API_URL` build paytida kodga yoziladi. Admin boshqa domendan API'ga
murojaat qilsa (`VITE_API_URL=https://api...`), o'sha domenni backend
`.env` dagi `CORS_ALLOWED_ORIGINS` ga qo'shing.

Rasm/audio fayllar konteyner ichida emas — serverdagi `backend/media/`
papkasida (bind mount). Zaxira uchun shu papkani ko'chirish kifoya.

```
1. cp .env.example .env                  # DB_PASSWORD, WEB_PORT, API_PORT
   cp backend/.env.example backend/.env  # SECRET_KEY, ALLOWED_HOSTS, TELEGRAM_BOT_TOKEN
2. docker compose up -d --build
3. Ma'lumot ko'chirish — 3-bo'lim (docker compose exec backend python manage.py ...)
4. Rasmlar: eski mobil backenddagi media/ → backend/media/
5. Tizim nginx'i: mobile.prava777.uz → proxy_pass http://127.0.0.1:8010;
   (Host, X-Forwarded-For, X-Forwarded-Proto sarlavhalari shart — busiz rasm
   URL'lari http:// bo'lib qoladi va iOS ularni ochmaydi;
   `proxy_set_header X-Real-IP $remote_addr;` ham shart — Payme IP cheklovi
   faqat shu sarlavhani o'qiydi, 10-bo'lim)
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

## 9. Mehmon rejimi

Yangi mobil ilova birinchi ochilganda `POST /api/v1/auth/guest/` chaqiradi va
telefonsiz `role=guest` foydalanuvchi hamda 3 kunlik sessiya oladi
(`settings.GUEST_DAYS`). Muddat tugagach har so'rov `401` va
`code: "guest_expired"` qaytaradi.

- Bu yo'l ochiq (tokensiz), shuning uchun **tizim nginx'ida ham** login kabi
  tezlik cheklovini qo'ying (`nginx/conf.d/default.conf` dagi
  `location = /api/v1/auth/guest/` blokiga qarang). Backend o'zi ham IP bo'yicha
  soatiga 20 ta bilan cheklaydi (`DEFAULT_THROTTLE_RATES["guest"]`).
- `prune_devices` (cron) ro'yxatdan o'tmagan, kelganiga 33 kundan oshgan
  mehmonlarni o'chiradi. Shu oraliqda ro'yxatdan o'tgan mehmon natijalari bilan
  o'quvchiga aylanadi.

## 10. PRO to'lovlari (Payme / Click)

Tariflar, sotish platformalari va provayder kalitlari **Django admin**'da
(`/admin/payments/`) kiritiladi — `.env` da emas. "To'lov sozlamalari" sahifasini
faqat **superuser** ko'radi; kalit maydonlari sahifaga qaytib chiqmaydi, bo'sh
qoldirilsa eski qiymat saqlanadi.

Merchant kabinetlariga yoziladigan manzillar (domen — API qaysi domenda bo'lsa):

| Provayder | Manzil |
|---|---|
| Payme (Endpoint URL) | `https://<domen>/api/v1/payments/payme/` |
| Click (Prepare URL) | `https://<domen>/api/v1/payments/click/prepare/` |
| Click (Complete URL) | `https://<domen>/api/v1/payments/click/complete/` |

To'lovdan keyingi qaytish sahifasi: `https://<domen>/api/v1/payments/done/`.

Diqqat:

- **`X-Real-IP`**: tizim nginx'ida `proxy_set_header X-Real-IP $remote_addr;`
  bo'lmasa, Payme IP ro'yxati to'ldirilganda hamma so'rov rad etiladi.
  `X-Forwarded-For` ataylab o'qilmaydi (soxtalashtirish oson).
- **`SECRET_KEY` almashtirilsa** bazadagi shifrlangan kalitlar ochilmay qoladi —
  Payme va Click kalitlarini admin'da qayta kiriting.
- iOS'da sotish standart holatda o'chiq (`sell_ios`) — Apple App Store qoidalari
  (3.1.1) ilova ichida tashqi to'lovni cheklaydi.

## 11. Push bildirishnomalar (FCM)

Admin → Foydalanuvchilar: filtrlab (rol — mehmon ham, filial, PRO, til, «push
qurilma: Bor») belgilang → amal **«Bildirishnoma yuborish (push)»** → matn
(o'zbekcha majburiy, kirill/rus ixtiyoriy) → Yuborish. Har kimga ilovada
tanlagan tilida boradi; bo'sh tilga o'zbekchasi. Hammaga yuborish —
Bildirishnomalar → Qo'shish, «Kimga: Hammaga», «Push ham yuborilsin».
Natija (yetkazildi / xato) Bildirishnomalar ro'yxatida.

Yuborishni `push-worker` servisi qiladi (`manage.py push_worker`, har 3 s
navbatni tekshiradi). Yaroqsiz tokenlar (ilova o'chirilgan) avtomatik nofaol.

Bir martalik sozlash:
1. Firebase service account JSON → serverda `<loyiha>/firebase/service-account.json`
   (`chmod 600`). Boshqa joyda bo'lsa compose uchun `FIREBASE_DIR=/yo'l`.
2. `backend/.env`: `FIREBASE_CREDENTIALS_FILE=/run/secrets/firebase/service-account.json`
3. `docker compose up -d --build backend push-worker`;
   `docker compose logs -f push-worker` — «push_worker ishga tushdi» (oxirida
   «Firebase sozlanmagan!» bo'lmasligi kerak).
4. APNs kaliti (.p8) Firebase → Cloud Messaging → Apple app configuration'da
   bo'lishi shart, aks holda iOS'ga yetmaydi (Android ishlayveradi).

