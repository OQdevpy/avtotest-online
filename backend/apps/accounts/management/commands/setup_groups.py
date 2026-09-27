"""Django admin uchun `teacher` va `admin` guruhlarini sozlaydi.

Biznes huquqlari `User.role` orqali hal qilinadi; bu guruhlar faqat admin
paneli ichidagi ko'rinishni belgilaydi. Idempotent — qayta ishlatilsa
guruh takrorlanmaydi va huquqlar aynan ushbu ro'yxatga keltiriladi.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# O'qituvchi: o'quvchi natijalarini ko'radi, hech narsa o'zgartirmaydi.
TEACHER_VIEW_MODELS = [
    ("progress", "lessonresult"),
    ("progress", "ticketresult"),
    ("progress", "blitsresult"),
    ("progress", "examattempt"),
    ("progress", "questionattempt"),
    ("progress", "mistake"),
    ("progress", "savedquestion"),
    ("exams", "examsession"),
    ("accounts", "user"),
]

# Shef: kontent va to'lovni to'liq boshqaradi.
ADMIN_FULL_MODELS = [
    ("content", "section"),
    ("content", "lesson"),
    ("content", "question"),
    ("content", "answer"),
    ("content", "ticket"),
    ("content", "ticketquestion"),
    ("content", "topic"),
    ("content", "blits"),
    ("content", "blitsquestion"),
    ("billing", "branch"),
    ("billing", "studentpayment"),
    ("billing", "paymentreport"),
    ("accounts", "accesscode"),
    ("notifications", "notification"),
]

# Foydalanuvchini shef ko'radi va tahrirlaydi, lekin o'chirmaydi —
# o'chirilgan hisob bilan uning progressi va to'lov tarixi ham ketadi.
ADMIN_USER_ACTIONS = ("view", "change", "add")


def permissions_for(app_label: str, model: str, actions) -> list[Permission]:
    return list(
        Permission.objects.filter(
            content_type__app_label=app_label,
            codename__in=[f"{action}_{model}" for action in actions],
        )
    )


class Command(BaseCommand):
    help = "teacher va admin guruhlarini kerakli huquqlar bilan yaratadi"

    def handle(self, *args, **options):
        teacher, _ = Group.objects.get_or_create(name="teacher")
        admin_group, _ = Group.objects.get_or_create(name="admin")

        teacher_perms = []
        for app_label, model in TEACHER_VIEW_MODELS:
            teacher_perms += permissions_for(app_label, model, ("view",))
        teacher.permissions.set(teacher_perms)

        admin_perms = []
        for app_label, model in ADMIN_FULL_MODELS:
            admin_perms += permissions_for(
                app_label, model, ("view", "add", "change", "delete")
            )
        admin_perms += permissions_for("accounts", "user", ADMIN_USER_ACTIONS)
        admin_perms += permissions_for("accounts", "device", ("view", "delete"))
        admin_group.permissions.set(admin_perms)

        self.stdout.write(
            f"teacher: {teacher.permissions.count()} huquq, "
            f"admin: {admin_group.permissions.count()} huquq"
        )
