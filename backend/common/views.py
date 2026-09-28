"""Oddiy statik sahifalar (maxfiylik siyosati) — App Store/Play talab qiladi."""

from django.http import HttpResponse
from django.views.decorators.cache import cache_control

_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privacy Policy — Avtotest Tayyorlov</title>
<style>
  body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.6;
       max-width:760px;margin:0 auto;padding:28px 20px;color:#1b1a17;background:#fff}
  h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:26px 0 8px}
  .muted{color:#6b6b6b;font-size:14px;margin-bottom:18px}
  ul{padding-left:20px} li{margin:4px 0} a{color:#12885B}
  hr{border:none;border-top:1px solid #eee;margin:28px 0}
</style>
</head>
<body>
<h1>Privacy Policy</h1>
<div class="muted">Avtotest Tayyorlov &middot; Last updated: 2026-09-06</div>

<p>This Privacy Policy explains how the <strong>Avtotest Tayyorlov</strong> mobile
application ("the App") collects, uses, and protects your information. By using the
App you agree to this policy.</p>

<h2>Information we collect</h2>
<ul>
  <li><strong>Account data:</strong> phone number, full name, and password (stored
      only as a secure hash).</li>
  <li><strong>Telegram data:</strong> your Telegram ID and phone number, used only to
      deliver 6-digit verification codes for registration and password reset via our
      Telegram bot (@AvtotestTayyorlovBot). You link it voluntarily by sharing your
      contact in the bot.</li>
  <li><strong>Learning progress:</strong> lesson/exam/ticket results, mistakes, saved
      questions, statistics, language and theme preferences.</li>
</ul>
<p>We do <strong>not</strong> collect location, camera, microphone, contacts, or
advertising identifiers. The App contains no third-party advertising or tracking SDKs.</p>

<h2>How we use it</h2>
<ul>
  <li>To create and secure your account and authenticate you.</li>
  <li>To deliver one-time verification codes via Telegram.</li>
  <li>To save and show your learning progress and statistics.</li>
</ul>

<h2>Sharing</h2>
<p>We do <strong>not</strong> sell or rent your personal data. Verification codes are
delivered through Telegram (Telegram LLC) solely to reach the account you linked. We
may disclose information if required by law.</p>

<h2>Data storage &amp; security</h2>
<p>Data is stored on our secured server. Passwords are hashed. One-time codes are kept
in temporary storage (Redis) and expire within minutes. Traffic is encrypted (HTTPS).</p>

<h2>Data retention &amp; deletion</h2>
<p>We keep account data while your account is active. You may request deletion of your
account and associated data by contacting us at the email below; we will remove it
within a reasonable period.</p>

<h2>Children</h2>
<p>The App is intended for users preparing for a driver's license exam and is not
directed at children under 13.</p>

<h2>Changes</h2>
<p>We may update this policy; the "Last updated" date reflects the latest version.</p>

<h2>Contact</h2>
<p>Questions or deletion requests: <a href="mailto:oqdevpy@gmail.com">oqdevpy@gmail.com</a></p>

<hr>

<h1>Maxfiylik siyosati (o'zbekcha)</h1>
<p><strong>Avtotest Tayyorlov</strong> ilovasi qanday ma'lumot yig'ishi va ishlatishi.</p>
<h2>Yig'iladigan ma'lumot</h2>
<ul>
  <li><strong>Hisob:</strong> telefon raqami, ism, parol (faqat xavfsiz hash ko'rinishida).</li>
  <li><strong>Telegram:</strong> Telegram ID va raqamingiz — faqat ro'yxatdan o'tish va
      parolni tiklash uchun 6 xonali kodni @AvtotestTayyorlovBot orqali yuborishga. Siz
      buni botda kontakt ulashish orqali ixtiyoriy bog'laysiz.</li>
  <li><strong>O'quv jarayoni:</strong> dars/imtihon/bilet natijalari, xatolar, saqlangan
      savollar, statistika, til va mavzu sozlamalari.</li>
</ul>
<p>Joylashuv, kamera, mikrofon, kontaktlar yoki reklama identifikatorlari
<strong>yig'ilmaydi</strong>. Reklama/kuzatuv SDK'lari yo'q.</p>
<h2>Ishlatilishi</h2>
<p>Hisobni yaratish/himoyalash va kirish; Telegram orqali tasdiqlash kodi; o'quv
jarayonini saqlash va ko'rsatish.</p>
<h2>Ulashish</h2>
<p>Ma'lumotingiz <strong>sotilmaydi</strong>. Kodlar faqat siz bog'lagan hisobga yetkazish
uchun Telegram orqali yuboriladi. Qonun talab qilsa oshkor qilinishi mumkin.</p>
<h2>Saqlash va o'chirish</h2>
<p>Hisob faol bo'lganda saqlanadi. O'chirishni so'rash uchun yuqoridagi elektron
pochtaga yozing.</p>
<h2>Aloqa</h2>
<p><a href="mailto:oqdevpy@gmail.com">oqdevpy@gmail.com</a></p>
</body>
</html>"""


@cache_control(public=True, max_age=3600)
def privacy_policy(request):
    return HttpResponse(_PRIVACY_HTML, content_type="text/html; charset=utf-8")
