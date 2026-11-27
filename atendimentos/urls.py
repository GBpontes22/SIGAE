from django.urls import path

from . import views

app_name = "atendimentos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("pacientes/", views.pacientes, name="pacientes"),
    path("triagem/", views.triagem, name="triagem"),
    path("triagem/<int:id>/reclassificar/", views.reclassificar, name="reclassificar"),
    path("triagem/<int:id>/cancelar/", views.cancelar_paciente, name="cancelar_paciente"),
    path("medicos/", views.medicos, name="medicos"),
    path("atendimentos/", views.atendimentos, name="atendimentos"),
    path("atendimentos/chamar/", views.chamar, name="chamar"),
    path("atendimentos/<int:id>/concluir/", views.concluir, name="concluir"),
    path("atendimentos/<int:id>/cancelar/", views.cancelar_atendimento, name="cancelar_atendimento"),
    path("historico/", views.historico, name="historico"),
    path("estruturas/", views.estruturas, name="estruturas"),
    path("estruturas/demonstrar-colisao/", views.demonstrar_colisao, name="demonstrar_colisao"),
]
