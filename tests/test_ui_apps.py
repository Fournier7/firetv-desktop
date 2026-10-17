import pytest
from PySide6.QtCore import Qt

from fakes import FakeConnection
from firetv.config import AppConfig, load_config
from firetv.session import Session
from firetv.apps import AppEntry
from firetv.ui.apps_tab import AppsTab, AppTile

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
    assert not netflix.star_button.isChecked()
    netflix.star_button.click()
    assert cfg.favorites == ["com.netflix.ninja"]
    assert load_config().favorites == ["com.netflix.ninja"]
    netflix = next(t for t in tab.tiles() if t.name_label.text() == "Netflix")
    assert netflix.star_button.isChecked()
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


NETFLIX = "com.netflix.ninja"


def test_search_placeholder_shows_total_of_loaded_apps(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(hidden=["x.y.z"]), expected_tiles=2)
    assert tab.search_edit.placeholderText() == "Buscar nos 3 apps"  # conta os escondidos também


def test_search_placeholder_without_apps(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    tab = make_tab(qtbot, session, AppConfig())
    assert tab.search_edit.placeholderText() == "Buscar apps"


def test_set_current_app_marks_only_that_tile_on_screen(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(), expected_tiles=3)
    tab.set_current_app(NETFLIX)
    flags = {t.entry.package: not t.badge_label.isHidden() for t in tab.tiles()}
    assert flags == {NETFLIX: True, "x.y.z": False, "a.b.c": False}
    assert next(t for t in tab.tiles() if t.entry.package == NETFLIX).badge_label.text() == "NA TELA"
    tab.set_current_app(None)
    assert all(t.badge_label.isHidden() for t in tab.tiles())


def test_current_app_survives_a_re_render(qtbot, env):
    _, session = env
    tab = make_tab(qtbot, session, AppConfig(), expected_tiles=3)
    tab.set_current_app(NETFLIX)
    tab.search_edit.setText("netf")
    [tile] = tab.tiles()
    assert not tile.badge_label.isHidden()


def test_tile_is_tinted_with_the_app_color(qtbot):
    entry = AppEntry(package=NETFLIX, name="Netflix", color="#E50914", favorite=False, hidden=False)
    tile = AppTile(entry)
    qtbot.addWidget(tile)
    assert "rgba(229, 9, 20" in tile.styleSheet()


def test_tile_without_star(qtbot):
    entry = AppEntry(package=NETFLIX, name="Netflix", color="#E50914", favorite=True, hidden=False)
    tile = AppTile(entry, show_star=False)
    qtbot.addWidget(tile)
    assert tile.star_button is None


def test_tile_star_reflects_favorite(qtbot):
    entry = AppEntry(package=NETFLIX, name="Netflix", color="#E50914", favorite=True, hidden=False)
    tile = AppTile(entry)
    qtbot.addWidget(tile)
    assert tile.star_button.isChecked() and tile.badge_label.isHidden()


def test_compact_tile_is_smaller(qtbot):
    entry = AppEntry(package=NETFLIX, name="Netflix", color="#E50914", favorite=False, hidden=False)
    normal, compact = AppTile(entry), AppTile(entry, show_star=False, compact=True)
    qtbot.addWidget(normal)
    qtbot.addWidget(compact)
    assert compact.width() < normal.width() and compact.height() < normal.height()
    assert compact.width() * 4 + 3 * 8 <= 340  # 4 tiles cabem na largura útil do painel
