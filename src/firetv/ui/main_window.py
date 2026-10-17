"""Janela principal, com as abas Início, Controle, Apps e Ajustes."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from firetv.config import AppConfig
from firetv.session import Session
from firetv.ui.apps_tab import AppsTab
from firetv.ui.home_tab import HomeTab
from firetv.ui.remote_tab import RemoteTab
from firetv.ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("Fire TV Desktop")
        self.resize(440, 760)
        self.home_tab = HomeTab(session, cfg)
        self.remote_tab = RemoteTab(session, cfg)
        self.apps_tab = AppsTab(session, cfg)
        self.settings_tab = SettingsTab(session, cfg)
        self.apps_tab.favorites_changed.connect(self.home_tab.refresh_favorites)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.home_tab, "Início")
        self.tabs.addTab(self.remote_tab, "Controle")
        self.tabs.addTab(self.apps_tab, "Apps")
        self.tabs.addTab(self.settings_tab, "Ajustes")
        self.setCentralWidget(self.tabs)
