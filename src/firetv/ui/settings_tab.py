"""Aba Ajustes: IP do Stick, conexão e status."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from firetv.config import AppConfig, save_config, validate_host
from firetv.connection import AuthRequiredError, ConnectionFailedError
from firetv.session import ConnectionState, Session
from firetv.ui.worker import get_bridge, run_in_background

MSG_INVALID_HOST = "Digite um IP válido, por exemplo 192.168.0.10."
MSG_FAILED = (
    "Não foi possível alcançar o Stick. Confira o IP, se a TV está ligada "
    "e se o PC e a TV estão na mesma rede."
)
MSG_AUTH = "Aceite o pedido de autorização que apareceu na TV e conecte de novo."
HELP_TEXT = "No Stick: Configurações > Meu Fire TV > Opções do desenvolvedor > Depuração ADB."
STATUS_TEXT = {
    ConnectionState.CONNECTED: "Conectado",
    ConnectionState.DISCONNECTED: "Desconectado",
    ConnectionState.RECONNECTING: "Reconectando...",
}


class SettingsTab(QWidget):
    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg

        self.host_edit = QLineEdit(cfg.host)
        self.host_edit.setPlaceholderText("IP do Stick, ex.: 192.168.0.10")
        self.connect_button = QPushButton("Conectar")
        self.status_label = QLabel(STATUS_TEXT[session.state])
        self.status_label.setObjectName("status")
        self.message_label = QLabel("")
        self.message_label.setObjectName("message")
        self.message_label.setWordWrap(True)
        self.help_label = QLabel(HELP_TEXT)
        self.help_label.setObjectName("help")
        self.help_label.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(self.host_edit, 1)
        row.addWidget(self.connect_button)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.message_label)
        layout.addWidget(self.help_label)
        layout.addStretch(1)

        self.connect_button.clicked.connect(self._on_connect_clicked)
        get_bridge(session).state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, state: ConnectionState) -> None:
        self.status_label.setText(STATUS_TEXT[state])

    def _on_connect_clicked(self) -> None:
        try:
            host = validate_host(self.host_edit.text())
        except ValueError:
            self.message_label.setText(MSG_INVALID_HOST)
            return
        self.message_label.setText("")
        self.connect_button.setEnabled(False)
        run_in_background(
            lambda: self._session.connect(host),
            lambda _: self._on_connected(host),
            self._on_connect_error,
        )

    def _on_connected(self, host: str) -> None:
        self.connect_button.setEnabled(True)
        self._cfg.host = host
        save_config(self._cfg)

    def _on_connect_error(self, exc: Exception) -> None:
        self.connect_button.setEnabled(True)
        if isinstance(exc, AuthRequiredError):
            self.message_label.setText(MSG_AUTH)
        else:
            self.message_label.setText(MSG_FAILED)
