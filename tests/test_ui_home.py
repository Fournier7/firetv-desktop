import pytest

from fakes import FakeConnection
from firetv.config import AppConfig
from firetv.session import ConnectionState, Session
from firetv.ui.home_tab import HomeTab
from firetv.ui.main_window import MainWindow
from firetv.ui.worker import get_bridge

FOCUS = "dumpsys window | grep mCurrentFocus"
NETFLIX = "mCurrentFocus=Window{abc u0 com.netflix.ninja/com.netflix.ninja.MainActivity}"
UNKNOWN = "mCurrentFocus=Window{abc u0 x.y.z/x.y.z.Main}"
PM = "pm list packages"


@pytest.fixture
def env():
    conn = FakeConnection()
    conn.responses[FOCUS] = NETFLIX
    conn.responses[PM] = "package:com.netflix.ninja\npackage:x.y.z\n"
    session = Session(lambda: conn, sleep=lambda s: None)
    session.connect("192.168.0.10")
    return conn, session


def make_home(qtbot, session, cfg=None):
    home = HomeTab(session, cfg or AppConfig())
    qtbot.addWidget(home)
    home.show()
    return home


def test_home_shows_current_app_name(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    home.poll()
    qtbot.waitUntil(lambda: home.current_app_label.text() == "Netflix", timeout=3000)


def test_home_unknown_package_shows_package_name(qtbot, env):
    conn, session = env
    conn.responses[FOCUS] = UNKNOWN
    home = make_home(qtbot, session)
    home.poll()
    qtbot.waitUntil(lambda: home.current_app_label.text() == "x.y.z", timeout=3000)


def test_home_no_foreground_app_shows_placeholder(qtbot, env):
    conn, session = env
    conn.responses[FOCUS] = "mCurrentFocus=null"
    home = make_home(qtbot, session)
    home.poll()
    qtbot.waitUntil(lambda: home.current_app_label.text() == "Nenhum app em primeiro plano", timeout=3000)


def test_home_favorites_strip_lists_favorites(qtbot, env):
    _, session = env
    home = make_home(qtbot, session, AppConfig(favorites=["com.netflix.ninja"]))
    assert [t.name_label.text() for t in home.favorite_tiles()] == ["Netflix"]


def test_home_favorites_match_apps_tab(qtbot, env):
    _, session = env
    win = MainWindow(session, AppConfig())
    qtbot.addWidget(win)
    win.show()
    win.apps_tab.refresh()
    qtbot.waitUntil(lambda: len(win.apps_tab.tiles()) == 2, timeout=3000)
    assert win.home_tab.favorite_tiles() == []
    netflix = next(t for t in win.apps_tab.tiles() if t.name_label.text() == "Netflix")
    netflix.star_button.click()
    assert [t.name_label.text() for t in win.home_tab.favorite_tiles()] == ["Netflix"]


def test_home_polling_stops_when_disconnected(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    assert home.timer.isActive() and home.timer.interval() == 3000
    bridge = get_bridge(session)
    bridge.state_changed.emit(ConnectionState.DISCONNECTED)
    assert not home.timer.isActive()
    bridge.state_changed.emit(ConnectionState.CONNECTED)
    assert home.timer.isActive()


def test_home_does_not_poll_while_never_connected(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    home = make_home(qtbot, session)
    assert not home.timer.isActive()
