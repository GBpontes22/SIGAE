from contextlib import ExitStack
from typing import Generic

from ..contratos import Valor


class TabelaHash(Generic[Valor]):
    """Tabela com dispersão modular e encadeamento separado."""

    def __init__(self, capacidade: int = 11, fator_carga_maximo: float = 0.75):
        if type(capacidade) is not int or capacidade < 1:
            raise ValueError("A capacidade deve ser um inteiro positivo.")
        if not 0 < fator_carga_maximo <= 1:
            raise ValueError("O fator de carga deve estar entre zero e um.")
        self._buckets: list[list[tuple[int, Valor]]] = [[] for _ in range(capacidade)]
        self._quantidade = 0
        self._limite = fator_carga_maximo

    @property
    def capacidade(self) -> int:
        return len(self._buckets)

    def __len__(self) -> int:
        return self._quantidade

    def capacidade_para(self, novas_chaves: int) -> int:
        capacidade = self.capacidade
        while self._quantidade + novas_chaves > capacidade * self._limite:
            capacidade = capacidade * 2 + 1
        return capacidade

    def _localizar(self, chave: int) -> tuple[list[tuple[int, Valor]], int | None]:
        if type(chave) is not int:
            raise ValueError("A chave da Hash deve ser um inteiro.")
        bucket = self._buckets[chave % self.capacidade]
        for posicao, (atual, _) in enumerate(bucket):
            if chave == atual:
                return bucket, posicao
        return bucket, None

    def inserir(self, chave: int, valor: Valor) -> None:
        if valor is None:
            raise ValueError("None representa uma chave ausente.")
        bucket, posicao = self._localizar(chave)
        if posicao is not None:
            raise ValueError(f"Chave duplicada: {chave}.")
        capacidade = self.capacidade_para(1)
        if capacidade != self.capacidade:
            self._redimensionar(capacidade)
            bucket = self._buckets[chave % self.capacidade]
        bucket.append((chave, valor))
        self._quantidade += 1

    def _redimensionar(self, capacidade: int) -> None:
        novos: list[list[tuple[int, Valor]]] = [[] for _ in range(capacidade)]
        for bucket in self._buckets:
            for registro in bucket:
                novos[registro[0] % capacidade].append(registro)
        self._buckets = novos

    def buscar(self, chave: int) -> Valor | None:
        bucket, posicao = self._localizar(chave)
        return None if posicao is None else bucket[posicao][1]

    def atualizar(self, chave: int, valor: Valor) -> None:
        bucket, posicao = self._localizar(chave)
        if posicao is None:
            raise KeyError(chave)
        if valor is None:
            raise ValueError("None representa uma chave ausente.")
        bucket[posicao] = (chave, valor)

    def remover(self, chave: int) -> Valor:
        bucket, posicao = self._localizar(chave)
        if posicao is None:
            raise KeyError(chave)
        _, valor = bucket.pop(posicao)
        self._quantidade -= 1
        return valor

    def registrar_reversao(self, chave: int, reverter: ExitStack) -> None:
        """Guarda só o bucket afetado e recupera a tabela anterior se houver rehash."""
        bucket, _ = self._localizar(chave)
        buckets = self._buckets
        registros = bucket.copy()
        quantidade = self._quantidade

        def restaurar() -> None:
            bucket[:] = registros
            self._buckets = buckets
            self._quantidade = quantidade

        reverter.callback(restaurar)

    def listar_valores(self) -> list[Valor]:
        return [valor for bucket in self._buckets for _, valor in bucket]

    def chaves_por_bucket(self) -> tuple[tuple[int, ...], ...]:
        return tuple(tuple(chave for chave, _ in bucket) for bucket in self._buckets)

    def validar(self) -> None:
        quantidade = 0
        chaves: set[int] = set()
        for indice, bucket in enumerate(self._buckets):
            for chave, valor in bucket:
                if chave % self.capacidade != indice or chave in chaves or valor is None:
                    raise ValueError("A Tabela Hash contém um registro inconsistente.")
                chaves.add(chave)
                quantidade += 1
        if quantidade != len(self):
            raise ValueError("A contagem de registros da Tabela Hash está incorreta.")
