# Nova interface do Fire TV Desktop (v2): Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refazer a interface para ficar igual à da gravação de referência (painel na bandeja, cinco abas, cor de destaque por app), acrescentar a aba Atividade e o diagnóstico de volume.

**Architecture:** A lógica da v1 (`connection`, `session`, `controller`, `apps`) não muda, salvo o método de volume. Entram duas lógicas puras novas (`activity.py`, `volume.py`) e uma camada de interface refeita sobre elas (tema, ícones, componentes, abas e `Panel`).

**Tech Stack:** Python 3, PySide6 (inclui QtSvg), pytest, pytest-qt, PyInstaller.

**Spec:** escrita e aprovada em conversa durante o projeto (documento não publicado).

## Global Constraints

- Windows; Fire TV Stick; Python 3; interface em PySide6.
- Não mexer na lógica da v1, exceto `Controller.volume` e os campos novos de `AppConfig`. Os testes de lógica existentes continuam passando; testes de interface são reescritos junto com a tela que mudam.
- Sem logos oficiais de apps e sem marca ou texto da LG. Sem botão de ligar, entradas HDMI, ajustes de imagem, transmitir ou cursor.
- Atividade: o tempo somado por consulta tem teto de 10 s; o launcher `com.amazon.tv.launcher` não conta; grava a cada 30 s e ao sair; retém 90 dias; dados só no PC.
- Volume: `volume_method` vazio usa o método atual; `none` esconde os botões. Os comandos dos métodos candidatos não foram verificados no Stick e precisam ser conferidos nele.
- Mensagens ao usuário em português, sem texto técnico cru.

## Review Focus

1. Volume: `volume_method` vazio vira `keyevent`; valor desconhecido (arquivo editado à mão) cai em `keyevent` sem quebrar; `none` esconde os botões e não envia nada. Tarefas 1, 3 e 5.
2. `activity.json` ausente, corrompido, com dia inválido ou relógio que volta: abre vazio sem travar, e o corrompido vira `.bak`. Tarefa 2.
3. Garantias da v1 que a nova aba Controle mantém: atalhos ignorados em campo de texto e com a aba escondida, aviso de caracteres ignorados, aviso de sem conexão. Tarefa 6.
4. O painel some ao perder o foco, mas não com o diálogo de diagnóstico aberto, nem logo depois de abrir pelo ícone da bandeja. Tarefa 11.
5. Conectar sozinho ao abrir: falha não derruba o app nem abre diálogo, só aparece no rodapé. Tarefa 11.
6. Cor de destaque: app desconhecido ou nenhum vira azul padrão, e o estilo só é reaplicado quando a cor muda. Tarefas 4 e 11.

---

## Estrutura de arquivos

| Arquivo | Mudança |
|---|---|
| `src/firetv/config.py` | novos campos `tv_name` e `volume_method` |
| `src/firetv/activity.py` | novo: `ActivityLog`, `format_duration` |
| `src/firetv/volume.py` | novo: métodos de volume e comandos |
| `src/firetv/controller.py` | `volume(key, method)` |
| `src/firetv/ui/theme.py` | reescrito: cor de destaque e estilo |
| `src/firetv/ui/icons.py` | novo: ícones SVG |
| `src/firetv/ui/widgets.py` | novo: `Card`, `DPad`, `AudioCard`, `TvCard` |
| `src/firetv/ui/remote_tab.py`, `apps_tab.py`, `home_tab.py` | reescritos |
| `src/firetv/ui/activity_tab.py`, `volume_dialog.py` | novos |
| `src/firetv/ui/settings_tab.py` | nome da TV e diagnóstico |
| `src/firetv/ui/panel.py` | novo: `Panel`, `panel_position`, `TrayController` (substitui `main_window.py`, que é apagado) |
| `src/firetv/main.py` | bandeja, conexão automática, gravação |

---

### Task 1: Configuração: nome da TV e método de volume

**Files:** Modify `src/firetv/config.py`; Test `tests/test_config.py`

**Interfaces:**
- Produces: `AppConfig(host, favorites, hidden, tv_name: str = 'Fire TV', volume_method: str = '')`. `load_config` aceita arquivos sem os campos novos; `tv_name` vazio, nulo ou só espaços vira `'Fire TV'`; `host` nulo vira `''`.

- [ ] **Step 1: Testes (falham)**

```python
def test_new_fields_roundtrip(tmp_path):        # tv_name='Sala', volume_method='keyboard'
def test_old_file_without_new_fields_loads_defaults(tmp_path):
def test_blank_or_null_tv_name_becomes_default(tmp_path):   # '', '  ', null
def test_null_host_becomes_empty_string(tmp_path):
```

- [ ] **Step 2:** `pytest tests/test_config.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar os campos e a normalização em `load_config`.
- [ ] **Step 4:** `pytest -q`. Esperado: tudo passa.
- [ ] **Step 5: Commit** (`feat: nome da TV e método de volume na configuração`)

---

### Task 2: Registro de atividade

**Files:** Create `src/firetv/activity.py`; Test `tests/test_activity.py`

**Interfaces:**
- Produces: `LAUNCHER_PACKAGES = {'com.amazon.tv.launcher'}`, `MAX_SAMPLE_SECONDS = 10`, `RETENTION_DAYS = 90`.
- Produces: `ActivityLog(path: Path | None = None, today: Callable[[], date] = date.today)`. Padrão do caminho: `config_dir() / 'activity.json'`. `record(package: str, now: float) -> None` soma `min(now - último, 10)` ao pacote no dia de `today()`; a primeira amostra, ou a primeira depois de `reset_clock()`, soma 0; launcher atualiza o relógio mas não soma. `reset_clock() -> None`. `totals(period: str) -> list[tuple[str, int]]` (`'today'`, `'7d'`, `'30d'`; ordenado do maior para o menor; 7d e 30d incluem hoje). `total_seconds(period: str) -> int`. `save() -> None`.
- Formato: `{'days': {'AAAA-MM-DD': {'pacote': segundos}}}`. Ao carregar e ao salvar, descarta dias com mais de 90 dias, chaves de dia inválidas e valores que não sejam números não negativos. Arquivo ilegível vira `.bak` e começa vazio.
- Produces: `format_duration(seconds: int) -> str`: abaixo de 60 vira `'42 s'`, abaixo de 3600 vira `'51 min'`, acima vira `'1 h 05 min'`.

- [ ] **Step 1: Testes (falham)**

```python
def test_first_sample_adds_nothing():
def test_adds_elapsed_between_samples():             # 3 s entre duas amostras soma 3
def test_elapsed_is_capped_at_ten_seconds():         # 600 s soma 10
def test_launcher_does_not_count_but_advances_clock():
def test_reset_clock_makes_next_sample_add_nothing():
def test_totals_by_period_include_today_and_sort_desc():
def test_old_days_are_pruned_on_save_and_load():     # 91 dias
def test_save_and_reload_roundtrip(tmp_path):
def test_corrupt_file_becomes_bak_and_starts_empty(tmp_path):
def test_invalid_day_keys_and_values_are_ignored(tmp_path):
def test_clock_going_backwards_adds_nothing():       # now menor que o último
def test_new_day_starts_a_new_bucket():              # today() muda entre amostras
def test_format_duration():                          # 0, 42, 59, 60, 3060, 3900
```

- [ ] **Step 2:** `pytest tests/test_activity.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `activity.py`.
- [ ] **Step 4:** `pytest -q`. Esperado: tudo passa.
- [ ] **Step 5: Commit** (`feat: registro de atividade`)

---

### Task 3: Métodos de volume

**Files:** Create `src/firetv/volume.py`; Modify `src/firetv/controller.py`; Test `tests/test_volume.py`, `tests/test_controller_keys.py`

**Interfaces:**
- Produces em `volume.py`: `DEFAULT_METHOD = 'keyevent'`, `NONE = 'none'`, `METHOD_ORDER = ('keyevent', 'keyboard', 'media_session', 'media')`, `normalize_method(value: str) -> str` (vazio ou desconhecido vira `keyevent`; `none` fica `none`; método conhecido fica igual) e `volume_command(method: str, key: KeyCode) -> str`.
- Comandos (candidatos a conferir no Stick): `keyevent` → `input keyevent <código>`; `keyboard` → `input keyboard keyevent <código>`; `media_session` → `cmd media_session volume --show --adj <raise|lower|toggle-mute>`; `media` → `media volume --show --adj <raise|lower|toggle-mute>`. VOLUME_UP vira `raise`, VOLUME_DOWN vira `lower`, MUTE vira `toggle-mute`.
- Produces: `Controller.volume(key: KeyCode, method: str = '') -> bool`. Usa `normalize_method`; com `none` não envia nada e devolve False; senão envia `volume_command` e mantém a regra atual (False se a saída tiver `error` ou `exception`).

- [ ] **Step 1: Testes (falham)**

```python
def test_normalize_method():           # '', 'xyz' -> 'keyevent'; 'none' e 'keyboard' ficam
def test_volume_command_strings():     # os 4 métodos x 3 teclas, texto exato
def test_volume_command_rejects_non_volume_key():
def test_controller_volume_uses_method(ctl, conn):
    ctl.volume(KeyCode.VOLUME_UP, 'media_session')
    assert conn.commands == ['cmd media_session volume --show --adj raise']
def test_controller_volume_none_sends_nothing_and_returns_false():
def test_controller_volume_default_is_unchanged():   # os testes atuais continuam
```

- [ ] **Step 2:** `pytest tests/test_volume.py tests/test_controller_keys.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `volume.py` e ajustar `Controller.volume`.
- [ ] **Step 4:** `pytest -q`. Esperado: tudo passa.
- [ ] **Step 5: Commit** (`feat: métodos de volume`)
- [ ] **Step 6 (manual, Willian, no Stick):** conferir no diagnóstico (Tarefa 10) qual método mexe no volume da TV.

---

### Task 4: Tema e ícones

**Files:** Rewrite `src/firetv/ui/theme.py`; Create `src/firetv/ui/icons.py`; Test `tests/test_theme.py`

**Interfaces:**
- Produces em `theme.py`: `DEFAULT_ACCENT = '#3B82F6'`, `accent_for(package: str | None) -> str` (cor de `KNOWN_APPS`; senão o padrão), `build_stylesheet(accent: str) -> str`, `tint(color: str, alpha: float) -> str` (devolve `rgba(r, g, b, a)`), `STYLESHEET = build_stylesheet(DEFAULT_ACCENT)`. Mantém as constantes de cor atuais.
- Produces em `icons.py`: `ICON_NAMES` (`home`, `remote`, `apps`, `activity`, `settings`, `back`, `menu`, `play_pause`, `rewind`, `forward`, `volume_down`, `volume_up`, `mute`, `star`, `star_filled`, `search`) e `icon(name: str, color: str = '#E8E8EA') -> QIcon` (SVG embutido, desenhado em 24x24 e renderizado em 48x48). Nome desconhecido levanta `KeyError`.

- [ ] **Step 1: Testes (falham)**

```python
def test_accent_for_known_unknown_and_none():
def test_stylesheet_contains_accent():
def test_tint_format():                  # tint('#FF0000', 0.5) == 'rgba(255, 0, 0, 0.5)'
def test_every_icon_renders_non_null(qapp):
def test_unknown_icon_raises():
def test_icon_color_changes_pixels(qapp):   # duas cores dão imagens diferentes
```

- [ ] **Step 2:** `pytest tests/test_theme.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar tema e ícones. O estilo cobre painel, cartões, abas, botões, campos, barras e rótulos, todos derivados da cor de destaque.
- [ ] **Step 4:** `pytest -q`. Esperado: tudo passa.
- [ ] **Step 5: Commit** (`feat: tema com cor de destaque e ícones`)

---

### Task 5: Componentes: cartão, direcional, áudio e TV

**Files:** Create `src/firetv/ui/widgets.py`; Test `tests/test_ui_widgets.py`

**Interfaces:**
- Consumes: `normalize_method`, `Controller.volume`, `icon`, `tint`, `run_in_background`, `Session`, `AppConfig`, `KeyCode`.
- Produces: `Card(title: str = '')` (QFrame com objectName `card`).
- Produces: `DPad(QWidget)` com sinal `pressed(object)` (leva um `KeyCode`), `key_at(pos: QPoint) -> KeyCode | None` (centro até 36% do raio é OK; o anel se divide em quatro setores UP, RIGHT, DOWN e LEFT; fora do círculo é `None`) e `set_accent(color: str)`. Tamanho fixo 200x200.
- Produces: `AudioCard(session, cfg)` com `vol_down_button`, `mute_button`, `vol_up_button`, `notice_label` e `refresh()` (relê `cfg.volume_method`). Lê o método a cada clique. Com `none`, esconde os botões e mostra `Volume indisponível: depende do controle físico da TV.` Falha de volume mostra `O volume não respondeu neste aparelho. Este recurso é experimental.`; conexão perdida mostra `Sem conexão com o Stick. Conecte na aba Ajustes.`
- Produces: `TvCard()` com `set_app(name: str | None, accent: str)`: título `AGORA NA TELA`, nome do app ou `Nada em primeiro plano`.

- [ ] **Step 1: Testes (falham)**

```python
def test_dpad_key_at_center_and_four_sectors(qapp):
def test_dpad_outside_circle_is_none(qapp):
def test_dpad_click_emits_pressed(qtbot):
def test_audio_card_sends_configured_method(qtbot):   # media_session -> comando exato
def test_audio_card_default_method_is_keyevent(qtbot):
def test_audio_card_none_hides_buttons_and_shows_message(qtbot):
def test_audio_card_refresh_picks_up_new_method(qtbot):
def test_audio_card_failure_and_lost_connection_notices(qtbot):
def test_tv_card_texts(qtbot):
```

- [ ] **Step 2:** `pytest tests/test_ui_widgets.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar os quatro componentes (o `DPad` é desenhado em `paintEvent`).
- [ ] **Step 4:** `pytest -q`. Esperado: tudo passa.
- [ ] **Step 5: Commit** (`feat: componentes visuais`)

---

### Task 6: Aba Controle

**Files:** Rewrite `src/firetv/ui/remote_tab.py`; Rewrite `tests/test_ui_remote.py`

**Interfaces:**
- Consumes: `DPad`, `AudioCard`, `Card`, `icon`, `Session.run`, `Controller.press`, `Controller.send_text`.
- Produces: `RemoteTab(session, cfg)` com `dpad`, `buttons: dict[KeyCode, QPushButton]` (HOME, BACK, MENU, REWIND, PLAY_PAUSE, FAST_FORWARD), `text_edit`, `send_button`, `notice_label` e `audio_card`. Mantém o filtro de atalhos da v1 (setas, Enter, Esc, só com a aba visível e fora de campos de texto). Mensagens: `Não foi possível enviar: <caracteres>` e `Sem conexão com o Stick. Conecte na aba Ajustes.`

- [ ] **Step 1: Reescrever os testes (falham)** com os mesmos comportamentos da v1, sobre os novos componentes: seta para cima envia `input keyevent 19`; Enter e Esc enviam OK e Voltar; atalhos ignorados com foco no campo de texto e com a aba escondida; clique no `dpad` e nos botões envia a tecla; enviar texto simples; aviso de caracteres ignorados (`ação`); comando sem conexão mostra o aviso. Os testes de volume saem daqui (já cobertos na Tarefa 5).
- [ ] **Step 2:** `pytest tests/test_ui_remote.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar a aba com a disposição do vídeo: direcional circular com Início, Voltar e Menu ao redor; linha de mídia; cartão de teclado; cartão de áudio embaixo.
- [ ] **Step 4:** `pytest tests/test_ui_remote.py -v`, depois `pytest -q`. Esperado: passa (`MainWindow` ainda usa a assinatura antiga; ajustar a chamada lá com `cfg`).
- [ ] **Step 5: Commit** (`feat: nova aba Controle`)

---

### Task 7: Aba Apps

**Files:** Rewrite `src/firetv/ui/apps_tab.py`; Rewrite `tests/test_ui_apps.py`

**Interfaces:**
- Consumes: `tint`, `icon`, `AppEntry`, `search`, `toggle_favorite`, `toggle_hidden`, `save_config`.
- Produces: `AppTile(entry: AppEntry, show_star: bool = True)` com fundo e borda na cor do app, `name_label`, `star_button` (checável; marcado quando favorito; ausente com `show_star=False`) e rótulo `NA TELA` quando `set_on_screen(True)`. Sinais `launch_requested`, `favorite_requested`, `hidden_requested` como na v1.
- Produces: `AppsTab(session, cfg)` com campo de busca `Buscar nos N apps` (N é o total de apps carregados), `set_current_app(package: str | None)`, e tudo o que a v1 já expõe (`tiles()`, `refresh()`, `toggle_favorite`, `toggle_hidden`, `favorites_changed`, `empty_label`, `show_hidden_check`).

- [ ] **Step 1: Reescrever os testes (falham):** todos os comportamentos da v1 (esconder, mostrar, favoritar e salvar, buscar, estado vazio, pacote desconhecido pelo nome, clique abre o app, atualizar ao conectar) mais: placeholder mostra o total; `set_current_app` marca só o tile certo com `NA TELA`; `show_star=False` não cria estrela. Onde a v1 lia o texto da estrela, ler `star_button.isChecked()`.
- [ ] **Step 2:** `pytest tests/test_ui_apps.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar o novo tile e a aba.
- [ ] **Step 4:** `pytest tests/test_ui_apps.py -v`. Esperado: PASS.
- [ ] **Step 5: Commit** (`feat: nova aba Apps`)

---

### Task 8: Aba Início

**Files:** Rewrite `src/firetv/ui/home_tab.py`; Rewrite `tests/test_ui_home.py`

**Interfaces:**
- Consumes: `TvCard`, `AudioCard`, `AppTile(show_star=False)`, `accent_for`, `KNOWN_APPS`, `POLL_INTERVAL_SECONDS`.
- Produces: `HomeTab(session, cfg)` com `tv_card`, `audio_card`, `timer`, `poll()`, `favorite_tiles()` (no máximo 4), `refresh_favorites()`, botão `Ver todos` e sinais `see_all_requested()` e `polled(object)` (emitido a cada resposta de consulta, com o pacote ou `None`). Mantém a regra da v1: consulta só enquanto conectado, e o timer para ao desconectar.

- [ ] **Step 1: Reescrever os testes (falham):** mostra o nome do app; pacote desconhecido mostra o pacote; sem app mostra `Nada em primeiro plano`; no máximo 4 favoritos na faixa e sem estrela; `Ver todos` emite o sinal; `polled` é emitido a cada consulta; o timer segue o estado da conexão; nunca conectado não consulta.
- [ ] **Step 2:** `pytest tests/test_ui_home.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar a aba.
- [ ] **Step 4:** `pytest tests/test_ui_home.py -v`. Esperado: PASS.
- [ ] **Step 5: Commit** (`feat: nova aba Início`)

---

### Task 9: Aba Atividade

**Files:** Create `src/firetv/ui/activity_tab.py`; Test `tests/test_ui_activity.py`

**Interfaces:**
- Consumes: `ActivityLog`, `format_duration`, `KNOWN_APPS`, `tint`.
- Produces: `ActivityTab(log: ActivityLog)` com botões de período `Hoje`, `7 dias` e `30 dias` (padrão Hoje), `total_label`, linhas por app com nome, duração e barra proporcional ao maior, `empty_label` (`Ainda sem dados. O histórico começa a contar quando o Stick estiver conectado.`), nota de rodapé (`Histórico local. Conta o app em primeiro plano no Stick.`) e `refresh()`. A aba chama `refresh()` ao ser mostrada.

- [ ] **Step 1: Testes (falham):** total em destaque formatado; ordem das linhas; trocar de período muda total e linhas; estado vazio; barras proporcionais (a maior com largura máxima).
- [ ] **Step 2:** `pytest tests/test_ui_activity.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar a aba.
- [ ] **Step 4:** `pytest tests/test_ui_activity.py -v`. Esperado: PASS.
- [ ] **Step 5: Commit** (`feat: aba Atividade`)

---

### Task 10: Ajustes e diagnóstico de volume

**Files:** Modify `src/firetv/ui/settings_tab.py`; Create `src/firetv/ui/volume_dialog.py`; Modify `tests/test_ui_settings.py`; Test `tests/test_ui_volume_dialog.py`

**Interfaces:**
- Consumes: `METHOD_ORDER`, `Controller.volume`, `save_config`, `AppConfig`.
- Produces: `SettingsTab` ganha `name_edit` (grava `cfg.tv_name` ao terminar a edição, vazio volta a `Fire TV`), `diagnostic_button`, e sinais `name_changed(str)` e `volume_method_changed()`.
- Produces: `VolumeDialog(session, cfg, parent=None)` com `yes_button`, `no_button`, `status_label`. Percorre `METHOD_ORDER`: envia VOLUME_UP pelo método e pergunta `O volume da TV subiu?`. Sim grava o método em `cfg.volume_method`, salva e fecha; Não segue para o próximo; ao esgotar, grava `none` e mostra `Nenhum método funcionou. O volume parece depender do controle físico.`; Cancelar não muda nada. Conexão perdida mostra `Sem conexão com o Stick. Conecte na aba Ajustes.` Sinal `finished_with(str)`.

- [ ] **Step 1: Testes (falham):** nome salvo e sinal emitido; nome vazio volta ao padrão; diagnóstico com Sim no segundo método envia dois comandos, grava `keyboard` e emite os sinais; todos Não gravam `none`; Cancelar mantém a configuração; sem conexão mostra o aviso. Os testes atuais de IP, mensagens e status continuam.
- [ ] **Step 2:** `pytest tests/test_ui_settings.py tests/test_ui_volume_dialog.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Mesmos testes. Esperado: PASS.
- [ ] **Step 5: Commit** (`feat: nome da TV e diagnóstico de volume`)

---

### Task 11: Painel, bandeja e conexão automática

**Files:** Create `src/firetv/ui/panel.py`; Delete `src/firetv/ui/main_window.py`; Modify `src/firetv/main.py`; Test `tests/test_ui_panel.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: todas as abas, `ActivityLog`, `accent_for`, `build_stylesheet`, `icon`, `Session`, `ConnectionState`, `get_bridge`.
- Produces: `panel_position(avail: QRect, size: QSize, margin: int = 12) -> QPoint` (canto inferior direito da área disponível, com margem, sem sair da área).
- Produces: `Panel(session, cfg, log)`: janela sem borda, sempre por cima, 380x560. Cabeçalho (nome da TV e `Fire TV Stick`), cinco botões de aba com ícone (`tab_buttons`), `stack`, rodapé (`status_label` com `Conectada`, `Desconectada` ou `Reconectando...`, e `host_label`), `accent` e `accent_changes` (contador). Liga: `home.polled` atualiza a cor (reaplica o estilo só se mudar), chama `apps.set_current_app` e `log.record(pacote, time.monotonic())` quando o pacote não é `None`; `home.see_all_requested` abre Apps; `settings.name_changed` atualiza o cabeçalho; `settings.volume_method_changed` chama `refresh()` nos dois cartões de áudio; ao desconectar, `log.reset_clock()`. `hide_on_deactivate` esconde ao perder o foco, salvo com `suppress_hide` ligado (diálogo aberto) ou nos 300 ms seguintes a `show_panel()`.
- Produces: `auto_connect(session, cfg) -> None`: sem IP não faz nada; com IP chama `session.connect` em segundo plano e ignora erros.
- Produces: `TrayController(app, panel)` com ícone, menu Abrir e Sair, clique esquerdo alternando o painel e `toggle()`. Sem bandeja disponível, abre o painel como janela normal. Sair grava o log e a configuração.
- `main()`: `setQuitOnLastWindowClosed(False)`, painel, bandeja, conexão automática, timer de 30 s e `aboutToQuit` gravando o log. Sem IP salvo, abre o painel direto na aba Ajustes. `--selftest` monta o painel, renderiza todos os ícones, chama `_load_signer()` e devolve 0.

- [ ] **Step 1: Testes (falham)**

```python
def test_panel_position_bottom_right_and_clamped():
def test_panel_header_shows_tv_name_and_updates(qtbot):
def test_status_footer_follows_state_and_shows_host(qtbot):
def test_tab_buttons_switch_stack(qtbot):
def test_accent_follows_polled_package_and_applies_only_on_change(qtbot):
def test_polled_records_activity_but_not_none(qtbot):
def test_hides_on_deactivate(qtbot):
def test_does_not_hide_when_suppressed_or_right_after_show(qtbot):
def test_see_all_opens_apps_tab(qtbot):
def test_volume_method_changed_refreshes_audio_cards(qtbot):
def test_auto_connect_without_host_does_nothing():
def test_auto_connect_with_host_connects_and_swallows_errors(qtbot):
def test_selftest_builds_panel_icons_and_key(qapp):    # em tests/test_main.py
```

- [ ] **Step 2:** `pytest tests/test_ui_panel.py tests/test_main.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `panel.py`, apagar `main_window.py` e atualizar `main.py`.
- [ ] **Step 4:** `pytest -q`. Esperado: toda a suíte passa.
- [ ] **Step 5: Commit** (`feat: painel na bandeja e conexão automática`)

---

### Task 12: Capturas, README e verificação

**Files:** Modify `README.md`; Create `docs/screenshots/*.png` (substitui as antigas)

- [ ] **Step 1:** Rodar `pytest -v`. Esperado: tudo passa.
- [ ] **Step 2:** Gerar uma captura de cada aba fora da tela, com dados de exemplo, e compará-las lado a lado com os quadros da gravação de referência. Anotar diferenças visíveis e corrigir as pequenas.
- [ ] **Step 3:** Gerar o executável de teste no Linux com `pyinstaller --noconfirm --onefile --noconsole --name FireTVDesktop --paths src app.py` e rodar `--selftest`. Esperado: `selftest ok`, código 0. Confirmar que o QtSvg entrou no pacote.
- [ ] **Step 4:** Atualizar o `README.md`: bandeja, as cinco abas, Atividade, diagnóstico de volume e roteiro manual novo. O `build_exe.bat` não muda.
- [ ] **Step 5 (manual, Willian, no Windows):**
  - [ ] o ícone aparece na bandeja e o clique abre e fecha o painel
  - [ ] o painel aparece perto do relógio e some ao clicar fora
  - [ ] ao abrir, conecta sozinho ao IP salvo
  - [ ] a cor muda ao abrir YouTube e Prime Video
  - [ ] Ajustes > Diagnóstico de volume: anotar qual método mexe na TV
  - [ ] Atividade passa a somar tempo depois de alguns minutos
  - [ ] fontes e tamanho no seu monitor ficam legíveis
- [ ] **Step 6: Commit** (`docs: README e capturas da v2`)
