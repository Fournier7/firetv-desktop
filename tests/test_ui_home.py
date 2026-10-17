import pytest

from fakes import FakeConnection
from firetv.config import AppConfig
from firetv.session import ConnectionState, Session
from firetv.ui.home_tab import HomeTab
from firetv.ui.widgets import AudioCard, TvCard
from firetv.ui.worker import get_bridge

FOCUS = "dumpsys window | grep mCurrentFocus"
NETFLIX = "mCurrentFocus=Window{abc u0 com.netflix.ninja/com.netflix.ninja.MainActivity}"
UNKNOWN = "mCurrentFocus=Window{abc u0 x.y.z/x.y.z.Main}"
PM = "pm list packages"
FIVE = ["com.netflix.ninja", "com.amazon.firetv.youtube", "com.amazon.avod",
        "com.disney.disneyplus", "x.y.z"]


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


def poll_and_wait(qtbot, home):
    with qtbot.waitSignal(home.polled, timeout=3000) as blocker:
        home.poll()
    return blocker.args[0]


def test_structure(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    assert isinstance(home.tv_card, TvCard) and isinstance(home.audio_card, AudioCard)


def test_home_shows_current_app_name(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    assert poll_and_wait(qtbot, home) == "com.netflix.ninja"
    assert home.tv_card.name_label.text() == "Netflix"
    assert "rgba(229, 9, 20" in home.tv_card.styleSheet()  # cor do app


def test_home_unknown_package_shows_package_name(qtbot, env):
    conn, session = env
    conn.responses[FOCUS] = UNKNOWN
    home = make_home(qtbot, session)
    assert poll_and_wait(qtbot, home) == "x.y.z"
    assert home.tv_card.name_label.text() == "x.y.z"


def test_home_no_foreground_app_shows_placeholder_and_emits_none(qtbot, env):
    conn, session = env
    conn.responses[FOCUS] = "mCurrentFocus=null"
    home = make_home(qtbot, session)
    assert poll_and_wait(qtbot, home) is None
    assert home.tv_card.name_label.text() == "Nada em primeiro plano"


def test_polled_is_emitted_on_every_poll(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    poll_and_wait(qtbot, home)
    assert poll_and_wait(qtbot, home) == "com.netflix.ninja"


def test_home_favorites_strip_lists_favorites_without_star(qtbot, env):
    _, session = env
    home = make_home(qtbot, session, AppConfig(favorites=["com.netflix.ninja"]))
    tiles = home.favorite_tiles()
    assert [t.name_label.text() for t in tiles] == ["Netflix"]
    assert all(t.star_button is None for t in tiles)
    assert home.favorites_empty_label.isHidden()


def test_home_favorites_strip_shows_at_most_four(qtbot, env):
    _, session = env
    home = make_home(qtbot, session, AppConfig(favorites=FIVE))
    assert len(home.favorite_tiles()) == 4
    assert [t.entry.package for t in home.favorite_tiles()] == FIVE[:4]


def test_home_without_favorites_shows_hint(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    assert home.favorite_tiles() == []
    assert not home.favorites_empty_label.isHidden()


def test_refresh_favorites_follows_config(qtbot, env):
    _, session = env
    cfg = AppConfig()
    home = make_home(qtbot, session, cfg)
    cfg.favorites.append("com.netflix.ninja")
    home.refresh_favorites()
    assert len(home.favorite_tiles()) == 1
    cfg.favorites.clear()
    home.refresh_favorites()
    assert home.favorite_tiles() == [] and not home.favorites_empty_label.isHidden()


def test_see_all_button_emits_signal(qtbot, env):
    _, session = env
    home = make_home(qtbot, session)
    with qtbot.waitSignal(home.see_all_requested, timeout=1000):
        home.see_all_button.click()


def test_favorite_tile_click_launches_app(qtbot, env):
    conn, session = env
    home = make_home(qtbot, session, AppConfig(favorites=["com.netflix.ninja"]))
    home.favorite_tiles()[0].launch_requested.emit("com.netflix.ninja")
    expected = "monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1"
    qtbot.waitUntil(lambda: expected in conn.commands, timeout=3000)


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
    qtbot.wait(100)
    assert conn.commands == []
