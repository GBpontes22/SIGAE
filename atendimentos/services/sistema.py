from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo
from threading import RLock

from ..domain.atendimento import Atendimento, SituacaoAtendimento
from ..domain.medico import Medico, SituacaoMedico
from ..domain.paciente import Paciente, SituacaoPaciente
from ..structures.arvore_rubro_negra import ArvoreRubroNegra
from ..structures.min_heap import MinHeap
from ..structures.tabela_hash import TabelaHash


@dataclass(frozen=True, slots=True)
class PacienteNaFila:
    id: int
    nome: str
    chegada: datetime
    prioridade: int
    situacao: SituacaoPaciente

    @classmethod
    def de_paciente(cls, paciente: Paciente) -> "PacienteNaFila":
        return cls(paciente.id, paciente.nome, paciente.chegada, paciente.prioridade, paciente.situacao)


class SistemaAtendimento:
    """Coordena os cadastros e mantém os índices em uma sessão da aplicação."""

    def __init__(self, relogio: Callable[[], datetime] | None = None):
        self._relogio = relogio or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._pacientes: TabelaHash[Paciente] = TabelaHash()
        self._medicos: TabelaHash[Medico] = TabelaHash()
        self._atendimentos: TabelaHash[Atendimento] = TabelaHash()
        self._ativos_por_paciente: TabelaHash[Atendimento] = TabelaHash()
        self._chegadas = ArvoreRubroNegra()
        self._fila = MinHeap[Paciente](lambda paciente: paciente.chave_prioridade)
        self._disponiveis = MinHeap[Medico](lambda medico: medico.chave_disponibilidade)
        self._proximo_paciente = 1
        self._proximo_medico = 1
        self._proximo_atendimento = 1

    @contextmanager
    def _operacao(self) -> Iterator[ExitStack]:
        # As etapas concluídas são desfeitas em ordem inversa se a operação falhar.
        with self._lock, ExitStack() as reverter:
            yield reverter
            reverter.pop_all()

    def cadastrar_paciente(
        self, nome: str, chegada: datetime, prioridade: int, ficha: str = "",
    ) -> Paciente:
        with self._operacao() as reverter:
            paciente = Paciente(self._proximo_paciente, nome, chegada, prioridade, ficha)
            self._inserir_paciente(paciente, reverter)
            self._proximo_paciente += 1
            return paciente

    def _inserir_paciente(self, paciente: Paciente, reverter: ExitStack) -> None:
        self._pacientes.registrar_reversao(paciente.id, reverter)
        self._pacientes.inserir(paciente.id, paciente)
        def desfazer_arvore():
            if self._chegadas.buscar(paciente.chave_chegada) is paciente:
                self._chegadas.remover(paciente.chave_chegada)

        def desfazer_heap():
            if self._fila.buscar(paciente.id) is paciente:
                self._fila.remover(paciente.id)

        reverter.callback(desfazer_arvore)
        self._chegadas.inserir(paciente.chave_chegada, paciente)
        reverter.callback(desfazer_heap)
        self._fila.inserir(paciente)

    def demonstrar_colisao(self) -> tuple[int, int, int]:
        with self._operacao() as reverter:
            capacidade = self._pacientes.capacidade_para(2)
            primeiro_id = self._proximo_paciente
            segundo_id = primeiro_id + capacidade
            chegada = self._relogio()
            self._inserir_paciente(Paciente(primeiro_id, "Paciente fictício A", chegada, 5), reverter)
            self._inserir_paciente(Paciente(segundo_id, "Paciente fictício B", chegada, 5), reverter)
            self._proximo_paciente = segundo_id + 1
            return primeiro_id, segundo_id, primeiro_id % capacidade

    def buscar_paciente(self, id: int) -> Paciente | None:
        with self._lock:
            return self._pacientes.buscar(id)

    def listar_chegadas(self) -> list[Paciente]:
        with self._lock:
            return sorted(self._pacientes.listar_valores(), key=lambda paciente: paciente.chave_chegada)

    def listar_fila(self) -> list[Paciente]:
        with self._lock:
            return self._chegadas.em_ordem()

    def proximo_paciente(self) -> Paciente | None:
        with self._lock:
            return self._fila.consultar_minimo()

    def resumo_triagem(self) -> tuple[tuple[PacienteNaFila, ...], PacienteNaFila | None]:
        with self._lock:
            fila = tuple(PacienteNaFila.de_paciente(paciente) for paciente in self._chegadas.em_ordem())
            raiz = self._fila.consultar_minimo()
            proximo = PacienteNaFila.de_paciente(raiz) if raiz is not None else None
            return fila, proximo

    def reclassificar_paciente(self, id: int, prioridade: int) -> Paciente:
        with self._operacao() as reverter:
            paciente = self.buscar_paciente(id)
            if paciente is None:
                raise KeyError(id)
            anterior = paciente.prioridade
            paciente.reclassificar(prioridade)
            reverter.callback(paciente.reclassificar, anterior)
            self._fila.atualizar(id)
            return paciente

    def cadastrar_medico(self, nome: str, registro: str) -> Medico:
        with self._operacao() as reverter:
            medico = Medico(self._proximo_medico, nome, registro)
            self._medicos.registrar_reversao(medico.id, reverter)
            self._medicos.inserir(medico.id, medico)
            self._disponiveis.inserir(medico)
            self._proximo_medico += 1
            return medico

    def buscar_medico(self, id: int) -> Medico | None:
        with self._lock:
            return self._medicos.buscar(id)

    def listar_medicos(self) -> list[Medico]:
        with self._lock:
            return sorted(self._medicos.listar_valores(), key=lambda medico: medico.id)

    def chamar_proximo(self) -> Atendimento:
        with self._operacao() as reverter:
            paciente = self._fila.consultar_minimo()
            if paciente is None:
                raise ValueError("A fila de pacientes está vazia.")
            medico = self._disponiveis.consultar_minimo()
            if medico is None:
                raise ValueError("Nenhum médico está disponível. O paciente continua na fila.")

            inicio = self._relogio()
            atendimento = Atendimento(self._proximo_atendimento, paciente, medico, inicio)
            self._fila.extrair_minimo()
            reverter.callback(self._fila.inserir, paciente)
            self._chegadas.remover(paciente.chave_chegada)
            reverter.callback(self._chegadas.inserir, paciente.chave_chegada, paciente)
            self._disponiveis.extrair_minimo()
            reverter.callback(self._disponiveis.inserir, medico)
            self._atendimentos.inserir(atendimento.id, atendimento)
            reverter.callback(self._atendimentos.remover, atendimento.id)
            self._ativos_por_paciente.inserir(paciente.id, atendimento)
            reverter.callback(self._ativos_por_paciente.remover, paciente.id)
            reverter.callback(setattr, medico, "_estado", medico._estado)
            medico.iniciar_atendimento(inicio)
            paciente.iniciar_atendimento()
            self._proximo_atendimento += 1
            return atendimento

    def buscar_atendimento(self, id: int) -> Atendimento | None:
        with self._lock:
            return self._atendimentos.buscar(id)

    def concluir_atendimento(self, id: int) -> Atendimento:
        with self._operacao() as reverter:
            atendimento = self.buscar_atendimento(id)
            if atendimento is None:
                raise KeyError(id)
            self._encerrar(atendimento, reverter, concluir=True)
            return atendimento

    def cancelar_paciente(self, id: int) -> Paciente:
        with self._operacao() as reverter:
            paciente = self.buscar_paciente(id)
            if paciente is None:
                raise KeyError(id)
            if paciente.situacao == SituacaoPaciente.AGUARDANDO:
                self._fila.remover(id)
                reverter.callback(self._fila.inserir, paciente)
                self._chegadas.remover(paciente.chave_chegada)
                reverter.callback(self._chegadas.inserir, paciente.chave_chegada, paciente)
                paciente.cancelar()
            elif paciente.situacao == SituacaoPaciente.EM_ATENDIMENTO:
                atendimento = self._ativos_por_paciente.buscar(id)
                if atendimento is None:
                    raise RuntimeError("Paciente em atendimento sem vínculo ativo.")
                self._encerrar(atendimento, reverter, concluir=False)
            else:
                raise ValueError("O paciente já possui um registro encerrado.")
            return paciente

    def cancelar_atendimento(self, id: int) -> Atendimento:
        with self._operacao() as reverter:
            atendimento = self.buscar_atendimento(id)
            if atendimento is None:
                raise KeyError(id)
            self._encerrar(atendimento, reverter, concluir=False)
            return atendimento

    def _encerrar(self, atendimento: Atendimento, reverter: ExitStack, *, concluir: bool) -> None:
        if atendimento.situacao != SituacaoAtendimento.EM_ATENDIMENTO:
            raise ValueError("O atendimento já foi encerrado.")

        paciente, medico = atendimento.paciente, atendimento.medico
        self._ativos_por_paciente.remover(paciente.id)
        reverter.callback(self._ativos_por_paciente.inserir, paciente.id, atendimento)
        reverter.callback(setattr, atendimento, "_fim", atendimento.fim)
        reverter.callback(setattr, atendimento, "_situacao", atendimento.situacao)
        reverter.callback(setattr, medico, "_estado", medico._estado)
        fim = self._relogio()
        if concluir:
            atendimento.concluir(fim)
            medico.concluir_atendimento()
        else:
            atendimento.cancelar(fim)
            medico.cancelar_atendimento()
        self._disponiveis.inserir(medico)
        reverter.callback(self._disponiveis.remover, medico.id)
        if concluir:
            paciente.concluir_atendimento()
        else:
            paciente.cancelar()

    def listar_atendimentos_ativos(self) -> list[Atendimento]:
        with self._lock:
            return sorted(self._ativos_por_paciente.listar_valores(), key=self._chave_atendimento)

    @staticmethod
    def _chave_atendimento(atendimento: Atendimento) -> tuple[datetime, int]:
        return atendimento.inicio.astimezone(UTC), atendimento.id

    def listar_historico(self, medico_id: int | None = None) -> list[Atendimento]:
        with self._lock:
            encerrados = [
                atendimento for atendimento in self._atendimentos.listar_valores()
                if atendimento.fim is not None and (medico_id is None or atendimento.medico.id == medico_id)
            ]
            return sorted(encerrados, key=self._chave_atendimento)

    def obter_indicadores(self) -> dict[str, int]:
        with self._lock:
            contagem = Counter(paciente.situacao for paciente in self._pacientes.listar_valores())
            return {situacao.value: contagem[situacao] for situacao in SituacaoPaciente}

    def resumo_painel(self, fuso: tzinfo) -> dict:
        with self._lock:
            hoje = self._relogio().astimezone(fuso).date()
            concluidos_hoje = sum(
                1
                for atendimento in self._atendimentos.listar_valores()
                if atendimento.situacao == SituacaoAtendimento.CONCLUIDO
                and atendimento.fim is not None
                and atendimento.fim.astimezone(fuso).date() == hoje
            )
            fila = self._fila.primeiros(5)
            medicos = [
                medico for medico in self._medicos.listar_valores()
                if medico.situacao == SituacaoMedico.DISPONIVEL
            ]
            medicos.sort(key=lambda medico: medico.chave_disponibilidade)
            return {
                **self.obter_indicadores(),
                "medicos_disponiveis": len(self._disponiveis),
                "concluidos_hoje": concluidos_hoje,
                "fila": fila,
                "proximo": fila[0] if fila else None,
                "medico_elegivel": self._disponiveis.consultar_minimo(),
                "medicos": medicos,
            }

    def inspecionar_indices(self) -> dict:
        with self._lock:
            self.validar_indices()
            buckets = self._pacientes.chaves_por_bucket()
            return {
                "arvore": self._chegadas.inspecionar(),
                "nos_arvore": len(self._chegadas),
                "heap_pacientes": [
                    (paciente.id, paciente.nome, paciente.prioridade, paciente.chegada)
                    for paciente in self._fila.em_ordem_de_posicao()
                ],
                "heap_medicos": [
                    (medico.id, medico.nome, medico.total_concluidos, medico.ultima_atribuicao)
                    for medico in self._disponiveis.em_ordem_de_posicao()
                ],
                "buckets": buckets,
                "capacidade_hash": self._pacientes.capacidade,
                "registros_hash": len(self._pacientes),
                "colisoes_hash": sum(len(bucket) > 1 for bucket in buckets),
            }

    def validar_indices(self) -> None:
        with self._lock:
            for indice in (
                self._pacientes, self._medicos, self._atendimentos, self._ativos_por_paciente,
                self._chegadas, self._fila, self._disponiveis,
            ):
                indice.validar()
            pacientes = self._pacientes.listar_valores()
            aguardando = [p for p in pacientes if p.situacao == SituacaoPaciente.AGUARDANDO]
            if len(aguardando) != len(self._fila) or len(aguardando) != len(self._chegadas):
                raise ValueError("A contagem de pacientes em espera diverge dos índices.")
            for paciente in aguardando:
                if (self._fila.buscar(paciente.id) is not paciente
                        or self._chegadas.buscar(paciente.chave_chegada) is not paciente):
                    raise ValueError("Um paciente aguardando não está nos dois índices.")

            ativos = []
            concluidos = Counter()
            for atendimento in self._atendimentos.listar_valores():
                paciente, medico = atendimento.paciente, atendimento.medico
                if self._pacientes.buscar(paciente.id) is not paciente or self._medicos.buscar(medico.id) is not medico:
                    raise ValueError("O atendimento referencia um cadastro inexistente.")
                if atendimento.situacao.value != paciente.situacao.value:
                    raise ValueError("O paciente e o atendimento têm situações incompatíveis.")
                if atendimento.situacao == SituacaoAtendimento.EM_ATENDIMENTO:
                    ativos.append(atendimento)
                    if self._ativos_por_paciente.buscar(paciente.id) is not atendimento or atendimento.fim is not None:
                        raise ValueError("Um vínculo ativo está inconsistente.")
                elif atendimento.fim is None:
                    raise ValueError("Um atendimento encerrado não possui horário final.")
                elif atendimento.situacao == SituacaoAtendimento.CONCLUIDO:
                    concluidos[medico.id] += 1

            pacientes_ativos = {a.paciente.id for a in ativos}
            medicos_ativos = {a.medico.id for a in ativos}
            if (len(ativos) != len(self._ativos_por_paciente)
                    or len(ativos) != len(medicos_ativos)
                    or pacientes_ativos != {p.id for p in pacientes if p.situacao == SituacaoPaciente.EM_ATENDIMENTO}):
                raise ValueError("Há vínculos órfãos ou duplicados entre os atendimentos ativos.")
            medicos = self._medicos.listar_valores()
            if len(self._disponiveis) + len(medicos_ativos) != len(medicos):
                raise ValueError("A contagem de médicos disponíveis é inconsistente.")
            for medico in medicos:
                ocupado = medico.id in medicos_ativos
                esperado = SituacaoMedico.EM_ATENDIMENTO if ocupado else SituacaoMedico.DISPONIVEL
                disponivel = self._disponiveis.buscar(medico.id)
                if medico.situacao != esperado or disponivel is not (None if ocupado else medico):
                    raise ValueError("A situação do médico diverge da fila de disponíveis.")
                if medico.total_concluidos != concluidos[medico.id]:
                    raise ValueError("O contador do médico diverge do histórico.")
