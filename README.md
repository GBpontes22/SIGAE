# SIGAE

Simulador acadêmico de gerenciamento de atendimentos de emergência, em Python e Django. Use nomes e registros médicos fictícios.

## Execução local

Com Python 3.12, abra o PowerShell na pasta do projeto e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Abra [SIGAE WEB](http://127.0.0.1:8000/). Em Linux ou macOS, substitua `.\.venv\Scripts\python.exe` por `.venv/bin/python`.

Os cadastros, filas, atendimentos e contadores ficam em memória, compartilhados pelas requisições do mesmo processo. Reiniciar o servidor zera a simulação. Use um único processo durante a defesa.

## Demonstração

1. Em **Médicos**, cadastre A, B e C com registros fictícios.
2. Cadastre quatro pacientes com riscos diferentes. Preencha a ficha de um deles e confira o texto na consulta por ID em **Pacientes**. Em **Triagem e fila**, a tabela segue a ordem de chegada e o cartão destaca a raiz do heap na mesma leitura. Uma reclassificação pode mudar quem será chamado primeiro.
3. Faça três chamadas e confirme as atribuições. A quarta deve manter o próximo paciente na fila enquanto os três médicos estiverem ocupados.
4. Conclua um atendimento e cancele outro. Confira os contadores e chame o próximo paciente. Entre os disponíveis, o médico com menos conclusões tem preferência. Empates usam a atribuição mais antiga e depois o menor ID.
5. Confira os encerramentos e o filtro por médico em **Histórico**. O **Painel geral** mostra os totais acumulados de pacientes por situação, as conclusões do dia no fuso configurado e os médicos disponíveis. O total de cancelados inclui pacientes cancelados na espera e durante o atendimento.
6. Em **Estruturas**, veja as três estruturas e use **Validar índices**. Use **Demonstrar colisão** para adicionar dois pacientes fictícios ao mesmo bucket e consulte cada cadastro pelo link do ID.

## Testes e documentação

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
```

- [Relatório técnico e evidências de teste](docs/relatorio-tecnico.md)
- [Arquitetura e contratos](docs/arquitetura.md)
- [Histórias de usuário e critérios de aceite](docs/historias-de-usuario.md)
- [Registro de práticas XP](docs/registro-xp.md)
- [Roteiro de defesa](docs/roteiro-defesa.md)

Metodologia de desenvolvimento declarada pelo projeto: Extreme Programming (XP).
