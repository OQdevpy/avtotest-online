import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

PASSWORD = "pass1234"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def auth():
    """`auth(client, user)` — mijozga shu foydalanuvchining JWT'sini biriktiradi."""

    def _auth(client, user):
        access = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    return _auth


@pytest.fixture
def student(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110001", PASSWORD, full_name="O'quvchi"
    )


@pytest.fixture
def other_student(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110002", PASSWORD, full_name="Boshqa o'quvchi"
    )


@pytest.fixture
def teacher(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110003", PASSWORD, full_name="O'qituvchi", role="teacher"
    )


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110004", PASSWORD, full_name="Shef", role="admin", is_staff=True
    )


# --- Kontent fixture'lari ---------------------------------------------------

@pytest.fixture
def section(db):
    from apps.content.models import Section

    return Section.objects.create(name_uz="1-bo'lim", name_ru="Раздел 1",
                                  name_cry="1-бўлим", order=1)


@pytest.fixture
def lesson(section):
    from apps.content.models import Lesson

    return Lesson.objects.create(section=section, name_uz="Yo'l belgilari",
                                 name_ru="Дорожные знаки", name_cry="Йўл белгилари",
                                 order=1)


def _make_question(lesson, text="Savol", order=0, published=True):
    from apps.content.models import Answer, Question

    question = Question.objects.create(
        lesson=lesson, text_uz=text, text_ru=f"{text} ru", text_cry=f"{text} cry",
        order=order, is_published=published,
    )
    Answer.objects.create(question=question, text_uz="To'g'ri", is_true=True, order=0)
    Answer.objects.create(question=question, text_uz="Xato", is_true=False, order=1)
    return question


@pytest.fixture
def make_question():
    return _make_question


@pytest.fixture
def question(lesson):
    return _make_question(lesson, "Nechta guruh bor?", order=0)


@pytest.fixture
def ticket(question):
    from apps.content.models import Ticket, TicketQuestion

    ticket = Ticket.objects.create(number=1)
    TicketQuestion.objects.create(ticket=ticket, question=question, order=0)
    return ticket


@pytest.fixture
def blits(lesson, make_question):
    from apps.content.models import Blits, BlitsQuestion

    blits = Blits.objects.create(name_uz="Blits 1", name_ru="Блиц 1",
                                 name_cry="Блиц 1", order=1)
    for index in range(3):
        question = make_question(lesson, f"Blits savol {index}", order=index)
        BlitsQuestion.objects.create(blits=blits, question=question, order=index)
    return blits


@pytest.fixture
def many_questions(lesson):
    """Imtihon uchun yetarli savol (20 rejimi 20 ta savol so'raydi)."""
    return [_make_question(lesson, f"Savol {i}", order=i) for i in range(25)]
