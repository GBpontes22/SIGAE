from datetime import UTC, datetime
from unittest.mock import patch

from django.test import Client, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from atendimentos import views
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
        self.assertEqual(resposta.context["fila"], [pacientes[i] for i in (3, 1, 2, 5, 4)])
        self.assertEqual(resposta.context["medicos"], [elegivel])
        self.assertIs(resposta.context["medico_elegivel"], elegivel)
        self.assertNotContains(resposta, medico.nome)
        self.assertContains(resposta, f"/pacientes/?id={pacientes[3].id}")
        self.assertContains(resposta, "Chamar próximo")
        self.assertIs(self.sistema.proximo_paciente(), pacientes[3])
        self.sistema.validar_indices()

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

    def test_defesa_web_com_tres_medicos_e_acoes_fora_de_ordem(self):
        def rota(nome, *args):
            return reverse(f"atendimentos:{nome}", args=args)

        for letra in "ABC":
            self.client.post(rota("medicos"), {"nome": f"Médico {letra}", "registro": f"SIM-{letra}"})
        for numero, risco in enumerate((4, 2, 3, 5), 1):
            self.client.post(rota("pacientes"), {"nome": f"Paciente {numero}", "prioridade": risco})
        self.client.post(rota("reclassificar", 3), {"prioridade": 1})
        self.assertEqual([p.id for p in self.client.get(rota("triagem")).context["fila"]], [1, 2, 3, 4])

        for paciente, medico in ((3, "A"), (2, "B"), (1, "C")):
            self.assertContains(
                self.client.post(rota("chamar"), follow=True), f"Paciente {paciente} com Médico {medico}",
            )
        self.assertContains(self.client.post(rota("chamar"), follow=True), "Nenhum médico está disponível")
        self.assertEqual([p.id for p in self.client.get(rota("triagem")).context["fila"]], [4])

        self.client.post(rota("concluir", 1))
        self.client.post(rota("concluir", 1))
        self.client.post(rota("cancelar_atendimento", 2))
        self.assertContains(self.client.post(rota("chamar"), follow=True), "Paciente 4 com Médico B")

        self.client.post(rota("cancelar_atendimento", 3))
        self.client.post(rota("cancelar_atendimento", 4))
        self.client.post(rota("pacientes"), {"nome": "Paciente 5", "prioridade": 1})
        self.assertContains(self.client.post(rota("chamar"), follow=True), "Paciente 5 com Médico C")

        medicos = self.client.get(rota("medicos"), {"id": 1}).context["medicos"]
        self.assertEqual([medico.total_concluidos for medico in medicos], [1, 0, 0])
        historico_b = self.client.get(rota("historico"), {"id": 2}).context["historico"]
        self.assertEqual([a.paciente.id for a in historico_b], [2, 4])
        self.assertContains(self.client.post(rota("estruturas")), "Índices consistentes.")

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

    def test_estruturas_exibem_nos_raizes_capacidade_e_colisoes_da_sessao(self):
        self.sistema.cadastrar_medico("Médico fictício", "SIM-001")
        chegada = timezone.now()
        primeiro = self.sistema.cadastrar_paciente("Comum", chegada, 4)
        # IDs espaçados simulam uma colisão no mesmo bucket com capacidade 11.
        with patch.object(self.sistema, "_proximo_paciente", primeiro.id + 11):
            urgente = self.sistema.cadastrar_paciente("Urgente", chegada, 1)

        rota = reverse("atendimentos:estruturas")
        resposta = self.client.get(rota)
        indices = resposta.context["indices"]
        self.assertEqual(indices["arvore"]["cor"], "preto")
        self.assertEqual(indices["arvore"]["direita"]["cor"], "vermelho")
        self.assertEqual(indices["heap_pacientes"][0][0], urgente.id)
        self.assertEqual(indices["heap_medicos"][0][1], "Médico fictício")
        self.assertEqual(indices["capacidade_hash"], 11)
        self.assertEqual(indices["buckets"][1], (primeiro.id, urgente.id))
        self.assertEqual(indices["colisoes_hash"], 1)
        self.assertContains(resposta, "Raiz", count=2)
        self.assertContains(resposta, '<a href="/pacientes/?id=1">#1</a>')
        self.assertContains(resposta, '<a href="/pacientes/?id=12">#12</a>')
        self.assertContains(self.client.post(rota), "Índices consistentes.")

        with patch.object(self.sistema, "validar_indices", side_effect=ValueError("Heap inconsistente.")):
            self.assertContains(self.client.post(rota), "Heap inconsistente.", status_code=500)

    def test_demonstracao_gera_colisao_mesmo_quando_cadastro_redimensiona_hash(self):
        rota = reverse("atendimentos:demonstrar_colisao")
        estruturas = reverse("atendimentos:estruturas")
        pacientes = reverse("atendimentos:pacientes")
        cliente = Client(enforce_csrf_checks=True)
        pagina = cliente.get(estruturas)
        self.assertContains(pagina, "Demonstrar colisão")
        self.assertEqual(cliente.get(rota).status_code, 405)
        self.assertEqual(cliente.post(rota).status_code, 403)
        token = cliente.cookies["csrftoken"].value

        for numero in range(1, 8):
            cliente.post(pacientes, {
                "csrfmiddlewaretoken": token, "nome": f"Paciente {numero}", "prioridade": 5,
            })
        self.assertEqual(cliente.get(estruturas).context["indices"]["capacidade_hash"], 11)

        resposta = cliente.post(rota, {"csrfmiddlewaretoken": token}, follow=True)
        self.assertRedirects(resposta, estruturas)
        indices = resposta.context["indices"]
        self.assertEqual(indices["capacidade_hash"], 23)
        self.assertEqual(indices["buckets"][8], (8, 31))
        self.assertEqual(indices["colisoes_hash"], 1)
        for id, nome in ((8, "Paciente fictício A"), (31, "Paciente fictício B")):
            self.assertContains(resposta, f'<a href="{pacientes}?id={id}">#{id}</a>')
            consulta = cliente.get(pacientes, {"id": id}).context["encontrado"]
            self.assertEqual((consulta.id, consulta.nome), (id, nome))
        self.assertContains(cliente.post(estruturas, {"csrfmiddlewaretoken": token}), "Índices consistentes.")
