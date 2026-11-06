from django import forms
from django.utils import timezone

from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ("titulo", "categoria", "descricao", "data_inicio", "local", "vagas")
        widgets = {
            # O seletor nativo do navegador exige exatamente este formato.
            "data_inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            ),
            "descricao": forms.Textarea(attrs={"rows": 6}),
            "vagas": forms.NumberInput(attrs={"min": 1}),
        }

    def clean_data_inicio(self):
        data = self.cleaned_data["data_inicio"]
        # Só valida quando a data muda, para permitir corrigir o texto de um
        # evento que já aconteceu.
        if "data_inicio" in self.changed_data and data <= timezone.now():
            raise forms.ValidationError("Escolha uma data no futuro.")
        return data

    def clean_vagas(self):
        vagas = self.cleaned_data["vagas"]
        if self.instance.pk and vagas < self.instance.inscricoes.count():
            raise forms.ValidationError(
                "O evento já tem mais inscritos do que esse número de vagas."
            )
        return vagas
