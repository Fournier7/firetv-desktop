"""Estado de conexão e uma ação de acesso direto na janela desktop."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from firetv.config import AppConfig
from firetv.session import ConnectionState
from firetv.ui.widgets import Card


class ConnectionBar(Card):
    action_requested = Signal()

    def __init__(self, cfg: AppConfig, state: ConnectionState) -> None:
        super().__init__()
        self._cfg = cfg
        self._state = state
        self._busy = False
        self._error = ""
        self.dot = QLabel("●")
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("connectionTitle")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("help")
        self.detail_label.setWordWrap(True)
        text = QVBoxLayout()
        text.setSpacing(4)
        text.addWidget(self.title_label)
        text.addWidget(self.detail_label)
        self.action_button = QPushButton()
        self.action_button.setObjectName("primary")
        self.action_button.clicked.connect(self.action_requested)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self.dot)
        row.addLayout(text, 1)
        row.addWidget(self.action_button)
        self.body.addLayout(row)
        self.refresh()

    def set_state(self, state: ConnectionState) -> None:
        self._state = state
        if state is ConnectionState.CONNECTED:
            self._error = ""
        self.refresh()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self._error = ""
        self.refresh()

    def show_error(self, message: str) -> None:
        self._error = message
        self.refresh()

    def refresh(self) -> None:
        busy = self._busy or self._state is ConnectionState.RECONNECTING
        connected = self._state is ConnectionState.CONNECTED
        self.title_label.setText(
            "Conectando à TV…" if busy else
            (f"Conectado a {self._cfg.tv_name}" if connected else "TV desconectada")
        )
        detail = self._cfg.host if connected else (
            "Confira se a TV está ligada e na mesma rede." if self._cfg.host else
            "Informe o IP do Fire TV em Ajustes para começar."
        )
        if busy:
            detail = "Na primeira conexão, aceite a autorização que aparece na TV."
        self.detail_label.setText(self._error or detail)
        self.action_button.setText("Aguarde…" if busy else ("Reconectar" if self._cfg.host else "Configurar TV"))
        self.action_button.setEnabled(not busy)
        color = "#F59E0B" if busy else ("#34D399" if connected else "#94A3B8")
        self.dot.setStyleSheet(f"color: {color}; background: transparent;")
