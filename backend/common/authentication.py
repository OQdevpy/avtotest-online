"""JWT autentifikatsiyasi + kirish kodi sessiyasining tirikligi.

Kirish kodi bilan chiqarilgan tokenlarda `did` (Device pk) bor. Shef kodni
nofaol qilsa yoki kompyuter bog'lanishini bekor qilsa `Device.is_active=False`
bo'ladi — shu kompyuter keyingi so'rovdayoq 401 oladi (access token 1 kun
yashashini kutmaydi). `did` yo'q tokenlar (mobil, telefon+parol) avvalgidek.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class SessionAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        device_pk = validated_token.get("did")
        if device_pk is not None:
            from apps.accounts.models import Device

            if not Device.objects.filter(pk=device_pk, is_active=True).exists():
                raise AuthenticationFailed("Sessiya tugagan yoki uzilgan.", code="session_closed")
        return user
