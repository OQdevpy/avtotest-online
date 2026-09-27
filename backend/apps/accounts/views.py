from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SocialAccount, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    SocialLoginSerializer,
    UserSerializer,
    tokens_for,
)


def auth_response(user: User, created: bool = False) -> Response:
    return Response(
        {"user": UserSerializer(user).data, "tokens": tokens_for(user)},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@extend_schema(tags=["auth"])
class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return auth_response(user, created=True)


@extend_schema(tags=["auth"])
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return auth_response(serializer.validated_data["user"])


@extend_schema(tags=["auth"])
class SocialLoginView(generics.GenericAPIView):
    """Apple / Google / Telegram / Email sign-in.

    TODO(auth): verify the provider token server-side before trusting `uid`
    (Apple: identity token JWT; Google: tokeninfo; Telegram: login-widget hash).
    Until then this endpoint must not be exposed in production.
    """

    serializer_class = SocialLoginSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        link = (
            SocialAccount.objects
            .select_related("user")
            .filter(provider=data["provider"], uid=data["uid"])
            .first()
        )
        if link:
            return auth_response(link.user)

        phone = data.get("phone")
        user = User.objects.filter(phone=phone).first() if phone else None
        created = False
        if user is None:
            # Social-only accounts have no phone yet; a placeholder keeps the
            # unique constraint satisfied until the user adds a real number.
            user = User.objects.create_user(
                phone=phone or f"+998{data['uid'][-9:].rjust(9, '0')}",
                full_name=data.get("full_name", ""),
            )
            created = True

        SocialAccount.objects.create(
            user=user,
            provider=data["provider"],
            uid=data["uid"],
            email=data.get("email", ""),
        )
        return auth_response(user, created=created)


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Hisob va unga bog'liq barcha ma'lumotlar (progress, xatolar, saqlangan
        # savollar, natijalar) FK cascade orqali o'chadi. Apple/Google talabi.
        instance.delete()


@extend_schema(tags=["auth"])
class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Parol yangilandi."})
