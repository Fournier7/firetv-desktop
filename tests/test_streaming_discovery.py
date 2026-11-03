from PySide6.QtCore import QAbstractAnimation, QEvent, Qt

from fakes import FakeConnection
from firetv.apps import build_entries, streaming_suggestions
from firetv.config import AppConfig
from firetv.session import Session
from firetv.ui.apps_tab import AppsTab, AppTile
from firetv.ui.widgets import TvCard


def test_catalog_recognizes_apps_and_excludes_internal_overlays():
    packages = ['com.globo.globotv', 'com.kick.mobile', 'com.esaba.downloader',
                'com.amazon.tv.settings.v2.overlay.localisation.common']
    entries = {e.package: e for e in build_entries(packages, AppConfig(), third_party=set(packages))}
    assert entries['com.globo.globotv'].name == 'Globoplay'
    assert entries['com.kick.mobile'].name == 'Kick'
    assert entries['com.esaba.downloader'].name == 'Downloader'
    assert not entries[packages[-1]].featured


def test_suggestions_do_not_duplicate_installed_services_or_package_aliases():
    installed = build_entries(['com.wbd.stream', 'com.globo.globotv'], AppConfig())
    names = [e.name for e in streaming_suggestions(installed)]
    assert 'HBO Max' not in names and 'Globoplay' not in names
    assert 'Paramount+' in names and 'Apple TV' in names
    assert len(names) == len(set(names))
    assert 'Downloader' not in names


def test_suggestions_do_not_send_launch_or_install_commands(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn)
    tab = AppsTab(session, AppConfig())
    qtbot.addWidget(tab)
    tab.mode_tabs.setCurrentIndex(1)
    assert 'HBO Max' in [t.entry.name for t in tab.tiles()]
    tile = next(t for t in tab.tiles() if t.entry.name == 'HBO Max')
    qtbot.mouseClick(tile, Qt.LeftButton)
    assert conn.commands == []
    assert 'HBO Max' in tab.message_label.text()
    assert tile.star_button is None


def test_tv_display_preserves_name_and_does_not_restart_transition_for_same_app(qtbot):
    card = TvCard()
    qtbot.addWidget(card)
    card.show()
    card.set_app('Globoplay', '#F45B39')
    assert card.name_label.text() == 'Globoplay'
    assert card.screen is not None
    qtbot.wait(300)
    card.set_app('Globoplay', '#F45B39')
    assert card.transition.state() == QAbstractAnimation.Stopped


def test_favorite_animation_does_not_move_tile_or_duplicate_launch(qtbot):
    entry = build_entries(['com.netflix.ninja'], AppConfig())[0]
    tile = AppTile(entry, show_star=False, compact=True, animated=True)
    qtbot.addWidget(tile)
    tile.show()
    original = tile.geometry()
    from PySide6.QtWidgets import QApplication
    QApplication.sendEvent(tile, QEvent(QEvent.Enter))
    qtbot.wait(200)
    assert tile.geometry() == original
    with qtbot.waitSignal(tile.launch_requested) as signal:
        qtbot.mouseClick(tile, Qt.LeftButton)
    assert signal.args == ['com.netflix.ninja']
    tile.hide()
    assert tile.hover_animation.state() == QAbstractAnimation.Stopped
