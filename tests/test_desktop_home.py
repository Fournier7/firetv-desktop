from PySide6.QtCore import QPoint, Qt

from fakes import FakeConnection
from firetv.activity import ActivityLog
from firetv.config import AppConfig
from firetv.connection import AuthRequiredError, ConnectionFailedError
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.panel import Panel
from firetv.ui.settings_tab import MSG_AUTH, MSG_FAILED
from firetv.ui.worker import get_bridge
from firetv.session import ConnectionState


def make_panel(qtbot, tmp_path, *, connected=True, host="192.0.2.10"):
    conn = FakeConnection()
    conn.responses["dumpsys window | grep mCurrentFocus"] = "mCurrentFocus=null"
    session = Session(lambda: conn, sleep=lambda _: None)
    if connected:
        session.connect(host)
    cfg = AppConfig(host=host, tv_name="Sala", favorites=["com.netflix.ninja"])
    panel = Panel(session, cfg, ActivityLog(tmp_path / "activity.json"))
    qtbot.addWidget(panel)
    return conn, session, panel


def test_home_uses_two_columns_and_stacks_when_narrow(qtbot, tmp_path):
    _, _, panel = make_panel(qtbot, tmp_path)
    panel.resize(1060, 820)
    panel.show()
    qtbot.wait(50)
    home = panel.home_tab
    assert home.quick_remote.geometry().right() < home.summary.geometry().left()
    panel.resize(420, 760)
    qtbot.wait(50)
    assert home.quick_remote.geometry().bottom() < home.summary.geometry().top()


def test_home_remote_sends_command_once_and_does_not_intercept_typing(qtbot, tmp_path):
    conn, _, panel = make_panel(qtbot, tmp_path)
    panel.show()
    remote = panel.home_tab.quick_remote
    remote.buttons[KeyCode.HOME].click()
    qtbot.waitUntil(lambda: "input keyevent 3" in conn.commands)
    assert conn.commands.count("input keyevent 3") == 1
    remote.text_edit.setText("teste")
    qtbot.keyClick(remote.text_edit, Qt.Key_Return)
    qtbot.waitUntil(lambda: "input text 'teste'" in conn.commands)
    assert "input keyevent 23" not in conn.commands


def test_reconnect_from_home_and_show_tv_name(qtbot, tmp_path):
    conn, _, panel = make_panel(qtbot, tmp_path, connected=False)
    panel.connection_bar.action_button.click()
    assert not panel.connection_bar.action_button.isEnabled()
    qtbot.waitUntil(lambda: panel.connection_bar.action_button.isEnabled())
    assert conn.connect_calls == 1
    assert "Conectado a Sala" == panel.connection_bar.title_label.text()


def test_connection_errors_are_visible_on_home(qtbot, tmp_path):
    conn, _, panel = make_panel(qtbot, tmp_path, connected=False)
    for error, message in [(ConnectionFailedError("raw"), MSG_FAILED), (AuthRequiredError("raw"), MSG_AUTH)]:
        conn.fail_connect = error
        panel.connection_bar.action_button.click()
        qtbot.waitUntil(lambda: panel.connection_bar.action_button.isEnabled())
        assert panel.connection_bar.detail_label.text() == message


def test_without_ip_connection_action_opens_settings(qtbot, tmp_path):
    conn, _, panel = make_panel(qtbot, tmp_path, connected=False, host="")
    panel.connection_bar.action_button.click()
    assert panel.current_page() is panel.settings_tab
    assert conn.connect_calls == 0


def test_volume_configuration_is_accessible_from_home(qtbot, tmp_path):
    _, _, panel = make_panel(qtbot, tmp_path)
    audio = panel.home_tab.audio_card
    assert not audio.vol_up_button.isEnabled()
    audio.configure_button.click()
    assert panel.settings_tab.volume_dialog is not None
    panel.settings_tab.volume_dialog.reject()


def test_resized_directional_hit_testing_matches_visible_center(qtbot, tmp_path):
    conn, _, panel = make_panel(qtbot, tmp_path)
    panel.resize(1060, 820)
    panel.show()
    qtbot.wait(50)
    pad = panel.home_tab.quick_remote.dpad
    qtbot.mouseClick(pad, Qt.LeftButton, pos=QPoint(pad.width() // 2, pad.height() // 2))
    qtbot.waitUntil(lambda: "input keyevent 23" in conn.commands)


def test_disconnection_clears_the_previous_current_app(qtbot, tmp_path):
    _, session, panel = make_panel(qtbot, tmp_path)
    home = panel.home_tab
    home._on_current_app("com.netflix.ninja")
    assert home.tv_card.name_label.text() == "Netflix"
    get_bridge(session).state_changed.emit(ConnectionState.DISCONNECTED)
    assert home.tv_card.name_label.text() == "Nada em primeiro plano"
