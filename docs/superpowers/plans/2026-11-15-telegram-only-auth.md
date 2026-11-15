# Faqat Telegram orqali kirish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parol bilan kirish butunlay yo'qoladi: mobil ilovada faqat mehmon rejimi va bitta "Telegram orqali kirish" (kirish = ro'yxatdan o'tish), React admin panel ham Telegram orqali; `qq` tili olib tashlanadi.

**Architecture:** Mavjud Redis'dagi Telegram tasdiqlash sessiyasiga yangi `auth` maqsadi qo'shiladi — raqamsiz ochiladi, bot kontaktdan raqam va ismni yozadi. Yangi `auth/telegram/claim/` tasdiqlangan sessiyani bir marta tokenlarga almashtiradi (topadi yoki yaratadi, mehmonni aylantiradi). Parol yo'llari `400 update_required` qaytaradi.

**Tech Stack:** Django 6, DRF, Redis, python-telegram-bot, pytest-django; Expo 57 / RN 0.86 / TS; React + Vite (admin).

**Spec:** `docs/superpowers/specs/2026-11-15-telegram-only-auth-design.md`

## Global Constraints

- Backend repo `avtotest-online`, mobil repo `avtotest/avtotest-mobile` — ikkalasida branch `feat/telegram-auth` (`feat/pro-payments` dan).
- Izoh va commit xabarlari o'zbekcha (lotin); commit oxirida `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Testlar: `cd backend && <venv>/python -m pytest -q -p no:cacheprovider` (`DJANGO_SETTINGS_MODULE=config.settings_test`).
- Yopilgan yo'llar javobi aynan: `400 {"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}`.
- Desktop/web kirish kodi (`login-code/`), `guest/`, `token/refresh/`, `logout/`, `me/`, `devices/` o'zgarmaydi. Django admin paroli qoladi.
- Raqam faqat `+998XXXXXXXXX`; kontakt faqat yuboruvchining o'ziniki.
- `?lang=qq`, `Accept-Language: qq`, `language="qq"` — xatosiz `uz` deb qabul qilinadi.

## Review Focus

- Bitta tasdiqlangan token bilan `claim` ikki marta (parallel) → ikkinchisi `400 verification_invalid` → Task 2 `test_claim_single_use`.
- Raqami bazada bor o'quvchi `guest_refresh` bilan kirsa yangi hisob ochilmaydi, mehmon ma'lumoti ko'chmaydi → Task 2 `test_claim_existing_with_guest_refresh`.
- Avtomaktab bloklagan talaba (`Student.is_active=False`) → `403 blocked`, token berilmaydi → Task 2 `test_claim_blocked_student`.
- Tasdiqlanmagan (`pending`) yoki `mismatch` sessiya bilan `claim` → 400 → Task 2 `test_claim_not_verified`.
- Eski ilova `PATCH auth/me/ {language:"qq"}` → 200, `language=="uz"` → Task 4 `test_patch_language_qq_maps_to_uz`.

---

### Task 1: `auth` sessiyasi va bot

**Files:**
- Modify: `backend/apps/telegramauth/models.py` (`Purpose` → faqat `AUTH = "auth"`), `verification.py`, `serializers.py` (`TelegramStartSerializer`), `views.py` (`TelegramStartView`), `management/commands/runbot.py` (`on_app_contact`), `telegram.py` (matn kaliti `auth_done` uz/kr/ru)
- Test: `backend/tests/test_telegram_verification.py` (qayta yoziladi)

**Interfaces:**
- Produces:
  - `verification.start_session(phone: str | None, purpose: str, lang: str, ip: str = "") -> str` — `auth` da `phone=None`; cheklov kaliti `tgv:count:ip:<ip>` (ip bo'sh bo'lsa `tgv:count:ip:-`). `MAX_SESSIONS=5`/600 s saqlanadi.
  - Sessiya JSON: `{phone, purpose, lang, status, telegram_id, full_name}`.
  - `verification.resolve_contact(token, shared_raw, telegram_id, full_name: str = "") -> (outcome, session_phone, shared_phone)` — `purpose=="auth"` bo'lsa solishtirmaydi: `+998` bo'lsa sessiyaga `phone=shared`, `full_name` yoziladi, `verified`; aks holda `foreign` (holat `mismatch`).
  - `verification.consume_auth(token: str) -> dict | None` — `verified` + `purpose=="auth"` sessiyani o'chirib qaytaradi (Redis `delete()==1` bo'lgandagina), aks holda `None`.
  - `POST auth/telegram/start/` `{lang?}` (`purpose` ixtiyoriy, default `auth`; `phone` kerak emas) → `{token, link, expires_in}`; IP `X-Real-IP` → `REMOTE_ADDR`.
  - `GET auth/telegram/status/<token>/` o'zgarmaydi.

- [ ] **Step 1: Failing testlar** (`fake_redis` fixture):
  - `test_start_without_phone` → 200, `link` `https://t.me/` bilan, sessiya `purpose=="auth"`, `phone is None`.
  - `test_start_rate_limited_by_ip` → bir IP dan 6-chi so'rov 429 `too_many`.
  - `test_auth_contact_verifies_and_stores_phone` → `resolve_contact(tok, "998901234567", 7, "Ali Valiyev")` → `("verified", ...)`, sessiyada `phone=="+998901234567"`, `full_name=="Ali Valiyev"`, `status_of(tok)=="verified"`.
  - `test_auth_contact_foreign` → `"+79001234567"` → `foreign`, status `mismatch`.
  - `test_consume_auth_once` → birinchi `consume_auth` dict, ikkinchisi `None`; `pending` sessiya → `None`.
  - Mavjud `test_mask_phone`, `test_chat_binding`, `test_resolve_contact_expired` saqlanadi.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement; botda `on_app_contact` `resolve_contact(..., full_name=from_user.full_name)` chaqiradi, `verified` → `tg.t("auth_done", lang)` ("Tasdiqlandi ✅ Ilovaga qayting.") + «Ilovaga qaytish» tugmasi; `mismatch` matni endi kerak emas.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `telegram: raqamsiz kirish sessiyasi — bot kontaktdan raqam va ismni oladi`.

### Task 2: `auth/telegram/claim/` — topish yoki yaratish

**Files:**
- Create: `backend/apps/telegramauth/claim.py`
- Modify: `backend/apps/telegramauth/views.py` (`TelegramClaimView`), `urls.py` (`telegram/claim/`), `serializers.py` (`TelegramClaimSerializer`)
- Test: `backend/tests/test_telegram_claim.py`

**Interfaces:**
- Consumes: `verification.consume_auth`, `accounts.serializers.guest_from_refresh`, `issue_tokens`, `UserSerializer`, `accounts.views.auth_response`.
- Produces:
  - `claim.user_for_phone(phone: str, full_name: str, lang: str, guest_refresh: str = "") -> tuple[User, bool]` — `transaction.atomic`; mavjud (mehmon emas) → `(user, False)` va `guest_refresh` mehmonining faol `Device` lari yopiladi; yo'q → mehmon aylanadi yoki yangi `User` (`set_unusable_password`, `role=student`, `language=lang`), `is_pro=True`, `pro_until=now+12 kun`, `TelegramAccount(phone=..., user__isnull=True)` bog'lanadi → `(user, True)`.
  - `claim.is_blocked(user) -> bool` — `not user.is_active` yoki `Student.objects.filter(user=user, is_active=False).exists()`.
  - `POST auth/telegram/claim/` `{token, guest_refresh?, platform?, device_label?}` → yangi: `201 {user, tokens, created: true}`; mavjud: `200 {..., created: false}`; xato: `400 verification_invalid` (mavjud `VERIFICATION_INVALID` matni), `403 {"code":"blocked","detail":"Hisob bloklangan."}`, device limiti `403` (mavjud xabar).
  - Bloklangan holatda sessiya baribir ishlatilgan (consume) bo'ladi.

- [ ] **Step 1: Failing testlar** (yordamchi `verified_token(phone, name="Ali Valiyev")` — `start_session` + `resolve_contact`):
  - `test_claim_creates_student` → 201, `created is True`, `role=="student"`, `full_name=="Ali Valiyev"`, `pro_active`, `has_usable_password() is False`.
  - `test_claim_existing_user_logs_in` → `student` fixture raqami bilan → 200, `user.id==student.id`, `User` soni o'zgarmaydi.
  - `test_claim_converts_guest_keeps_progress` → mehmon + `SavedQuestion` → `guest_refresh` bilan claim → o'sha `user.id`, `role=="student"`, saqlangan savol joyida.
  - `test_claim_converts_expired_guest` → mehmon `Device.expires_at` o'tgan → baribir aylanadi.
  - `test_claim_existing_with_guest_refresh` → mavjud raqam + mehmon refresh → `student` ga kiradi, mehmon `Device` lari `is_active=False`, mehmon `role=="guest"` qoladi.
  - `test_claim_blocked_user` (`is_active=False`) va `test_claim_blocked_student` (`Student.is_active=False`) → 403 `blocked`, javobda `tokens` yo'q.
  - `test_claim_single_use` → ikkinchi claim 400 `verification_invalid`.
  - `test_claim_not_verified` → `pending` token 400; `mismatch` token 400.
  - `test_claim_links_telegram_account` → `TelegramAccount(telegram_id=7, phone=...)` `user` bilan bog'lanadi.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `auth: telegram/claim — kontakt raqami bo'yicha kirish yoki hisob ochish`.

### Task 3: Parol yo'llarini yopish

**Files:**
- Modify: `backend/apps/accounts/urls.py`, `views.py` (`RegisterView`, `LoginView`, `SocialLoginView`, `ChangePasswordView` o'chiriladi; `UpdateRequiredView` qo'shiladi), `serializers.py` (`RegisterSerializer`, `LoginSerializer`, `SocialLoginSerializer`, `ChangePasswordSerializer` o'chiriladi; `guest_from_refresh` qoladi), `apps/telegramauth/urls.py`, `views.py` (`SendCodeView`, `VerifyCodeView`, `ResetPasswordView` o'chiriladi), `serializers.py`, `backend/config/settings.py` (`REGISTER_REQUIRE_TELEGRAM` o'chiriladi), `common/tunnel.py` agar `auth/login/` ro'yxatida bo'lsa
- Delete: `backend/apps/accounts/social.py` (agar boshqa joyda ishlatilmasa), `backend/tests/test_register_telegram.py`, `test_md5_upgrade.py`, `test_social_auth.py`
- Modify tests: `test_devices.py`, `test_access_codes.py`, `test_guest.py`, `test_review_fixes.py`, `test_review_guest_fixes.py`, `test_student_signal.py`, `test_schema.py`, `test_tunnel.py` — parol bilan login o'rniga `issue_tokens(user, platform=...)` yoki claim yordamchisi; parolga xos testlar o'chiriladi
- Test: `backend/tests/test_auth_closed.py`

**Interfaces:**
- Produces: `UpdateRequiredView` (AllowAny, `authentication_classes=()`, POST) → `400 UPDATE_REQUIRED` (mavjud konstanta). Yo'llar va URL nomlari saqlanadi: `register`, `login`, `social-login`, `change-password`, `send-code`, `verify-code`, `reset-password`.

- [ ] **Step 1: Failing test** `test_auth_closed.py`: parametrlangan — 7 yo'lning har biriga POST (tokensiz va token bilan) → 400, `code=="update_required"`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement va testlarni moslang.
- [ ] **Step 4:** To'liq to'plam → PASS.
- [ ] **Step 5: Commit** — `auth: parol, ijtimoiy kirish va OTP yo'llari yopildi — update_required`.

### Task 4: Qoraqalpoq tili olib tashlanadi

**Files:**
- Modify: `backend/apps/accounts/models.py` (`Language.QQ` o'chadi), `serializers.py` (`LanguageField`), `common/lang.py` (docstring; `CLIENT_TO_DB["qq"]="uz"` eski ilova uchun qoladi), `apps/telegramauth/telegram.py`, `models.py` (docstring), `apps/content/views.py` (Swagger tavsifi `uz | kr | ru`)
- Create: `backend/apps/accounts/migrations/0008_language_qq_to_uz.py` (`RunPython` qq→uz + `AlterField` choices)
- Test: `backend/tests/test_lang_qq.py`

**Interfaces:**
- Produces: `accounts.serializers.LanguageField(serializers.ChoiceField)` — `to_internal_value("qq") -> "uz"`; `UserSerializer.language`, `GuestSerializer.lang`, `TelegramStartSerializer.lang`, `TelegramClaimSerializer` (yo'q — til sessiyadan) shu maydonni ishlatadi.

- [ ] **Step 1: Failing testlar:** `test_patch_language_qq_maps_to_uz`; `test_guest_lang_qq` (`auth/guest/` `lang:"qq"` → 201, `language=="uz"`); `test_content_lang_qq_is_uz` (`?lang=qq` → uz matni); `test_language_choices_no_qq` (`"qq" not in User.Language.values`); `test_migration_moves_qq` (migratsiya funksiyasi `language="qq"` qatorni `uz` qiladi).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement, `makemigrations` + RunPython.
- [ ] **Step 4:** To'liq to'plam → PASS.
- [ ] **Step 5: Commit** — `til: qoraqalpoq (qq) olib tashlandi, eski ilovadan kelgani uz deb o'qiladi`.

### Task 5: Mobil — Telegram kirish ekrani, parolsiz, `qq` siz

**Files (mobil repo):**
- Modify: `src/api/telegram.ts` (`startAuth(lang)`, `claim(token, guestRefresh)`), `src/api/index.ts` (`login`, `register` o'chadi), `src/api/types.ts` (`ClaimResponse = AuthResponse & {created: boolean}`), `src/store.tsx`, `src/screens/Login.tsx`, `src/screens/auth/TelegramStep.tsx`, `src/screens/GuestExpired.tsx`, `src/screens/Profile.tsx`, `src/screens/Home.tsx`, `src/screens/Pro.tsx`, `src/i18n/translations.ts`
- Delete: `src/screens/auth/Register.tsx`, `src/screens/auth/Forgot.tsx`, `src/api/otp.ts`

**Interfaces:**
- Consumes: Task 1–2 endpointlari.
- Produces (store): `telegramLogin(token: string): Promise<void>` (claim + `markHadSession` + `afterAuth`), `openAuth(): void` (argumentsiz); `AuthView`, `login`, `register` o'chadi. `LangCode = 'uz' | 'kr' | 'ru'`; saqlangan `qq` → `uz`.
- UI: `Login` — logo/`AuthShell`, `t.login_welcome`, `Notice` (guestFailed), `PrimaryBtn` `t.tg_login` → `TelegramStep` (raqamsiz: `onVerified(token)`, `onCancel`), ostida `t.tg_login_hint`. `TelegramStep` dan `phone`, `display`, `purpose`, "raqamni o'zgartirish" olib tashlanadi; `mismatch` → `t.tg_foreign` + "Qayta urinish".
- Tarjimalar (uz/kr/ru): `tg_login` "Telegram orqali kirish", `tg_login_hint` "Telegram'da kontaktingizni yuboring — raqamingiz shu orqali tasdiqlanadi", `tg_foreign` "Faqat O'zbekiston raqami (+998) qabul qilinadi"; ishlatilmay qolgan kalitlar (`login_pass*`, `login_forgot`, `reg_*`, `err_pass*`, `forgot_*` va h.k.) o'chiriladi; `err_blocked` "Hisob bloklangan" qo'shiladi.

- [ ] **Step 1:** API va turlar.
- [ ] **Step 2:** Store va kirish nuqtalari (Home banner, Profile, GuestExpired — bitta tugma `t.tg_login`; Pro — mehmon `openAuth()`).
- [ ] **Step 3:** `Login.tsx`, `TelegramStep.tsx`, eski ekranlarni o'chirish.
- [ ] **Step 4:** Tarjimalar va `qq`.
- [ ] **Step 5:** `npx tsc --noEmit` → xatosiz.
- [ ] **Step 6: Commit** (mobil repo) — `mobil: faqat mehmon va Telegram orqali kirish, parol va qq olib tashlandi`.

### Task 6: React admin panel — Telegram orqali kirish

**Files:**
- Modify: `admin/src/services/api.js` (`login` o'rniga `startTelegram()`, `telegramStatus(token)`, `claimTelegram(token)`), `admin/src/context/AuthContext.jsx`, `admin/src/pages/Login.jsx`, `admin/package.json` (`qrcode.react`)

**Interfaces:**
- `claimTelegram` `{token, platform:"web", device_label:"Admin Panel"}`; `user.role !== "admin"` → tokenlar tozalanadi, xato "Bu panel faqat shef uchun".
- Login sahifasi: "Telegram orqali kirish" → `start`; havola yangi oynada + QR (`QRCodeSVG value={link}`); har 2 s `status`; `verified` → claim → bosh sahifa; `expired` → "Qayta urinish".

- [ ] **Step 1:** Implement.
- [ ] **Step 2:** `npm run build` → xatosiz; `npx eslint src` yangi xatosiz.
- [ ] **Step 3: Commit** — `admin: Telegram orqali kirish (havola va QR), parol olib tashlandi`.

### Task 7: Hujjatlar va lokal tekshiruv

**Files:** `README.md` (Autentifikatsiya bo'limi), `docs/DEPLOY.md` (1-bo'lim: eski ilova parol bilan kira olmaydi; `qq`)

- [ ] **Step 1:** Hujjatlarni yangilash.
- [ ] **Step 2:** To'liq backend to'plami → PASS.
- [ ] **Step 3:** `docker compose --profile bot up -d --build`; Metro (`EXPO_PUBLIC_API_URL=http://10.0.2.2:9005`) emulyatorda: kirish ekranida faqat Telegram tugmasi va til ro'yxatida 3 til; `curl` bilan start → bot → claim oqimi.
- [ ] **Step 4: Commit** — `docs: faqat Telegram orqali kirish`.
