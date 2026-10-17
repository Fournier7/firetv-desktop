# Fire TV Desktop

Aplicativo de desktop para **Windows** que controla um **Fire TV Stick** pela rede local, via ADB.
Feito em Python (PySide6), com a lógica separada da interface e testada sem precisar da TV.

![Controle](docs/screenshots/controle.png) ![Apps](docs/screenshots/apps.png)

## O que faz

- **Controle remoto:** direcionais, OK, Voltar, Início, Menu, play/pause, retroceder e avançar.
  Atalhos: setas, Enter (OK) e Esc (Voltar), que não disparam enquanto você digita em um campo de texto.
- **Digitação:** escreva no teclado do PC e envie para o campo de texto aberto na TV.
  O Android só aceita ASCII simples nesse modo: acentos e `%` são ignorados e o app avisa quais.
- **Volume (experimental):** mais, menos e mudo. Em um Stick depende de HDMI-CEC e pode não responder.
- **Apps:** grade dos apps instalados, com busca, favoritos e opção de esconder/mostrar apps.
- **Início:** app em execução na TV e faixa de favoritos.
- **Reconexão automática** se a conexão cair.

Fora da versão 1: entrada HDMI, espelhamento e captura de tela, estatísticas, e conexão sem ADB.

## Configurar o Stick (uma vez)

1. No Stick: **Configurações > Meu Fire TV > Opções do desenvolvedor > Depuração ADB** (ligada).
   Se "Opções do desenvolvedor" não aparecer, abra **Sobre** e clique várias vezes em **Fire TV Stick** até ativar.
2. Anote o IP do Stick (**Configurações > Meu Fire TV > Sobre > Rede**).
   O ideal é reservar um IP fixo para ele no roteador, porque o ADB não se anuncia na rede.
3. Na primeira conexão, a TV mostra um pedido de autorização. Aceite (e marque "sempre permitir").

## Rede

O PC e o Stick precisam estar na **mesma rede local**, atrás do mesmo roteador.
PC no cabo e Stick no wifi funcionam. **Rede de convidados** ou **isolamento de clientes (AP isolation)**
costumam bloquear a conexão: se não conectar, confira isso no roteador.

## Instalar e rodar (desenvolvimento)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m firetv.main
```

## Testes

```bash
pytest
```

Os testes usam uma conexão falsa (`tests/fakes.py`): nenhum teste usa rede de verdade.

## Gerar o executável (Windows)

**Mais fácil:** instale o Python 3.10 ou mais novo (marque "Add python.exe to PATH") e dê dois cliques em
`build_exe.bat`. Ele cria o ambiente, instala as dependências e gera **`dist\\FireTVDesktop.exe`**, um arquivo
único que você pode copiar para onde quiser (não precisa instalar nada para abrir).

Para conferir que o executável sobe e que a chave ADB funciona, rode no terminal
`start /wait "" dist\\FireTVDesktop.exe --selftest` seguido de `echo %errorlevel%`: deve mostrar `0`.

**Sem instalar Python:** o workflow `.github/workflows/build-windows.yml` gera o `.exe` no GitHub
(aba Actions > Build Windows > Run workflow) e deixa o arquivo para baixar.

Comando manual equivalente: `pyinstaller --noconfirm --onefile --noconsole --name FireTVDesktop --paths src app.py`.

## Arquitetura

Três camadas: **interface** (`firetv/ui`), **controle** (`controller.py`, `session.py`, `apps.py`) e
**conexão ADB** (`connection.py`, a única que fala com o Stick). A interface não conhece ADB;
trocar a conexão por outra implementação não mexe no resto.

## Roteiro de teste manual (no Stick real)

Com o PC no cabo e o Stick no wifi:

- [ ] conectar pelo IP e aceitar a autorização na TV
- [ ] direcionais, OK, Voltar e Início respondem
- [ ] atalhos de teclado funcionam, e não disparam ao digitar no campo de texto
- [ ] enviar texto simples e texto com acento (o aviso aparece)
- [ ] botões de volume: anotar se funcionam
- [ ] grade de apps lista e abre Netflix e YouTube
- [ ] esconder e mostrar um app; favoritar e ver na tela Início
- [ ] desligar o Stick e ligar de novo: o app mostra "Reconectando..." e volta

Pontos a conferir no Stick real (os comandos foram escritos sem acesso a um aparelho):
`pm list packages` lista os apps de streaming? Os pacotes da tabela em `apps.py` estão certos?
`dumpsys window | grep mCurrentFocus` devolve o app aberto?

## Licença

MIT.
