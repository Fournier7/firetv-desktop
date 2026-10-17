"""Diagnóstico de volume: testa os jeitos de mandar volume ao Stick, um por vez."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from firetv.config import AppConfig, save_config
from firetv.connection import ConnectionLostError
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.worker import run_in_background
from firetv.volume import METHOD_ORDER, NONE

MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
MSG_NONE = "Nenhum método funcionou. O volume parece depender do controle físico."


class VolumeDialog(QDialog):
    finished_with = Signal(str)  # método escolhido, ou 'none'

    def __init__(self, session: Session, cfg: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._session = session
        self._cfg = cfg
        self._index = 0
        self._closed = False
        self.setWindowTitle("Diagnóstico de volume")
        self.setModal(True)

        intro = QLabel(
            "Vou mandar \"volume +\" para a TV de jeitos diferentes. "
            "Olhe a TV e diga se o volume subiu."
        )
        intro.setWordWrap(True)
        intro.setObjectName("help")
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.message_label = QLabel("")
        self.message_label.setObjectName("message")
        self.message_label.setWordWrap(True)
        self.yes_button = QPushButton("Sim")
        self.no_button = QPushButton("Não")
        self.cancel_button = QPushButton("Cancelar")
        row = QHBoxLayout()
        for button in (self.yes_button, self.no_button, self.cancel_button):
            row.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.status_label)
        layout.addWidget(self.message_label)
        layout.addLayout(row)

        self.yes_button.clicked.connect(self._confirm)
        self.no_button.clicked.connect(self._advance)
        self.cancel_button.clicked.connect(self._cancel)
        self._set_answers_enabled(False)

    def start(self) -> None:
        self._index = 0
        self._closed = False
        self._send_current()

    def _set_answers_enabled(self, enabled: bool) -> None:
        self.yes_button.setEnabled(enabled)
        self.no_button.setEnabled(enabled)

    def _send_current(self) -> None:
        method = METHOD_ORDER[self._index]
        self.status_label.setText(
            f"Teste {self._index + 1} de {len(METHOD_ORDER)}: enviei \"volume +\". "
            "O volume da TV subiu?"
        )
        self.message_label.setText("")
        self._set_answers_enabled(False)
        run_in_background(
            lambda: self._session.run(lambda c: c.volume(KeyCode.VOLUME_UP, method)),
            self._on_sent,
            self._on_error,
        )

    def _on_sent(self, ok: object) -> None:
        if self._closed:
            return
        if ok:
            self._set_answers_enabled(True)
        else:  # o comando deu erro: nem adianta perguntar, passa para o próximo
            self._advance()

    def _on_error(self, exc: Exception) -> None:
        if self._closed:
            return
        self.message_label.setText(MSG_LOST if isinstance(exc, ConnectionLostError) else str(exc))

    def _confirm(self) -> None:
        method = METHOD_ORDER[self._index]
        self._closed = True
        self._cfg.volume_method = method
        save_config(self._cfg)
        self.finished_with.emit(method)
        self.accept()

    def _advance(self) -> None:
        if self._closed:
            return
        self._index += 1
        if self._index < len(METHOD_ORDER):
            self._send_current()
            return
        self._closed = True
        self._cfg.volume_method = NONE
        save_config(self._cfg)
        self.status_label.setText("")
        self.message_label.setText(MSG_NONE)
        self.yes_button.hide()
        self.no_button.hide()
        self.cancel_button.setText("Fechar")
        self.finished_with.emit(NONE)

    def _cancel(self) -> None:
        self._closed = True
        self.reject()
