import pytest

from fakes import FakeConnection
from firetv.config import AppConfig, load_config
from firetv.connection import AuthRequiredError, ConnectionFailedError
from firetv.session import ConnectionState, Session
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


def test_name_field_starts_with_saved_name(qtbot, env):
    _, session, _ = env
    tab = make_tab(qtbot, session, AppConfig(tv_name="Sala"))
    assert tab.name_edit.text() == "Sala"


def test_name_is_saved_and_signalled(qtbot, env):
    _, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    with qtbot.waitSignal(tab.name_changed, timeout=1000) as blocker:
        tab.name_edit.setText("  Sala  ")
        tab.name_edit.editingFinished.emit()
    assert blocker.args == ["Sala"]
    assert cfg.tv_name == "Sala" and load_config().tv_name == "Sala"


def test_blank_name_goes_back_to_default(qtbot, env):
    _, session, cfg = env
    cfg.tv_name = "Sala"
    tab = make_tab(qtbot, session, cfg)
    with qtbot.waitSignal(tab.name_changed, timeout=1000) as blocker:
        tab.name_edit.setText("   ")
        tab.name_edit.editingFinished.emit()
    assert blocker.args == ["Fire TV"] and tab.name_edit.text() == "Fire TV"
    assert cfg.tv_name == "Fire TV"


def test_diagnostic_button_exists(qtbot, env):
    _, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    assert tab.diagnostic_button.text() == "Diagnóstico de volume"


def test_connected_signal_carries_the_host(qtbot, env):
    conn, session, cfg = env
    tab = make_tab(qtbot, session, cfg)
    with qtbot.waitSignal(tab.connected, timeout=3000) as blocker:
        click_connect(tab, "192.168.0.10")
    assert blocker.args == ["192.168.0.10"]


def test_connected_signal_not_emitted_on_failure(qtbot, env):
    conn, session, cfg = env
    conn.fail_connect = ConnectionFailedError("x")
    tab = make_tab(qtbot, session, cfg)
    with qtbot.assertNotEmitted(tab.connected):
        click_connect(tab, "192.168.0.10")
        qtbot.waitUntil(lambda: tab.message_label.text() == MSG_FAILED, timeout=3000)
