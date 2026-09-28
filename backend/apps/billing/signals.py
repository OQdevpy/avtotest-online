"""Student <-> User sinxronizatsiyasi.

Talaba (Student) saqlanganda unga bog'liq `accounts.User` yaratiladi yoki
yangilanadi — "student yaratilsa default foydalanuvchi ham yaratilishi
kerak" qoidasi shu yerda. Mobil ilovaning kirishi (`LoginSerializer`)
`Student.password`ni to'g'ridan-to'g'ri tekshiradi, lekin JWT har doim shu
User uchun chiqariladi.

Mavjud foydalanuvchi qoidasi: telefon bo'yicha allaqachon `User` bo'lsa
(masalan ilovada o'z parolini o'rnatgan), uning paroli va ismi tegilmaydi —
faqat bog'lanadi (import qilishdagi "mavjudni buzma" qoidasi bilan bir xil).
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="billing.Student")
def sync_student_user(sender, instance, created, **kwargs):
    from apps.accounts.models import User

    student = instance

    if student.user_id is None:
        user = User.objects.filter(phone=student.phone).first()
        if user is None:
            user = User(phone=student.phone)
            user.set_password(student.password)
        user.role = User.Role.STUDENT
        user.full_name = user.full_name or student.name
        user.branch_id = user.branch_id or student.branch_id
        if not user.hujjat or user.hujjat == "-":
            user.hujjat = student.hujjat
        user.save()
        type(student).objects.filter(pk=student.pk).update(user=user)
        # Xotiradagi `student` obyektini ham yangilaymiz — aks holda shu
        # obyektga qilingan keyingi `.save()` yana shu tarmoqqa tushib,
        # mavjud foydalanuvchini "yangi" deb hisoblab qo'yadi (parol/filial
        # yangilanishini o'tkazib yuboradi).
        student.user = user
        return

    user = student.user
    if user is None:
        return
    changed = []
    if user.full_name != student.name:
        user.full_name = student.name
        changed.append("full_name")
    if user.branch_id != student.branch_id:
        user.branch_id = student.branch_id
        changed.append("branch")
    if user.hujjat != student.hujjat:
        user.hujjat = student.hujjat
        changed.append("hujjat")
    if user.phone != student.phone:
        user.phone = student.phone
        changed.append("phone")
    # PIN o'zgargan bo'lsa — shef ataylab reset qilgan, login paroli ham
    # yangilanadi.
    if getattr(student, "_previous_password", student.password) != student.password:
        if not user.check_password(student.password):
            user.set_password(student.password)
            changed.append("password")
    if changed:
        user.save(update_fields=changed)
