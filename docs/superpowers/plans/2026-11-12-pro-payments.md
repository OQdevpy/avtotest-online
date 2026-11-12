# PRO obunani Payme/Click orqali sotish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ro'yxatdan o'tgan foydalanuvchi mobil ilovadan admin'da kiritilgan tariflardan birini Payme yoki Click orqali sotib oladi va PRO shu kunlarga yoqiladi.

**Architecture:** Yangi `apps.payments` Django app: tariflar, shifrlangan provayder sozlamalari (singleton), buyurtma va provayder tranzaksiyalari; ilova uchun `plans/checkout/orders` API va Payme JSON-RPC hamda Click SHOP webhook'lari. PRO berish/qaytarish bitta xizmat modulida, qator qulfi bilan. Mobil ilovada yangi `pro` ekrani havolani `Linking` bilan ochadi va `AppState` qaytganda buyurtma holatini so'raydi.

**Tech Stack:** Django 6, DRF 3.17, `cryptography` (AES-GCM + HKDF), pytest-django; Expo 57 / React Native 0.86 / TypeScript.

**Spec:** `docs/superpowers/specs/2026-11-12-pro-payments-design.md`

## Global Constraints

- Backend repo: `avtotest-online` (branch `feat/pro-payments`); mobil repo: `avtotest/avtotest-mobile` (branch `feat/pro-payments`).
- Kod izohlari va commit xabarlari o'zbekcha (lotin); commit oxirida `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Testlar: `cd backend && py -m pytest` (skretch venv). Baza: 391 passed / 3 skipped — hech biri sinmasligi kerak.
- Narx, kun, merchant ID, kalit kodda yoki ilovada **yo'q** — faqat admin/baza.
- Pul `int` so'mda saqlanadi; Payme bilan tiyin (`so'm * 100`) faqat chegarada.
- Maxfiy kalitlar logga, xato javobiga, Swagger'ga va admin formasiga qaytib chiqmaydi.
- Checkout faqat ro'yxatdan o'tganga (`common.permissions.IsRegistered`); mehmonga `403`, `code: "register_required"`.
- Sotish platforma bo'yicha: `sell_android` (default True), `sell_ios` (default False).
- PRO qo'shish: `pro_until = max(now, pro_until) + days`; `is_pro=True, pro_until=None` (muddatsiz) bo'lsa checkout `400 already_unlimited`.
- Webhook'lar: `AllowAny`, `authentication_classes = ()`, faqat POST, `select_for_update()` + `atomic`.

## Review Focus

- Payme `PerformTransaction` ikki marta ketma-ket kelsa PRO bir marta qo'shiladi → Task 4 testi `test_perform_twice_grants_once`.
- Click `complete` `error=-5017` bilan kelsa PRO berilmaydi, buyurtma `cancelled` → Task 5 testi `test_complete_with_click_error_cancels`.
- Admin tarif narxini o'zgartirsa ochiq buyurtma summasi o'zgarmaydi (Payme eski summa bilan keladi) → Task 4 testi `test_plan_price_change_keeps_order_amount`.
- Kalit o'rnatilmagan/provayder o'chiq bo'lsa checkout 500 emas, `400 provider_unavailable` → Task 3 testi `test_checkout_disabled_provider`.
- Foydalanuvchi o'chirilgan buyurtmaga Payme `CancelTransaction` 500 bermaydi → Task 4 testi `test_cancel_after_user_deleted`.

---

### Task 1: `apps.payments` — modellar, shifrlash, singleton sozlamalar

**Files:**
- Create: `backend/apps/payments/__init__.py`, `apps.py`, `models.py`, `crypto.py`, `migrations/0001_initial.py` (makemigrations)
- Modify: `backend/config/settings.py` (INSTALLED_APPS ga `"apps.payments"`)
- Test: `backend/tests/test_payments_models.py`

**Interfaces:**
- Produces:
  - `crypto.encrypt(plain: str) -> str`, `crypto.decrypt(token: str) -> str` — AES-GCM, kalit `HKDF(SECRET_KEY, info=b"payments-secrets")`, natija base64 (`iv|ct`). Bo'sh satr → bo'sh satr. Buzilgan token → `""` (xato emas).
  - `ProPlan(title_uz, title_ru, title_cry, days: PositiveInt>=1, price: PositiveInt>=1, order, is_active=True)`; ordering `("order","id")`.
  - `PaymentConfig` singleton: `PaymentConfig.get() -> PaymentConfig` (pk=1, yo'q bo'lsa yaratadi). Maydonlar: `sell_android=True`, `sell_ios=False`; `payme_enabled=False`, `payme_test_mode=False`, `payme_merchant_id`, `payme_secret_key_enc`, `payme_test_secret_key_enc`, `payme_allowed_ips` (TextField, vergul/yangi qator bilan CIDR); `click_enabled=False`, `click_service_id`, `click_merchant_id`, `click_merchant_user_id`, `click_secret_key_enc`; `mxik_code`, `package_code`, `vat_percent` (PositiveSmallInt, null).
    Property'lar: `payme_secret_key`, `payme_test_secret_key`, `click_secret_key` (o'qish — decrypt; yozish — encrypt). `payme_ready() -> bool`, `click_ready() -> bool` (enabled va majburiy maydonlar to'la). `allowed_ip_list() -> list[str]`.
  - `ProOrder(user FK SET_NULL null, plan FK PROTECT, title, days, amount, provider ∈ {"payme","click"}, status ∈ {"pending","paid","cancelled","refunded"} default pending, granted_days=0, created_at, paid_at null, cancelled_at null)`. Index `(user, -created_at)`.
  - `ProviderTransaction(order FK CASCADE related_name="transactions", provider, external_id, state: SmallInt, amount: int so'm, create_time, perform_time null, cancel_time null, reason: SmallInt null, extra: JSON default dict)`. `unique_together=(provider, external_id)`. State konstantalari klassda: `CREATED=1, PERFORMED=2, CANCELLED=-1, CANCELLED_AFTER_PERFORM=-2`.

- [ ] **Step 1: Failing testlar** — `test_payments_models.py`:
  - `test_encrypt_roundtrip`: `decrypt(encrypt("k3y"))=="k3y"`, `encrypt("k3y")!="k3y"`, ikki chaqiruv natijasi farq qiladi (tasodifiy iv).
  - `test_decrypt_garbage_returns_empty`: `decrypt("not-a-token")==""`.
  - `test_config_secret_stored_encrypted`: `c=PaymentConfig.get(); c.payme_secret_key="S1"; c.save()`; bazadagi `payme_secret_key_enc` ichida `"S1"` yo'q; `PaymentConfig.get().payme_secret_key=="S1"`.
  - `test_config_singleton`: ikki `get()` bir xil pk=1.
  - `test_ready_flags`: enabled=False → `payme_ready() is False`; enabled + merchant_id + secret → True; click: enabled + service_id + merchant_id + secret → True.
- [ ] **Step 2:** `py -m pytest tests/test_payments_models.py` → FAIL (import xatosi).
- [ ] **Step 3:** Modul va modellarni yozing, `py manage.py makemigrations payments` (`DJANGO_SETTINGS_MODULE=config.settings_test`).
- [ ] **Step 4:** Testlar → PASS; to'liq to'plam → 391+ passed.
- [ ] **Step 5: Commit** — `payments: tarif, shifrlangan provayder sozlamalari, buyurtma modellari`.

### Task 2: Xizmatlar — PRO berish/qaytarish va to'lov havolalari

**Files:**
- Create: `backend/apps/payments/services.py`, `backend/apps/payments/links.py`
- Test: `backend/tests/test_payments_services.py`

**Interfaces:**
- Consumes: Task 1 modellari.
- Produces:
  - `services.grant_pro(order: ProOrder) -> bool` — chaqiruvchi `atomic` ichida, `order` qulflangan. `status=="paid"` bo'lsa `False`. Aks holda `status="paid"`, `paid_at=now`; `order.user` bor bo'lsa user'ni `select_for_update` bilan oladi, `pro_until = max(now, pro_until or now) + timedelta(days=order.days)`, `is_pro=True`, `granted_days=order.days`. Muddatsiz (`is_pro and pro_until is None`) user'ga tegilmaydi, `granted_days=0`. `True` qaytaradi.
  - `services.revoke_pro(order) -> None` — `paid` bo'lsa `status="refunded"`, `cancelled_at=now`; user bor va `pro_until` bor bo'lsa `pro_until -= granted_days`; `pro_until <= now` → `is_pro=False`.
  - `services.cancel_pending(order) -> None` — `pending` → `cancelled`, `cancelled_at=now`.
  - `services.available_providers(config, platform: str) -> list[str]` — platform `"ios"` → `sell_ios`, boshqasi → `sell_android`; o'chiq bo'lsa `[]`; aks holda tartib bilan `["payme","click"]` dan `*_ready()` bo'lganlari.
  - `links.payme_url(order, config, lang: str, return_url: str) -> str` — base `https://test.paycom.uz/` (test_mode) yoki `https://checkout.paycom.uz/`; `base64("m=<merchant_id>;ac.order_id=<id>;a=<amount*100>;l=<uz|ru>;c=<return_url>")`. `lang` `ru` bo'lsa `ru`, aks holda `uz`.
  - `links.click_url(order, config, return_url: str) -> str` — `https://my.click.uz/services/pay?` + urlencode `service_id, merchant_id, amount, transaction_param=<order.id>, return_url`.

- [ ] **Step 1: Failing testlar:**
  - `test_grant_adds_days_from_now`: `pro_until=None,is_pro=False` → grant(15) → `pro_until≈now+15d`, `is_pro`, `granted_days==15`, `status=="paid"`.
  - `test_grant_extends_active_pro`: `pro_until=now+5d` → grant(15) → `≈now+20d`.
  - `test_grant_is_idempotent`: ikkinchi `grant_pro` → `False`, muddat o'zgarmaydi.
  - `test_grant_unlimited_user_untouched`: `is_pro=True,pro_until=None` → `pro_until is None`, `granted_days==0`.
  - `test_revoke_subtracts_and_turns_off`: grant(15) dan keyin revoke → `is_pro False`, `status=="refunded"`; oldin `now+30d` bo'lgan user'da → `≈now+30d`, `is_pro True`.
  - `test_available_providers_platform`: ios + `sell_ios=False` → `[]`; android + faqat click ready → `["click"]`.
  - `test_payme_url_decodes`: base64 dekod → `m=M1;ac.order_id=<id>;a=1500000;l=uz;c=https://x/done/`; test_mode → `https://test.paycom.uz/` bilan boshlanadi.
  - `test_click_url_params`: `parse_qs` → `service_id`, `merchant_id`, `amount=="15000"`, `transaction_param==str(id)`, `return_url`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `services.py`, `links.py` ni yozing.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `payments: PRO berish/qaytarish xizmati va Payme/Click havolalari`.

### Task 3: Ilova API — plans, checkout, order, done sahifasi

**Files:**
- Create: `backend/apps/payments/serializers.py`, `views.py`, `urls.py`, `templates/payments/done.html`
- Modify: `backend/config/urls.py` (`path("payments/", include("apps.payments.urls"))` api_v1 ichida), `backend/config/settings.py` (`DEFAULT_THROTTLE_RATES["payments_checkout"]="20/hour"`)
- Test: `backend/tests/test_payments_api.py`

**Interfaces:**
- Consumes: Task 1–2.
- Produces (ilova shartnomasi, Task 7 shunga tayanadi):
  - `GET /api/v1/payments/plans/?lang=&platform=ios|android` (IsAuthenticated) → `200 {"plans":[{"id","title","days","price"}], "providers":[...]}` — faqat `is_active` tariflar, `title` `common.lang` orqali.
  - `POST /api/v1/payments/checkout/` `{"plan": int, "provider": "payme"|"click", "platform": "ios"|"android"}` (IsRegistered, ScopedRateThrottle `payments_checkout`) → `201 {"order_id","amount","days","provider","payment_url"}`.
    Xatolar `400 {"detail","code"}`: `plan_unavailable` (yo'q/faol emas), `provider_unavailable` (platforma yoki provayder o'chiq/tayyor emas), `already_unlimited`. Mehmon → `403 {"code":"register_required"}`.
    `return_url = request.build_absolute_uri("/api/v1/payments/done/")`; `lang` — `request.user.language`.
  - `GET /api/v1/payments/orders/<id>/` → `{"id","status","days","amount","provider","paid_at","pro_until","pro_active"}`; begona/yo'q → 404.
  - `GET /api/v1/payments/done/` (AllowAny, HTML, uz+ru matn, ma'lumotsiz).

- [ ] **Step 1: Failing testlar:**
  - `test_plans_lists_active_only` (inactive tarif chiqmaydi, `title` ru da `?lang=ru`).
  - `test_plans_ios_hidden_by_default` → `providers==[]`.
  - `test_checkout_creates_order_with_snapshot` → 201, `ProOrder.amount==plan.price`, `days==plan.days`, `payment_url` `https://checkout.paycom.uz/` bilan boshlanadi.
  - `test_checkout_guest_forbidden` → mehmon (`role="guest"`, `phone=guest_phone()`) 403, `code=="register_required"`.
  - `test_checkout_disabled_provider` → click o'chiq → 400 `provider_unavailable`.
  - `test_checkout_inactive_plan` → 400 `plan_unavailable`.
  - `test_checkout_unlimited_user` → 400 `already_unlimited`.
  - `test_checkout_throttled` → 21-so'rov 429.
  - `test_order_detail_owner_only` → begona 404, egasi 200 `status=="pending"`.
  - `test_done_page_public` → 200, `text/html`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Serializer/view/url/template.
- [ ] **Step 4:** Run → PASS; `tests/test_schema.py` ham o'tadi.
- [ ] **Step 5: Commit** — `payments: ilova uchun tariflar, checkout va buyurtma holati API`.

### Task 4: Payme Merchant API webhook

**Files:**
- Create: `backend/apps/payments/payme.py` (view + metodlar + xato konstantalari)
- Modify: `backend/apps/payments/urls.py` (`payme/`)
- Test: `backend/tests/test_payments_payme.py`

**Interfaces:**
- Consumes: Task 1–2 (`grant_pro`, `revoke_pro`, `cancel_pending`, `PaymentConfig.get()`).
- Produces: `POST /api/v1/payments/payme/` — JSON-RPC 2.0, javob doim HTTP 200, `{"jsonrpc":"2.0","id":<req id>,"result"|"error":{code,message:{uz,ru,en},data?}}`.

Qoidalar (spec bo'yicha, aniq qiymatlar):
- Auth: `Authorization: Basic base64("Paycom:<key>")`; key = `payme_secret_key`, `test_mode` da `payme_test_secret_key` ham. `constant_time_compare`. Xato → `-32504`. `payme_enabled` o'chiq ham `-32504`.
- IP: `allowed_ip_list()` bo'sh bo'lmasa `X-Real-IP` (yo'q bo'lsa `REMOTE_ADDR`) CIDR'larda bo'lishi shart, aks holda `-32504`. `X-Forwarded-For` o'qilmaydi.
- Parse xatosi `-32700`, noma'lum metod `-32601`.
- `account.order_id` yo'q/topilmasa `-31050`; summa (`params.amount != order.amount*100`) `-31001`; buyurtma `pending` emas `-31050`.
- `CreateTransaction`: shu buyurtmada boshqa `external_id` li state=1 tranzaksiya bo'lsa `-31099`. Mavjud `external_id` bo'lsa uni qaytaradi (state 1 bo'lsa va 12 soatdan eski — cancel `reason=4`, `-31008`).
- `PerformTransaction`: tranzaksiya yo'q `-31003`; state 2 → mavjud natija; state != 1 `-31008`; 12 soat (`43_200_000` ms) o'tgan → cancel `reason=4`, `-31008`; aks holda `grant_pro`, state 2, `perform_time`.
- `CancelTransaction`: state 1 → state -1, `cancel_pending`; state 2 → state -2, `revoke_pro`; javob `{transaction, cancel_time, state}`. Takror — o'sha natija.
- `CheckTransaction`, `GetStatement` (`from`/`to` ms, `create_time` bo'yicha) — `ProviderTransaction` maydonlaridan; `transaction` = `str(tx.id)`.
- `CheckPerformTransaction` → `{"allow": true}`; `mxik_code` to'la bo'lsa `"detail": {"receipt_type":0,"items":[{"title","price":amount*100,"count":1,"code":mxik,"package_code","vat_percent"}]}`.
- `ChangePassword` → `-32504`.

- [ ] **Step 1: Failing testlar** (yordamchi `rpc(api, method, params, key="S")`):
  - `test_bad_auth` → `-32504`; `test_disabled_provider_rejects` → `-32504`; `test_ip_allowlist` (`allowed_ips="10.0.0.0/8"`, `HTTP_X_REAL_IP="1.2.3.4"` → `-32504`; `"10.1.1.1"` → ok).
  - `test_check_perform_ok_and_wrong_amount` → allow; `-31001`.
  - `test_full_flow_grants_pro` → Check→Create→Perform: `order.status=="paid"`, user `pro_active`, tx state 2.
  - `test_perform_twice_grants_once` → ikkinchi Perform state 2, `pro_until` o'zgarmagan.
  - `test_second_transaction_busy` → boshqa `id` bilan Create → `-31099`.
  - `test_create_timeout` → `create_time` 13 soat oldin → Perform `-31008`, state -1, reason 4.
  - `test_cancel_before_perform` → state -1, order `cancelled`.
  - `test_cancel_after_perform_revokes` → state -2, order `refunded`, user `is_pro False`.
  - `test_cancel_after_user_deleted` → user o'chirilgan (`order.user` None) → state -2, 500 yo'q.
  - `test_plan_price_change_keeps_order_amount` → checkout'dan keyin `plan.price` o'zgartiriladi, Payme eski summa bilan → ok.
  - `test_get_statement_range`, `test_check_transaction_fields`, `test_fiscal_detail_when_mxik_set`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `payme.py` ni yozing; har metod `transaction.atomic()` + `select_for_update()` (order va tx).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `payments: Payme Merchant API webhook (12 soat, band buyurtma, qaytarish)`.

### Task 5: Click SHOP API webhook

**Files:**
- Create: `backend/apps/payments/click.py`
- Modify: `backend/apps/payments/urls.py` (`click/prepare/`, `click/complete/`)
- Test: `backend/tests/test_payments_click.py`

**Interfaces:**
- Consumes: Task 1–2.
- Produces: `POST /api/v1/payments/click/prepare/` va `.../complete/` — form-encoded kirish, JSON javob `{click_trans_id, merchant_trans_id, merchant_prepare_id?, merchant_confirm_id?, error, error_note}` (`error` — int).

Qoidalar:
- Imzo: `md5(click_trans_id + service_id + secret + merchant_trans_id + (merchant_prepare_id faqat action=1) + amount + action + sign_time)`, **xom POST qiymatlari**, `constant_time_compare` → aks holda `-1`. `service_id` admin'dagiga teng bo'lmasa `-1`. `click_enabled` o'chiq → `-1`.
- Majburiy maydon yo'q → `-8`. action noto'g'ri → `-3`.
- Buyurtma (`merchant_trans_id`) yo'q → `-5`; summa `Decimal(amount) != order.amount` → `-2`; `paid` → `-4`; `cancelled/refunded` → `-9`.
- prepare: `ProviderTransaction(provider="click", external_id=click_trans_id, state=1, extra={"click_paydoc_id"})` (bor bo'lsa o'sha), `merchant_prepare_id=tx.id`, `error=0`.
- complete: tx `merchant_prepare_id` bo'yicha va `external_id==click_trans_id`, aks holda `-6`. **POST `error` < 0 → tx state -1, `cancel_pending`, javob `-9`.** Aks holda `grant_pro`, state 2, `merchant_confirm_id=tx.id`, `error=0`; mxik to'la bo'lsa `fiscal_items`.

- [ ] **Step 1: Failing testlar** (yordamchi `signed(data, secret)`):
  - `test_bad_sign` → `-1`; `test_wrong_service_id` → `-1`.
  - `test_prepare_ok` → `error==0`, `merchant_prepare_id`.
  - `test_prepare_wrong_amount` → `-2`; `test_prepare_unknown_order` → `-5`.
  - `test_complete_grants_pro` → order `paid`, user `pro_active`.
  - `test_complete_with_click_error_cancels` → `error=-5017` → javob `-9`, order `cancelled`, `pro_active False`.
  - `test_complete_twice_already_paid` → ikkinchisi `-4`, muddat bir marta qo'shilgan.
  - `test_complete_mismatched_trans_id` → `-6`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `click.py` ni yozing.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `payments: Click Prepare/Complete webhook — Click xatosida PRO berilmaydi`.

### Task 6: Django admin, hujjatlar

**Files:**
- Create: `backend/apps/payments/admin.py`
- Modify: `docs/DEPLOY.md` (5-qadam: `proxy_set_header X-Real-IP $remote_addr;`; merchant kabinetlariga yoziladigan manzillar; `SECRET_KEY` almashsa kalitlar qayta kiritiladi), `README.md` (Endpointlar bo'limiga "To'lovlar")
- Test: `backend/tests/test_payments_admin.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `ProPlanAdmin`: `list_display=("title_uz","days","price","order","is_active")`, `list_editable=("days","price","order","is_active")`.
  - `PaymentConfigAdmin`: faqat superuser (`has_view/change_permission` → `request.user.is_superuser`), qo'shish/o'chirish yo'q, changelist → pk=1 change sahifasiga redirect. Forma: `*_enc` maydonlari yo'q; o'rniga `payme_secret_key`, `payme_test_secret_key`, `click_secret_key` — `PasswordInput(render_value=False)`, bo'sh qoldirilsa eski qiymat saqlanadi, `help_text` da "o'rnatilgan"/"o'rnatilmagan".
  - `ProOrderAdmin`: faqat o'qish (`has_change/add/delete_permission=False`), inline `ProviderTransaction` read-only; `list_filter=("status","provider")`, `search_fields=("user__phone","id")`.

- [ ] **Step 1: Failing testlar** (`client.force_login`):
  - `test_config_hidden_from_staff_admin` → `admin_user` (is_staff, superuser emas) `/admin/payments/paymentconfig/1/change/` → 403.
  - `test_config_form_never_renders_secret` → superuser, secret "TOPSECRET" o'rnatilgan, GET change sahifasi — javobda `TOPSECRET` yo'q.
  - `test_blank_secret_keeps_old` → POST bo'sh secret bilan → `payme_secret_key` o'zgarmagan; yangi qiymat bilan → yangilangan.
  - `test_orders_read_only` → `ProOrder` change POST 403.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `admin.py`, DEPLOY.md, README.md.
- [ ] **Step 4:** Run → PASS; to'liq to'plam.
- [ ] **Step 5: Commit** — `payments: Django admin (kalitlar faqat superuser'ga, maxfiy maydon ko'rinmaydi), hujjat`.

### Task 7: Mobil — PRO ekrani va to'lov oqimi

**Files (mobil repo):**
- Create: `src/api/payments.ts`, `src/screens/Pro.tsx`
- Modify: `src/api/types.ts`, `src/store.tsx` (`Screen` ga `'pro'`, `openPro()`, `refreshUser()`), `src/AppShell.tsx` (`pro: Pro`), `src/components/modals.tsx` (`ProModal` asosiy tugmasi → `closePro(); openPro()`), `src/screens/Home.tsx` (`ProBanner` → `openPro`), `src/screens/Profile.tsx` (PRO qatori: `proUntilText` + `openPro`), `src/i18n/translations.ts` (uz, ru)

**Interfaces:**
- Consumes: Task 3 API shartnomasi.
- Produces:
  - `types.ts`: `ApiProPlan {id:number; title:string; days:number; price:number}`, `ApiPlans {plans: ApiProPlan[]; providers: PayProvider[]}`, `type PayProvider = 'payme'|'click'`, `ApiCheckout {order_id:number; amount:number; days:number; provider:PayProvider; payment_url:string}`, `ApiProOrder {id:number; status:'pending'|'paid'|'cancelled'|'refunded'; days:number; amount:number; provider:PayProvider; paid_at:string|null; pro_until:string|null; pro_active:boolean}`.
  - `payments.ts`: `proPlans(lang): Promise<ApiPlans>`, `checkout(plan:number, provider:PayProvider): Promise<ApiCheckout>`, `proOrder(id:number): Promise<ApiProOrder>`; `platform` — `Platform.OS === 'ios' ? 'ios' : 'android'`.
  - Store: `openPro(): void` (nav `'pro'`), `refreshUser(): Promise<void>` (`api.me()` → `patch({user})`).
  - Mehmon PRO ekranidan ro'yxatdan o'tsa qaytib PRO ekraniga tushadi: store'da `returnTo: Screen | null` — `openAuth` PRO ekranidan chaqirilganda `'pro'` yoziladi, `afterAuth` `screen: returnTo ?? 'home'` qiladi va uni tozalaydi.

Ekran holatlari: `choose` (tariflar kartalari, narx `toLocaleString` + " so'm", tanlangan tarif; providers bo'sh bo'lsa sotib olish bloki ko'rinmaydi, faqat PRO holati) → provayder tugmalari (Payme / Click) → "To'lash" (`isGuest` → `openAuth('register')`) → `checkout` → `Linking.openURL` → `waiting` ("To'lov kutilmoqda", "Tekshirish" tugmasi; `AppState` active'da darhol, so'ng har 3 s, jami 2 daqiqa `proOrder`) → `paid` → `refreshUser()`, muvaffaqiyat + "Davom etish" (`back`) | `cancelled/refunded` → xabar + "Qayta urinish" (`choose`). `ApiError` `code` lar (`register_required`, `provider_unavailable`, `plan_unavailable`, `already_unlimited`) uchun matn.

Yangi matn kalitlari (uz/ru): `pro_title, pro_plans, pro_days, pro_sum, pro_pay_with, pro_pay, pro_waiting, pro_waiting_sub, pro_check, pro_success, pro_success_sub, pro_failed, pro_retry, pro_continue, pro_register_first, pro_unavailable, pro_err_unlimited, pro_active_until`.

- [ ] **Step 1:** API turlari va `payments.ts`.
- [ ] **Step 2:** Store (`'pro'`, `openPro`, `refreshUser`) va `AppShell`.
- [ ] **Step 3:** `Pro.tsx` — mavjud `ScreenScroll`, `Header`, `Card`, `Tap`, `Gradient`, `theme.amber` uslubida.
- [ ] **Step 4:** Kirish nuqtalari (ProModal, Home ProBanner, Profile) va tarjimalar.
- [ ] **Step 5: Tekshirish:** `npx tsc --noEmit` → xatosiz.
- [ ] **Step 6: Commit** (mobil repo) — `mobil: PRO ekrani — tarif tanlash, Payme/Click havolasi, to'lov holatini kutish`.

### Task 8: Lokal ishga tushirish va oxirgi tekshiruv

- [ ] **Step 1:** `docker compose up -d --build` (backend), `docker compose exec backend python manage.py migrate`, `/api/docs/` da `payments` yo'llari ko'rinadi.
- [ ] **Step 2:** Admin'da superuser bilan bitta tarif (15 kun) va test Payme sozlamalari (test_mode) kiritiladi; `curl` bilan `plans/` → tarif va `providers` qaytadi.
- [ ] **Step 3:** Mobil: `EXPO_PUBLIC_API_URL=http://<lokal IP>:9005 npx expo start` — PRO ekrani ochiladi, tariflar chiqadi.
- [ ] **Step 4:** To'liq backend testlari: `py -m pytest` → avvalgi 391 + yangi testlar o'tadi.
