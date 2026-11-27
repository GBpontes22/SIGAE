# Relatório técnico do SIGAE WEB

O SIGAE WEB simula cadastro, triagem, distribuição entre médicos, conclusão e cancelamento de atendimentos. Os formulários Django chamam um serviço que concentra as regras. As seis áreas podem ser usadas com dados fictícios diretamente no navegador.

## Estruturas e regras

| Estrutura própria | Uso no fluxo |
| --- | --- |
| Tabela Hash | Cadastros e vínculos por ID. Usa resto da divisão, encadeamento separado e redimensionamento. |
| Árvore Rubro-Negra | Índice da espera por chegada e ID. Inserção e remoção aplicam rotações e recoloração. A tela de triagem usa o percurso em ordem. |
| Dois Min-Heaps | A raiz de um seleciona o paciente pelo risco, chegada e ID. A raiz do outro seleciona o médico disponível pelo menor número de conclusões, atribuição mais antiga e ID. Cada heap usa uma Hash própria para localizar posições. |

A chamada verifica as duas filas antes de remover registros. Atualizações dos índices e dos vínculos são protegidas por uma trava no processo. Se uma etapa falhar, as alterações já realizadas são revertidas em ordem inversa. Concluir libera o médico e incrementa seu contador uma vez. Cancelar libera o médico sem incrementar o contador. As chaves cronológicas usam UTC.

A página **Estruturas** mostra os dados de uma leitura consistente da sessão, incluindo as cores reais dos nós, a posição de cada item nos dois vetores e os IDs por bucket da Hash de pacientes. **Validar índices** executa as verificações do serviço. O cancelamento pelo navegador passa por uma tela de confirmação e a alteração é enviada via POST com proteção CSRF.

## Evidências

O comando `python manage.py test --verbosity 2` executa a suíte reproduzível. Na verificação local, os 33 testes passaram.

- `test_estruturas.py` cobre colisões, redimensionamento, mudanças de prioridade no heap e as invariantes da árvore após inserções e remoções.
- `test_sistema.py` cobre três médicos, desempates, indisponibilidade, reclassificação, chamadas concorrentes e falhas intermediárias. Também testa a reversão de falhas ao cancelar um paciente aguardando e um atendimento ativo.
- `test_fluxo_web.py` cobre formulários, chamada, histórico, confirmação de cancelamento, CSRF e exibição e validação dos índices.
- `test_paciente.py` cobre as regras do paciente e a ordenação quando o horário local se repete.

A instalação pelo README foi repetida em uma cópia limpa neste computador. O roteiro também foi executado com dados fictícios em um servidor HTTP isolado. A demonstração usa uma sessão em memória por processo.
