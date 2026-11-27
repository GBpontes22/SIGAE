# Registro de práticas XP

## Evidências observadas na cópia local

| Etapa de trabalho | Evidência |
| --- | --- |
| Fluxo operacional | Implementação das estruturas próprias e integração de cadastro, triagem, chamada, conclusão e cancelamento. O relatório técnico e a suíte local registram as verificações. |
| Revisão do painel | O painel foi ajustado a partir da referência visual enviada pelo usuário. A consulta e a chamada pelo novo painel foram verificadas no navegador com dados fictícios. |
| Revisão a partir do Trello | A leitura dos cartões SIGAE-20, 22 e 23 evidenciou a necessidade de confirmação de cancelamento, inspeção dos índices e teste de rollback no cancelamento. As três mudanças entraram na cópia local. |

O quadro orientou a divisão em entregas pequenas. As histórias e seus critérios de aceite estão em [Histórias de usuário](historias-de-usuario.md). O GitHub Actions está configurado para executar verificações em pushes e pull requests. Os testes registrados neste relatório foram executados localmente.

## Planejamento sugerido para a revisão da equipe

| Iteração | Objetivo demonstrável | Critério de revisão |
| --- | --- | --- |
| 1 | Executar o fluxo básico no Django com as três estruturas. | Cadastrar, consultar por ID, reclassificar, chamar, concluir e cancelar com dados fictícios. |
| 2 | Validar os cenários de defesa e tornar os índices inspecionáveis. | Conferir empates, indisponibilidade e rollback. Mostrar a árvore, os heaps e a Hash durante a defesa. |

Para completar o histórico da equipe, acrescentar datas reais, estimativas acordadas, responsáveis pelas duplas, rodízios e feedback recebido. Usar apenas informações que os participantes consigam confirmar.
