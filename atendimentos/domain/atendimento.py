from datetime import UTC, datetime
from enum import StrEnum

from .medico import Medico
from .paciente import Paciente


class SituacaoAtendimento(StrEnum):
    EM_ATENDIMENTO = "em_atendimento"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class Atendimento:
    def __init__(self, id: int, paciente: Paciente, medico: Medico, inicio: datetime):
        if type(id) is not int or id <= 0:
            raise ValueError("O ID do atendimento deve ser um inteiro positivo.")
        if not isinstance(inicio, datetime) or inicio.utcoffset() is None:
            raise ValueError("O início do atendimento deve possuir data, hora e fuso.")
        self._id = id
        self._paciente = paciente
        self._medico = medico
        self._inicio = inicio
        self._fim: datetime | None = None
        self._situacao = SituacaoAtendimento.EM_ATENDIMENTO

    @property
    def id(self) -> int:
        return self._id

    @property
    def paciente(self) -> Paciente:
        return self._paciente

    @property
    def medico(self) -> Medico:
        return self._medico

    @property
    def inicio(self) -> datetime:
        return self._inicio

    @property
    def fim(self) -> datetime | None:
        return self._fim

    @property
    def situacao(self) -> SituacaoAtendimento:
        return self._situacao

    def concluir(self, fim: datetime) -> None:
        self._encerrar(fim, SituacaoAtendimento.CONCLUIDO)

    def cancelar(self, fim: datetime) -> None:
        self._encerrar(fim, SituacaoAtendimento.CANCELADO)

    def _encerrar(self, fim: datetime, situacao: SituacaoAtendimento) -> None:
        if self.situacao != SituacaoAtendimento.EM_ATENDIMENTO:
            raise ValueError("O atendimento já foi encerrado.")
        if not isinstance(fim, datetime) or fim.utcoffset() is None:
            raise ValueError("O fim do atendimento deve possuir data, hora e fuso.")
        if fim.astimezone(UTC) < self.inicio.astimezone(UTC):
            raise ValueError("O encerramento não pode anteceder o início do atendimento.")
        self._fim = fim
        self._situacao = situacao
