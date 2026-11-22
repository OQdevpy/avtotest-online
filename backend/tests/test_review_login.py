"""App Store / Google Play tekshiruvchisi uchun test hisob: telefon + parol.

Faqat admin `review_account` belgilagan hisob kira oladi. Qolganlar uchun
`auth/login/` avvalgidek `update_required` (kirish faqat Telegram orqali).
"""

import pytest

from apps.releases.models import AppRelease

pytestmark = pytest.mark.django_db
URL = "/api/v1/auth/login/"
OPTIONS = "/api/v1/app/login-options/"


@pytest.fixture(autouse=True)
def review_mode_on():
    """Ko'p testlar uchun iOS'da tekshiruv rejimi yoqilgan."""
    return AppRelease.objects.create(platform="ios", review_mode=True)


@pytest.fixture
def reviewer(django_user_model):
    u = django_user_model.objects.create_user("+998900000099", "Review2026!", full_name="App Review")
    u.review_account = True
    u.save()
    return u


def login(api, phone, password, platform="ios"):
    return api.post(URL, {"phone": phone, "password": password, "platform": platform}, format="json")


def test_review_account_logs_in(api, reviewer):
    r = login(api, "900000099", "Review2026!")
    assert r.status_code == 200, r.data
    assert r.data["user"]["phone"] == "+998900000099"
    assert r.data["tokens"]["access"] and r.data["tokens"]["refresh"]


def test_normal_user_gets_update_required_even_with_right_password(api, student):
    r = login(api, student.phone, "pass1234")
    assert r.status_code == 400 and r.data["code"] == "update_required"


def test_wrong_password_looks_the_same(api, reviewer):
    r = login(api, "900000099", "notogri")
    assert r.status_code == 400 and r.data["code"] == "update_required"


def test_inactive_review_account_blocked(api, reviewer):
    reviewer.is_active = False
    reviewer.save()
    assert login(api, "900000099", "Review2026!").data["code"] == "update_required"


def test_register_still_closed(api):
    r = api.post("/api/v1/auth/register/", {"phone": "901112233", "password": "x" * 8}, format="json")
    assert r.data["code"] == "update_required"


@pytest.mark.parametrize("phone", ["abc", "", "+1", "9" * 40])
def test_garbage_phone_is_400_not_500(api, phone):
    r = login(api, phone, "x")
    assert r.status_code == 400 and r.data["code"] == "update_required"


def test_review_mode_off_closes_login(api, reviewer, review_mode_on):
    review_mode_on.review_mode = False
    review_mode_on.save()
    assert login(api, "900000099", "Review2026!").data["code"] == "update_required"


def test_review_mode_is_per_platform(api, reviewer):
    # Android uchun rejim yoqilmagan
    assert login(api, "900000099", "Review2026!", platform="android").data["code"] == "update_required"
    assert login(api, "900000099", "Review2026!", platform="").data["code"] == "update_required"


def test_login_options(api, review_mode_on):
    assert api.get(OPTIONS, {"platform": "ios"}).json() == {"review_login": True}
    assert api.get(OPTIONS, {"platform": "android"}).json() == {"review_login": False}
    review_mode_on.review_mode = False
    review_mode_on.save()
    assert api.get(OPTIONS, {"platform": "ios"}).json() == {"review_login": False}
    assert api.get(OPTIONS).json() == {"review_login": False}
