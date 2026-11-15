# Faqat Telegram orqali kirish, parolsiz; qoraqalpoq tili olib tashlanadi — dizayn

Sana: 2026-11-15. Qamrov: `avtotest-online` (backend, bot, React `admin/`) va mobil
ilova (`avtotest/avtotest-mobile`, alohida repo).

## Maqsad

Telefon+parol bilan kirish va ro'yxatdan o'tish butunlay yo'qoladi. Mobil ilovada
faqat ikki yo'l qoladi:

1. **Mehmon rejimi** — avvalgidek, ilova birinchi ochilganda 5 kun.
2. **Telegram orqali kirish** — bitta tugma. Foydalanuvchi raqam ham, parol ham
   yozmaydi: bot kontaktni so'raydi, backend raqam bo'yicha foydalanuvchini taniydi.
   Raqam bazada bo'lsa — kiradi, bo'lmasa — hisob ochiladi. Kirish va ro'yxatdan
   o'tish — bitta oqim.

Shu bilan qoraqalpoq tili (`qq`) hamma joydan olib tashlanadi.

## Shef qarorlari

- Parol hech qayerda yo'q — mobilda ham, shefda ham ("hammasi faqat Telegram orqali").
- Do'kondagi eski ilova parol bilan kira olmaydi — yangilashi kerak.
- Mobilda faqat mehmon rejimi va Telegram auth.
- `qq` hamma joydan olib tashlanadi.

## Quruvchi qarorlari (tekshirib chiqing)

- **Django admin (`/admin/`) paroli qoladi** — bu serverning favqulodda eshigi
  (`createsuperuser`, Payme/Click kalitlari). Oddiy foydalanuvchi u yerga kirmaydi.
- **React admin panel ham Telegram orqali kiradi** — sahifada tugma va QR kod; shef
  telefonida kontaktini yuboradi, sahifa o'zi kiradi. Kirgan foydalanuvchi `admin`
  rolida bo'lmasa panel "ruxsat yo'q" deydi (`manage/` baribir yopiq).
- **Desktop va web ilovalar (kirish kodi) o'zgarmaydi.**
- **Ijtimoiy kirish (`auth/social/`) ham yopiladi** — mobil ilovada uning tugmalari
  yo'q, "faqat Telegram" qoidasiga mos.
- **Ism Telegram kontaktidan** (`first_name last_name`) olinadi; foydalanuvchi keyin
  Profil'da o'zgartira oladi.
- **Bloklangan hisob** (`User.is_active=False` yoki avtomaktab bloklagan
  `Student.is_active=False`) Telegram orqali ham kira olmaydi.
- Ro'yxatdan o'tishdagi **12 kunlik PRO sovg'a** yangi hisobga avvalgidek beriladi.
- Avtomaktab bergan PIN (`Student.password`) endi kirish uchun ishlatilmaydi; maydon
  bazada qoladi (front-ofis ma'lumoti), unga tegilmaydi.

## Oqim

```
Ilova                     Backend                       Bot (@prava777Robot)
  │ POST auth/telegram/start/ {purpose:"auth", lang}
  │ ───────────────────────▶ sessiya (Redis, 10 daqiqa)
  │ ◀── {token, link}
  │ link ni ochadi ──────────────────────────────────▶ /start <token>
  │                                                     kontakt so'raydi
  │                                                     kontakt o'ziniki? raqam +998?
  │                          ◀── sessiya: verified, phone, ism, telegram_id
  │ GET auth/telegram/status/<token>/ (har ~2 s)
  │ ◀── verified
  │ POST auth/telegram/claim/ {token, guest_refresh?, platform, device_label}
  │ ◀── {user, tokens, created}
```

## Backend

### Telegram sessiyasi (`apps/telegramauth/verification.py`)

- Yangi maqsad `purpose="auth"`. Bu maqsadda `phone` **so'ralmaydi** —
  `start_session(None, "auth", lang)`. Cheklov (`MAX_SESSIONS`) raqam o'rniga IP bo'yicha
  (`tgv:count:ip:<ip>`), IP `X-Real-IP` → `REMOTE_ADDR` (payments'dagi uslub).
- Bot kontakt kelganda `auth` sessiyasida raqamni solishtirmaydi — kontakt raqami
  (normallashtirilgan, `+998…`) va ism sessiyaga yoziladi, holat `verified`.
  O'zbekiston raqami bo'lmasa — `foreign` (avvalgidek, `mismatch` holati).
- Kontakt yuboruvchining o'ziniki ekanini tekshirish saqlanadi (`contact.user_id ==
  from_user.id`).
- Bot javobi: "Tasdiqlandi, ilovaga qayting" + mavjud «Ilovaga qaytish» tugmasi.
- `register` va `reset` maqsadlari olib tashlanadi.

### Yangi endpoint: `POST /api/v1/auth/telegram/claim/` (AllowAny)

`{token, guest_refresh?, platform?, device_label?}` →
`200/201 {user, tokens, created}`.

- Sessiya `verified` va `purpose="auth"` bo'lishi shart, aks holda
  `400 verification_invalid`. Token **bir marta** ishlatiladi (Redis `delete`).
- Raqam bo'yicha `User` topilsa:
  - bloklangan bo'lsa → `403 {code: "blocked"}`;
  - mehmon (`role=guest`) bo'lsa ham topilmaydi — mehmonlarda `phone` o'rinbosar.
  - aks holda shu foydalanuvchiga sessiya (`issue_tokens`) — `200`.
  - `guest_refresh` berilgan bo'lsa ham mehmon ma'lumoti ko'chirilmaydi, mehmon
    sessiyasi yopiladi (mavjud "mehmon mavjud hisobga kirsa" qoidasi).
- Topilmasa — yangi o'quvchi:
  - `guest_refresh` yaroqli bo'lsa o'sha mehmon `User` aylanadi (mavjud register
    mantig'i: telefon, ism, `role=student`, mehmon sessiyasi yopiladi, natijalar
    saqlanadi; muddati o'tgan mehmon ham aylanadi);
  - aks holda yangi `User` (`set_unusable_password`);
  - 12 kunlik PRO sovg'a; `TelegramAccount` bog'lanadi — `201`.
- Device limiti avvalgidek (`issue_tokens`, `platform` default `mobile`).

### Yopiladigan yo'llar

`auth/login/`, `auth/register/`, `auth/reset-password/`, `auth/change-password/`,
`auth/social/`, `auth/send-code/`, `auth/verify-code/` — hammasi
`400 {code: "update_required", detail: "Ilovaning yangi versiyasini o'rnating."}`
qaytaradi (eski ilova tushunarli xabar ko'rsatadi). Ularning serializer va
mantig'i o'chiriladi. `REGISTER_REQUIRE_TELEGRAM` sozlamasi olib tashlanadi.

Qoladi: `guest/`, `login-code/` (desktop/web), `token/refresh/`, `logout/`, `me/`,
`devices/`, `telegram/start|status|claim|return/`.

### Qoraqalpoq tili

- `User.Language.QQ` olib tashlanadi; migratsiya `language="qq"` → `"uz"`.
- `common/lang.py`: `qq` tanlovdan chiqadi, lekin eski ilova yuborgan `?lang=qq` va
  `Accept-Language: qq` jimgina `uz` deb o'qiladi (xato bermaydi).
- `auth/me/` PATCH va `guest/` da `language="qq"` kelsa — `uz` ga aylantiriladi (eski
  ilova uchun), `400` emas.
- Bot (`app_lang_to_bot`), Swagger tavsiflari, README va spec'lardagi eslatmalar
  yangilanadi.

### Django admin

Foydalanuvchi sahifasida parol maydoni qoladi (superuser uchun). O'zgarish yo'q.

## Mobil ilova

- **Kirish ekrani (`Login.tsx`):** logo, "Xush kelibsiz", bitta katta
  "Telegram orqali kirish" tugmasi, ostida qisqa izoh ("Telegram'da kontaktingizni
  yuboring — raqamingiz shu orqali tasdiqlanadi"). Telefon, parol, "Parolni
  unutdingizmi?", "Ro'yxatdan o'tish" — yo'q.
- **Kutish holati:** mavjud `TelegramStep` asosida — "Telegram'da kontaktingizni
  yuboring", "Telegram'ni qayta ochish", "Bekor qilish". `AppState` "active" bo'lganda
  darhol va har ~2 s `status` so'raladi; `verified` → `claim` → bosh sahifa.
  `mismatch` (chet el raqami) → xabar; `expired` → qayta boshlash.
- **O'chiriladi:** `auth/Register.tsx`, `auth/Forgot.tsx`, `api/otp.ts`
  (`resetPassword`), `api/index.ts` dagi `login`/`register`, tegishli tarjimalar.
- **Mehmon:** banner, Profil va `GuestExpired` ekranidagi "Ro'yxatdan o'tish" /
  "Kirish" tugmalari bitta "Telegram orqali kirish" tugmasiga almashadi;
  `claim` ga `guest_refresh` yuboriladi.
- **PRO ekrani:** mehmon "Sotib olish" bossa — shu Telegram kirish oqimi.
- **Til:** `LangCode` dan `qq` olib tashlanadi, `LANG_META` da 3 til. Qurilmada `qq`
  saqlangan bo'lsa `uz` ga tushadi.
- `app.json` ga yangi ruxsat yoki sxema qo'shilmaydi.

## React admin panel (`admin/`)

- `Login.jsx`: "Telegram orqali kirish" tugmasi. Bosilganda `start` → havola yangi
  oynada ochiladi va QR kod ko'rsatiladi (telefonda skanerlash uchun); sahifa `status`
  ni so'raydi, `verified` → `claim` (`platform: "web"`, `device_label: "Admin Panel"`).
- `claim` dan kelgan `user.role` `admin` bo'lmasa — "Bu panel faqat shef uchun",
  tokenlar tashlanadi.
- QR uchun kichik kutubxona (`qrcode` yoki shunga o'xshash) yoki havolaning o'zi —
  quruvchi ixtiyorida.

## Testlar

- Yangi: `claim` — mavjud foydalanuvchi kiradi; yangi raqam → hisob ochiladi (+12 kun
  PRO, `TelegramAccount`); mehmon aylanadi (muddati o'tgan ham); mehmon mavjud hisobga
  kirsa ma'lumot ko'chmaydi; bloklangan `User` va `Student` → 403; token ikki marta
  ishlamaydi; `pending`/`mismatch` sessiya → 400; device limit.
- Bot: `auth` sessiyasida kontakt → `verified` va raqam/ism yoziladi; chet el raqami →
  `mismatch`; begona kontakt rad etiladi.
- Yopilgan yo'llar → `400 update_required`.
- `qq`: migratsiya, `?lang=qq` → `uz` kontent, PATCH `language=qq` → `uz`.
- Eski login/register/reset testlari yangi qoidaga moslanadi yoki o'chiriladi.
  Qolgan to'plam (to'lovlar, kontent, desktop kirish kodi) o'tishda davom etadi.
- Mobil: `npx tsc --noEmit` xatosiz; emulyatorda lokal backend va
  `@AvtoPravanewbot` bilan qo'lda: yangi raqam, mavjud raqam, mehmon aylanishi.

## Maqsad emas

- Telegram'siz kirish usuli (SMS, email, Apple/Google).
- Desktop/web kirish kodini o'zgartirish.
- Django admin'ni Telegram'ga o'tkazish.

## Muvaffaqiyatsizlik deb hisoblanadi

- Begona raqam bilan kirish (kontakt boshqa odamniki bo'lsa ham qabul qilinsa).
- Bitta tasdiqlangan token bilan ikki marta token olish.
- Bloklangan o'quvchining Telegram orqali kirishi.
- Mehmon natijalarining Telegram orqali ro'yxatdan o'tganda yo'qolishi.
- Eski ilovada `?lang=qq` bilan kontent ochilmay qolishi.
- Mavjud foydalanuvchining (raqami bazada bor) yangi hisob bilan ikkilanishi.

## Quruvchi ixtiyorida

- Sessiyadagi maydon nomlari, `claim` javobidagi qo'shimcha maydonlar.
- IP cheklovining aniq soni.
- Kirish ekranining ko'rinishi — mavjud dizayn tili asosida.
- Admin panelda QR kod usuli.
