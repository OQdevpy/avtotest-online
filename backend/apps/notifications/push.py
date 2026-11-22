"""FCM orqali push yuborish (iOS va Android).

Admin xabarni `push_status=pending` qilib qo'yadi; `push_worker` buyrug'i
navbatdagisini `claim_next()` bilan oladi va `deliver()` bilan yuboradi.
Har foydalanuvchiga o'z tilida (`user.language`) boradi.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.lang import CLIENT_TO_DB, DEFAULT_LANG, pick

from .models import Notification, PushDevice

logger = logging.getLogger(__name__)

BATCH = 500  # FCM multicast chegarasi
COLOR = "#ED020A"
CHANNEL = "default"
Status = Notification.PushStatus

_app = None


def is_configured() -> bool:
    path = settings.FIREBASE_CREDENTIALS_FILE
    return bool(path) and os.path.isfile(path)


def _firebase():
    global _app
    if _app is None:
        import firebase_admin
        from firebase_admin import credentials

        _app = firebase_admin.initialize_app(
            credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE), name="push"
        )
    return _app


def _send_multicast(tokens, title, body, data) -> list[tuple[bool, Exception | None]]:
    """Yagona tashqi chaqiruv — testlarda almashtiriladi."""
    import warnings

    from firebase_admin import messaging

    # `tokens` 7.8 da "deprecated" deb ogohlantiradi, lekin aynan qurilma
    # (registration) tokenlari shu yerga beriladi. `fids` — Firebase Installation
    # ID, unga berilsa FCM har tokenni NotRegistered deb qaytaradi.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return _send(messaging, tokens, title, body, data)


def _send(messaging, tokens, title, body, data):
    message = messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(title=title, body=body or None),
        data=data,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(channel_id=CHANNEL, color=COLOR),
        ),
        apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))),
    )
    response = messaging.send_each_for_multicast(message, app=_firebase())
    return [(r.success, r.exception) for r in response.responses]


def _is_invalid_token(exc: Exception | None) -> bool:
    """Token endi yaroqsiz (ilova o'chirilgan, boshqa loyiha, buzuq) — qurilmani o'chiramiz."""
    from firebase_admin import exceptions, messaging

    return isinstance(exc, (messaging.UnregisteredError, messaging.SenderIdMismatchError,
                            exceptions.InvalidArgumentError))


def target_devices(notification: Notification):
    qs = PushDevice.objects.filter(is_active=True).select_related("user")
    if notification.audience == Notification.Audience.SELECTED:
        qs = qs.filter(user__in=notification.recipients.all())
    return qs.filter(user__is_active=True)


def claim_next() -> Notification | None:
    """Navbatdagi xabarni oladi va `sending` qiladi — ikki worker bir xabarni olmaydi."""
    with transaction.atomic():
        n = (Notification.objects.select_for_update(skip_locked=True)
             .filter(push_status=Status.PENDING).order_by("created_at", "pk").first())
        if n is None:
            return None
        n.push_status = Status.SENDING
        n.save(update_fields=["push_status"])
        return n


def deliver(notification: Notification) -> tuple[int, int]:
    """Xabarni qurilmalarga yuboradi; (yetkazildi, xato) qaytaradi va holatni yozadi."""
    sent = failed = 0
    if not is_configured():
        logger.warning("push: FIREBASE_CREDENTIALS_FILE sozlanmagan — #%s yuborilmadi",
                       notification.pk)
        _finish(notification, Status.FAILED, 0, 0)
        return 0, 0

    by_lang: dict[str, list[str]] = defaultdict(list)
    for token, lang in target_devices(notification).values_list("token", "user__language"):
        by_lang[CLIENT_TO_DB.get(lang, DEFAULT_LANG)].append(token)

    data = {"notification_id": str(notification.pk), "kind": notification.kind,
            "screen": "notifications"}
    for lang, tokens in by_lang.items():
        title = pick(notification, "title", lang)
        body = pick(notification, "body", lang)
        for i in range(0, len(tokens), BATCH):
            chunk = tokens[i:i + BATCH]
            try:
                results = _send_multicast(chunk, title, body, data)
            except Exception:  # tarmoq / autentifikatsiya — butun bo'lak xato
                logger.exception("push: #%s bo'lagi yuborilmadi", notification.pk)
                failed += len(chunk)
                continue
            invalid = []
            for token, (ok, exc) in zip(chunk, results):
                if ok:
                    sent += 1
                    continue
                failed += 1
                if _is_invalid_token(exc):
                    invalid.append(token)
            if invalid:
                PushDevice.objects.filter(token__in=invalid).update(
                    is_active=False, last_error="yaroqsiz token (FCM)")

    _finish(notification, Status.DONE, sent, failed)
    logger.info("push: #%s yuborildi — %s ta, xato %s ta", notification.pk, sent, failed)
    return sent, failed


def _finish(notification, status, sent, failed):
    notification.push_status = status
    notification.push_sent = sent
    notification.push_failed = failed
    notification.pushed_at = timezone.now()
    notification.save(update_fields=["push_status", "push_sent", "push_failed", "pushed_at"])


def reset_stuck() -> int:
    """Worker yiqilib qolgan `sending` xabarlarni qayta navbatga qo'yadi (ishga tushganda)."""
    return Notification.objects.filter(push_status=Status.SENDING).update(push_status=Status.PENDING)


def process_pending(limit: int = 10) -> int:
    done = 0
    while done < limit:
        n = claim_next()
        if n is None:
            break
        try:
            deliver(n)
        except Exception:
            logger.exception("push: #%s yuborishda xato", n.pk)
            _finish(n, Status.FAILED, n.push_sent, n.push_failed)
        done += 1
    return done
