from datetime import UTC, datetime, timedelta
from random import Random
from unittest import TestCase

from atendimentos.domain.paciente import Paciente
from atendimentos.structures.arvore_rubro_negra import ArvoreRubroNegra
from atendimentos.structures.min_heap import MinHeap
from atendimentos.structures.tabela_hash import TabelaHash


CHEGADA = datetime(2026, 11, 26, 8, tzinfo=UTC)


class EstruturasTests(TestCase):
    def test_hash_colisoes_redimensionamento_e_remocao(self):
        tabela = TabelaHash(5)
        for id in (1, 6, 11):
            tabela.inserir(id, str(id))
        self.assertEqual(tabela.capacidade, 5)
        self.assertEqual(tabela.buscar(6), "6")
        with self.assertRaises(ValueError):
            tabela.inserir(6, "duplicado")

        tabela.inserir(16, "16")
        self.assertGreater(tabela.capacidade, 5)
        self.assertEqual(set(tabela.listar_valores()), {"1", "6", "11", "16"})
        tabela.atualizar(11, "atualizado")
        self.assertEqual(tabela.remover(11), "atualizado")
        self.assertIsNone(tabela.buscar(11))
        with self.assertRaises(KeyError):
            tabela.remover(11)
        self.assertEqual(len(tabela), 3)
        tabela.validar()

    def test_heap_reclassifica_nas_duas_direcoes_e_remove_por_id(self):
        heap = MinHeap(lambda paciente: paciente.chave_prioridade)
        primeiro = Paciente(1, "A", CHEGADA, 3)
        urgente = Paciente(2, "B", CHEGADA + timedelta(minutes=1), 2)
        terceiro = Paciente(3, "C", CHEGADA, 4)
        for paciente in (primeiro, urgente, terceiro):
            heap.inserir(paciente)
        self.assertIs(heap.consultar_minimo(), urgente)
        primeiro.reclassificar(1)
        heap.atualizar(primeiro.id)
        self.assertIs(heap.consultar_minimo(), primeiro)
        primeiro.reclassificar(5)
        heap.atualizar(primeiro.id)
        self.assertIs(heap.consultar_minimo(), urgente)
        self.assertIs(heap.remover(primeiro.id), primeiro)
        self.assertIsNone(heap.buscar(primeiro.id))
        heap.validar()
        self.assertIs(heap.extrair_minimo(), urgente)
        self.assertIs(heap.extrair_minimo(), terceiro)
        with self.assertRaises(IndexError):
            heap.extrair_minimo()
        heap.validar()

    def test_arvore_balanceia_insercoes_e_remocoes_com_chegadas_empatadas(self):
        arvore = ArvoreRubroNegra()
        pacientes = [
            Paciente(id, "Paciente", CHEGADA + timedelta(minutes=id % 17), 3)
            for id in range(1, 101)
        ]
        aleatorio = Random(712)
        aleatorio.shuffle(pacientes)
        for paciente in pacientes:
            arvore.inserir(paciente.chave_chegada, paciente)
            arvore.validar()
        self.assertEqual(arvore.em_ordem(), sorted(pacientes, key=lambda p: p.chave_chegada))
        with self.assertRaises(ValueError):
            arvore.inserir(pacientes[0].chave_chegada, pacientes[0])

        aleatorio.shuffle(pacientes)
        for paciente in pacientes:
            self.assertIs(arvore.buscar(paciente.chave_chegada), paciente)
            self.assertIs(arvore.remover(paciente.chave_chegada), paciente)
            self.assertIsNone(arvore.buscar(paciente.chave_chegada))
            arvore.validar()
        self.assertEqual(arvore.em_ordem(), [])
        self.assertEqual(len(arvore), 0)
