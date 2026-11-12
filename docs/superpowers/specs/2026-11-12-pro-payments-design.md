# PRO obunani Payme va Click orqali sotish — dizayn

Sana: 2026-11-12. Qamrov: `avtotest-online/backend` (API, webhook'lar, Django admin)
va mobil ilova (`avtotest/avtotest-mobile`, alohida repo).

## Maqsad

Foydalanuvchi mobil ilovadan PRO obunani pulga sotib oladi. To'lov **Payme** yoki
**Click** orqali: ilova backend'dan tayyor to'lov havolasini oladi, havolani ochadi
(telefonda Payme/Click ilovasi bo'lsa o'sha, bo'lmasa brauzer), foydalanuvchi o'sha
yerda to'laydi, provayder backend'ga webhook yuboradi, backend PRO'ni yoqadi.
Ilovaga qaytganda foydalanuvchi PRO faollashganini ko'radi.

Hozir PRO faqat qo'lda (admin) yoki ro'yxatdan o'tishdagi 12 kunlik sovg'a bilan
beriladi; ilovadagi "PRO'ni ochish" tugmasi hech narsa qilmaydi.

## Shef qarorlari

- **Tariflar bir nechta** bo'ladi — har biri: necha kun va narxi. Hammasi
  **admin paneldan** kiritiladi va o'zgartiriladi (kodda narx yo'q). Birinchi tarif —
  15 kun.
- **Payme va Click kalitlari admin paneldan** kiritiladi (`.env` da emas).
- Havolalar va provayder ma'lumotlari faqat backend'dan keladi — ilovada hech qanday
  merchant ID, kalit yoki narx yozilmaydi.
- Integratsiya xavfsizlik birinchi o'rinda turib quriladi.
- **Faqat ro'yxatdan o'tgan foydalanuvchi to'laydi.** Mehmon tariflarni ko'radi, lekin
  "Sotib olish" bosilganda ro'yxatdan o'tish ekrani ochiladi; ro'yxatdan o'tgach to'lay
  oladi. Backend'da checkout mehmonga `403` (`code: "register_required"`).

## Mening qarorlarim (tekshirib chiqing)

- "Admin panel" — Django admin (`/admin/`). Shefning React `admin/` paneliga
  qo'shilmaydi. Payme/Click kalitlarini faqat **superuser** ko'radi va o'zgartiradi
  (shef hisobi superuser bo'lishi kerak).
- **Hisob o'chirilsa to'lov yozuvlari saqlanadi**: `ProOrder.user` — `SET_NULL`
  (null=True). Webhook'lar foydalanuvchisi yo'q buyurtmaga ham to'g'ri javob beradi
  (`CheckTransaction`, `GetStatement`, `CancelTransaction`), faqat PRO berish/qaytarish
  o'tkazib yuboriladi. Hisobni o'chirish va `prune_devices` avvalgidek ishlaydi.
- **Server va IP:** webhook'lar `https://mobile.avtotest-tayyorlov.uz/api/v1/payments/...`
  ga keladi. Payme IP tekshiruvi `X-Real-IP` ni o'qiydi — tizim nginx'ida
  `proxy_set_header X-Real-IP $remote_addr;` bo'lishi shart; DEPLOY.md 5-qadamiga
  qo'shiladi. `X-Real-IP` yo'q bo'lsa `REMOTE_ADDR` olinadi (`X-Forwarded-For` ga
  ishonilmaydi).
- **PRO tugamagan bo'lsa muddat ustiga qo'shiladi**: `pro_until = max(hozir, pro_until) + kunlar`.
  `is_pro=True` va `pro_until=None` (muddatsiz) foydalanuvchi sotib ololmaydi —
  checkout `400 already_unlimited`.
- **To'lov qaytarilsa (Payme CancelTransaction to'langan tranzaksiyaga) PRO ham
  qaytariladi**: berilgan kunlar `pro_until` dan ayiriladi; natija hozirdan oldin
  bo'lsa — `is_pro=False`.
- Ilovaga qaytish **deep link'siz**: ilova `AppState` "active" bo'lganda va qisqa
  vaqt davomida har bir necha soniyada buyurtma holatini so'raydi (Telegram tasdig'idagi
  mavjud uslub). `return_url` — backend'dagi oddiy "To'lov qabul qilindi, ilovaga
  qayting" sahifasi.
- Mobil UI — alohida **"PRO" ekrani** (tariflar ro'yxati → provayder tanlash → to'lash
  → kutish → natija). Mavjud PRO oynasidagi "PRO'ni ochish" tugmasi, Home'dagi PRO
  banneri va Profil'dagi PRO qatori shu ekranga olib boradi.

## Backend

Yangi app: `apps.payments`.

### Modellar

**`ProPlan`** — tarif. `title_uz/ru/cry`, `days` (musbat butun), `price` (so'm, butun,
> 0), `order`, `is_active`. Admin'da ro'yxat, tartib va yoqish/o'chirish. Faol bo'lmagan
tarif ilovaga chiqmaydi va unga yangi buyurtma ochilmaydi. Seed migratsiyada **yo'q** —
shef o'zi kiritadi (narx kodga tushmasin).

**Provayder sozlamalari** — har provayder uchun bitta yozuv (singleton), admin'da:

- Payme: `is_enabled`, `test_mode`, `merchant_id` (kassa ID), `secret_key`,
  `test_secret_key`, `allowed_ips` (bo'sh — cheklovsiz; CIDR qabul qilinadi).
- Click: `is_enabled`, `service_id`, `merchant_id`, `merchant_user_id`, `secret_key`.
- Ikkalasida ixtiyoriy fiskal maydonlar: `mxik_code` (IKPU), `package_code`,
  `vat_percent`. To'ldirilgan bo'lsa Payme `CheckPerformTransaction` javobiga `detail`
  (chek bandlari), Click `complete` javobiga `fiscal_items` qo'shiladi; bo'sh bo'lsa
  qo'shilmaydi.

Provayder ilovaga va checkout'ga faqat `is_enabled=True` **va** majburiy maydonlari
to'la bo'lsa chiqadi.

**`ProOrder`** — bitta sotib olish urinishi. `user`, `plan` (PROTECT), yaratilgan
paytdagi **nusxa**: `days`, `amount` (so'm), `title`; `provider` (payme/click), `status`
(`pending` / `paid` / `cancelled` / `refunded`), `created_at`, `paid_at`,
`cancelled_at`, `granted_days` (aslida berilgan kunlar — qaytarishda shu ayiriladi).
Tarif narxi keyin o'zgarsa ham ochiq buyurtma summasi o'zgarmaydi.

**`ProviderTransaction`** — provayder tomondagi tranzaksiya. `order` FK, `provider`,
`external_id` (Payme `id` / Click `click_trans_id`; `(provider, external_id)` noyob),
`state`, `amount` (tiyin yoki so'm — bitta tanlanib izchil ishlatilsin), `create_time`,
`perform_time`, `cancel_time`, `reason`, `extra` (JSON: `click_paydoc_id` va h.k.).
Payme `GetStatement` va `CheckTransaction` shu jadvaldan javob beradi.

### Kalitlarni saqlash

- Maxfiy maydonlar (`secret_key`, `test_secret_key`) bazada **shifrlangan** holda
  saqlanadi. Kalit `SECRET_KEY` dan HKDF orqali hosil qilinadi (`common/tunnel.py`
  dagi uslub, `cryptography` allaqachon o'rnatilgan). Usul quruvchi ixtiyorida.
  `SECRET_KEY` almashsa kalitlar admin'dan qayta kiritiladi — DEPLOY.md'ga yozilsin.
- Admin formasida maxfiy maydon **hech qachon qaytarib ko'rsatilmaydi**: "o'rnatilgan /
  o'rnatilmagan" yozuvi va bo'sh qoldirilsa eskisi saqlanadigan parol maydoni.
- Provayder sozlamalari admin'da faqat **superuser** uchun ko'rinadi va tahrirlanadi.
  Tariflar va buyurtmalar — superuser va `role=admin` (`is_staff`) uchun; buyurtmalar
  faqat o'qish (statusni qo'lda o'zgartirib PRO berish yo'q — PRO qo'lda User
  sahifasidan beriladi, avvalgidek).
- Kalitlar logga, xato javoblariga va Swagger'ga chiqmaydi.

### Ilova uchun API

Hammasi `/api/v1/payments/` ostida.

- `GET plans/?lang=` (`IsAuthenticated`, mehmon ham) →
  `{plans: [{id, title, days, price}], providers: ["payme","click"]}`.
- `POST checkout/` (`IsRegistered` — mehmonga `403 register_required`) `{plan, provider}`
  → `{order_id, amount, days, provider, payment_url}`.
  - Tarif faol, provayder yoqilgan bo'lishi shart; aks holda `400` (`code` bilan).
  - Throttle: foydalanuvchiga cheklov (masalan 20/soat) — `DEFAULT_THROTTLE_RATES` ga
    yangi scope.
  - Bitta foydalanuvchining eski `pending` buyurtmalari bekor qilinmaydi (Payme/Click
    sahifasi hali ochiq bo'lishi mumkin); muddati provayder qoidasi bilan tugaydi.
- `GET orders/{id}/` → `{id, status, days, amount, provider, paid_at, pro_until, pro_active}`.
  Faqat **o'z** buyurtmasi — begonasi `404`.

**Havolalar** (faqat backend tuzadi):

- Payme: `https://checkout.paycom.uz/<base64("m=<merchant_id>;ac.order_id=<order.id>;a=<tiyin>;l=<til>;c=<return_url>")>`;
  `test_mode` da `https://test.paycom.uz/`.
- Click: `https://my.click.uz/services/pay?service_id=..&merchant_id=..&amount=..&transaction_param=<order.id>&return_url=<url-encoded>`.

### Webhook'lar

`AllowAny`, `authentication_classes = ()`, faqat `POST`. Manzillar:
`/api/v1/payments/payme/`, `/api/v1/payments/click/prepare/`,
`/api/v1/payments/click/complete/`. nginx'da ular uchun alohida cheklov yo'q.

**Umumiy qoidalar:**

- Har webhook buyurtma va tranzaksiya qatorini `select_for_update()` bilan
  `transaction.atomic()` ichida o'qiydi — bir xabar ikki marta yoki bir vaqtda kelsa
  PRO ikki marta berilmaydi.
- PRO berish va qaytarish bitta xizmat funksiyasida (`grant_pro(order)` /
  `revoke_pro(order)`), idempotent: `paid` buyurtmaga qayta berilmaydi.
- Summa butun sonlarda solishtiriladi (Payme tiyin = `amount * 100`; Click `amount`
  — kasr bo'lishi mumkin, butunga aniq mos kelishi shart).
- Imzo/parol solishtirish `constant_time_compare` bilan.
- Har webhook so'rovi va javobi logga yoziladi (`logging`), `Authorization` va
  imzo maydonlarisiz.

**Payme Merchant API** (JSON-RPC, Basic auth `Paycom:<key>`; `test_mode` da test
kaliti ham qabul qilinadi; `allowed_ips` to'ldirilgan bo'lsa IP tekshiriladi —
IP `X-Real-IP` dan, nginx o'rnatgan). Barcha metodlar spetsifikatsiya bo'yicha:

- `CheckPerformTransaction` — buyurtma bor, `pending`, summa mos → `allow: true`
  (+ fiskal `detail`).
- `CreateTransaction` — bir buyurtmada faqat **bitta** faol Payme tranzaksiyasi;
  boshqa `id` bilan kelsa `-31099` ("buyurtma band"). 12 soatdan eski tranzaksiya
  `CreateTransaction`/`PerformTransaction` da `-31008` bilan rad etiladi va
  `reason=4` bilan bekor qilinadi.
- `PerformTransaction` — PRO beriladi, buyurtma `paid`. Takror chaqiruv o'sha
  natijani qaytaradi.
- `CancelTransaction` — to'lanmagan bo'lsa state `-1`, buyurtma `cancelled`;
  to'langan bo'lsa state `-2`, `revoke_pro`, buyurtma `refunded`.
- `CheckTransaction`, `GetStatement` — `ProviderTransaction` dan.
- `ChangePassword` — `-32504` (kalit faqat admin'dan o'zgaradi).

**Click SHOP API** (form-encoded, md5 `sign_string`):

- Imzo tekshiriladi va `service_id` admin'dagisiga teng bo'lishi shart.
- `prepare` (action=0): buyurtma bor, `pending`, summa mos → `merchant_prepare_id`
  (tranzaksiya yozuvi id) qaytadi.
- `complete` (action=1): Click yuborgan **`error` < 0 bo'lsa to'lov o'tmagan** —
  tranzaksiya va buyurtma bekor qilinadi, PRO **berilmaydi**, javob `-9`.
  `error = 0` bo'lsa `merchant_prepare_id` va `click_trans_id` mosligi tekshiriladi,
  PRO beriladi. Takror `complete` → `-4` "Already paid".
- Xato kodlari Click hujjatidagidek (`-1` imzo, `-2` summa, `-4` to'langan, `-5`
  buyurtma yo'q, `-6` tranzaksiya yo'q, `-8` so'rov xatosi, `-9` bekor qilingan).

### return_url sahifasi

`GET /api/v1/payments/done/` (`AllowAny`) — oddiy HTML (uz/ru), "To'lov qabul
qilindi. Ilovaga qayting." Hech qanday holat yoki ma'lumot ko'rsatmaydi (havola ochiq —
kim ochishi mumkin). `/api/` ostida — mavjud nginx sozlamalari o'zgarmasdan ishlaydi.

### Testlar

`backend/tests/` ga: checkout (faol emas tarif, o'chiq provayder, begona buyurtma
404, throttle), Payme to'liq oqimi va har xato kodi, 12 soat timeout, ikki
tranzaksiya — "band", to'langandan keyin cancel → PRO qaytadi, Click prepare/complete,
`error<0` → PRO yo'q, takror complete, noto'g'ri imzo, PRO muddat ustiga qo'shilishi,
mehmon checkout → 403, foydalanuvchisi o'chirilgan buyurtmaga webhook, kalit admin
formasida ko'rinmaydi. Mavjud 391 test o'tishda davom etadi.

## Mobil ilova

- **API:** `src/api/payments.ts` — `plans(lang)`, `checkout(plan, provider)`,
  `order(id)`; turlar `types.ts` ga.
- **Ekran `pro`:**
  1. Tariflar ro'yxati (nomi, kunlar, narxi — so'm formatida). PRO faol bo'lsa
     tepada "Amal qiladi: <sana>" va "uzaytirish" ma'nosidagi matn.
  2. Provayder tanlash — Payme va Click (faqat backend qaytarganlari).
  3. "To'lash" → `checkout` → `Linking.openURL(payment_url)`.
  4. Kutish holati: "To'lov kutilmoqda". `AppState` "active" bo'lganda darhol, keyin
     har ~3 soniyada ~2 daqiqa `order(id)` so'raladi; "Tekshirish" tugmasi ham bor.
  5. `paid` → `me()` qayta olinadi (store'dagi `user` yangilanadi, qulflar ochiladi),
     muvaffaqiyat ko'rinishi. `cancelled` → xabar va qaytadan urinish.
- **Mehmon:** tariflarni ko'radi; "Sotib olish" → `openAuth('register')`. Ro'yxatdan
  o'tgach PRO ekraniga qaytadi.
- **Kirish nuqtalari:** `ProModal` dagi asosiy tugma (hozir faqat yopadi), Home PRO
  banneri, Profil PRO qatori → `pro` ekrani.
- **Store:** `refreshUser()` — `me()` ni chaqirib `user` ni yangilaydi.
- **Matnlar:** `translations.ts` — uz va ru (kr/qq mavjud uslubda hosil bo'ladi).
- Ilovada hech qanday merchant ID, kalit, narx yoki havola shabloni yo'q.
- `app.json` ga yangi ruxsat yoki deep link sxemasi qo'shilmaydi.

## Maqsad emas

- Avtomatik obuna yangilanishi (recurring), saqlangan karta bilan to'lash.
- Promokod, chegirma.
- Web/desktop frontlarda sotish.
- Shefning React `admin/` panelida tarif yoki kalit tahrirlash.

## Muvaffaqiyatsizlik deb hisoblanadi (texnik ishlasa ham)

- Pul tushmagan holda PRO ochilishi (mm_academy'dagi Click `error` xatosi).
- Bitta to'lov uchun PRO ikki marta berilishi.
- Kalitlarning admin sahifasida, logda yoki API javobida ochiq ko'rinishi.
- Begona foydalanuvchi buyurtmasini ko'rish yoki uning nomidan to'lash.
- Ilovada narx yoki merchant ma'lumotining qattiq yozilishi.

## Quruvchi ixtiyorida

- Modellar va maydonlarning aniq nomlari, singleton'ni qanday amalga oshirish.
- Shifrlash usuli (HKDF + AES-GCM yoki Fernet).
- Summani tiyinda yoki so'mda saqlash (izchil bo'lsa).
- Kutish holatidagi so'rov oralig'i va davomiyligi.
- PRO ekranining ko'rinishi — mavjud dizayn tili (ranglar, `Card`, `Gradient`) asosida.
