from collections.abc import Callable
from typing import Generic

from ..contratos import Registro
from .tabela_hash import TabelaHash


class MinHeap(Generic[Registro]):
    """Heap binário com tabela própria para localizar posições por ID."""

    def __init__(self, chave: Callable[[Registro], tuple]):
        self._chave = chave
        self._itens: list[Registro] = []
        self._posicoes: TabelaHash[int] = TabelaHash()

    def __len__(self) -> int:
        return len(self._itens)

    def _trocar(self, a: int, b: int) -> None:
        self._itens[a], self._itens[b] = self._itens[b], self._itens[a]
        self._posicoes.atualizar(self._itens[a].id, a)
        self._posicoes.atualizar(self._itens[b].id, b)

    def _menor(self, a: int, b: int) -> bool:
        return self._chave(self._itens[a]) < self._chave(self._itens[b])

    def _subir(self, posicao: int) -> None:
        while posicao:
            pai = (posicao - 1) // 2
            if not self._menor(posicao, pai):
                return
            self._trocar(posicao, pai)
            posicao = pai

    def _descer(self, posicao: int) -> None:
        filho = 2 * posicao + 1
        while filho < len(self):
            direito = filho + 1
            if direito < len(self) and self._menor(direito, filho):
                filho = direito
            if not self._menor(filho, posicao):
                return
            self._trocar(posicao, filho)
            posicao = filho
            filho = 2 * posicao + 1

    def _reorganizar(self, posicao: int) -> None:
        if posicao and self._menor(posicao, (posicao - 1) // 2):
            self._subir(posicao)
        else:
            self._descer(posicao)

    def _posicao(self, id: int) -> int:
        posicao = self._posicoes.buscar(id)
        if posicao is None:
            raise KeyError(id)
        return posicao

    def inserir(self, item: Registro) -> None:
        posicao = len(self)
        self._posicoes.inserir(item.id, posicao)
        self._itens.append(item)
        self._subir(posicao)

    def consultar_minimo(self) -> Registro | None:
        return self._itens[0] if self._itens else None

    def em_ordem_de_posicao(self) -> tuple[Registro, ...]:
        """Consulta a disposição interna, da raiz ao fim do vetor."""
        return tuple(self._itens)

    def primeiros(self, limite: int) -> list[Registro]:
        """Consulta os primeiros itens, sem modificar o heap."""
        if limite <= 0 or not self._itens:
            return []
        resultado = []
        candidatos = [0]
        while candidatos and len(resultado) < limite:
            # Só os filhos dos nós já exibidos podem conter o próximo mínimo.
            posicao = min(candidatos, key=lambda indice: self._chave(self._itens[indice]))
            candidatos.remove(posicao)
            resultado.append(self._itens[posicao])
            for filho in (2 * posicao + 1, 2 * posicao + 2):
                if filho < len(self):
                    candidatos.append(filho)
        return resultado

    def buscar(self, id: int) -> Registro | None:
        posicao = self._posicoes.buscar(id)
        return None if posicao is None else self._itens[posicao]

    def extrair_minimo(self) -> Registro:
        if not self._itens:
            raise IndexError("O Heap está vazio.")
        return self.remover(self._itens[0].id)

    def remover(self, id: int) -> Registro:
        posicao = self._posicao(id)
        ultimo = len(self) - 1
        if posicao != ultimo:
            self._trocar(posicao, ultimo)
        item = self._itens.pop()
        self._posicoes.remover(id)
        if posicao < len(self):
            self._reorganizar(posicao)
        return item

    def atualizar(self, id: int) -> None:
        self._reorganizar(self._posicao(id))

    def validar(self) -> None:
        self._posicoes.validar()
        if len(self._posicoes) != len(self):
            raise ValueError("A contagem do Heap difere da Hash de posições.")
        for posicao, item in enumerate(self._itens):
            if self._posicoes.buscar(item.id) != posicao:
                raise ValueError("Uma posição do Heap está inconsistente.")
            if posicao and self._menor(posicao, (posicao - 1) // 2):
                raise ValueError("A ordem do Heap está inconsistente.")
