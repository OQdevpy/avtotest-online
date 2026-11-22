# FCM push bildirishnomalar — dizayn

Sana: 2026-11-23 · Branch: `prava777` (backend), `feat/push` (mobil, `feat/telegram-auth` ustidan)

## Maqsad

Shef Django admin'da kerakli foydalanuvchilarni (mehmon ham) tanlab, ularning
telefoniga haqiqiy push bildirishnoma yubora oladi — ilova yopiq bo'lsa ham
keladi. iOS va Android ikkalasi ham FCM orqali.

Hozir: `apps/notifications` faqat ilova ichidagi ro'yxat (hammaga yoki bitta
`user`ga), push yo'q; mobil'da Firebase yo'q.

### Maqsadlar
- Django admin → Foydalanuvchilar ro'yxatida mavjud filtrlar (rol, filial,
  PRO, til, faol) + qidiruv bilan tanlash → "Bildirishnoma yuborish" amali.
  "Hammasini tanlash (N ta)" ham ishlaydi.
- Hammaga yuborish (Bildirishnomalar bo'limidan) ham push bilan.
- Xabar foydalanuvchining tilida (uz / ru / kirill; bo'sh bo'lsa uz).
- Har bir xabar ilova ichidagi ro'yxatda ham turadi (hozirgidek).
- Bosilganda ilovada Bildirishnomalar ekrani ochiladi.
- Admin'da natija: nechta qurilmaga yuborildi, nechta xato.

### Maqsad emas
- Rejalashtirilgan (keyinroq yuboriladigan) xabarlar, takrorlanuvchi kampaniyalar.
- Avtomatik triggerlar (masalan "PRO tugayapti" — keyin alohida qo'shiladi).
- React admin panelidagi sahifa.
- Desktop / web ilovalarga push.

### Anti-maqsad
- Admin "Yuborish" bosganda sahifa minglab foydalanuvchida osilib qolishi.
- Bitta odamga bir xabar ikki marta kelishi.
- Chiqib ketgan (logout) foydalanuvchi telefoniga oldingi hisob xabarlari kelishi.

## Yondashuvlar

- **A. Django admin (tanlandi).** Foydalanuvchilar ro'yxati + amal + oraliq forma.
  Filtrlar va "hammasini tanlash" allaqachon bor, ish kam.
- B. React admin'da alohida sahifa — chiroyliroq, lekin ro'yxat/filtr/API
  noldan, 2–3 barobar ish. Shef A ni tanladi.

Texnika: mobil'da `@react-native-firebase/messaging` (iOS'da ham FCM token
beradi; `expo-notifications` iOS'da faqat APNs token beradi), backend'da
`firebase-admin` (FCM HTTP v1).

## Backend (`apps/notifications`)

### Model o'zgarishlari
`Notification`:
- `audience`: `all` | `selected` (yangi). `user` FK o'rniga `recipients`
  M2M (`User`). Ma'lumot migratsiyasi: `user` bor qatorlar → `selected` +
  `recipients=[user]`, qolganlari → `all`; so'ng `user` olib tashlanadi.
  `visible_to(user)` = `audience=all` YOKI `recipients` ichida.
- Push holati: `push_status` (`none` | `pending` | `sending` | `done` | `failed`),
  `push_sent`, `push_failed` (int), `pushed_at`.

`PushDevice` (yangi):
- `user` FK, `token` (unique), `platform` (`android`/`ios`), `app_version`,
  `is_active`, `created_at`, `updated_at`, `last_error`.

### API (auth talab qilinadi, mehmon ham)
- `POST /api/v1/notifications/devices/` `{token, platform, app_version}` —
  upsert: token boshqa userda bo'lsa joriy userga o'tadi (bitta telefon =
  bitta egasi), `is_active=True`.
- `POST /api/v1/notifications/devices/remove/` `{token}` — logout oldidan;
  faqat o'z tokenini o'chiradi.

### Yuborish
- `apps/notifications/push.py`: Firebase'ni bir marta ishga tushiradi
  (`FIREBASE_CREDENTIALS_FILE` env — service account JSON yo'li).
  Sozlanmagan bo'lsa push o'tkazib yuboriladi (log + `failed`), xabar ro'yxatda qoladi.
- Qabul qiluvchilar: `audience=all` → barcha faol `PushDevice`; `selected` →
  recipients'ning faol qurilmalari. Til bo'yicha guruhlanadi, har guruh 500
  tokenlik `send_each_for_multicast`.
- Payload: `notification` (title/body) + `data` `{notification_id, kind,
  screen: "notifications"}`; Android channel `default`, rang `#ED020A`;
  iOS `sound: default`, badge yo'q.
- `UNREGISTERED` / `INVALID_ARGUMENT` / `SENDER_ID_MISMATCH` → qurilma
  `is_active=False`. Boshqa xatolar faqat sanaladi.
- **Fon jarayoni:** admin faqat `push_status=pending` qo'yadi va darrov
  qaytadi. Yangi `push-worker` compose servisi (`manage.py push_worker`) har
  3 soniyada `pending`ni `select_for_update(skip_locked)` bilan olib
  yuboradi → takror yuborilmaydi. Celery qo'shilmaydi.

### Admin
- `UserAdmin` amali **"Bildirishnoma yuborish"** → oraliq sahifa: tanlanganlar
  soni (shundan nechtasida faol qurilma bor), `kind`, sarlavha va matn
  (uz majburiy, ru/kirill ixtiyoriy) → `selected` Notification + `pending`.
- `NotificationAdmin`: `audience`, recipients (autocomplete), "Push ham
  yuborilsin" belgisi (yangi xabarda default yoqiq); ro'yxatda push holati va
  sonlar; amal "Push'ni qayta yuborish".
- `PushDeviceAdmin`: faqat ko'rish/qidirish (telefon, platforma, faol).
- `UserAdmin` ro'yxatida "Push qurilmasi bor" filtri.

### Testlar
Model migratsiyasi, `visible_to`, device upsert/remove, admin amali
(pending yaratadi), worker (firebase-admin mock: muvaffaqiyat, yaroqsiz
token o'chiriladi, til tanlovi, 500 lik bo'laklar, takror yubormaslik).

## Mobil (`mobil`, versiya 1.3.0 / versionCode 10)

- Paketlar: `@react-native-firebase/app`, `@react-native-firebase/messaging`
  + config plugin'lar; `expo-build-properties` → `ios.useFrameworks: "static"`;
  `app.json`: `android.googleServicesFile`, `ios.googleServicesFile`,
  `POST_NOTIFICATIONS` ruxsati, `UIBackgroundModes: remote-notification`.
  Expo 57 hujjatlari bo'yicha tekshiriladi (AGENTS.md).
- `google-services.json` va `GoogleService-Info.plist` mobil repo'ga
  commit qilinadi (mijoz konfiguratsiyasi, maxfiy emas).
- `src/push.ts`:
  - Ruxsat: bosh sahifa birinchi marta ochilganda bir marta so'raladi
    (splash/login'da emas). Rad etilsa qayta so'ralmaydi.
  - Sessiya (mehmon yoki foydalanuvchi) bo'lganda va `onTokenRefresh`da token
    `devices/` ga yuboriladi.
  - Logout: avval `devices/remove/`, so'ng mehmon sessiyasi ochilgach qayta
    ro'yxatdan o'tadi. Mehmon → o'quvchi (claim) dan keyin ham qayta yuboriladi.
  - Bosish: `getInitialNotification` / `onNotificationOpenedApp` →
    Bildirishnomalar ekrani.
  - Ilova ochiq paytida (`onMessage`): ekran tepasida qisqa toast + badge
    yangilanadi.
- Android bildirishnoma ikonkasi: mavjud monoxrom ikonka, rang `#ED020A`.

## Sozlash (bir marta)
- Firebase loyiha, Android/iOS ilovalar, APNs .p8 Firebase'ga yuklangan,
  FCM API v1 yoqilgan, service account JSON — shef Chrome extension orqali beradi.
- Serverga JSON: `/root/avtotest/firebase/service-account.json`, `.env`:
  `FIREBASE_CREDENTIALS_FILE=/run/secrets/firebase.json` (compose volume).
  Lokal: `~/projects/avtotest/firebase/` (git'dan tashqari).

## Builder'ga qoldirilgan
Toast ko'rinishi, admin oraliq sahifa dizayni, worker log formati,
migratsiya raqamlari.
