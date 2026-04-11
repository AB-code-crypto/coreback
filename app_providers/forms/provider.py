from django import forms

from app_providers.config import (
    get_supported_provider_choices,
    normalize_provider_code,
)
from app_providers.models.provider import Provider


class ProviderAdminForm(forms.ModelForm):
    code = forms.ChoiceField(
        choices=[],
        label="Код",
        help_text="Выберите одного из поддерживаемых провайдеров.",
    )

    class Meta:
        model = Provider
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = get_supported_provider_choices()
        self.fields["code"].choices = choices

        if self.instance and self.instance.pk:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "Код провайдера нельзя менять после создания."

    def clean_code(self):
        return normalize_provider_code(self.cleaned_data["code"])
