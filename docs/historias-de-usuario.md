# Histórias de usuário do SIGAE

O operador usa nomes e registros profissionais fictícios. Os critérios cobrem o fluxo do simulador e podem servir de referência para a revisão do SIGAE-07.

| História | Aceite em caso de sucesso | Aceite em caso de erro ou exceção |
| --- | --- | --- |
| Como operador, quero cadastrar um paciente para incluí-lo na fila de espera. | Um nome válido e um risco de 1 a 5 geram ID e horário automaticamente. O paciente entra na Hash, na árvore e no heap como Aguardando. | Nome em branco ou risco inválido mantém o cadastro e a fila intactos. |
| Como operador, quero consultar o paciente por ID para localizar seu registro. | Um ID existente exibe o nome e a situação, inclusive após a saída da fila. | Um ID ausente informa que o paciente não foi encontrado. Um ID inválido produz erro de formulário. |
| Como operador, quero reclassificar o risco para aplicar a nova prioridade à próxima chamada. | A reclassificação de um paciente aguardando reorganiza o heap e preserva a ordem por chegada na árvore. | A operação rejeita reclassificação após a saída da espera. |
| Como operador, quero cadastrar e consultar médicos para acompanhar quem está disponível. | O registro fictício gera um ID e o médico inicia disponível com zero conclusões. A consulta pelo ID mostra a situação e a contagem. | Nome ou registro vazio impede o cadastro. ID inexistente produz indicação de busca sem resultado. |
| Como operador, quero chamar o próximo paciente para atribuí-lo a um médico disponível. | A chamada escolhe pelo risco, pela chegada e pelo ID. Entre médicos disponíveis, compara conclusões, última atribuição e ID. Os dois ficam em atendimento. | Fila vazia ou ausência de médico disponível preserva os cadastros e os índices. |
| Como operador, quero concluir o atendimento para atualizar o histórico e liberar o médico. | Uma conclusão encerra o vínculo, libera o médico e acrescenta uma conclusão. | Repetir a conclusão produz erro e preserva o contador. |
| Como operador, quero confirmar um cancelamento para evitar mudanças acidentais. | A tela permite voltar ou confirmar. O cancelamento tira o paciente da espera ou encerra o atendimento e libera o médico com o total preservado. | Voltar mantém o estado original. Falha intermediária restaura os índices e vínculos. |
| Como operador, quero ver o painel e o histórico para acompanhar os estados e as chegadas. | O painel mostra a próxima chamada e os totais. O histórico lista atendimentos encerrados, permite filtro por médico e mostra chegadas em ordem cronológica. | Uma sessão vazia exibe indicadores zerados e mensagens de ausência de registros. |
| Como operador, quero inspecionar e validar os índices para conferir o efeito de cada operação. | A página mostra cores e ramos da árvore, raízes dos heaps e IDs por bucket. Uma validação bem-sucedida confirma os vínculos e os contadores. | Uma inconsistência produz mensagem de erro visível, com a causa informada pelo validador. |
