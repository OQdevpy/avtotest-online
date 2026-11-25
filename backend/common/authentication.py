"""JWT autentifikatsiyasi + kirish kodi va mehmon sessiyasining tirikligi.

Kirish kodi va mehmon tokenlarida `did` (Device pk) bor. Shef kodni nofaol
qilsa yoki kompyuter bog'lanishini bekor qilsa `Device.is_active=False`
bo'ladi — shu kompyuter keyingi so'rovdayoq 401 oladi (access token 1 kun
yashashini kutmaydi). Mehmonning 3 kunlik muddati tugasa ham shunday, lekin
`code: "guest_expired"` bilan — ilova ro'yxatdan o'tish ekranini ochadi.
`did` yo'q tokenlar (mobil, telefon+parol) avvalgidek.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

SESSION_CLOSED = {"detail": "Sessiya tugagan yoki uzilgan.", "code": "session_closed"}
GUEST_EXPIRED = {"detail": "Sinov muddati tugadi. Ro'yxatdan o'ting.", "code": "guest_expired"}


def issued_before_cutoff(user, token) -> bool:
    """Token `user.tokens_valid_after` dan oldin chiqarilganmi (eski baza tokeni)."""
    cutoff = getattr(user, "tokens_valid_after", None)
    iat = token.get("iat")
    return cutoff is not None and (iat is None or iat < cutoff.timestamp())


class SessionAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if issued_before_cutoff(user, validated_token):
            raise AuthenticationFailed(SESSION_CLOSED)
        device_pk = validated_token.get("did")
        if device_pk is not None:
            from apps.accounts.models import Device

            # `is_active` bilan filtrlanmaydi: `prune_devices` muddati o'tgan mehmon
            # sessiyasini nofaol qiladi, lekin ilova baribir `guest_expired` ni ko'rishi kerak.
            # Qurilma shu foydalanuvchiniki bo'lishi shart (boshqa bazadan kelgan `did`).
            device = Device.objects.filter(pk=device_pk, user_id=user.pk).first()
            if device is not None and device.is_expired and user.is_guest:
                raise AuthenticationFailed(GUEST_EXPIRED)
            if device is None or not device.is_active or device.is_expired:
                raise AuthenticationFailed(SESSION_CLOSED)
        return user
