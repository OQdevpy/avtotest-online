from django import forms

from .models import Notification


class SendPushForm(forms.Form):
    """Tanlangan foydalanuvchilarga yuboriladigan xabar matni (har biriga o'z tilida)."""

    kind = forms.ChoiceField(label="Turi", choices=Notification.Kind.choices,
                             initial=Notification.Kind.INFO)
    title_uz = forms.CharField(label="Sarlavha (o'zbekcha)", max_length=255)
    body_uz = forms.CharField(label="Matn (o'zbekcha)", required=False,
                              widget=forms.Textarea(attrs={"rows": 3}))
    title_cry = forms.CharField(label="Sarlavha (кирилл)", max_length=255, required=False)
    body_cry = forms.CharField(label="Matn (кирилл)", required=False,
                               widget=forms.Textarea(attrs={"rows": 3}))
    title_ru = forms.CharField(label="Sarlavha (русский)", max_length=255, required=False)
    body_ru = forms.CharField(label="Matn (русский)", required=False,
                              widget=forms.Textarea(attrs={"rows": 3}))


class NotificationAdminForm(forms.ModelForm):
    send_push = forms.BooleanField(
        label="Push ham yuborilsin", required=False, initial=True,
        help_text="Saqlanganda telefonlarga push bildirishnoma navbatga qo'yiladi. "
                  "Bo'sh qoldirilsa faqat ilova ichidagi ro'yxatda ko'rinadi.",
    )

    class Meta:
        model = Notification
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if (data.get("audience") == Notification.Audience.SELECTED
                and not data.get("recipients")):
            self.add_error("recipients", "Tanlanganlarga yuborish uchun kamida bitta foydalanuvchi.")
        return data
