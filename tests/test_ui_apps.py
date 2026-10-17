import pytest
from PySide6.QtCore import Qt

from fakes import FakeConnection
from firetv.config import AppConfig, load_config
from firetv.session import Session
from firetv.ui.apps_tab import AppsTab

PM = "pm list packages"
PACKAGES = "package:com.netflix.ninja\npackage:x.y.z\npackage:a.b.c\n"
EMPTY_MSG = "Nenhum app encontrado. Conecte ao Stick na aba Ajustes."


@pytest.fixture
def env():
    conn = FakeConnection()
    conn.responses[PM] = PACKAGES
    session = Session(lambda: conn, sleep=lambda s: None)
    session.connect("192.168.0.10")
    return conn, session


def make_tab(qtbot, session, cfg, expected_tiles=None):
    tab = AppsTab(session, cfg)
    qtbot.addWidget(tab)
    tab.show()
    tab.refresh()
    if expected_tiles is not None:
        qtbot.waitUntil(lambda: len(tab.tiles()) == expected_tiles, timeout=3000)
    return tab


def names(tab):
    return [t.name_label.text() for t in tab.tiles()]


def test_grid_hides_hidden_apps_by_default(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(hidden=["x.y.z"]), expected_tiles=2)
    assert names(tab) == ["a.b.c", "Netflix"]


def test_show_hidden_option_reveals_them(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(hidden=["x.y.z"]), expected_tiles=2)
    tab.show_hidden_check.setChecked(True)
    assert names(tab) == ["a.b.c", "Netflix", "x.y.z"]


def test_star_click_toggles_favorite_and_saves_config(qtbot, env):
    _, session = env
    cfg = AppConfig()
    tab = make_tab(qtbot, session, cfg, expected_tiles=3)
    netflix = next(t for t in tab.tiles() if t.name_label.text() == "Netflix")
    netflix.star_button.click()
    assert cfg.favorites == ["com.netflix.ninja"]
    assert load_config().favorites == ["com.netflix.ninja"]
    netflix = next(t for t in tab.tiles() if t.name_label.text() == "Netflix")
    assert netflix.star_button.text() == "★"
    netflix.star_button.click()
    assert cfg.favorites == []


def test_toggle_hidden_hides_tile_and_saves_config(qtbot, env):
    _, session = env
    cfg = AppConfig()
    tab = make_tab(qtbot, session, cfg, expected_tiles=3)
    tab.toggle_hidden("x.y.z")
    assert cfg.hidden == ["x.y.z"] and load_config().hidden == ["x.y.z"]
    assert names(tab) == ["a.b.c", "Netflix"]


def test_search_filters_grid(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(), expected_tiles=3)
    tab.search_edit.setText("netf")
    assert names(tab) == ["Netflix"]


def test_empty_list_shows_empty_state_message(qtbot, env):
    conn, session = env
    conn.responses[PM] = ""
    tab = make_tab(qtbot, session, AppConfig())
    qtbot.waitUntil(lambda: tab.empty_label.isVisible(), timeout=3000)
    assert tab.empty_label.text() == EMPTY_MSG
    assert tab.tiles() == []


def test_not_connected_shows_empty_state_message(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    tab = make_tab(qtbot, session, AppConfig())
    qtbot.waitUntil(lambda: tab.empty_label.isVisible(), timeout=3000)
    assert tab.empty_label.text() == EMPTY_MSG


def test_unknown_package_tile_shows_package_name(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(), expected_tiles=3)
    assert "x.y.z" in names(tab)


def test_tile_click_launches_package(qtbot, env):
    conn, session = env
    tab = make_tab(qtbot, session, AppConfig(), expected_tiles=3)
    netflix = next(t for t in tab.tiles() if t.name_label.text() == "Netflix")
    qtbot.mouseClick(netflix, Qt.LeftButton)
    expected = "monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1"
    qtbot.waitUntil(lambda: expected in conn.commands, timeout=3000)


def test_refreshes_when_session_connects(qtbot):
    conn = FakeConnection()
    conn.responses[PM] = PACKAGES
    session = Session(lambda: conn, sleep=lambda s: None)
    tab = AppsTab(session, AppConfig())
    qtbot.addWidget(tab)
    tab.show()
    session.connect("192.168.0.10")
    qtbot.waitUntil(lambda: len(tab.tiles()) == 3, timeout=3000)
