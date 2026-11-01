# Mehmon rejimi va Telegram orqali ro'yxatdan o'tish — dizayn

Sana: 2026-11-01. Qamrov: `avtotest-online/backend` (API va bot) va mobil ilova
(`avtotest/avtotest-mobile`, alohida repo).

Ikki qism bir-biriga bog'langan: yangi foydalanuvchi ilovani ro'yxatdan o'tmasdan
5 kun **mehmon** sifatida ishlatadi, so'ng Telegram orqali ro'yxatdan o'tadi va
mehmon hisobi o'quvchiga aylanadi.

## 1-qism. Mehmon rejimi

### Shef qarorlari

- Ilova o'rnatilib ochilishi bilan ro'yxatdan o'tmasdan ishlaydi: **5 kun**
  davomida PRO'ga aloqador bo'lmagan hamma narsa ochiq. PRO qismlar avvalgidek
  qulf bilan.
- 5 kundan keyin ro'yxatdan o'tish shart.
- Backend kim mehmon, kim o'quvchi, kim PRO ekanini bilishi kerak. Mehmon
  serverda **sessiya** sifatida yashaydi (telefonda yashirin hisoblagich emas).
  Alohida yoqish/o'chirish tugmasi ("richag") kerak emas.
- Ilovani o'chirib qayta o'rnatib yana 5 kun olish **muammo emas** — qurilmani
  server tomonda kuzatish shart emas.

### Backend

**Yangi rol:** `User.Role.GUEST = "guest"` ("Mehmon"). Mehmonning telefoni yo'q;
`phone` ustuni majburiy va noyob bo'lgani uchun unga noyob o'rinbosar yoziladi.
O'rinbosar haqiqiy `+998…` raqamga **o'xshamasligi** shart (mavjud
`placeholder_phone` soxta `+998` raqam yasaydi — bu yerda yaramaydi: haqiqiy
foydalanuvchi raqami bilan to'qnashishi mumkin). Shakli quruvchi ixtiyorida
(13 belgiga sig'ishi kerak). Mehmonda parol yo'q (`set_unusable_password`).

**`POST /api/v1/auth/guest/`** (`AllowAny`) — `{device_id, lang, device_label?}`
→ `{user, tokens, guest_until}`.

- Yangi mehmon `User` va unga `Device` sessiyasi (`platform=mobile`,
  `expires_at = hozir + GUEST_DAYS`) yaratiladi. `settings.GUEST_DAYS = 5`.
- Tokenlarda kirish kodi sessiyasidagi kabi `did` (Device pk) bo'ladi — shunda
  har so'rovda sessiya tirikligi tekshiriladi va 5 kun tugashi bilan 1 kunlik
  access token kutilmaydi.
- `device_id` — ilova o'rnatilganda yaratib saqlaydigan tasodifiy ID. Faqat
  ma'lumot uchun (admin'da ko'rinadi), cheklov uchun ishlatilmaydi.
- Endpointni ommaviy chaqirib baza to'ldirilmasligi uchun IP bo'yicha cheklov
  (masalan nginx `limit_req`, login'dagi kabi). Son quruvchi ixtiyorida.

**Muddat tugashi:** `common/authentication.py` `did` bor tokenlarda hozir faqat
`Device.is_active` ni tekshiradi; muddat (`expires_at`) ham tekshirilsin. Mehmon
sessiyasi tugagan bo'lsa → `401`, `code: "guest_expired"`. Refresh ham rad
etiladi (mavjud `device_for_refresh` muddatni allaqachon tekshiradi).

**Huquqlar:** mehmon o'quvchi bilan bir xil kontent va `progress/` yo'llarini
ishlatadi; `pro_active` har doim `False`. `teacher/` va `manage/` yopiq
(mavjud ruxsat sinflari). `change-password/` mehmonga yopiq.

**Ro'yxatdan o'tganda mehmon aylanadi:** `POST /auth/register/` mehmonning
`guest_refresh` tokeni bilan chaqirilsa yangi hisob ochilmaydi — o'sha `User` ga
telefon, parol, ism yoziladi, `role = student`, mehmon sessiyasi yopiladi va
odatdagi (muddatsiz mobil) sessiya tokenlari qaytadi. Bilet natijalari, xatolar
va sevimlilar shu `User` ga bog'langani uchun o'z-o'zidan saqlanadi.
Ro'yxatdan o'tishdagi mavjud "12 kun PRO sovg'a" qoidasi saqlanadi.
*(Natijalar saqlanishi — quruvchi qarori, shef so'ramagan.)*

**Muddati o'tgan mehmon ham aylanadi.** Ko'pchilik 5 kun tugagach majburan
ro'yxatdan o'tadi, shuning uchun aylanish faqat shu holatda ishlasa natijalar
amalda saqlanmaydi. Qoida:

- `register/` mehmonni uning **refresh tokeni** (`guest_refresh` maydoni) orqali
  taniydi: imzo va tokenning o'z umri (90 kun) tekshiriladi, mehmon sessiyasining
  5 kunlik muddati esa e'tiborsiz. Access token 1 kunda eskiradi, shuning uchun
  u bu ishga yaramaydi. Boshqa barcha yo'llarda `guest_expired` qoidasi kuchida.
- Aylanish mehmon `User` tozalanmaguncha mumkin (quyidagi 30 kun).
- Mobil ilova `guest_expired` olganda mehmon tokenlarini **o'chirmaydi** —
  ular faqat ro'yxatdan o'tish uchun saqlanadi; refresh urinilmaydi.

*(Quruvchi qarori.)*

**Mehmon mavjud hisobga kirsa** (`auth/login/`) — mehmon ma'lumotlari ko'chirilmaydi,
mehmon sessiyasi tashlab ketiladi. *(Quruvchi qarori.)*

**Tozalash:** `prune_devices` (cron) muddati o'tganiga 30 kundan oshgan,
aylanmagan mehmon `User` larni o'chiradi. *(Quruvchi qarori — baza
mehmonlar bilan to'lmasligi uchun.)*

**Django admin:** foydalanuvchilar ro'yxatida `role` filtri mehmonlarni ham
ko'rsatadi; mehmon uchun qachon kelgani va sessiyasi qachon tugashi ko'rinsin.

### Mobil ilova

- **Birinchi ochilish:** ilova o'rnatilgandan beri hech qachon sessiya
  bo'lmagan bo'lsa (qurilmada saqlanadigan belgi), login ekrani o'rniga ilova
  `auth/guest/` ni chaqiradi va to'g'ridan-to'g'ri bosh sahifani ochadi.
  Internet bo'lmasa — mavjud xato holati va "Qayta urinish".
- **Yangi mehmon faqat birinchi ochilishda yaratiladi.** Keyingi holatlarda
  yangi 5 kun berilmaydi *(quruvchi qarori)*:
  - mehmon muddati tugagan → "Sinov muddati tugadi" ekrani (ilovani yopib
    ochsa ham);
  - ro'yxatdan o'tgan foydalanuvchi chiqdi (logout) yoki sessiyasi yopildi →
    odatdagi login ekrani;
  - ilovani yangilagan, avval chiqib ketgan eski foydalanuvchi → login ekrani.

  Faqat ilovani o'chirib qayta o'rnatish belgini tozalaydi (shef buni qabul
  qilgan).
- **Bosh sahifada mehmon banneri:** "Mehmon rejimi · N kun qoldi" va
  "Ro'yxatdan o'tish" tugmasi. Kirish (mavjud hisob) havolasi ham bor.
- **Profil tabi** mehmonga profil o'rniga "Ro'yxatdan o'tish" va "Kirish"
  tugmalarini ko'rsatadi.
- **`guest_expired`** kelganda (istalgan so'rovda) ilova "Sinov muddati tugadi —
  davom etish uchun ro'yxatdan o'ting" ekraniga o'tadi: ro'yxatdan o'tish
  (2-qism oqimi) yoki kirish. Orqaga qaytib bo'lmaydi.
- Ro'yxatdan o'tish mehmon tokeni bilan chaqiriladi (yuqoridagi aylanish).

### Eski ilova

Eski versiyalar `auth/guest/` ni bilmaydi — ular uchun hech narsa o'zgarmaydi.

## 2-qism. Telegram orqali ro'yxatdan o'tish

## Nima uchun

Hozir mobil ilovada ro'yxatdan o'tish juda murakkab. Foydalanuvchi:

1. ilovada til, ism, telefon va parolni kiritadi;
2. "kod yuborish"ni bosadi — raqam botga bog'lanmagan bo'lsa xato oladi;
3. @AvtotestTayyorlovBot'ni o'zi topadi, /start bosadi, tilni tanlaydi,
   kontaktini ulashadi;
4. ilovaga qaytadi, kodni qayta so'raydi;
5. Telegram'dan 6 xonali kodni ko'chirib ilovaga yozadi.

Bundan tashqari `POST /auth/register/` raqamni hech tekshirmaydi — istalgan
begona raqamga hisob ochish mumkin.

Maqsad: raqamni tasdiqlashni **bitta havola va bitta tugmaga** qisqartirish.
Telegram faqat "bu odam shu raqam egasi" ekanini isbotlash uchun kerak:
foydalanuvchi va raqam bir xil bo'lishi kifoya.

## Shef qarorlari (foydalanuvchi aytgan)

- Tasdiqlash Telegram bot orqali, kontakt ulashish bilan. SMS yo'q, kod yozish yo'q.
- Bot ulashilgan raqamni ilovaga kiritilgan raqam bilan solishtiradi. Mos kelmasa
  bot aniq aytadi: "bu siz kiritgan raqam emas".
- Kirish (login) avvalgidek **telefon + parol** bilan. Telegram faqat ro'yxatdan
  o'tishda (va parolni tiklashda) raqamni tasdiqlaydi.
- Telegram'i yo'q yoki Telegram'i boshqa raqamda bo'lgan odam **hozircha ro'yxatdan
  o'ta olmaydi**.
- Do'kondagi eski versiya ilovada ro'yxatdan o'tishga urinilsa "Ilovaning yangi
  versiyasini o'rnating" chiqadi. Tasdiqlanmagan ro'yxatdan o'tish server tomonda
  yopiladi.

## Maqsadlar

- Ilova tasdiqlanganini **o'zi sezadi**: foydalanuvchi Telegram'da kontaktni
  ulashib ilovaga qaytganda, u allaqachon kirgan holatda bosh sahifada bo'ladi.
- Raqam mos kelmaganda foydalanuvchi bot'da ham, ilovada ham sababini ko'radi va
  ilovada raqamni tuzatib qayta urinadi.
- Server tasdiqlanmagan raqamga hisob ochmaydi.

## Maqsad emas

- WebSocket yoki push. Oddiy so'rov (polling) yetarli — hozirgi gunicorn (WSGI)
  sozlamasi o'zgarmaydi, Channels/ASGI qo'shilmaydi.
- SMS provayder.
- Telegram orqali kirish (login).
- Telegram'siz foydalanuvchilar uchun muqobil yo'l.
- Desktop va web ilovalar (ular shef bergan kirish kodi bilan ishlaydi — tegilmaydi).

## Anti-maqsadlar (texnik ishlasa ham muvaffaqiyatsizlik)

- Foydalanuvchi baribir biror kodni ko'chirib yozishi kerak bo'lsa.
- Birovning kontaktini yuborib (forward), begona raqamni tasdiqlash mumkin bo'lsa.
- Ilova "kutish" ekranida qotib qolsa va foydalanuvchi nima qilishni bilmasa.
- Mavjud foydalanuvchilarning kirishi (telefon + parol, kirish kodi) buzilsa.

## Oqim

```
Ilova                          Server                         Bot
  | 1. ism, telefon, parol       |                              |
  |---- POST telegram/start ---->|  sessiya: pending (Redis)    |
  |<--- {token, link} -----------|                              |
  | 2. "Telegram'da tasdiqlash"  |                              |
  |---- t.me/Bot?start=<token> ----------------------------->   |
  |                              |   /start <token>             |
  |                              |<-- sessiyani o'qiydi --------|
  |                              |   "Kontaktni ulashish" tugma |
  |                              |   kontakt keladi             |
  |                              |<-- verified / mismatch ------|
  | 3. har ~2 s va ilovaga        |                              |
  |    qaytganda:                |                              |
  |---- GET telegram/status ---->|                              |
  |<--- verified ----------------|                              |
  |---- POST register {+token} ->|  tokenni ishlatadi, hisob    |
  |<--- {user, tokens} ----------|                              |
  | 4. bosh sahifa               |                              |
```

## Backend

### Tasdiqlash sessiyasi (Redis)

Mavjud `apps/telegramauth/otpstore.py` uslubida, TTL bilan Redis'da saqlanadi
(bazaga yozilmaydi):

- kalit: tasodifiy, taxmin qilib bo'lmaydigan token (Telegram `start` parametri
  cheklovi: 64 belgigacha, faqat `A-Z a-z 0-9 _ -`);
- qiymat: `phone` (normallashgan `+998…`), `purpose` (`register` | `reset`),
  `lang` (ilova tili), `status` (`pending` | `verified` | `mismatch`),
  tasdiqlagan `telegram_id`;
- umri: 10 daqiqa. Muddati o'tgan sessiya `expired` deb hisoblanadi.

### Endpointlar

**`POST /api/v1/auth/telegram/start/`** — `{phone, purpose, lang}` →
`{token, link, expires_in}`. `link` — `https://t.me/<BOT_USERNAME>?start=<token>`.

- `purpose=register` va raqam allaqachon ro'yxatdan o'tgan bo'lsa → `400`,
  `code: "phone_taken"`. Ilova "Bu raqam ro'yxatdan o'tgan — kiring yoki parolni
  tiklang" deydi.
- `purpose=reset` va raqam bo'yicha foydalanuvchi bo'lmasa → `404`, `code: "no_user"`.
- Bir raqamga ketma-ket ko'p sessiya ochishni cheklash kerak (mavjud cooldown
  mexanizmi kabi).

**`GET /api/v1/auth/telegram/status/<token>/`** → `{status}`, bu yerda status
`pending` | `verified` | `mismatch` | `expired`. Token sir: uni faqat shu sessiyani
ochgan ilova biladi. Javobda boshqa shaxsiy ma'lumot qaytmaydi.

**`POST /api/v1/auth/register/`** — endi `verification` (token) majburiy.

- Token `verified`, `purpose=register` va undagi raqam so'rovdagi raqamga teng
  bo'lsa → hisob ochiladi, token ishlatiladi (qayta ishlamaydi), `TelegramAccount`
  shu foydalanuvchiga bog'lanadi.
- `verification` yo'q (eski ilova) → `400`,
  `{code: "update_required", detail: "Ilovaning yangi versiyasini o'rnating."}`.
- Token yaroqsiz, muddati o'tgan yoki raqam mos emas → `400` tegishli `code` bilan.

**`POST /api/v1/auth/send-code/`** `purpose=register` (eski ilova ro'yxatdan
o'tishning 1-qadami) → `400 update_required` xuddi shu matn bilan. Eski ilova bu
matnni (`detail`) ekranda ko'rsatadi (`api/client.ts` → `ApiError.messageFrom`),
shuning uchun foydalanuvchi kod oqimiga kirmasdan darhol "yangilang"ni ko'radi.

**`POST /api/v1/auth/reset-password/`** — yangi tasdiqlash tokenini
(`purpose=reset`) ham qabul qiladi. Eski `send-code`/`verify-code` tokeni bilan
tiklash ham ishlashda davom etadi (do'kondagi eski ilova uchun).

### Parol tiklash va `Student` paroli

Hozir talaba (`billing.Student` yozuvi bor foydalanuvchi) kirganda parol
`Student.password` (ochiq matn) bilan tekshiriladi
(`apps/accounts/serializers.py`, `LoginSerializer`). `reset-password/` esa faqat
`User.password` ni o'zgartiradi — talaba yangi parol bilan kira olmaydi, eski PIN
ishlayveradi. Parol tiklash shu ish ichida buni tuzatishi kerak,
aks holda "Parolni unutdim" talabalarda ishlamaydi. Qanday tuzatilishi — shef
qarori kutilmoqda (pastdagi "Ochiq savol").

Eski `send-code`/`verify-code` tokeni bilan tiklash ham xuddi shu qoidaga
bo'ysunadi (bitta endpoint). *(Quruvchi qarori.)*

### Sozlama

`settings.REGISTER_REQUIRE_TELEGRAM` (standart `True`). Yangi ilova versiyasi
do'kon tekshiruvidan o'tguncha backendni oldindan chiqarish kerak bo'lsa,
vaqtincha `False` qilib eski ro'yxatdan o'tishni ochiq qoldirish mumkin.
*(Quruvchi qarori — shef so'ramagan, deploy tartibini xavfsiz qilish uchun.)*

## Bot (`apps/telegramauth/management/commands/runbot.py`)

**`/start <token>`:**

- Sessiya topilmasa yoki muddati o'tgan bo'lsa: "Havola eskirgan. Ilovaga qaytib,
  qaytadan boshlang."
- Topilsa: til tanlash **so'ralmaydi** — sessiyadagi `lang` ishlatiladi. Bot qisqa
  matn va faqat bitta "📱 Kontaktni ulashish" tugmasini ko'rsatadi. Bu Telegram
  foydalanuvchisi uchun faol token eslab qolinadi (masalan Redis'da
  `telegram_id → token`), shunda kelgan kontakt qaysi sessiyaga tegishli ekani
  ma'lum bo'ladi.

**Kontakt kelganda (faol token bor bo'lsa):**

- `contact.user_id != from_user.id` (o'zining emas, forward qilingan kontakt) →
  rad etiladi (mavjud tekshiruv saqlanadi).
- Raqam sessiyadagi raqamga **teng** → sessiya `verified`, `telegram_id`
  yoziladi. `TelegramAccount` yaratiladi yoki yangilanadi (`verified_at`).
  Javob: "✅ Raqamingiz tasdiqlandi. Ilovaga qayting." Tugmalar yopiladi.
- Raqam **teng emas** → sessiya `mismatch`. Javob, ikkala raqam qisman yashirilgan
  holda:
  "❌ Siz ulashgan raqam (+998 90 ***-45-67) ilovaga kiritilgan raqam
  (+998 91 ***-11-22) bilan mos emas. Ilovaga qaytib, Telegram'dagi raqamingizni
  kiriting."

**`/start` parametrsiz va eski "Kodni olish" tugmasi** — o'zgarmaydi (eski
ilovadagi parol tiklash oqimi shunga tayanadi).

Matnlar uch tilda (`uz`, `kr`, `ru`) — mavjud `telegram.t()` lug'atiga qo'shiladi.
Ilova tili `qq` bo'lsa bot `uz` ishlatadi.

## Mobil ilova (`avtotest-mobile`)

**Ro'yxatdan o'tish (`screens/auth/Register.tsx`):** 2 qadam — ma'lumotlar →
Telegram.

- Alohida "til tanlash" qadami olib tashlanadi; til tanlagich sarlavhada qoladi
  (`AuthShell`ning mavjud til tugmasi). *(Quruvchi qarori — oqimni qisqartirish
  uchun; shef so'rasa qaytariladi.)*
- **Ma'lumotlar qadami:** ism, familiya, telefon, parol, parolni takrorlash
  (o'zgarmaydi). "Davom etish" → `telegram/start`.
- **Telegram qadami:** kiritilgan raqam ko'rsatiladi. Katta "Telegram'da
  tasdiqlash" tugmasi `link`ni ochadi (`Linking.openURL`). Ostida holat matni:
  "Telegram'da «Kontaktni ulashish»ni bosing…".
  - Ekran ochiq turganda ilova holatni ~2 soniyada bir so'raydi. Ilova oldingi
    planga qaytganda (`AppState` → `active`) darhol so'raydi.
  - `verified` → `register(phone, pass, name, verification)` → kirgan holatda
    bosh sahifa.
  - `mismatch` → "Telegram'dagi raqamingiz boshqa. Raqamni o'zgartiring" va
    ma'lumotlar qadamiga qaytish tugmasi.
  - `expired` → "Vaqt tugadi" va "Qaytadan" tugmasi (yangi sessiya).
  - Telegram o'rnatilmagan telefonda `t.me` havolasi brauzerda ochiladi —
    alohida ishlov kerak emas.

**Parolni tiklash (`screens/auth/Forgot.tsx`):** telefon → xuddi shu Telegram
qadami (`purpose=reset`) → yangi parol → `reset-password/`.

**`OtpStep.tsx` va `api/otp.ts`** — yangi oqimda ishlatilmaydi. Qoldirish yoki
o'chirish quruvchi ixtiyorida.

**Yangi tarjima matnlari** — `src/i18n/translations` ga, barcha ilova tillarida.

## Chiqarish tartibi

1. Backend: mehmon va Telegram endpointlari, bot (`REGISTER_REQUIRE_TELEGRAM=False`
   bilan, agar yangi ilova hali do'konda bo'lmasa).
2. Yangi mobil versiya do'konga chiqadi.
3. `REGISTER_REQUIRE_TELEGRAM=True` — eski ilovada "yangilang" chiqa boshlaydi.

Bot (`docker compose --profile bot`) faqat bitta joyda ishlashi kerak — mavjud
cheklov.

## Talaba paroli tiklanganda

`Student.password` 10 belgigacha, ochiq matnda va front-ofis xodimiga ko'rinadi.
Talaba o'zi tanlagan parolni u yerga yozish uni xodimga ko'rsatgan bo'lardi.
Qoida: tiklashda `Student.password` bo'shatiladi va `User.password` (hash)
yangilanadi; `LoginSerializer` `Student.password` bo'sh bo'lsa odatdagi hash
tekshiruviga o'tadi. Xodim keyin yangi PIN bersa, u yana ishlaydi (mavjud signal
`User.password` ni ham yangilaydi). Talaba uchun ham parol qoidasi odatdagidek
(kamida 6 belgi). *(Quruvchi taklifi — shef hali tasdiqlamagan.)*

## Quruvchi qarorlari (shef tekshirishi uchun belgilangan)

- `REGISTER_REQUIRE_TELEGRAM=False` faqat tokensiz eski yo'llarni ochiq
  qoldiradi; token yuborilsa u baribir to'liq tekshiriladi.
- Sessiya `verified` bo'lgandan keyin yana kamida 10 daqiqa yashaydi —
  foydalanuvchi ilovaga kech qaytsa ham `register` muvaffaqiyatsiz bo'lmaydi.
- Telegram raqami `+998` emas bo'lsa (xorijiy raqam), bot uni "mos emas" deb
  ko'rsatadi: "Faqat O'zbekiston raqami bilan ro'yxatdan o'tish mumkin."
- Kutish ekranida bot javob bermasa ham foydalanuvchi qotib qolmaydi: "Havolani
  qayta ochish" va "Raqamni o'zgartirish" tugmalari doim ko'rinadi.

## Quruvchi ixtiyorida

- Token uzunligi va formati (Telegram cheklovi ichida), sessiyalarni cheklash
  sonlari va polling oralig'i.
- Redis kalit nomlari va `telegram_id → token` ni saqlash usuli.
- Bot va ilovadagi aniq matnlar (yuqoridagi mazmunda).
- Testlar: backend `pytest` (sessiya holatlari, mos/mos emas raqam, forward
  kontakt, eski ilova `update_required`, talaba parolini tiklash). Bot
  handlerlari uchun mavjud test uslubiga mos ravishda.
