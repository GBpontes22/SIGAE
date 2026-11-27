from ..contratos import ChaveChegada
from ..domain.paciente import Paciente


class _No:
    def __init__(self, chave: ChaveChegada | None, paciente: Paciente | None, vermelho: bool):
        self.chave = chave
        self.paciente = paciente
        self.vermelho = vermelho
        self.esquerda = self.direita = self.pai = self


class ArvoreRubroNegra:
    """Índice cronológico balanceado, com uma sentinela preta nas folhas."""

    def __init__(self):
        self._nil = _No(None, None, False)
        self._raiz = self._nil
        self._quantidade = 0

    def __len__(self) -> int:
        return self._quantidade

    def _buscar_no(self, chave: ChaveChegada) -> _No:
        no = self._raiz
        while no is not self._nil and no.chave != chave:
            no = no.esquerda if chave < no.chave else no.direita
        return no

    def buscar(self, chave: ChaveChegada) -> Paciente | None:
        return self._buscar_no(chave).paciente

    def inserir(self, chave: ChaveChegada, paciente: Paciente) -> None:
        # A chave canônica usa UTC, inclusive quando há repetição da hora local.
        if chave != paciente.chave_chegada:
            raise ValueError("A chave deve corresponder à chegada e ao ID do paciente.")
        pai = self._nil
        atual = self._raiz
        while atual is not self._nil:
            pai = atual
            if chave == atual.chave:
                raise ValueError("Chave de chegada duplicada.")
            atual = atual.esquerda if chave < atual.chave else atual.direita

        no = _No(chave, paciente, True)
        no.pai = pai
        no.esquerda = no.direita = self._nil
        if pai is self._nil:
            self._raiz = no
        elif chave < pai.chave:
            pai.esquerda = no
        else:
            pai.direita = no
        self._corrigir_insercao(no)
        self._quantidade += 1

    def _substituir(self, no: _No, novo: _No) -> None:
        if no.pai is self._nil:
            self._raiz = novo
        elif no is no.pai.esquerda:
            no.pai.esquerda = novo
        else:
            no.pai.direita = novo
        novo.pai = no.pai

    def _girar_esquerda(self, no: _No) -> None:
        promovido = no.direita
        no.direita = promovido.esquerda
        if no.direita is not self._nil:
            no.direita.pai = no
        self._substituir(no, promovido)
        promovido.esquerda = no
        no.pai = promovido

    def _girar_direita(self, no: _No) -> None:
        promovido = no.esquerda
        no.esquerda = promovido.direita
        if no.esquerda is not self._nil:
            no.esquerda.pai = no
        self._substituir(no, promovido)
        promovido.direita = no
        no.pai = promovido

    def _corrigir_insercao(self, no: _No) -> None:
        while no.pai.vermelho:
            pai = no.pai
            avo = pai.pai
            pai_esquerdo = pai is avo.esquerda
            tio = avo.direita if pai_esquerdo else avo.esquerda
            if tio.vermelho:
                pai.vermelho = tio.vermelho = False
                avo.vermelho = True
                no = avo
                continue

            filho_interno = pai.direita if pai_esquerdo else pai.esquerda
            girar_pai = self._girar_esquerda if pai_esquerdo else self._girar_direita
            girar_avo = self._girar_direita if pai_esquerdo else self._girar_esquerda
            if no is filho_interno:
                girar_pai(pai)
                no, pai = pai, no
            pai.vermelho = False
            avo.vermelho = True
            girar_avo(avo)
        self._raiz.vermelho = False

    def remover(self, chave: ChaveChegada) -> Paciente:
        no = self._buscar_no(chave)
        if no is self._nil:
            raise KeyError(chave)
        paciente = no.paciente
        vermelho = no.vermelho
        if no.esquerda is self._nil:
            filho = no.direita
            self._substituir(no, filho)
        elif no.direita is self._nil:
            filho = no.esquerda
            self._substituir(no, filho)
        else:
            sucessor = no.direita
            while sucessor.esquerda is not self._nil:
                sucessor = sucessor.esquerda
            vermelho = sucessor.vermelho
            filho = sucessor.direita
            if sucessor.pai is no:
                filho.pai = sucessor
            else:
                self._substituir(sucessor, filho)
                sucessor.direita = no.direita
                sucessor.direita.pai = sucessor
            self._substituir(no, sucessor)
            sucessor.esquerda = no.esquerda
            sucessor.esquerda.pai = sucessor
            sucessor.vermelho = no.vermelho

        if not vermelho:
            self._corrigir_remocao(filho)
        self._nil.pai = self._nil
        self._quantidade -= 1
        return paciente

    def _corrigir_remocao(self, no: _No) -> None:
        while no is not self._raiz and not no.vermelho:
            pai = no.pai
            esquerda = no is pai.esquerda
            girar_pai = self._girar_esquerda if esquerda else self._girar_direita
            girar_irmao = self._girar_direita if esquerda else self._girar_esquerda
            irmao = pai.direita if esquerda else pai.esquerda

            if irmao.vermelho:
                irmao.vermelho = False
                pai.vermelho = True
                girar_pai(pai)
                irmao = pai.direita if esquerda else pai.esquerda

            perto = irmao.esquerda if esquerda else irmao.direita
            longe = irmao.direita if esquerda else irmao.esquerda
            if not perto.vermelho and not longe.vermelho:
                irmao.vermelho = True
                no = pai
                continue

            if not longe.vermelho:
                perto.vermelho = False
                irmao.vermelho = True
                girar_irmao(irmao)
                longe, irmao = irmao, perto
            irmao.vermelho = pai.vermelho
            pai.vermelho = longe.vermelho = False
            girar_pai(pai)
            break
        else:
            no.vermelho = False

    def em_ordem(self) -> list[Paciente]:
        pacientes: list[Paciente] = []

        def percorrer(no: _No) -> None:
            if no is not self._nil:
                percorrer(no.esquerda)
                pacientes.append(no.paciente)
                percorrer(no.direita)

        percorrer(self._raiz)
        return pacientes

    def inspecionar(self) -> dict | None:
        """Retorna os nós, seus ramos e cores sem expor objetos mutáveis da árvore."""
        def copiar(no: _No) -> dict | None:
            if no is self._nil:
                return None
            return {
                "id": no.paciente.id,
                "nome": no.paciente.nome,
                "chegada": no.paciente.chegada,
                "cor": "vermelho" if no.vermelho else "preto",
                "esquerda": copiar(no.esquerda),
                "direita": copiar(no.direita),
            }

        return copiar(self._raiz)

    def validar(self) -> None:
        if self._nil.vermelho or self._raiz.vermelho or self._raiz.pai is not self._nil:
            raise ValueError("A raiz e a sentinela da árvore devem ser pretas.")

        def conferir(no: _No, minimo, maximo) -> tuple[int, int]:
            if no is self._nil:
                return 1, 0
            if not (minimo is None or minimo < no.chave) or not (maximo is None or no.chave < maximo):
                raise ValueError("A ordem das chaves da árvore está incorreta.")
            if no.paciente.chave_chegada != no.chave:
                raise ValueError("A chave da árvore diverge da chave do paciente.")
            for filho in (no.esquerda, no.direita):
                if filho is not self._nil and filho.pai is not no:
                    raise ValueError("Um filho da árvore está ligado ao pai incorreto.")
                if no.vermelho and filho.vermelho:
                    raise ValueError("Um nó vermelho possui um filho vermelho.")
            altura_esq, tamanho_esq = conferir(no.esquerda, minimo, no.chave)
            altura_dir, tamanho_dir = conferir(no.direita, no.chave, maximo)
            if altura_esq != altura_dir:
                raise ValueError("Os caminhos da árvore têm alturas pretas diferentes.")
            return altura_esq + int(not no.vermelho), 1 + tamanho_esq + tamanho_dir

        _, quantidade = conferir(self._raiz, None, None)
        if quantidade != len(self):
            raise ValueError("A contagem de nós da árvore está incorreta.")
