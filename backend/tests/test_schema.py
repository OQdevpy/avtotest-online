"""OpenAPI schema spec'da va'da qilingan endpointlarni qamrab olishi kerak."""

import json

import pytest

pytestmark = pytest.mark.django_db

# Spec §7 dagi endpointlar. `{id}` — drf-spectacular yozadigan ko'rinish.
PROMISED = [
    "/api/v1/auth/register/",
    "/api/v1/auth/login/",
    "/api/v1/auth/login-code/",
    "/api/v1/auth/social/",
    "/api/v1/auth/token/refresh/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/me/",
    "/api/v1/auth/change-password/",
    "/api/v1/auth/devices/",
    "/api/v1/auth/devices/{id}/",
    "/api/v1/sections/",
    "/api/v1/lessons/",
    "/api/v1/questions/",
    "/api/v1/topics/",
    "/api/v1/tickets/",
    "/api/v1/tickets/stats/",
    "/api/v1/blits/",
    "/api/v1/blits/{id}/",
    "/api/v1/exams/start/",
    "/api/v1/exams/",
    "/api/v1/exams/{id}/",
    "/api/v1/exams/{id}/answer/",
    "/api/v1/exams/{id}/finish/",
    "/api/v1/progress/lesson-results/",
    "/api/v1/progress/ticket-results/",
    "/api/v1/progress/blits-results/",
    "/api/v1/progress/exam-attempts/",
    "/api/v1/progress/mistakes/",
    "/api/v1/progress/stats/",
    "/api/v1/progress/reset/",
    "/api/v1/manage/users/",
    "/api/v1/manage/access-codes/",
    "/api/v1/manage/sections/",
    "/api/v1/manage/lessons/",
    "/api/v1/manage/questions/",
    "/api/v1/manage/answers/",
    "/api/v1/manage/topics/",
    "/api/v1/manage/tickets/",
    "/api/v1/manage/blits/",
    "/api/v1/manage/questions/{id}/image/",
    "/api/v1/manage/questions/{id}/audio/",
    "/api/v1/manage/branches/",
    "/api/v1/manage/payments/",
    "/api/v1/manage/payment-reports/",
    "/api/v1/manage/lessons/reorder/",
    "/api/v1/teacher/students/",
    "/api/v1/teacher/students/{id}/stats/",
    "/api/v1/teacher/stats/",
    "/api/v1/notifications/",
]


@pytest.fixture
def schema(api, admin_user, auth):
    auth(api, admin_user)
    response = api.get("/api/schema/?format=json")
    assert response.status_code == 200
    return json.loads(response.content)


def test_openapi_schema_builds(schema):
    assert schema["openapi"].startswith("3.")


def test_schema_documents_every_promised_endpoint(schema):
    missing = [path for path in PROMISED if path not in schema["paths"]]
    assert missing == [], f"Schema'da yo'q: {missing}"


def test_deprecated_endpoints_are_marked(schema):
    generate = schema["paths"]["/api/v1/exam/generate/"]["get"]
    assert generate.get("deprecated") is True


def test_swagger_ui_is_served(api, admin_user, auth):
    auth(api, admin_user)
    assert api.get("/api/docs/").status_code == 200
