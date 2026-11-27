from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from unittest.mock import patch

from django.test import Client, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from atendimentos import views
from atendimentos.domain.paciente import LIMITE_FICHA
from atendimentos.services.sistema import SistemaAtendimento


class FluxoWebTests(SimpleTestCase):
    def setUp(self):
        self.sistema = SistemaAtendimento()
        substituicao = patch.object(views, "_sistema", self.sistema)
        substituicao.start()
        self.addCleanup(substituicao.stop)

    def test_painel_exibe_fila_e_candidatos_reais_e_conta_conclusoes_no_dia_local(self):
        antes_da_meia_noite = datetime(2026, 11, 26, 2, 59, tzinfo=UTC)
        depois_da_meia_noite = datetime(2026, 11, 26, 3, 1, tzinfo=UTC)
        with patch.object(self.sistema, "_relogio", return_value=antes_da_meia_noite) as relogio:
            medico = self.sistema.cadastrar_medico("Médico com histórico", "SIM-1")
            self.sistema.cadastrar_paciente("Atendimento de ontem", antes_da_meia_noite, 3)
            self.sistema.concluir_atendimento(self.sistema.chamar_proximo().id)
            relogio.return_value = depois_da_meia_noite
            self.sistema.cadastrar_paciente("Atendimento de hoje", depois_da_meia_noite, 3)
            self.sistema.concluir_atendimento(self.sistema.chamar_proximo().id)
            self.sistema.cadastrar_paciente("Atendimento em curso", depois_da_meia_noite, 3)
            self.sistema.chamar_proximo()
            self.sistema.cancelar_atendimento(self.sistema.listar_atendimentos_ativos()[0].id)
            cancelado = self.sistema.cadastrar_paciente("Cancelado na fila", depois_da_meia_noite, 3)
            self.sistema.cancelar_paciente(cancelado.id)
            self.sistema.cadastrar_paciente("Paciente em curso", depois_da_meia_noite, 3)
            self.sistema.chamar_proximo()
            elegivel = self.sistema.cadastrar_medico("Médico elegível", "SIM-2")
            pacientes = [
                self.sistema.cadastrar_paciente(f"Paciente {n}", depois_da_meia_noite, risco)
                for n, risco in enumerate((5, 2, 3, 1, 4, 3), 1)
            ]

            with timezone.override("America/Sao_Paulo"):
                resposta = self.client.get(reverse("atendimentos:inicio"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["aguardando"], 6)
        self.assertEqual(resposta.context["em_atendimento"], 1)
        self.assertEqual(resposta.context["medicos_disponiveis"], 1)
        self.assertEqual(resposta.context["concluidos_hoje"], 1)
        self.assertEqual(resposta.context["concluido"], 2)
        self.assertEqual(resposta.context["cancelado"], 2)
        self.assertEqual(resposta.context["fila"], [pacientes[i] for i in (3, 1, 2, 5, 4)])
        self.assertEqual(resposta.context["medicos"], [elegivel])
        self.assertIs(resposta.context["medico_elegivel"], elegivel)
        self.assertNotContains(resposta, medico.nome)
        self.assertContains(resposta, f"/pacientes/?id={pacientes[3].id}")
        self.assertContains(resposta, "Chamar próximo")
        self.assertContains(resposta, "<dt>Concluídos no total</dt><dd>2</dd>", html=True)
        self.assertContains(resposta, "<dt>Cancelados no total</dt><dd>2</dd>", html=True)
        self.assertIs(self.sistema.proximo_paciente(), pacientes[3])
        self.sistema.validar_indices()

    def test_triagem_usa_mesma_leitura_da_fila_e_da_raiz_ao_renderizar(self):
        chegada = timezone.now()
        primeiro = self.sistema.cadastrar_paciente("Primeiro da fila", chegada, 1)
        segundo = self.sistema.cadastrar_paciente("Segundo da fila", chegada, 3)
        self.sistema.cadastrar_medico("Médico fictício", "SIM-1")
        renderizar = views.render

        def render_com_chamada_simultanea(request, template, contexto):
            with ThreadPoolExecutor(max_workers=1) as executor:
                atendimento = executor.submit(self.sistema.chamar_proximo).result(timeout=5)
                self.assertIs(atendimento.paciente, primeiro)
            return renderizar(request, template, contexto)

        rota = reverse("atendimentos:triagem")
        with patch.object(views, "render", side_effect=render_com_chamada_simultanea):
            resposta = self.client.get(rota)

        self.assertEqual([paciente.id for paciente in resposta.context["fila"]], [primeiro.id, segundo.id])
        self.assertEqual(resposta.context["proximo"].id, primeiro.id)
        self.assertContains(resposta, ">Aguardando</span>", count=2)
        self.assertNotContains(resposta, ">Em atendimento</span>")
        atualizada = self.client.get(rota)
        self.assertNotContains(atualizada, primeiro.nome)
        self.assertEqual(atualizada.context["proximo"].id, segundo.id)

    def test_fluxo_de_cadastro_triagem_chamada_e_historico(self):
        url_pacientes = reverse("atendimentos:pacientes")
        url_medicos = reverse("atendimentos:medicos")
        url_triagem = reverse("atendimentos:triagem")
        self.assertRedirects(self.client.post(url_pacientes, {"nome": "Ana Sintética", "prioridade": 3}), url_pacientes)
        self.assertRedirects(self.client.post(url_pacientes, {"nome": "Bia Sintética", "prioridade": 4}), url_pacientes)
        self.assertContains(self.client.get(url_pacientes, {"id": 1}), "Ana Sintética")
        self.assertContains(self.client.get(url_pacientes, {"id": 99}), "Paciente não encontrado.")
        self.assertRedirects(self.client.post(url_medicos, {"nome": "Dr. Exemplo", "registro": "SIM-1"}), url_medicos)
        self.assertContains(self.client.get(url_medicos, {"id": 1}), "SIM-1")

        reclassificar = reverse("atendimentos:reclassificar", args=[2])
        self.assertRedirects(self.client.post(reclassificar, {"prioridade": 1}), url_triagem)
        self.assertContains(self.client.get(url_triagem), "Próximo pela prioridade")

        url_chamar = reverse("atendimentos:chamar")
        resposta = self.client.post(url_chamar, follow=True)
        self.assertContains(resposta, "Bia Sintética com Dr. Exemplo")
        self.assertContains(self.client.post(url_chamar, follow=True), "Nenhum médico está disponível")

        concluir = reverse("atendimentos:concluir", args=[1])
        self.assertContains(self.client.post(concluir, follow=True), "Atendimento #1 concluído.")
        self.assertContains(self.client.post(url_chamar, follow=True), "Ana Sintética com Dr. Exemplo")
        cancelar = reverse("atendimentos:cancelar_atendimento", args=[2])
        self.assertContains(self.client.post(cancelar, follow=True), "Atendimento #2 cancelado.")
        historico = self.client.get(reverse("atendimentos:historico"), {"id": 1})
        self.assertContains(historico, "Bia Sintética")
        self.assertContains(historico, "Ana Sintética")
        self.assertContains(historico, "Cancelado")
        self.assertContains(historico, "Concluído")
        self.assertEqual(self.sistema.buscar_medico(1).total_concluidos, 1)
        self.sistema.validar_indices()

    def test_mutacoes_exigem_metodo_post_e_token_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        url_triagem = reverse("atendimentos:triagem")
        url_chamar = reverse("atendimentos:chamar")
        self.assertEqual(cliente.get(url_chamar).status_code, 405)
        self.assertEqual(cliente.post(url_chamar).status_code, 403)
        self.assertEqual(cliente.get(url_triagem).status_code, 200)
        token = cliente.cookies["csrftoken"].value
        self.assertEqual(cliente.post(url_chamar, {"csrfmiddlewaretoken": token}).status_code, 302)

    def test_cadastro_de_paciente_salva_a_ficha_e_exibe_na_consulta(self):
        rota = reverse("atendimentos:pacientes")
        formulario = self.client.get(rota)
        self.assertContains(formulario, '<label for="id_nome">Nome:</label>', html=True)
        self.assertNotContains(formulario, "Nome fictício")
        self.assertNotContains(formulario, "Simulador acadêmico")
        self.assertContains(formulario, "Ficha do paciente")
        self.assertContains(formulario, "<textarea", count=1)

        ficha = "Queixa inicial\nObservação com <exemplo>"
        resposta = self.client.post(rota, {"nome": "Paciente teste", "prioridade": 3, "ficha": ficha})
        self.assertRedirects(resposta, rota)
        self.assertEqual(self.sistema.buscar_paciente(1).ficha, ficha)
        consulta = self.client.get(rota, {"id": 1})
        self.assertContains(consulta, "Queixa inicial<br>Observação com &lt;exemplo&gt;")
        self.assertNotContains(consulta, "<exemplo>")
        invalido = self.client.post(rota, {
            "nome": "Paciente teste", "prioridade": 3, "ficha": "x" * (LIMITE_FICHA + 1),
        })
        self.assertIn("ficha", invalido.context["form"].errors)
        self.assertIsNone(self.sistema.buscar_paciente(2))

    def test_cadastro_de_medico_exibe_apenas_nome_e_registro(self):
        rota = reverse("atendimentos:medicos")
        formulario = self.client.get(rota)
        self.assertContains(formulario, '<label for="id_nome">Nome:</label>', html=True)
        self.assertContains(formulario, '<label for="id_registro">Registro profissional:</label>', html=True)
        self.assertNotContains(formulario, "Nome fictício")
        self.assertNotContains(formulario, "Registro profissional fictício")
        self.assertNotContains(formulario, "Especialidade")
        self.assertEqual(list(formulario.context["form"].fields), ["nome", "registro"])

        dados = {"nome": "Médico teste", "registro": "SIM-123"}
        self.assertRedirects(self.client.post(rota, dados), rota)
        medico = self.sistema.buscar_medico(1)
        self.assertEqual(medico.registro, "SIM-123")
        consulta = self.client.get(rota, {"id": 1})
        self.assertContains(consulta, "SIM-123")
        self.assertNotContains(consulta, "Especialidade")

        invalido = self.client.post(rota, {**dados, "registro": ""})
        self.assertIn("registro", invalido.context["form"].errors)
        self.assertIsNone(self.sistema.buscar_medico(2))

    def test_confirmacao_web_preserva_o_registro_ate_o_post(self):
        paciente = self.sistema.cadastrar_paciente("Paciente fictício", timezone.now(), 3)
        url_cancelar = reverse("atendimentos:cancelar_paciente", args=[paciente.id])
        resposta = self.client.get(url_cancelar)
        self.assertContains(resposta, "Confirmar cancelamento")
        self.assertContains(resposta, "Voltar sem cancelar")
        self.assertEqual(self.sistema.listar_fila(), [paciente])
        self.assertEqual(Client(enforce_csrf_checks=True).post(url_cancelar).status_code, 403)
        self.assertRedirects(self.client.post(url_cancelar), reverse("atendimentos:triagem"))
        self.assertEqual(self.sistema.listar_fila(), [])

        self.sistema.cadastrar_paciente("Outro paciente", timezone.now(), 2)
        self.sistema.cadastrar_medico("Médico fictício", "SIM-001")
        atendimento = self.sistema.chamar_proximo()
        url_cancelar = reverse("atendimentos:cancelar_atendimento", args=[atendimento.id])
        self.assertContains(self.client.get(url_cancelar), "Confirmar cancelamento")
        self.assertEqual(self.sistema.listar_atendimentos_ativos(), [atendimento])
        self.assertRedirects(self.client.post(url_cancelar), reverse("atendimentos:atendimentos"))
        self.assertEqual(self.sistema.listar_historico(), [atendimento])

    def test_indices_permanecem_internos_e_a_tela_de_estruturas_nao_existe(self):
        self.sistema.cadastrar_medico("Médico fictício", "SIM-001")
        chegada = timezone.now()
        primeiro = self.sistema.cadastrar_paciente("Comum", chegada, 4)
        # IDs espaçados simulam uma colisão no mesmo bucket com capacidade 11.
        with patch.object(self.sistema, "_proximo_paciente", primeiro.id + 11):
            urgente = self.sistema.cadastrar_paciente("Urgente", chegada, 1)

        painel = self.client.get(reverse("atendimentos:inicio"))
        self.assertNotContains(painel, 'href="/estruturas/"', html=False)
        self.assertEqual(self.client.get("/estruturas/").status_code, 404)
        indices = self.sistema.inspecionar_indices()
        self.assertEqual(indices["arvore"]["cor"], "preto")
        self.assertEqual(indices["arvore"]["direita"]["cor"], "vermelho")
        self.assertEqual(indices["heap_pacientes"][0][0], urgente.id)
        self.assertEqual(indices["heap_medicos"][0][1], "Médico fictício")
        self.assertEqual(indices["capacidade_hash"], 11)
        self.assertEqual(indices["buckets"][1], (primeiro.id, urgente.id))
        self.assertEqual(indices["colisoes_hash"], 1)
        with patch.object(self.sistema, "validar_indices", side_effect=ValueError("Heap inconsistente.")):
            with self.assertRaisesRegex(ValueError, "Heap inconsistente."):
                self.sistema.inspecionar_indices()
