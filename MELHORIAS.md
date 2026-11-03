# Versão desktop

## O que mudou

- Ao abrir o executável, aparece uma janela normal do Windows, inclusive com IP salvo.
- A janela tem título, ícone, minimizar/maximizar, tamanho ajustável e presença na barra de tarefas.
- Clicar em outro programa não esconde a janela. O X salva os dados e encerra o aplicativo.
- As abas agora também mostram os nomes, para facilitar encontrar cada função.
- O modo anterior permanece opcional com `--tray`.
- `build_exe.bat` gera o executável com ícone e cria um atalho na Área de Trabalho.
- `criar_atalho.ps1` permite recriar o atalho sem compilar novamente.
- Os ícones renderizados são reaproveitados em um cache limitado.
- A grade não reaplica os estilos a cada consulta quando o app em primeiro plano continua igual.
- A configuração é escrita em arquivo temporário e substituída após a gravação, preservando a versão anterior se a substituição falhar.
- O build isola os caminhos de bibliotecas para evitar incluir DLLs incompatíveis de outros programas.
- O instalador `FireTVDesktopSetup.exe` coloca o aplicativo numa pasta fixa do usuário e cria atalhos no menu Iniciar e na Área de Trabalho, sem exigir administrador.
- A instalação aparece nos aplicativos instalados do Windows, com desinstalação que preserva a configuração e o histórico.
- Abrir novamente o executável ou o atalho ativa a janela existente, inclusive minimizada.
- O aplicativo lembra tamanho, posição e estado maximizado; a restauração trata monitor desconectado e configuração inválida.
- A tela Início reúne controle remoto e teclado à esquerda, com app atual, favoritos e volume à direita. Em janelas estreitas, o conteúdo é empilhado.
- A conexão mostra o nome da TV e um botão Reconectar; falhas de rede e autorização aparecem na própria tela.
- Volume não configurado fica desativado até o usuário confirmar o diagnóstico, acessível no Início.
- O tema tem melhor contraste, espaçamento, dicas nos botões e indicação visual ao passar o mouse pelo direcional.
- Consultas antigas do app em primeiro plano são descartadas após uma mudança de conexão.
- O app atual aparece dentro de uma TV desenhada, com moldura, base e transição suave ao trocar de aplicativo.
- Favoritos têm brilho e ampliação do ícone ao passar o mouse e resposta visual ao clicar, sem mover os cartões.
- Na janela estreita, TV e favoritos vêm primeiro.
- Apps instalados e sugestões de streaming ficam separados. O catálogo reconhece Globoplay, Kick, Downloader, UniTV e Amazon Music, além dos serviços anteriores.
- Componentes internos deixam de aparecer no destaque. As sugestões não executam instalação, assinatura ou abertura de pacotes ausentes.

O código da versão anterior e o pacote de transferência foram preservados fora desta pasta. Nada foi enviado ao GitHub.

## Como usar

Abra `dist\FireTVDesktop.exe` ou o atalho `Fire TV Desktop` na Área de Trabalho. A primeira abertura mostra Ajustes para informar o IP; as seguintes abrem a janela e tentam conectar ao IP salvo.

Para manter o aplicativo em local permanente, feche a versão antiga, abra `dist\FireTVDesktopSetup.exe` e clique em Instalar. Ele usa `%LOCALAPPDATA%\Programs\FireTVDesktop`. Depois use os novos atalhos do menu Iniciar ou da Área de Trabalho. A versão portátil continua disponível em `dist\FireTVDesktop.exe`.

Minimizar mantém o aplicativo acessível na barra de tarefas. Você também pode fixá-lo nela. O X encerra o app; o atalho abre novamente.

O atalho aponta para o executável nesta pasta: se você mover o executável, recrie o atalho com `criar_atalho.ps1`. Ao distribuir apenas o `.exe`, salve-o em uma pasta permanente antes de criar um atalho.

## Próximas melhorias

1. **Validar volume no aparelho:** o diagnóstico continua experimental; confirmar qual método funciona antes de prometer suporte ao volume.
2. **Medir antes de novas otimizações:** comparar tempo de abertura e memória em uso no computador real. Um empacotamento em pasta pode reduzir o custo de extração do executável único, mas torna a distribuição menos simples.

Início automático com o Windows e múltiplas TVs podem vir depois. Para início automático, oferecer a opção ao usuário e manter a barra de tarefas acessível.

## Validação

A suíte automatizada passou com 329 testes no Windows. Cobre os fluxos anteriores e o layout adaptável, os comandos no Início, os avisos de conexão e o volume sem confirmação. As capturas foram conferidas em janela larga, estreita e desconectada, com dados fictícios. Os testes de instância, geometria e instalação continuam passando.

Ambiente usado: Python 3.14.5, PySide6 6.12.0, adb-shell 0.4.4, pytest 9.2.0, pytest-qt 4.5.0 e PyInstaller 6.22.3.

A captura `docs/screenshots/desktop.png` usa dados fictícios. Testes de software e de empacotamento não confirmam comunicação ou volume no Stick real.
