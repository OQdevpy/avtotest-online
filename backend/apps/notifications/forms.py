from django import forms

from .models import Notification


class SendPushForm(forms.Form):
    """Tanlangan foydalanuvchilarga yuboriladigan xabar matni (har biriga o'z tilida)."""

    kind = forms.ChoiceField(label="Turi", choices=Notification.Kind.choices,
                             initial=Notification.Kind.INFO)
    target = forms.ChoiceField(label="Bosilganda ochiladi", choices=Notification.Target.choices,
                               initial=Notification.Target.NOTIFICATIONS, required=False)
    url = forms.URLField(label="Havola", required=False,
                         help_text="Faqat «Havola» tanlanganda (masalan https://t.me/...).")
    title_uz = forms.CharField(label="Sarlavha (o'zbekcha)", max_length=255)
    body_uz = forms.CharField(label="Matn (o'zbekcha)", required=False,
                              widget=forms.Textarea(attrs={"rows": 3}))
    title_cry = forms.CharField(label="Sarlavha (кирилл)", max_length=255, required=False)
    body_cry = forms.CharField(label="Matn (кирилл)", required=False,
                               widget=forms.Textarea(attrs={"rows": 3}))
    title_ru = forms.CharField(label="Sarlavha (русский)", max_length=255, required=False)
    body_ru = forms.CharField(label="Matn (русский)", required=False,
                              widget=forms.Textarea(attrs={"rows": 3}))


    def clean(self):
        data = super().clean()
        data["target"] = data.get("target") or Notification.Target.NOTIFICATIONS
        if data["target"] == Notification.Target.URL and not data.get("url"):
            self.add_error("url", "«Havola» uchun manzil kiriting.")
        return data


class NotificationAdminForm(forms.ModelForm):
    send_push = forms.BooleanField(
        label="Push ham yuborilsin", required=False, initial=True,
        help_text="Saqlanganda telefonlarga push bildirishnoma navbatga qo'yiladi. "
                  "Bo'sh qoldirilsa faqat ilova ichidagi ro'yxatda ko'rinadi.",
    )

    class Meta:
        model = Notification
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "target" in self.fields:
            self.fields["target"].required = False

    def clean_target(self):
        return self.cleaned_data.get("target") or Notification.Target.NOTIFICATIONS

    def clean(self):
        data = super().clean()
        if (data.get("audience") == Notification.Audience.SELECTED
                and not data.get("recipients")):
            self.add_error("recipients", "Tanlanganlarga yuborish uchun kamida bitta foydalanuvchi.")
        return data
