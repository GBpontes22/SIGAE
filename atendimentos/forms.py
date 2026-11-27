from django import forms


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
    field_order = ("nome", "prioridade")
    nome = forms.CharField(label="Nome fictício", max_length=120)


class MedicoForm(forms.Form):
    nome = forms.CharField(label="Nome fictício", max_length=120)
    registro = forms.CharField(label="Registro profissional fictício", max_length=40)


class ConsultaForm(forms.Form):
    id = forms.IntegerField(label="Consultar por ID", min_value=1)
