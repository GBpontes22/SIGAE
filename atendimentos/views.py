from collections.abc import Callable

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .forms import PRIORIDADES, ConsultaForm, MedicoForm, PacienteForm, TriagemForm
from .services.sistema import SistemaAtendimento


_sistema = SistemaAtendimento()


@require_safe
def inicio(request):
    return render(
        request, "atendimentos/inicio.html",
        _sistema.resumo_painel(timezone.get_current_timezone()),
    )


def _consulta(request, buscar):
    form = ConsultaForm(request.GET if "id" in request.GET else None)
    resultado = buscar(form.cleaned_data["id"]) if form.is_valid() else None
    return form, resultado


@require_http_methods(["GET", "POST"])
def pacientes(request):
    form = PacienteForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        paciente = _sistema.cadastrar_paciente(chegada=timezone.now(), **form.cleaned_data)
        messages.success(request, f"Paciente #{paciente.id} cadastrado.")
        return redirect("atendimentos:pacientes")

    consulta, encontrado = _consulta(request, _sistema.buscar_paciente)
    return render(request, "atendimentos/pacientes.html", {
        "form": form, "consulta": consulta, "encontrado": encontrado,
        "pacientes": _sistema.listar_chegadas(),
    })


@require_http_methods(["GET", "POST"])
def medicos(request):
    form = MedicoForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        medico = _sistema.cadastrar_medico(**form.cleaned_data)
        messages.success(request, f"Médico #{medico.id} cadastrado.")
        return redirect("atendimentos:medicos")

    consulta, encontrado = _consulta(request, _sistema.buscar_medico)
    return render(request, "atendimentos/medicos.html", {
        "form": form, "consulta": consulta, "encontrado": encontrado,
        "medicos": _sistema.listar_medicos(),
    })


@require_safe
def triagem(request):
    fila, proximo = _sistema.resumo_triagem()
    return render(request, "atendimentos/triagem.html", {
        "fila": fila,
        "proximo": proximo,
        "prioridades": PRIORIDADES,
    })


@require_http_methods(["GET", "HEAD", "POST"])
def estruturas(request):
    try:
        indices = _sistema.inspecionar_indices()
    except ValueError as erro:
        return render(request, "atendimentos/estruturas.html", {"erro": str(erro)}, status=500)
    return render(request, "atendimentos/estruturas.html", {
        "indices": indices,
        "validado": request.method == "POST",
    })


def _confirmar_cancelamento(request, titulo, descricao, destino):
    return render(request, "atendimentos/confirmar_cancelamento.html", {
        "titulo": titulo, "descricao": descricao, "destino": f"atendimentos:{destino}",
    })


def _executar(
    request: HttpRequest, destino: str, operacao: Callable[[], str],
) -> HttpResponse:
    try:
        mensagem = operacao()
    except KeyError:
        messages.error(request, "O registro solicitado não existe.")
    except ValueError as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, mensagem)
    return redirect(f"atendimentos:{destino}")


@require_POST
def reclassificar(request, id):
    form = TriagemForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Selecione uma classificação de risco válida.")
        return redirect("atendimentos:triagem")

    def salvar():
        paciente = _sistema.reclassificar_paciente(id, form.cleaned_data["prioridade"])
        return f"Classificação de risco do paciente #{paciente.id} atualizada."

    return _executar(request, "triagem", salvar)


@require_http_methods(["GET", "HEAD", "POST"])
def cancelar_paciente(request, id):
    if request.method != "POST":
        paciente = _sistema.buscar_paciente(id)
        if paciente is None:
            raise Http404("Paciente não encontrado.")
        return _confirmar_cancelamento(
            request, f"Cancelar paciente #{paciente.id}?",
            f"O registro de {paciente.nome} será preservado com a situação Cancelado.",
            "triagem",
        )


    def cancelar():
        paciente = _sistema.cancelar_paciente(id)
        return f"Paciente #{paciente.id} cancelado."

    return _executar(request, "triagem", cancelar)


@require_POST
def demonstrar_colisao(request):
    def cadastrar():
        primeiro, segundo, bucket = _sistema.demonstrar_colisao()
        return f"Pacientes fictícios #{primeiro} e #{segundo} foram cadastrados no bucket {bucket}."

    return _executar(request, "estruturas", cadastrar)


@require_POST
def chamar(request):
    def atribuir():
        atendimento = _sistema.chamar_proximo()
        return f"Atendimento #{atendimento.id}: {atendimento.paciente.nome} com {atendimento.medico.nome}."

    return _executar(request, "atendimentos", atribuir)


@require_safe
def atendimentos(request):
    return render(request, "atendimentos/atendimentos.html", {
        "ativos": _sistema.listar_atendimentos_ativos(),
    })


@require_POST
def concluir(request, id):
    def concluir_atendimento():
        atendimento = _sistema.concluir_atendimento(id)
        return f"Atendimento #{atendimento.id} concluído."

    return _executar(request, "atendimentos", concluir_atendimento)


@require_http_methods(["GET", "HEAD", "POST"])
def cancelar_atendimento(request, id):
    if request.method != "POST":
        atendimento = _sistema.buscar_atendimento(id)
        if atendimento is None:
            raise Http404("Atendimento não encontrado.")
        return _confirmar_cancelamento(
            request, f"Cancelar atendimento #{atendimento.id}?",
            f"O médico de {atendimento.paciente.nome} será liberado e o total de conclusões será preservado.",
            "atendimentos",
        )

    def cancelar():
        atendimento = _sistema.cancelar_atendimento(id)
        return f"Atendimento #{atendimento.id} cancelado."

    return _executar(request, "atendimentos", cancelar)


@require_safe
def historico(request):
    filtro = ConsultaForm(request.GET if "id" in request.GET and request.GET["id"] else None)
    medico_id = filtro.cleaned_data["id"] if filtro.is_valid() else None
    return render(request, "atendimentos/historico.html", {
        "historico": _sistema.listar_historico(medico_id),
        "medico_id": medico_id,
        "filtro": filtro,
        "medicos": _sistema.listar_medicos(),
        "chegadas": _sistema.listar_chegadas(),
    })
