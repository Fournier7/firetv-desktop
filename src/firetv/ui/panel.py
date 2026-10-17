"""Painel na bandeja do sistema: janela sem borda com cabeçalho, abas e rodapé."""
from __future__ import annotations

import time
from typing import Callable

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from firetv.activity import ActivityLog
from firetv.config import AppConfig, save_config
from firetv.session import ConnectionState, Session
from firetv.ui import theme
from firetv.ui.activity_tab import ActivityTab
from firetv.ui.apps_tab import AppsTab
from firetv.ui.home_tab import HomeTab
from firetv.ui.icons import icon
from firetv.ui.remote_tab import RemoteTab
from firetv.ui.settings_tab import SettingsTab
from firetv.ui.theme import accent_for, build_stylesheet
from firetv.ui.worker import get_bridge, run_in_background

PANEL_SIZE = QSize(380, 560)
MARGIN = 12
SHOW_GUARD_SECONDS = 0.3  # ignora a perda de foco logo depois de abrir
STATUS_TEXT = {
    ConnectionState.CONNECTED: "Conectada",
    ConnectionState.DISCONNECTED: "Desconectada",
    ConnectionState.RECONNECTING: "Reconectando...",
}
STATUS_COLOR = {
    ConnectionState.CONNECTED: "#22C55E",
    ConnectionState.DISCONNECTED: "#6B7280",
    ConnectionState.RECONNECTING: "#F59E0B",
}
TAB_ORDER = ("home", "remote", "apps", "activity", "settings")


def panel_position(avail: QRect, size: QSize, margin: int = MARGIN) -> QPoint:
    """Canto inferior direito da área disponível, com margem, sem sair da área."""
    x = max(avail.left(), avail.left() + avail.width() - size.width() - margin)
    y = max(avail.top(), avail.top() + avail.height() - size.height() - margin)
    return QPoint(x, y)


def auto_connect(session: Session, cfg: AppConfig) -> None:
    """Conecta sozinho ao IP salvo; uma falha só aparece no rodapé do painel."""
    if not cfg.host:
        return
    host = cfg.host
    run_in_background(lambda: session.connect(host), lambda _: None, lambda exc: None)


class Panel(QWidget):
    def __init__(
        self,
        session: Session,
        cfg: AppConfig,
        log: ActivityLog,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PANEL_SIZE)
        self._session = session
        self._cfg = cfg
        self._log = log
        self._clock = clock
        self._shown_at = float("-inf")
        self.suppress_hide = False
        self.accent = theme.DEFAULT_ACCENT
        self.accent_changes = 0
        self.setStyleSheet(build_stylesheet(self.accent))

        self.home_tab = HomeTab(session, cfg)
        self.remote_tab = RemoteTab(session, cfg)
        self.apps_tab = AppsTab(session, cfg)
        self.activity_tab = ActivityTab(log)
        self.settings_tab = SettingsTab(session, cfg)
        pages = (self.home_tab, self.remote_tab, self.apps_tab, self.activity_tab, self.settings_tab)

        # cabeçalho
        self.name_label = QLabel(cfg.tv_name)
        self.name_label.setStyleSheet("font-size: 17px; font-weight: bold; background: transparent;")
        self.subtitle_label = QLabel("Fire TV Stick")
        self.subtitle_label.setObjectName("help")
        header = QVBoxLayout()
        header.setSpacing(0)
        header.addWidget(self.name_label)
        header.addWidget(self.subtitle_label)

        # abas
        self.stack = QStackedWidget()
        self.tab_buttons: dict[str, QToolButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        tabs_row = QHBoxLayout()
        icon_names = {"home": "home", "remote": "remote", "apps": "apps",
                      "activity": "activity", "settings": "settings"}
        for key, page in zip(TAB_ORDER, pages):
            button = QToolButton()
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setIconSize(QSize(22, 22))
            button.setIcon(icon(icon_names[key], theme.MUTED))
            button.setToolTip({"home": "Início", "remote": "Controle", "apps": "Apps",
                               "activity": "Atividade", "settings": "Ajustes"}[key])
            button.clicked.connect(lambda _=False, k=key: self.show_tab(k))
            group.addButton(button)
            self.tab_buttons[key] = button
            tabs_row.addWidget(button, 1)
            self.stack.addWidget(page)

        # rodapé
        self.status_dot = QLabel("●")
        self.status_label = QLabel("")
        self.host_label = QLabel(cfg.host)
        self.host_label.setObjectName("help")
        footer = QHBoxLayout()
        footer.addWidget(self.status_dot)
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        footer.addWidget(self.host_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.addLayout(header)
        layout.addLayout(tabs_row)
        layout.addWidget(self.stack, 1)
        layout.addLayout(footer)

        self._show_state(session.state)
        self.show_tab("home")
        self._wire(session)

    # --- ligações entre as partes ---
    def _wire(self, session: Session) -> None:
        get_bridge(session).state_changed.connect(self._on_state_changed)
        self.home_tab.polled.connect(self._on_polled)
        self.home_tab.see_all_requested.connect(lambda: self.show_tab("apps"))
        self.apps_tab.favorites_changed.connect(self.home_tab.refresh_favorites)
        self.settings_tab.name_changed.connect(self.name_label.setText)
        self.settings_tab.connected.connect(self.host_label.setText)
        self.settings_tab.volume_method_changed.connect(self._refresh_audio_cards)
        self.settings_tab.dialog_active.connect(self._set_suppress_hide)

    def _refresh_audio_cards(self) -> None:
        self.home_tab.audio_card.refresh()
        self.remote_tab.audio_card.refresh()

    def _set_suppress_hide(self, active: bool) -> None:
        self.suppress_hide = active

    def _show_state(self, state: ConnectionState) -> None:
        self.status_label.setText(STATUS_TEXT[state])
        self.status_dot.setStyleSheet(f"color: {STATUS_COLOR[state]}; background: transparent;")

    def _on_state_changed(self, state: ConnectionState) -> None:
        self._show_state(state)
        if state is not ConnectionState.CONNECTED:
            self._log.reset_clock()  # pausas e desconexões não contam como uso

    def _on_polled(self, package: str | None) -> None:
        self.set_accent(accent_for(package))
        self.apps_tab.set_current_app(package)
        if package is not None:
            self._log.record(package, self._clock())

    # --- abas e cor de destaque ---
    def show_tab(self, key: str) -> None:
        self.stack.setCurrentIndex(TAB_ORDER.index(key))
        for name, button in self.tab_buttons.items():
            button.setChecked(name == key)
        self._paint_tab_icons()

    def _paint_tab_icons(self) -> None:
        for name, button in self.tab_buttons.items():
            color = self.accent if button.isChecked() else theme.MUTED
            button.setIcon(icon(name, color))

    def set_accent(self, color: str) -> None:
        if color == self.accent:
            return
        self.accent = color
        self.accent_changes += 1
        self.setStyleSheet(build_stylesheet(color))
        self.remote_tab.dpad.set_accent(color)
        self._paint_tab_icons()

    # --- mostrar e esconder ---
    def show_panel(self) -> None:
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        self.move(panel_position(avail, self.size()))
        self._shown_at = self._clock()
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_on_deactivate(self) -> None:
        if self.suppress_hide or self._clock() - self._shown_at < SHOW_GUARD_SECONDS:
            return
        self.hide()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and self.isVisible() and not self.isActiveWindow():
            self.hide_on_deactivate()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(theme.PANEL_BORDER))
        painter.setBrush(QColor(theme.BG))
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 18, 18)

    def save(self) -> None:
        self._log.save()
        save_config(self._cfg)


class TrayController:
    """Ícone na bandeja: clique esquerdo abre ou fecha o painel; menu com Abrir e Sair."""

    def __init__(self, app: QApplication, panel: Panel) -> None:
        self._app = app
        self._panel = panel
        self.tray = QSystemTrayIcon(icon("remote", theme.DEFAULT_ACCENT), app)
        self.tray.setToolTip("Fire TV Desktop")
        menu = QMenu()
        menu.addAction("Abrir", panel.show_panel)
        menu.addAction("Sair", self.quit)
        self._menu = menu  # mantém o menu vivo
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:  # sem bandeja, abre como janela normal para o app continuar usável
            panel.show_panel()

    def toggle(self) -> None:
        if self._panel.isVisible():
            self._panel.hide()
        else:
            self._panel.show_panel()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.toggle()

    def quit(self) -> None:
        self._panel.save()
        self.tray.hide()
        self._app.quit()
