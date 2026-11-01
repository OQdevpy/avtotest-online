"""JWT autentifikatsiyasi + kirish kodi va mehmon sessiyasining tirikligi.

Kirish kodi va mehmon tokenlarida `did` (Device pk) bor. Shef kodni nofaol
qilsa yoki kompyuter bog'lanishini bekor qilsa `Device.is_active=False`
bo'ladi — shu kompyuter keyingi so'rovdayoq 401 oladi (access token 1 kun
yashashini kutmaydi). Mehmonning 5 kunlik muddati tugasa ham shunday, lekin
`code: "guest_expired"` bilan — ilova ro'yxatdan o'tish ekranini ochadi.
`did` yo'q tokenlar (mobil, telefon+parol) avvalgidek.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

GUEST_EXPIRED = {"detail": "Sinov muddati tugadi. Ro'yxatdan o'ting.", "code": "guest_expired"}


class SessionAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        device_pk = validated_token.get("did")
        if device_pk is not None:
            from apps.accounts.models import Device

            # `is_active` bilan filtrlanmaydi: `prune_devices` muddati o'tgan mehmon
            # sessiyasini nofaol qiladi, lekin ilova baribir `guest_expired` ni ko'rishi kerak.
            device = Device.objects.filter(pk=device_pk).first()
            if device is not None and device.is_expired and user.is_guest:
                raise AuthenticationFailed(GUEST_EXPIRED)
            if device is None or not device.is_active or device.is_expired:
                raise AuthenticationFailed({"detail": "Sessiya tugagan yoki uzilgan.",
                                            "code": "session_closed"})
        return user
