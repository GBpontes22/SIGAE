# Relatório técnico do SIGAE WEB

O SIGAE WEB simula cadastro, triagem, distribuição entre médicos, conclusão e cancelamento de atendimentos. Os formulários Django chamam um serviço que concentra as regras. As seis áreas podem ser usadas com dados fictícios diretamente no navegador.

## Estruturas e regras

| Estrutura própria | Uso no fluxo |
| --- | --- |
| Tabela Hash | Cadastros e vínculos por ID. Usa resto da divisão, encadeamento separado e redimensionamento. |
| Árvore Rubro-Negra | Índice da espera por chegada e ID. Inserção e remoção aplicam rotações e recoloração. A tela de triagem usa o percurso em ordem. |
| Dois Min-Heaps | A raiz de um seleciona o paciente pelo risco, chegada e ID. A raiz do outro seleciona o médico disponível pelo menor número de conclusões, atribuição mais antiga e ID. Cada heap usa uma Hash própria para localizar posições. |

A chamada verifica as duas filas antes de remover registros. Atualizações dos índices e dos vínculos são protegidas por uma trava no processo. Se uma etapa falhar, as alterações já realizadas são revertidas em ordem inversa. Concluir libera o médico e incrementa seu contador uma vez. Cancelar libera o médico sem incrementar o contador. As chaves cronológicas usam UTC.

A página Estruturas permite inspecionar e validar as cores dos nós, as posições dos heaps e os IDs por bucket da Hash de pacientes. O cancelamento pelo navegador passa por uma tela de confirmação e a alteração é enviada via POST com proteção CSRF.

## Evidências

O comando `python manage.py test --verbosity 2` executa a suíte reproduzível. Na verificação local, os 41 testes passaram.

- `test_estruturas.py` cobre colisões, redimensionamento, mudanças de prioridade, rollback durante a remoção no Heap e invariantes da árvore.
- `test_sistema.py` cobre três médicos, desempates, indisponibilidade, chamadas concorrentes e rollback durante cadastro, reclassificação, chamada, conclusão e cancelamento.
- `test_fluxo_web.py` cobre os cadastros, a consulta da ficha, chamada, histórico, triagem durante uma chamada concorrente, indicadores, confirmação de cancelamento e CSRF. Também verifica a página Estruturas, a colisão com redimensionamento e a consulta dos dois pacientes pela interface.
- `test_paciente.py` cobre as regras do paciente e a ordenação quando o horário local se repete.

## Critérios de aceitação da defesa

| Critério | Pontos | Cenário e evidência |
| --- | --- | --- |
| Árvore Rubro-Negra | 1,5 | Inserir e remover com horários empatados. Conferir busca, percurso ordenado, raiz preta, ausência de nós vermelhos adjacentes e mesma altura preta em cada ramo. `test_estruturas.py` |
| Heap Binário | 2,0 | Subir e descer a prioridade de um paciente. Na chamada, respeitar risco, chegada e ID. Entre médicos disponíveis, usar conclusões, atribuição mais antiga e ID. `test_estruturas.py`, `test_sistema.py` e `test_fluxo_web.py` |
| Tabela Hash | 1,0 | Colidir dois IDs, consultar ambos e repetir a consulta após redimensionamento. No navegador, conferir o bucket e abrir os dois cadastros pelos links. `test_estruturas.py` e `test_fluxo_web.py` |
| Integração | 1,5 | Chamar com todos os médicos ocupados, repetir uma conclusão, cancelar em espera e em atendimento, e conferir vínculos e contadores. Exercitar chamadas concorrentes e falhas intermediárias. `test_sistema.py` e `test_fluxo_web.py` |
| Interface web e usabilidade | 1,0 | Exercitar formulários, mensagens de erro, confirmação de cancelamento e filtro de histórico. As seis áreas obrigatórias e a tela Estruturas renderizaram no Chrome a 390 px sem rolagem horizontal da página. `test_views.py` e `test_fluxo_web.py` |
| Testes, documentação e defesa | 1,0 | Executar a suíte pelo README e seguir o [roteiro de defesa](roteiro-defesa.md) com dados fictícios. A explicação e a operação dos cenários cabem ao grupo durante a apresentação. |

A instalação pelo README foi repetida em uma cópia limpa neste computador. O roteiro também foi executado com dados fictícios em um servidor HTTP isolado. A demonstração usa uma sessão em memória por processo.
