import pytest

from fakes import FakeConnection
from firetv.config import AppConfig, load_config
from firetv.session import Session
from firetv.ui.settings_tab import SettingsTab
from firetv.ui.volume_dialog import VolumeDialog

MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
MSG_NONE = "Nenhum método funcionou. O volume parece depender do controle físico."
COMMANDS = [
    "input keyevent 24",
    "input keyboard keyevent 24",
    "cmd media_session volume --show --adj raise",
    "media volume --show --adj raise",
]


@pytest.fixture
def env():
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    session.connect("192.168.0.10")
    return conn, session


def make_dialog(qtbot, session, cfg):
    dialog = VolumeDialog(session, cfg)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.start()
    return dialog


def ready(qtbot, dialog):
    qtbot.waitUntil(dialog.yes_button.isEnabled, timeout=3000)


def test_first_step_sends_the_first_method_and_asks(qtbot, env):
    conn, session = env
    dialog = make_dialog(qtbot, session, AppConfig())
    qtbot.waitUntil(lambda: conn.commands == COMMANDS[:1], timeout=3000)
    ready(qtbot, dialog)
    assert "O volume da TV subiu?" in dialog.status_label.text()


def test_yes_on_second_method_saves_keyboard_and_emits(qtbot, env):
    conn, session = env
    cfg = AppConfig()
    dialog = make_dialog(qtbot, session, cfg)
    ready(qtbot, dialog)
    dialog.no_button.click()
    qtbot.waitUntil(lambda: conn.commands == COMMANDS[:2], timeout=3000)
    ready(qtbot, dialog)
    with qtbot.waitSignal(dialog.finished_with, timeout=3000) as blocker:
        dialog.yes_button.click()
    assert blocker.args == ["keyboard"]
    assert cfg.volume_method == "keyboard" and load_config().volume_method == "keyboard"
    assert conn.commands == COMMANDS[:2]


def test_all_no_saves_none_and_explains(qtbot, env):
    conn, session = env
    cfg = AppConfig()
    dialog = make_dialog(qtbot, session, cfg)
    for step in range(1, 4):
        qtbot.waitUntil(lambda s=step: len(conn.commands) == s, timeout=3000)
        ready(qtbot, dialog)
        dialog.no_button.click()
    qtbot.waitUntil(lambda: len(conn.commands) == 4, timeout=3000)
    ready(qtbot, dialog)
    with qtbot.waitSignal(dialog.finished_with, timeout=3000) as blocker:
        dialog.no_button.click()
    assert blocker.args == ["none"]
    assert conn.commands == COMMANDS
    assert cfg.volume_method == "none" and load_config().volume_method == "none"
    assert dialog.message_label.text() == MSG_NONE
    assert dialog.yes_button.isHidden() and dialog.no_button.isHidden()


def test_cancel_keeps_config_and_emits_nothing(qtbot, env):
    conn, session = env
    cfg = AppConfig(volume_method="media")
    dialog = make_dialog(qtbot, session, cfg)
    ready(qtbot, dialog)
    with qtbot.assertNotEmitted(dialog.finished_with):
        dialog.cancel_button.click()
    assert cfg.volume_method == "media" and not dialog.isVisible()


def test_method_that_errors_is_skipped_without_asking(qtbot, env):
    conn, session = env
    conn.responses["input keyevent 24"] = "Error: not supported"
    dialog = make_dialog(qtbot, session, AppConfig())
    qtbot.waitUntil(lambda: conn.commands[:2] == COMMANDS[:2], timeout=3000)
    ready(qtbot, dialog)
    assert "O volume da TV subiu?" in dialog.status_label.text()


def test_lost_connection_shows_notice_and_disables_answers(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    dialog = make_dialog(qtbot, session, AppConfig())
    qtbot.waitUntil(lambda: dialog.message_label.text() == MSG_LOST, timeout=3000)
    assert not dialog.yes_button.isEnabled() and not dialog.no_button.isEnabled()


def test_settings_tab_opens_dialog_and_emits_signals(qtbot, env):
    conn, session = env
    cfg = AppConfig()
    tab = SettingsTab(session, cfg)
    qtbot.addWidget(tab)
    activity = []
    tab.dialog_active.connect(activity.append)
    tab.diagnostic_button.click()
    assert activity == [True]
    dialog = tab.volume_dialog
    ready(qtbot, dialog)
    with qtbot.waitSignal(tab.volume_method_changed, timeout=3000):
        dialog.yes_button.click()
    qtbot.waitUntil(lambda: activity == [True, False], timeout=3000)
    assert cfg.volume_method == "keyevent"


def test_settings_tab_cancel_reports_inactive_and_does_not_signal_method(qtbot, env):
    _, session = env
    tab = SettingsTab(session, AppConfig())
    qtbot.addWidget(tab)
    activity = []
    tab.dialog_active.connect(activity.append)
    changed = []
    tab.volume_method_changed.connect(lambda: changed.append(1))
    tab.diagnostic_button.click()
    ready(qtbot, tab.volume_dialog)
    tab.volume_dialog.cancel_button.click()
    qtbot.waitUntil(lambda: activity == [True, False], timeout=3000)
    assert changed == []
