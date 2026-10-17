import pytest

from fakes import FakeConnection
from firetv.config import AppConfig, load_config
from firetv.connection import AuthRequiredError, ConnectionFailedError
from firetv.session import ConnectionState, Session
from firetv.ui.main_window import MainWindow
from firetv.ui.settings_tab import SettingsTab
from firetv.ui.worker import get_bridge

MSG_INVALID = "Digite um IP válido, por exemplo 192.168.0.10."
MSG_FAILED = (
    "Não foi possível alcançar o Stick. Confira o IP, se a TV está ligada "
    "e se o PC e a TV estão na mesma rede."
)
MSG_AUTH = "Aceite o pedido de autorização que apareceu na TV e conecte de novo."


@pytest.fixture
def env():
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    cfg = AppConfig()
    return conn, session, cfg


def make_tab(qtbot, session, cfg):
    tab = SettingsTab(session, cfg)
    qtbot.addWidget(tab)
    return tab


def click_connect(tab, host):
    tab.host_edit.setText(host)
    tab.connect_button.click()


def test_connect_with_valid_host_calls_session_and_saves_host(qtbot, env):
    conn, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    click_connect(tab, " 192.168.0.10 ")
    qtbot.waitUntil(lambda: cfg.host == "192.168.0.10", timeout=3000)
    assert session.state is ConnectionState.CONNECTED
    assert conn.host == "192.168.0.10"
    assert load_config().host == "192.168.0.10"
    assert tab.message_label.text() == ""


def test_invalid_host_shows_message_and_does_not_connect(qtbot, env):
    conn, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    click_connect(tab, "999.1.1.1")
    assert tab.message_label.text() == MSG_INVALID
    assert conn.connect_calls == 0


def test_empty_host_shows_message(qtbot, env):
    conn, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    click_connect(tab, "")
    assert tab.message_label.text() == MSG_INVALID
    assert conn.connect_calls == 0


def test_connection_failed_shows_network_message(qtbot, env):
    conn, session, cfg = env
    conn.fail_connect = ConnectionFailedError("x")
    tab = make_tab(qtbot, session, cfg)
    click_connect(tab, "192.168.0.10")
    qtbot.waitUntil(lambda: tab.message_label.text() == MSG_FAILED, timeout=3000)
    qtbot.waitUntil(tab.connect_button.isEnabled, timeout=3000)
    assert cfg.host == ""


def test_auth_required_shows_authorization_message(qtbot, env):
    conn, session, cfg = env
    conn.fail_connect = AuthRequiredError("x")
    tab = make_tab(qtbot, session, cfg)
    click_connect(tab, "192.168.0.10")
    qtbot.waitUntil(lambda: tab.message_label.text() == MSG_AUTH, timeout=3000)


def test_status_label_follows_state(qtbot, env):
    conn, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    assert tab.status_label.text() == "Desconectado"
    bridge = get_bridge(session)
    bridge.state_changed.emit(ConnectionState.RECONNECTING)
    assert tab.status_label.text() == "Reconectando..."
    click_connect(tab, "192.168.0.10")
    qtbot.waitUntil(lambda: tab.status_label.text() == "Conectado", timeout=3000)
    bridge.state_changed.emit(ConnectionState.DISCONNECTED)
    assert tab.status_label.text() == "Desconectado"


def test_host_field_starts_with_saved_host_and_help_is_visible(qtbot, env):
    _, session, _ = env
    tab = make_tab(qtbot, session, AppConfig(host="10.0.0.5"))
    assert tab.host_edit.text() == "10.0.0.5"
    assert "Depuração ADB" in tab.help_label.text()


def test_main_window_tab_order(qtbot, env):
    _, session, cfg = env
    win = MainWindow(session, cfg)
    qtbot.addWidget(win)
    titles = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert titles == ["Início", "Controle", "Apps", "Ajustes"]
