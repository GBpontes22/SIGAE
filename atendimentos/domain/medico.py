from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SituacaoMedico(StrEnum):
    DISPONIVEL = "disponivel"
    EM_ATENDIMENTO = "em_atendimento"


@dataclass(frozen=True)
class _EstadoMedico:
    situacao: SituacaoMedico = SituacaoMedico.DISPONIVEL
    total_concluidos: int = 0
    ultima_atribuicao: datetime | None = None


class Medico:
    def __init__(self, id: int, nome: str, registro: str):
        if type(id) is not int or id <= 0:
            raise ValueError("O ID do médico deve ser um inteiro positivo.")
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("O nome do médico é obrigatório.")
        if not isinstance(registro, str) or not registro.strip():
            raise ValueError("O registro fictício do médico é obrigatório.")
        self._id = id
        self._nome = nome.strip()
        self._registro = registro.strip()
        self._estado = _EstadoMedico()

    @property
    def id(self) -> int:
        return self._id

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def registro(self) -> str:
        return self._registro

    @property
    def situacao(self) -> SituacaoMedico:
        return self._estado.situacao

    @property
    def total_concluidos(self) -> int:
        return self._estado.total_concluidos

    @property
    def ultima_atribuicao(self) -> datetime | None:
        return self._estado.ultima_atribuicao

    @property
    def chave_disponibilidade(self) -> tuple[int, bool, datetime, int]:
        ultima = self.ultima_atribuicao
        instante = ultima.astimezone(UTC) if ultima else datetime.min.replace(tzinfo=UTC)
        return self.total_concluidos, ultima is not None, instante, self.id

    def iniciar_atendimento(self, inicio: datetime) -> None:
        if self.situacao != SituacaoMedico.DISPONIVEL:
            raise ValueError("O médico já está em atendimento.")
        if not isinstance(inicio, datetime) or inicio.utcoffset() is None:
            raise ValueError("O início do atendimento deve possuir data, hora e fuso.")
        self._estado = _EstadoMedico(
            SituacaoMedico.EM_ATENDIMENTO,
            self.total_concluidos,
            inicio,
        )

    def concluir_atendimento(self) -> None:
        self._liberar(concluido=True)

    def cancelar_atendimento(self) -> None:
        self._liberar(concluido=False)

    def _liberar(self, *, concluido: bool) -> None:
        if self.situacao != SituacaoMedico.EM_ATENDIMENTO:
            raise ValueError("O médico precisa estar em atendimento para ser liberado.")
        self._estado = _EstadoMedico(
            SituacaoMedico.DISPONIVEL,
            self.total_concluidos + int(concluido),
            self.ultima_atribuicao,
        )
