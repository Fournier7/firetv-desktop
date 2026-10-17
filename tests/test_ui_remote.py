import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from fakes import FakeConnection
from firetv.config import AppConfig
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.remote_tab import RemoteTab
from firetv.ui.widgets import AudioCard

MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."


@pytest.fixture
def env():
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    session.connect("192.168.0.10")
    return conn, session


@pytest.fixture
def tab(qtbot, env):
    _, session = env
    t = RemoteTab(session, AppConfig())
    qtbot.addWidget(t)
    t.show()
    return t


def sent(conn, command):
    return lambda: command in conn.commands


def test_structure(tab):
    assert set(tab.buttons) == {
        KeyCode.HOME, KeyCode.BACK, KeyCode.MENU,
        KeyCode.REWIND, KeyCode.PLAY_PAUSE, KeyCode.FAST_FORWARD,
    }
    assert isinstance(tab.audio_card, AudioCard)


def test_arrow_up_sends_dpad_up(qtbot, env, tab):
    conn, _ = env
    qtbot.keyClick(tab, Qt.Key_Up)
    qtbot.waitUntil(sent(conn, "input keyevent 19"), timeout=3000)


def test_enter_and_escape_map_to_ok_and_back(qtbot, env, tab):
    conn, _ = env
    qtbot.keyClick(tab, Qt.Key_Return)
    qtbot.keyClick(tab, Qt.Key_Escape)
    qtbot.waitUntil(sent(conn, "input keyevent 23"), timeout=3000)
    qtbot.waitUntil(sent(conn, "input keyevent 4"), timeout=3000)


def test_shortcuts_ignored_while_typing_in_text_field(qtbot, env, tab):
    conn, _ = env
    tab.activateWindow()
    tab.text_edit.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is tab.text_edit, timeout=3000)
    qtbot.keyClick(tab.text_edit, Qt.Key_Up)  # o campo ignora e o evento sobe ao pai
    qtbot.keyClick(tab.text_edit, Qt.Key_Left)
    qtbot.keyClick(tab.text_edit, Qt.Key_Return)
    qtbot.wait(150)
    assert conn.commands == []


def test_shortcuts_ignored_when_tab_is_hidden(qtbot, env):
    conn, session = env
    hidden = RemoteTab(session, AppConfig())
    qtbot.addWidget(hidden)
    qtbot.keyClick(hidden, Qt.Key_Up)
    qtbot.wait(150)
    assert conn.commands == []


@pytest.mark.parametrize(
    "key, command",
    [(KeyCode.HOME, "input keyevent 3"), (KeyCode.BACK, "input keyevent 4"),
     (KeyCode.MENU, "input keyevent 82"), (KeyCode.REWIND, "input keyevent 89"),
     (KeyCode.PLAY_PAUSE, "input keyevent 85"), (KeyCode.FAST_FORWARD, "input keyevent 90")],
)
def test_button_click_sends_key(qtbot, env, tab, key, command):
    conn, _ = env
    tab.buttons[key].click()
    qtbot.waitUntil(sent(conn, command), timeout=3000)


@pytest.mark.parametrize(
    "pos, command",
    [(QPoint(100, 15), "input keyevent 19"), (QPoint(100, 185), "input keyevent 20"),
     (QPoint(15, 100), "input keyevent 21"), (QPoint(185, 100), "input keyevent 22"),
     (QPoint(100, 100), "input keyevent 23")],
)
def test_dpad_click_sends_key(qtbot, env, tab, pos, command):
    conn, _ = env
    qtbot.mouseClick(tab.dpad, Qt.LeftButton, pos=pos)
    qtbot.waitUntil(sent(conn, command), timeout=3000)


def test_send_text_button_sends_text_and_clears_field(qtbot, env, tab):
    conn, _ = env
    tab.text_edit.setText("oi mundo")
    tab.send_button.click()
    qtbot.waitUntil(sent(conn, "input text 'oi%smundo'"), timeout=3000)
    qtbot.waitUntil(lambda: tab.text_edit.text() == "", timeout=3000)
    assert tab.notice_label.text() == ""


def test_return_in_text_field_sends_text(qtbot, env, tab):
    conn, _ = env
    tab.text_edit.setText("abc")
    qtbot.keyClick(tab.text_edit, Qt.Key_Return)
    qtbot.waitUntil(sent(conn, "input text 'abc'"), timeout=3000)


def test_empty_text_sends_nothing(qtbot, env, tab):
    conn, _ = env
    tab.send_button.click()
    qtbot.wait(150)
    assert conn.commands == []


def test_skipped_characters_notice(qtbot, env, tab):
    conn, _ = env
    tab.text_edit.setText("ação")
    tab.send_button.click()
    qtbot.waitUntil(lambda: "çã" in tab.notice_label.text(), timeout=3000)
    assert tab.notice_label.text() == "Não foi possível enviar: çã"
    assert conn.commands == ["input text 'ao'"]


def test_command_without_connection_shows_notice(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    t = RemoteTab(session, AppConfig())
    qtbot.addWidget(t)
    t.buttons[KeyCode.HOME].click()
    qtbot.waitUntil(lambda: t.notice_label.text() == MSG_LOST, timeout=3000)
