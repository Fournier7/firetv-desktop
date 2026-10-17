import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from fakes import FakeConnection
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.remote_tab import RemoteTab

MSG_VOLUME = "O volume não respondeu neste aparelho. Este recurso é experimental."
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
    t = RemoteTab(session)
    qtbot.addWidget(t)
    t.show()
    return t


def sent(conn, command):
    return lambda: command in conn.commands


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
    hidden = RemoteTab(session)
    qtbot.addWidget(hidden)
    qtbot.keyClick(hidden, Qt.Key_Up)
    qtbot.wait(150)
    assert conn.commands == []


def test_button_click_sends_key(qtbot, env, tab):
    conn, _ = env
    tab.buttons[KeyCode.HOME].click()
    qtbot.waitUntil(sent(conn, "input keyevent 3"), timeout=3000)


def test_send_text_button_sends_text(qtbot, env, tab):
    conn, _ = env
    tab.text_edit.setText("oi mundo")
    tab.send_button.click()
    qtbot.waitUntil(sent(conn, "input text 'oi%smundo'"), timeout=3000)
    qtbot.waitUntil(lambda: tab.text_edit.text() == "", timeout=3000)
    assert tab.notice_label.text() == ""


def test_skipped_characters_notice(qtbot, env, tab):
    conn, _ = env
    tab.text_edit.setText("ação")
    tab.send_button.click()
    qtbot.waitUntil(lambda: "çã" in tab.notice_label.text(), timeout=3000)
    assert tab.notice_label.text() == "Não foi possível enviar: çã"
    assert conn.commands == ["input text 'ao'"]


def test_volume_buttons_labelled_experimental(tab):
    assert tab.volume_label.text() == "Volume (experimental)"
    assert set(tab.volume_buttons) == {KeyCode.VOLUME_DOWN, KeyCode.MUTE, KeyCode.VOLUME_UP}


def test_volume_failure_shows_notice(qtbot, env, tab):
    conn, _ = env
    conn.responses["input keyevent 24"] = "Error: not supported"
    tab.volume_buttons[KeyCode.VOLUME_UP].click()
    qtbot.waitUntil(lambda: tab.notice_label.text() == MSG_VOLUME, timeout=3000)


def test_command_without_connection_shows_notice(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    t = RemoteTab(session)
    qtbot.addWidget(t)
    t.buttons[KeyCode.OK].click()
    qtbot.waitUntil(lambda: t.notice_label.text() == MSG_LOST, timeout=3000)
