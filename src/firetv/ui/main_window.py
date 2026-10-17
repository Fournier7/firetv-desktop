"""Janela principal, com as abas Início, Controle, Apps e Ajustes."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget

from firetv.config import AppConfig
from firetv.session import Session
from firetv.ui.settings_tab import SettingsTab


def _placeholder(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("help")
    return label


class MainWindow(QMainWindow):
    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("Fire TV Desktop")
        self.resize(440, 760)
        self.tabs = QTabWidget()
        self.tabs.addTab(_placeholder("Início: em breve"), "Início")
        self.tabs.addTab(_placeholder("Controle: em breve"), "Controle")
        self.tabs.addTab(_placeholder("Apps: em breve"), "Apps")
        self.tabs.addTab(SettingsTab(session, cfg), "Ajustes")
        self.setCentralWidget(self.tabs)
