"""Aba Ajustes: nome da TV, IP do Stick, conexão, status e diagnóstico de volume."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from firetv.config import AppConfig, save_config, validate_host
from firetv.connection import AuthRequiredError
from firetv.session import ConnectionState, Session
from firetv.ui.volume_dialog import VolumeDialog
from firetv.ui.worker import get_bridge, run_in_background

MSG_INVALID_HOST = "Digite um IP válido, por exemplo 192.168.0.10."
MSG_FAILED = (
    "Não foi possível alcançar o Stick. Confira o IP, se a TV está ligada "
    "e se o PC e a TV estão na mesma rede."
)
MSG_AUTH = "Aceite o pedido de autorização que apareceu na TV e conecte de novo."
HELP_TEXT = "No Stick: Configurações > Meu Fire TV > Opções do desenvolvedor > Depuração ADB."
DEFAULT_NAME = "Fire TV"
STATUS_TEXT = {
    ConnectionState.CONNECTED: "Conectado",
    ConnectionState.DISCONNECTED: "Desconectado",
    ConnectionState.RECONNECTING: "Reconectando...",
}


class SettingsTab(QWidget):
    name_changed = Signal(str)
    volume_method_changed = Signal()
    dialog_active = Signal(bool)  # o diálogo de diagnóstico está aberto?

    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg
        self.volume_dialog: VolumeDialog | None = None

        self.name_edit = QLineEdit(cfg.tv_name)
        self.name_edit.setPlaceholderText("Nome da TV")
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
        self.diagnostic_button = QPushButton("Diagnóstico de volume")

        row = QHBoxLayout()
        row.addWidget(self.host_edit, 1)
        row.addWidget(self.connect_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.name_edit)
        layout.addLayout(row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.message_label)
        layout.addWidget(self.help_label)
        layout.addWidget(self.diagnostic_button)
        layout.addStretch(1)

        self.connect_button.clicked.connect(self._on_connect_clicked)
        self.name_edit.editingFinished.connect(self._save_name)
        self.diagnostic_button.clicked.connect(self._open_diagnostic)
        get_bridge(session).state_changed.connect(self._on_state_changed)

    # --- nome da TV ---
    def _save_name(self) -> None:
        name = self.name_edit.text().strip() or DEFAULT_NAME
        self.name_edit.setText(name)
        self._cfg.tv_name = name
        save_config(self._cfg)
        self.name_changed.emit(name)

    # --- diagnóstico de volume ---
    def _open_diagnostic(self) -> None:
        dialog = VolumeDialog(self._session, self._cfg, self)
        self.volume_dialog = dialog
        dialog.finished_with.connect(lambda _method: self.volume_method_changed.emit())
        dialog.finished.connect(lambda _code: self.dialog_active.emit(False))
        self.dialog_active.emit(True)
        dialog.show()
        dialog.start()

    # --- conexão ---
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
