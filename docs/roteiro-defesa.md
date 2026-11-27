# Roteiro de defesa do SIGAE

Use uma sessão local nova e dados fictícios. Abra o painel e a página **Triagem e fila** para comparar a próxima chamada com a ordem de chegada.

| Passo | Ação | Resultado a mostrar |
| --- | --- | --- |
| 1 | Cadastre os médicos A, B e C com registros fictícios. | Os três começam disponíveis com zero conclusões. O heap de médicos destaca A se ele tiver o menor ID. |
| 2 | Cadastre quatro pacientes com riscos 4, 2, 3 e 5 nessa ordem. Reclassifique o terceiro para risco 1. | A árvore continua ordenada por chegada. O terceiro paciente se torna a raiz do heap. A Hash permite consultá-lo pelo ID. |
| 3 | Faça três chamadas. Tente uma quarta. | Os três médicos ficam ocupados. A quarta tentativa mantém o paciente restante na fila. |
| 4 | Conclua o primeiro atendimento e cancele o segundo. Na confirmação, volte uma vez antes de confirmar. | Voltar preserva o atendimento. Depois, A tem uma conclusão, B fica disponível com zero e o histórico registra os dois encerramentos. |
| 5 | Chame novamente o paciente restante. Abra **Estruturas** e clique em **Validar índices**. | B é escolhido por ter menos conclusões. A validação confirma os vínculos e contadores. |
| 6 | Cancele os atendimentos ativos de C e B. Cadastre e chame mais um paciente. | B e C continuam com zero conclusões. C é escolhido por ter recebido um paciente antes de B. |
| 7 | Filtre o histórico por médico e mostre a lista de chegadas. | Os registros encerrados continuam consultáveis e a lista mantém a ordem cronológica. |

Para demonstrar colisão pelo navegador, use **Estruturas → Demonstrar colisão**. O botão adiciona dois pacientes fictícios à fila e destaca o bucket que contém os dois IDs. Clique em cada ID para consultar o cadastro e use **Validar índices** para verificar a consistência.

Para mostrar também o redimensionamento na mesma ação, comece em uma sessão vazia, cadastre sete pacientes fictícios e confirme a capacidade inicial de 11 buckets. Clique em **Demonstrar colisão**. A capacidade passa para 23 e os IDs 8 e 31 ficam juntos no bucket 8.

Para demonstrar o rollback de cancelamento, execute `python manage.py test atendimentos.tests.test_sistema.SistemaTests.test_falha_no_cancelamento_restaura_espera_e_atendimento_ativo --verbosity 2`. O teste injeta falhas no meio das mudanças e verifica o estado antes de repetir a operação.

**Variação para o ensaio.** Peça à pessoa que operar o sistema que escolha, na hora, um paciente aguardando para reclassificar ou cancelar. Confira o próximo paciente e a ordem de chegada. Use a suíte de testes para demonstrar a validação interna dos índices.
