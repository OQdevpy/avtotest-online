import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def teacher_in_a(teacher, branch_a):
    teacher.branch = branch_a
    teacher.save(update_fields=["branch"])
    return teacher


@pytest.fixture
def student_in_a(student, branch_a):
    student.branch = branch_a
    student.save(update_fields=["branch"])
    return student


@pytest.fixture
def student_in_b(other_student, branch_b):
    other_student.branch = branch_b
    other_student.save(update_fields=["branch"])
    return other_student


# --- Ruxsat -----------------------------------------------------------------

def test_student_cannot_access_teacher_api(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/teacher/students/").status_code == 403


def test_anonymous_cannot_access_teacher_api(api):
    assert api.get("/api/v1/teacher/students/").status_code == 401


# --- Ro'yxat -----------------------------------------------------------------

def test_teacher_lists_only_own_branch_students(api, auth, teacher_in_a,
                                                student_in_a, student_in_b):
    auth(api, teacher_in_a)
    rows = api.get("/api/v1/teacher/students/").json()["results"]
    assert [r["phone"] for r in rows] == [student_in_a.phone]


def test_teacher_without_branch_sees_empty_list(api, auth, teacher, student_in_a):
    auth(api, teacher)
    assert api.get("/api/v1/teacher/students/").json()["results"] == []


def test_teacher_list_excludes_other_teachers(api, auth, teacher_in_a, branch_a,
                                              django_user_model):
    django_user_model.objects.create_user("+998901115555", "x", role="teacher",
                                          branch=branch_a)
    auth(api, teacher_in_a)
    rows = api.get("/api/v1/teacher/students/").json()["results"]
    assert rows == []


def test_admin_sees_all_branches(api, auth, admin_user, student_in_a, student_in_b):
    auth(api, admin_user)
    rows = api.get("/api/v1/teacher/students/").json()["results"]
    assert {r["phone"] for r in rows} == {student_in_a.phone, student_in_b.phone}


def test_admin_can_filter_by_branch(api, auth, admin_user, student_in_a, student_in_b,
                                    branch_a):
    auth(api, admin_user)
    rows = api.get(f"/api/v1/teacher/students/?branch={branch_a.id}").json()["results"]
    assert [r["phone"] for r in rows] == [student_in_a.phone]


# --- Bitta o'quvchi statistikasi --------------------------------------------

# Review Focus #3
def test_teacher_cannot_read_other_branch_student_stats(api, auth, teacher_in_a,
                                                       student_in_b):
    auth(api, teacher_in_a)
    response = api.get(f"/api/v1/teacher/students/{student_in_b.id}/stats/")
    assert response.status_code == 404


def test_teacher_reads_own_branch_student_stats(api, auth, teacher_in_a, student_in_a):
    auth(api, teacher_in_a)
    assert api.get(f"/api/v1/teacher/students/{student_in_a.id}/stats/").status_code == 200


def test_teacher_without_branch_cannot_read_any_stats(api, auth, teacher, student_in_a):
    auth(api, teacher)
    assert api.get(f"/api/v1/teacher/students/{student_in_a.id}/stats/").status_code == 404


def test_admin_reads_any_student_stats(api, auth, admin_user, student_in_b):
    auth(api, admin_user)
    assert api.get(f"/api/v1/teacher/students/{student_in_b.id}/stats/").status_code == 200


def test_own_stats_and_teacher_stats_agree(api, auth, teacher_in_a, student_in_a,
                                           lesson, make_question):
    """`progress/stats/` va o'qituvchi ko'rgan statistika bir xil bo'lishi kerak."""
    from apps.progress.models import LessonResult

    LessonResult.objects.create(user=student_in_a, lesson=lesson, score=4, total=5)
    auth(api, student_in_a)
    own = api.get("/api/v1/progress/stats/").json()
    api.credentials()
    auth(api, teacher_in_a)
    seen = api.get(f"/api/v1/teacher/students/{student_in_a.id}/stats/").json()
    assert seen["stats"] == own


# --- Filial kesimi ----------------------------------------------------------

def test_teacher_branch_summary(api, auth, teacher_in_a, student_in_a, student_in_b):
    auth(api, teacher_in_a)
    body = api.get("/api/v1/teacher/stats/").json()
    assert body["student_count"] == 1


def test_admin_branch_summary_counts_everyone(api, auth, admin_user, student_in_a,
                                              student_in_b):
    auth(api, admin_user)
    assert api.get("/api/v1/teacher/stats/").json()["student_count"] == 2
