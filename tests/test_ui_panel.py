import os
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QSystemTrayIcon

from fakes import FakeConnection
from firetv.activity import ActivityLog
from firetv.config import AppConfig, load_config
from firetv.connection import ConnectionFailedError
from firetv.session import ConnectionState, Session
from firetv.ui import panel as panel_module
from firetv.ui.panel import Panel, TrayController, auto_connect, panel_position
from firetv.ui.theme import DEFAULT_ACCENT
from firetv.ui.worker import get_bridge

FOCUS = "dumpsys window | grep mCurrentFocus"
NETFLIX = "com.netflix.ninja"
PRIME = "com.amazon.avod"


class SpyLog(ActivityLog):
    def __init__(self, path):
        super().__init__(path)
        self.records, self.resets, self.saves = [], 0, 0

    def record(self, package, now):
        self.records.append((package, now))
        super().record(package, now)

    def reset_clock(self):
        self.resets += 1
        super().reset_clock()

    def save(self):
        self.saves += 1
        super().save()


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def env(tmp_path):
    conn = FakeConnection()
    conn.responses[FOCUS] = f"mCurrentFocus=Window{{a u0 {NETFLIX}/x.Main}}"
    conn.responses["pm list packages"] = f"package:{NETFLIX}\npackage:{PRIME}\n"
    session = Session(lambda: conn, sleep=lambda s: None)
    return conn, session, AppConfig(host="192.168.0.10", tv_name="Sala"), SpyLog(tmp_path / "act.json")


def make_panel(qtbot, env, clock=None):
    _, session, cfg, log = env
    panel = Panel(session, cfg, log, clock=clock or Clock())
    qtbot.addWidget(panel)
    return panel


def test_panel_position_bottom_right_and_clamped():
    avail = QRect(0, 0, 1920, 1040)
    assert panel_position(avail, QSize(380, 560)) == QPoint(1528, 468)
    assert panel_position(avail, QSize(380, 560), margin=0) == QPoint(1540, 480)
    assert panel_position(QRect(100, 50, 300, 300), QSize(380, 560)) == QPoint(100, 50)
    offset = QRect(1920, 0, 1920, 1040)  # segundo monitor à direita
    assert panel_position(offset, QSize(380, 560)).x() == 1920 + 1920 - 380 - 12


def test_panel_window_flags_and_size(qtbot, env):
    panel = make_panel(qtbot, env)
    flags = panel.windowFlags()
    assert flags & Qt.FramelessWindowHint and flags & Qt.WindowStaysOnTopHint and flags & Qt.Tool
    assert panel.size() == QSize(380, 560)


def test_header_shows_tv_name_and_updates(qtbot, env):
    panel = make_panel(qtbot, env)
    assert panel.name_label.text() == "Sala" and panel.subtitle_label.text() == "Fire TV Stick"
    panel.settings_tab.name_changed.emit("Quarto")
    assert panel.name_label.text() == "Quarto"


def test_status_footer_follows_state_and_shows_host(qtbot, env):
    _, session, cfg, _ = env
    panel = make_panel(qtbot, env)
    assert panel.status_label.text() == "Desconectada" and panel.host_label.text() == "192.168.0.10"
    bridge = get_bridge(session)
    bridge.state_changed.emit(ConnectionState.CONNECTED)
    assert panel.status_label.text() == "Conectada"
    bridge.state_changed.emit(ConnectionState.RECONNECTING)
    assert panel.status_label.text() == "Reconectando..."
    bridge.state_changed.emit(ConnectionState.DISCONNECTED)
    assert panel.status_label.text() == "Desconectada"
    panel.settings_tab.connected.emit("10.0.0.9")
    assert panel.host_label.text() == "10.0.0.9"


def test_tab_buttons_switch_stack(qtbot, env):
    panel = make_panel(qtbot, env)
    tabs = {"home": panel.home_tab, "remote": panel.remote_tab, "apps": panel.apps_tab,
            "activity": panel.activity_tab, "settings": panel.settings_tab}
    assert list(panel.tab_buttons) == list(tabs)
    for key, widget in tabs.items():
        panel.tab_buttons[key].click()
        assert panel.current_page() is widget
        assert [k for k, b in panel.tab_buttons.items() if b.isChecked()] == [key]


def test_starts_on_home_tab(qtbot, env):
    panel = make_panel(qtbot, env)
    assert panel.current_page() is panel.home_tab and panel.tab_buttons["home"].isChecked()


def test_accent_follows_polled_package_and_applies_only_on_change(qtbot, env):
    panel = make_panel(qtbot, env)
    assert panel.accent == DEFAULT_ACCENT and panel.accent_changes == 0
    panel.home_tab.polled.emit(None)
    assert panel.accent_changes == 0
    panel.home_tab.polled.emit(NETFLIX)
    assert panel.accent == "#E50914" and panel.accent_changes == 1
    panel.home_tab.polled.emit(NETFLIX)
    assert panel.accent_changes == 1
    panel.home_tab.polled.emit("x.y.z")  # desconhecido -> azul padrão
    assert panel.accent == DEFAULT_ACCENT and panel.accent_changes == 2
    assert "#E50914" not in panel.styleSheet()


def test_accent_reaches_the_dpad_and_the_stylesheet(qtbot, env):
    panel = make_panel(qtbot, env)
    panel.home_tab.polled.emit(NETFLIX)
    assert "#E50914" in panel.styleSheet()
    assert panel.remote_tab.dpad._accent == "#E50914"


def test_polled_marks_current_app_in_apps_tab(qtbot, env):
    conn, session, cfg, log = env
    session.connect("192.168.0.10")
    panel = make_panel(qtbot, env)
    panel.apps_tab.refresh()
    qtbot.waitUntil(lambda: len(panel.apps_tab.tiles()) == 2, timeout=3000)
    panel.home_tab.polled.emit(NETFLIX)
    flags = {t.entry.package: not t.badge_label.isHidden() for t in panel.apps_tab.tiles()}
    assert flags == {NETFLIX: True, PRIME: False}


def test_polled_records_activity_but_not_none(qtbot, env):
    _, _, _, log = env
    clock = Clock(500.0)
    panel = make_panel(qtbot, env, clock)
    panel.home_tab.polled.emit(None)
    assert log.records == []
    panel.home_tab.polled.emit(NETFLIX)
    assert log.records == [(NETFLIX, 500.0)]


def test_disconnect_resets_the_activity_clock(qtbot, env):
    _, session, _, log = env
    make_panel(qtbot, env)
    get_bridge(session).state_changed.emit(ConnectionState.DISCONNECTED)
    assert log.resets == 1
    get_bridge(session).state_changed.emit(ConnectionState.CONNECTED)
    assert log.resets == 1


def test_hides_on_deactivate(qtbot, env):
    clock = Clock(100.0)
    panel = make_panel(qtbot, env, clock)
    panel.show_panel()
    clock.now = 101.0
    panel.hide_on_deactivate()
    assert not panel.isVisible()


def test_does_not_hide_right_after_show_or_when_suppressed(qtbot, env):
    clock = Clock(100.0)
    panel = make_panel(qtbot, env, clock)
    panel.show_panel()
    clock.now = 100.1
    panel.hide_on_deactivate()
    assert panel.isVisible()
    clock.now = 105.0
    panel.settings_tab.dialog_active.emit(True)
    panel.hide_on_deactivate()
    assert panel.isVisible()
    panel.settings_tab.dialog_active.emit(False)
    panel.hide_on_deactivate()
    assert not panel.isVisible()


def test_show_panel_places_it_inside_the_screen(qtbot, env):
    panel = make_panel(qtbot, env)
    panel.show_panel()
    assert panel.isVisible()
    screen = panel.screen().availableGeometry()
    assert screen.contains(panel.geometry().topLeft())


def test_show_tab(qtbot, env):
    panel = make_panel(qtbot, env)
    panel.show_tab("settings")
    assert panel.current_page() is panel.settings_tab and panel.tab_buttons["settings"].isChecked()


def test_see_all_opens_apps_tab(qtbot, env):
    panel = make_panel(qtbot, env)
    panel.home_tab.see_all_button.click()
    assert panel.current_page() is panel.apps_tab


def test_volume_method_changed_refreshes_audio_cards(qtbot, env):
    _, _, cfg, _ = env
    panel = make_panel(qtbot, env)
    cfg.volume_method = "none"
    panel.settings_tab.volume_method_changed.emit()
    assert panel.home_tab.audio_card.vol_up_button.isHidden()
    assert panel.remote_tab.audio_card.vol_up_button.isHidden()


def test_favorite_toggle_in_apps_updates_home_strip(qtbot, env):
    _, session, _, _ = env
    session.connect("192.168.0.10")
    panel = make_panel(qtbot, env)
    panel.apps_tab.refresh()
    qtbot.waitUntil(lambda: len(panel.apps_tab.tiles()) == 2, timeout=3000)
    netflix = next(t for t in panel.apps_tab.tiles() if t.entry.package == NETFLIX)
    netflix.star_button.click()
    assert [t.entry.package for t in panel.home_tab.favorite_tiles()] == [NETFLIX]


def test_save_persists_log_and_config(qtbot, env):
    _, _, cfg, log = env
    panel = make_panel(qtbot, env)
    panel.save()
    assert log.saves == 1
    assert load_config().tv_name == "Sala"


def test_auto_connect_without_host_does_nothing(qtbot, env):
    conn, session, _, _ = env
    auto_connect(session, AppConfig())
    qtbot.wait(150)
    assert conn.connect_calls == 0


def test_auto_connect_with_host_connects(qtbot, env):
    conn, session, cfg, _ = env
    auto_connect(session, cfg)
    qtbot.waitUntil(lambda: session.state is ConnectionState.CONNECTED, timeout=3000)
    assert conn.host == "192.168.0.10"


def test_auto_connect_failure_is_swallowed(qtbot, env):
    conn, session, cfg, _ = env
    conn.fail_connect = ConnectionFailedError("TV desligada")
    panel = make_panel(qtbot, env)
    auto_connect(session, cfg)
    qtbot.waitUntil(lambda: conn.connect_calls == 1, timeout=3000)
    qtbot.wait(200)
    assert session.state is ConnectionState.DISCONNECTED
    assert panel.status_label.text() == "Desconectada"


def test_tray_toggle_shows_and_hides(qtbot, env, monkeypatch, qapp):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    panel = make_panel(qtbot, env)
    tray = TrayController(qapp, panel)
    assert not panel.isVisible()
    tray.toggle()
    assert panel.isVisible()
    tray.toggle()
    assert not panel.isVisible()
    tray.tray.hide()


def test_tray_left_click_toggles_but_other_clicks_do_not(qtbot, env, monkeypatch, qapp):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    panel = make_panel(qtbot, env)
    tray = TrayController(qapp, panel)
    tray._on_activated(QSystemTrayIcon.Context)
    assert not panel.isVisible()
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert panel.isVisible()
    tray.tray.hide()


def test_without_system_tray_the_panel_opens_as_a_normal_window(qtbot, env, monkeypatch, qapp):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))
    panel = make_panel(qtbot, env)
    TrayController(qapp, panel)
    assert panel.isVisible()


def test_tray_quit_saves_and_quits(qtbot, env, monkeypatch, qapp):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    _, _, _, log = env
    panel = make_panel(qtbot, env)
    tray = TrayController(qapp, panel)
    quit_calls = []
    monkeypatch.setattr(qapp, "quit", lambda: quit_calls.append(1))
    tray.quit()
    assert log.saves == 1 and quit_calls == [1]
    tray.tray.hide()


def test_every_page_scrolls_vertically_and_never_horizontally(qtbot, env):
    from PySide6.QtWidgets import QScrollArea

    panel = make_panel(qtbot, env)
    for i in range(panel.stack.count()):
        area = panel.stack.widget(i)
        assert isinstance(area, QScrollArea) and area.widgetResizable()
        assert area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_remote_page_content_is_not_squeezed_into_the_panel(qtbot, env):
    panel = make_panel(qtbot, env)
    panel.show()
    panel.show_tab("remote")
    qtbot.wait(50)
    # o direcional (200 px) precisa caber inteiro, sem sobrepor a linha de mídia
    assert panel.remote_tab.dpad.height() == 200
    assert panel.remote_tab.height() >= panel.remote_tab.minimumSizeHint().height()


def test_real_deactivation_event_hides_the_panel(qtbot, env, qapp):
    from PySide6.QtCore import QEvent

    clock = Clock(100.0)
    panel = make_panel(qtbot, env, clock)
    panel.show_panel()
    clock.now = 101.0
    qapp.sendEvent(panel, QEvent(QEvent.ActivationChange))
    qtbot.wait(20)
    assert not panel.isVisible()


def test_clicking_the_tray_icon_while_open_closes_instead_of_reopening(qtbot, env, monkeypatch, qapp):
    """O clique no ícone tira o foco do painel (que se esconde) e só depois chega o clique da
    bandeja: sem tratamento, o painel reabriria no mesmo instante."""
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    clock = Clock(100.0)
    panel = make_panel(qtbot, env, clock)
    tray = TrayController(qapp, panel)
    panel.show_panel()
    clock.now = 101.0
    panel.hide_on_deactivate()          # foco perdido ao clicar no ícone
    clock.now = 101.1
    tray._on_activated(QSystemTrayIcon.Trigger)   # o clique chega logo depois
    assert not panel.isVisible()
    clock.now = 105.0                   # um clique de verdade, bem depois, abre
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert panel.isVisible()
    tray.tray.hide()
