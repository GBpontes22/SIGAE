from collections.abc import Callable
from contextlib import ExitStack
from operator import setitem
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

    def _trocar(self, a: int, b: int, reverter: ExitStack) -> None:
        item_a, item_b = self._itens[a], self._itens[b]
        self._posicoes.registrar_reversao(item_a.id, reverter)
        self._posicoes.atualizar(item_a.id, b)
        self._posicoes.registrar_reversao(item_b.id, reverter)
        self._posicoes.atualizar(item_b.id, a)
        reverter.callback(setitem, self._itens, a, item_a)
        reverter.callback(setitem, self._itens, b, item_b)
        self._itens[a], self._itens[b] = item_b, item_a

    def _menor(self, a: int, b: int) -> bool:
        return self._chave(self._itens[a]) < self._chave(self._itens[b])

    def _subir(self, posicao: int, reverter: ExitStack) -> None:
        while posicao:
            pai = (posicao - 1) // 2
            if not self._menor(posicao, pai):
                return
            self._trocar(posicao, pai, reverter)
            posicao = pai

    def _descer(self, posicao: int, reverter: ExitStack) -> None:
        filho = 2 * posicao + 1
        while filho < len(self):
            direito = filho + 1
            if direito < len(self) and self._menor(direito, filho):
                filho = direito
            if not self._menor(filho, posicao):
                return
            self._trocar(posicao, filho, reverter)
            posicao = filho
            filho = 2 * posicao + 1

    def _reorganizar(self, posicao: int, reverter: ExitStack) -> None:
        if posicao and self._menor(posicao, (posicao - 1) // 2):
            self._subir(posicao, reverter)
        else:
            self._descer(posicao, reverter)

    def _posicao(self, id: int) -> int:
        posicao = self._posicoes.buscar(id)
        if posicao is None:
            raise KeyError(id)
        return posicao

    def inserir(self, item: Registro) -> None:
        posicao = len(self)
        with ExitStack() as reverter:
            self._posicoes.registrar_reversao(item.id, reverter)
            self._posicoes.inserir(item.id, posicao)
            self._itens.append(item)
            reverter.callback(self._itens.pop)
            self._subir(posicao, reverter)
            reverter.pop_all()

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
        with ExitStack() as reverter:
            if posicao != ultimo:
                self._trocar(posicao, ultimo, reverter)
            item = self._itens.pop()
            reverter.callback(self._itens.append, item)
            self._posicoes.registrar_reversao(id, reverter)
            self._posicoes.remover(id)
            if posicao < len(self):
                self._reorganizar(posicao, reverter)
            reverter.pop_all()
            return item

    def atualizar(self, id: int) -> None:
        with ExitStack() as reverter:
            self._reorganizar(self._posicao(id), reverter)
            reverter.pop_all()

    def validar(self) -> None:
        self._posicoes.validar()
        if len(self._posicoes) != len(self):
            raise ValueError("A contagem do Heap difere da Hash de posições.")
        for posicao, item in enumerate(self._itens):
            if self._posicoes.buscar(item.id) != posicao:
                raise ValueError("Uma posição do Heap está inconsistente.")
            if posicao and self._menor(posicao, (posicao - 1) // 2):
                raise ValueError("A ordem do Heap está inconsistente.")
