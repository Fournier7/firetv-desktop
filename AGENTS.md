# Fire TV Desktop

Aplicativo pessoal de estudo para Windows: controlar um Fire TV Stick na rede local por ADB, com janela desktop por padrão, controle, texto, apps, favoritos e atividade local.

## Como rodar
- Python 3.10 ou superior; o workflow usa Python 3.12.
- Criar ambiente: `py -m venv .venv`.
- Instalar: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`.
- Executar: `.\.venv\Scripts\python.exe -m firetv.main`.
- A versão desktop passou em 324 testes no Windows com Python 3.14.5 e PySide6 6.12.0; execute os testes ao alterar o código. Os testes de instância precisam de permissão para criar canais locais do Windows.
- Testar: `.\.venv\Scripts\python.exe -m pytest -q`.
- Empacotar no Windows: `.\build_exe.bat`.
- Uso real exige depuração ADB, autorização na TV e IPv4 acessível na porta 5555.

## Estilo e arquitetura
- Python com type hints, nomes claros, funções pequenas e mensagens ao usuário em português.
- Preservar interface → Session/Controller → Connection; somente a conexão acessa o ADB.
- Preservar testes primeiro nas mudanças de comportamento e executar a suíte antes e depois de alterações no código.
- Usar workers para comandos de rede e Session para serialização; não bloquear a interface.
- Testes com FakeConnection e APPDATA temporário, sem rede nem dados reais do usuário.
- Manter validação de pacotes, escape de texto e recuperação de JSON corrompido.

## Regras
- Explicar as mudanças de forma simples: o usuário é iniciante.
- Não apagar arquivos sem avisar previamente.
- Não fazer git push, push --force nem publicar sem confirmação do usuário.
- Não incluir senhas, chaves ADB, configurações pessoais ou histórico real.
- Não usar logos oficiais nem ampliar o escopo para HDMI, espelhamento ou botão de ligar.
- Prioridade atual: acesso fácil pelo executável, atalho e barra de tarefas. Não voltar ao comportamento apenas na bandeja; --tray é opcional.
- Preservar instância única e geometria da janela. O build também gera FireTVDesktopSetup.exe; instalação por usuário, com atalhos e desinstalação que preserva os dados.
- Início desktop: controle/teclado e resumo em duas colunas, empilhadas em janelas estreitas. Reaproveitar RemoteTab; preservar proteção dos atalhos durante digitação. ConnectionBar usa o fluxo de conexão de SettingsTab.
- Volume vazio/desconhecido na interface exige diagnóstico antes de habilitar botões. Não tratar sucesso do comando como prova de efeito físico na TV.
- Consultar os planos como histórico; conferir no código o que já está implementado.
- Validar com testes pertinentes e informar honestamente o que não foi possível testar.
