from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from itertools import count
from unittest import TestCase
from unittest.mock import patch

from atendimentos.domain.atendimento import SituacaoAtendimento
from atendimentos.domain.medico import SituacaoMedico
from atendimentos.domain.paciente import SituacaoPaciente
from atendimentos.services.sistema import SistemaAtendimento


class SistemaTests(TestCase):
    def setUp(self):
        self.agora = datetime(2026, 11, 26, 8, tzinfo=UTC)
        segundos = count()
        self.sistema = SistemaAtendimento(lambda: self.agora + timedelta(hours=1, seconds=next(segundos)))
        self.medicos = [self.sistema.cadastrar_medico(nome, f"SIM-{nome}") for nome in ("A", "B", "C")]

    def _paciente(self, nome, prioridade=3, minutos=0):
        return self.sistema.cadastrar_paciente(nome, self.agora + timedelta(minutes=minutos), prioridade)

    def test_tres_medicos_e_chamada_sem_disponibilidade_preserva_fila(self):
        normal = self._paciente("Normal", 4)
        urgencia = self._paciente("Urgência", 2, 1)
        emergencia = self._paciente("Emergência", 1, 2)
        ultimo = self._paciente("Último", 5, 3)
        self.assertEqual(self.sistema.listar_fila(), [normal, urgencia, emergencia, ultimo])
        chamadas = [self.sistema.chamar_proximo() for _ in range(3)]
        self.assertEqual([a.paciente for a in chamadas], [emergencia, urgencia, normal])
        self.assertEqual([a.medico for a in chamadas], self.medicos)

        with self.assertRaisesRegex(ValueError, "Nenhum médico"):
            self.sistema.chamar_proximo()
        self.assertEqual(self.sistema.listar_fila(), [ultimo])
        self.assertIs(self.sistema.proximo_paciente(), ultimo)
        self.assertEqual(ultimo.situacao, SituacaoPaciente.AGUARDANDO)
        self.sistema.validar_indices()

        chamado_b = chamadas[1]
        self.sistema.concluir_atendimento(chamado_b.id)
        self.assertEqual(chamado_b.medico.total_concluidos, 1)
        self.assertIs(self.sistema.chamar_proximo().medico, chamado_b.medico)
        self.sistema.validar_indices()

    def test_medico_com_menos_conclusoes_e_desempate_pela_ultima_atribuicao(self):
        for esperado in self.medicos:
            self._paciente("Paciente")
            atendimento = self.sistema.chamar_proximo()
            self.assertIs(atendimento.medico, esperado)
            self.sistema.concluir_atendimento(atendimento.id)

        # Cada médico concluiu uma vez. O médico A recebeu o primeiro paciente.
        paciente_a = self._paciente("Com A")
        atendimento_a = self.sistema.chamar_proximo()
        self.assertIs(atendimento_a.medico, self.medicos[0])
        self.assertIs(atendimento_a.paciente, paciente_a)
        self.sistema.concluir_atendimento(atendimento_a.id)
        with self.assertRaises(ValueError):
            self.sistema.concluir_atendimento(atendimento_a.id)
        self.assertEqual(self.medicos[0].total_concluidos, 2)

        self._paciente("Com B")
        atendimento_b = self.sistema.chamar_proximo()
        self.assertIs(atendimento_b.medico, self.medicos[1])
        self.sistema.cancelar_atendimento(atendimento_b.id)
        self.assertEqual(atendimento_b.medico.total_concluidos, 1)
        self.assertEqual(atendimento_b.situacao, SituacaoAtendimento.CANCELADO)
        self.assertEqual(atendimento_b.medico.situacao, SituacaoMedico.DISPONIVEL)
        self.assertIn(atendimento_b, self.sistema.listar_historico(atendimento_b.medico.id))

        self._paciente("Com C")
        self.assertIs(self.sistema.chamar_proximo().medico, self.medicos[2])
        self.sistema.validar_indices()

    def test_reclassifica_consulta_e_cancela_sem_deixar_indice_orfao(self):
        primeiro = self._paciente("Primeiro", 2)
        segundo = self._paciente("Segundo", 3, 1)
        self.sistema.reclassificar_paciente(segundo.id, 1)
        self.assertEqual(self.sistema.listar_fila(), [primeiro, segundo])
        self.assertIs(self.sistema.proximo_paciente(), segundo)
        atendimento = self.sistema.chamar_proximo()
        self.assertIs(atendimento.paciente, segundo)
        self.sistema.cancelar_paciente(primeiro.id)
        self.sistema.cancelar_paciente(segundo.id)
        self.assertEqual(self.sistema.listar_fila(), [])
        self.assertEqual(self.sistema.listar_atendimentos_ativos(), [])
        self.assertEqual(self.sistema.listar_historico(), [atendimento])
        self.assertIs(self.sistema.buscar_paciente(primeiro.id), primeiro)
        self.assertEqual(self.sistema.obter_indicadores()["cancelado"], 2)
        self.sistema.validar_indices()

    def test_falha_intermediaria_em_cadastro_chamada_e_conclusao_desfaz_operacao(self):
        with patch.object(self.sistema._fila, "inserir", side_effect=RuntimeError("falha")):
            with self.assertRaisesRegex(RuntimeError, "falha"):
                self._paciente("Parcial")
        self.assertEqual(self.sistema.listar_chegadas(), [])
        self.sistema.validar_indices()

        paciente = self._paciente("Válido")
        self.assertEqual(paciente.id, 1)
        with patch.object(self.sistema._ativos_por_paciente, "inserir", side_effect=RuntimeError("falha")):
            with self.assertRaisesRegex(RuntimeError, "falha"):
                self.sistema.chamar_proximo()
        self.assertEqual(self.sistema.listar_fila(), [paciente])
        self.assertIsNone(self.sistema.buscar_atendimento(1))
        self.sistema.validar_indices()

        atendimento = self.sistema.chamar_proximo()
        with patch.object(self.sistema._disponiveis, "inserir", side_effect=RuntimeError("falha")):
            with self.assertRaisesRegex(RuntimeError, "falha"):
                self.sistema.concluir_atendimento(atendimento.id)
        self.assertIsNone(atendimento.fim)
        self.assertEqual(atendimento.medico.total_concluidos, 0)
        self.assertEqual(atendimento.medico.situacao, SituacaoMedico.EM_ATENDIMENTO)
        self.assertEqual(self.sistema.listar_atendimentos_ativos(), [atendimento])
        self.sistema.validar_indices()

    def test_chamadas_concorrentes_nao_duplicam_paciente_ou_medico(self):
        for id in range(8):
            self._paciente(f"Paciente {id}")

        def chamar(_):
            try:
                return self.sistema.chamar_proximo()
            except ValueError:
                return None

        with ThreadPoolExecutor(max_workers=8) as executor:
            chamados = [a for a in executor.map(chamar, range(8)) if a is not None]
        self.assertEqual(len(chamados), 3)
        self.assertEqual(len({a.paciente.id for a in chamados}), 3)
        self.assertEqual(len({a.medico.id for a in chamados}), 3)
        self.assertEqual(len(self.sistema.listar_fila()), 5)
        self.sistema.validar_indices()

    def test_falha_durante_troca_no_heap_reverte_cadastro_e_permite_repetir(self):
        anteriores = [self._paciente(f"Paciente {n}", 4) for n in range(8)]
        fila = self.sistema._fila
        vetor = fila.em_ordem_de_posicao()
        capacidade = fila._posicoes.capacidade
        cadastro = self.sistema._pacientes.chaves_por_bucket()
        atualizar = fila._posicoes.atualizar
        chamadas = count()

        def falhar_depois_da_gravacao(id, posicao):
            atualizar(id, posicao)
            if next(chamadas) == 2:
                raise RuntimeError("falha após atualizar a posição")

        with patch.object(fila._posicoes, "atualizar", side_effect=falhar_depois_da_gravacao):
            with self.assertRaisesRegex(RuntimeError, "falha após atualizar a posição"):
                self._paciente("Cadastro parcial", 1)

        self.assertEqual(fila.em_ordem_de_posicao(), vetor)
        self.assertEqual(fila._posicoes.capacidade, capacidade)
        self.assertEqual(self.sistema._pacientes.chaves_por_bucket(), cadastro)
        self.assertIsNone(fila.buscar(9))
        self.assertIsNone(self.sistema.buscar_paciente(9))
        self.assertEqual(self.sistema.listar_fila(), anteriores)
        self.sistema.validar_indices()

        novo = self._paciente("Cadastro repetido", 1)
        self.assertEqual(novo.id, 9)
        self.assertIs(self.sistema.proximo_paciente(), novo)
        self.sistema.validar_indices()

    def test_falha_durante_reclassificacao_preserva_prioridade_e_indices(self):
        primeiro = self._paciente("Primeiro", 3)
        segundo = self._paciente("Segundo", 4)
        fila = self.sistema._fila
        atualizar = fila._posicoes.atualizar

        def falhar_depois_da_gravacao(id, posicao):
            atualizar(id, posicao)
            raise RuntimeError("falha persistente durante a troca")

        with patch.object(fila._posicoes, "atualizar", side_effect=falhar_depois_da_gravacao) as falha:
            with self.assertRaisesRegex(RuntimeError, "falha persistente"):
                self.sistema.reclassificar_paciente(segundo.id, 1)
            falha.assert_called_once()

        self.assertEqual(segundo.prioridade, 4)
        self.assertIs(self.sistema.proximo_paciente(), primeiro)
        self.sistema.validar_indices()

    def test_falha_no_cancelamento_restaura_espera_e_atendimento_ativo(self):
        aguardando = self._paciente("Na fila", 4)
        ativo = self._paciente("Em atendimento", 1)
        atendimento = self.sistema.chamar_proximo()
        medico = atendimento.medico

        with patch.object(self.sistema._chegadas, "remover", side_effect=RuntimeError("falha na árvore")):
            with self.assertRaisesRegex(RuntimeError, "falha na árvore"):
                self.sistema.cancelar_paciente(aguardando.id)
        self.assertEqual(aguardando.situacao, SituacaoPaciente.AGUARDANDO)
        self.assertEqual(self.sistema.listar_fila(), [aguardando])
        self.assertIs(self.sistema.proximo_paciente(), aguardando)
        self.sistema.validar_indices()

        with patch.object(self.sistema._disponiveis, "inserir", side_effect=RuntimeError("falha no heap")):
            with self.assertRaisesRegex(RuntimeError, "falha no heap"):
                self.sistema.cancelar_atendimento(atendimento.id)
        self.assertEqual(ativo.situacao, SituacaoPaciente.EM_ATENDIMENTO)
        self.assertEqual(atendimento.situacao, SituacaoAtendimento.EM_ATENDIMENTO)
        self.assertIsNone(atendimento.fim)
        self.assertEqual(self.sistema.listar_atendimentos_ativos(), [atendimento])
        self.assertEqual(medico.situacao, SituacaoMedico.EM_ATENDIMENTO)
        self.assertEqual(medico.total_concluidos, 0)
        self.assertEqual(self.sistema.listar_historico(), [])
        self.sistema.validar_indices()

        self.sistema.cancelar_paciente(aguardando.id)
        self.sistema.cancelar_atendimento(atendimento.id)
        self.assertEqual(medico.situacao, SituacaoMedico.DISPONIVEL)
        self.assertEqual(medico.total_concluidos, 0)
        self.assertEqual(self.sistema.listar_historico(), [atendimento])
        self.sistema.validar_indices()

    def test_falha_depois_da_insercao_no_heap_restaura_cadastro(self):
        anterior = self._paciente("Anterior", 4)
        inserir = self.sistema._fila.inserir

        def falhar(paciente):
            inserir(paciente)
            raise RuntimeError("Falha após inserção")

        with patch.object(self.sistema._fila, "inserir", side_effect=falhar):
            with self.assertRaisesRegex(RuntimeError, "após inserção"):
                self._paciente("Urgente", 1)
        self.assertIsNone(self.sistema.buscar_paciente(anterior.id + 1))
        self.assertIs(self.sistema.proximo_paciente(), anterior)
        self.assertEqual(self.sistema.listar_fila(), [anterior])
        self.sistema.validar_indices()
        novo = self._paciente("Urgente", 1)
        self.assertIs(self.sistema.proximo_paciente(), novo)
        self.sistema.validar_indices()

    def test_chamada_anterior_a_chegada_preserva_fila_e_medico(self):
        paciente = self._paciente("Aguardando", minutos=2)
        with patch.object(self.sistema, "_relogio", return_value=self.agora):
            with self.assertRaisesRegex(ValueError, "anteceder a chegada"):
                self.sistema.cancelar_paciente(paciente.id)
            with self.assertRaisesRegex(ValueError, "anteceder a chegada"):
                self.sistema.chamar_proximo()
        self.assertEqual(self.sistema.listar_fila(), [paciente])
        self.assertEqual(self.sistema.listar_atendimentos_ativos(), [])
        self.sistema.validar_indices()
        with patch.object(self.sistema, "_relogio", return_value=paciente.chegada):
            atendimento = self.sistema.chamar_proximo()
        self.assertIs(atendimento.medico, self.medicos[0])
        self.assertIs(atendimento.paciente, paciente)
