from django import forms

from .domain.paciente import LIMITE_FICHA


PRIORIDADES = (
    (1, "1 · Emergência"),
    (2, "2 · Muito urgente"),
    (3, "3 · Urgente"),
    (4, "4 · Pouco urgente"),
    (5, "5 · Não urgente"),
)


class TriagemForm(forms.Form):
    prioridade = forms.TypedChoiceField(
        label="Classificação de risco", choices=PRIORIDADES, coerce=int, initial=3,
    )


class PacienteForm(TriagemForm):
    field_order = ("nome", "prioridade", "ficha")
    nome = forms.CharField(label="Nome", max_length=120)
    ficha = forms.CharField(
        label="Ficha do paciente",
        required=False,
        max_length=LIMITE_FICHA,
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class MedicoForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=120)
    registro = forms.CharField(label="Registro profissional", max_length=40)


class ConsultaForm(forms.Form):
    id = forms.IntegerField(label="Consultar por ID", min_value=1)
