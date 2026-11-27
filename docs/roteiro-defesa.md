# Roteiro de defesa do SIGAE

Use uma sessão local nova e dados fictícios. Abra o painel e a página **Triagem e fila** para comparar a próxima chamada com a ordem de chegada.

| Passo | Ação | Resultado a mostrar |
| --- | --- | --- |
| 1 | Cadastre os médicos A, B e C com registros fictícios. | Os três começam disponíveis com zero conclusões. O heap de médicos destaca A se ele tiver o menor ID. |
| 2 | Cadastre quatro pacientes com riscos 4, 2, 3 e 5 nessa ordem. Reclassifique o terceiro para risco 1. | A árvore continua ordenada por chegada. O terceiro paciente se torna a raiz do heap. A Hash permite consultá-lo pelo ID. |
| 3 | Faça três chamadas. Tente uma quarta. | Os três médicos ficam ocupados. A quarta tentativa mantém o paciente restante na fila. |
| 4 | Conclua o primeiro atendimento e cancele o segundo. Na confirmação, volte uma vez antes de confirmar. | Voltar preserva o atendimento. Depois, A tem uma conclusão, B fica disponível com zero e o histórico registra os dois encerramentos. |
| 5 | Chame novamente o paciente restante. Confira o novo vínculo em **Atendimentos**. | B é escolhido por ter menos conclusões. |
| 6 | Filtre o histórico por médico e mostre a lista de chegadas. | Os registros encerrados continuam consultáveis e a lista mantém a ordem cronológica. |

Para demonstrar colisão e redimensionamento de forma reproduzível, execute `python manage.py test atendimentos.tests.test_estruturas --verbosity 2`. O teste insere IDs espaçados no mesmo bucket. O cadastro normal usa IDs consecutivos e pode mostrar zero colisões mesmo com a Hash em funcionamento.

Para demonstrar o rollback de cancelamento, execute `python manage.py test atendimentos.tests.test_sistema.SistemaTests.test_falha_no_cancelamento_restaura_espera_e_atendimento_ativo --verbosity 2`. O teste injeta falhas no meio das mudanças e verifica o estado antes de repetir a operação.

**Variação para o ensaio.** Peça à pessoa que operar o sistema que escolha, na hora, um paciente aguardando para reclassificar ou cancelar. Confira o próximo paciente e a ordem de chegada. Use a suíte de testes para demonstrar a validação interna dos índices.
