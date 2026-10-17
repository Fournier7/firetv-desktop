"""Aba Controle: direcional circular, mídia, teclado, volume e atalhos de teclado."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from firetv.config import AppConfig
from firetv.connection import ConnectionLostError
from firetv.controller import Controller
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.icons import icon
from firetv.ui.widgets import AudioCard, Card, DPad
from firetv.ui.worker import run_in_background

MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."

_SHORTCUTS = {
    Qt.Key_Up: KeyCode.UP,
    Qt.Key_Down: KeyCode.DOWN,
    Qt.Key_Left: KeyCode.LEFT,
    Qt.Key_Right: KeyCode.RIGHT,
    Qt.Key_Return: KeyCode.OK,
    Qt.Key_Enter: KeyCode.OK,
    Qt.Key_Escape: KeyCode.BACK,
}
_TEXT_WIDGETS = (QLineEdit, QTextEdit, QAbstractSpinBox)
_ICONS = {
    KeyCode.HOME: "home", KeyCode.BACK: "back", KeyCode.MENU: "menu",
    KeyCode.REWIND: "rewind", KeyCode.PLAY_PAUSE: "play_pause", KeyCode.FAST_FORWARD: "forward",
}


class RemoteTab(QWidget):
    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session

        self.dpad = DPad()
        self.dpad.pressed.connect(self._press)
        self.buttons: dict[KeyCode, QPushButton] = {}

        def make(key: KeyCode) -> QPushButton:
            button = QPushButton()
            button.setIcon(icon(_ICONS[key]))
            button.setMinimumHeight(44)
            button.clicked.connect(lambda _=False, k=key: self._press(k))
            self.buttons[key] = button
            return button

        side_left = QVBoxLayout()
        side_left.addWidget(make(KeyCode.HOME))
        side_left.addWidget(make(KeyCode.BACK))
        side_left.addStretch(1)
        side_right = QVBoxLayout()
        side_right.addWidget(make(KeyCode.MENU))
        side_right.addStretch(1)
        pad_row = QHBoxLayout()
        pad_row.addLayout(side_left)
        pad_row.addWidget(self.dpad, 0, Qt.AlignCenter)
        pad_row.addLayout(side_right)
        media_row = QHBoxLayout()
        for key in (KeyCode.REWIND, KeyCode.PLAY_PAUSE, KeyCode.FAST_FORWARD):
            media_row.addWidget(make(key))

        controls = Card("Controle")
        controls.body.addLayout(pad_row)
        controls.body.addLayout(media_row)

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Digite no campo aberto na TV")
        self.send_button = QPushButton("Enviar")
        text_row = QHBoxLayout()
        text_row.addWidget(self.text_edit, 1)
        text_row.addWidget(self.send_button)
        keyboard = Card("Teclado")
        keyboard.body.addLayout(text_row)
        self.send_button.clicked.connect(self._send_text)
        self.text_edit.returnPressed.connect(self._send_text)

        self.notice_label = QLabel("")
        self.notice_label.setObjectName("message")
        self.notice_label.setWordWrap(True)
        self.audio_card = AudioCard(session, cfg)

        layout = QVBoxLayout(self)
        layout.addWidget(controls)
        layout.addWidget(keyboard)
        layout.addWidget(self.audio_card)
        layout.addWidget(self.notice_label)
        layout.addStretch(1)

        QApplication.instance().installEventFilter(self)

    # --- atalhos: valem só com a aba visível e fora de campos de texto ---
    def eventFilter(self, obj, event) -> bool:
        if event.type() != QEvent.KeyPress or not self.isVisible():
            return False
        # Teclas que o campo de texto ignora (como a seta para cima) sobem para o
        # widget pai; o foco continua no campo, então é ele que decide.
        if isinstance(obj, _TEXT_WIDGETS) or isinstance(QApplication.focusWidget(), _TEXT_WIDGETS):
            return False
        if not isinstance(obj, QWidget) or obj.window() is not self.window():
            return False
        key = _SHORTCUTS.get(event.key())
        if key is None:
            return False
        self._press(key)
        return True

    # --- ações ---
    def _run(self, op: Callable[[Controller], object], on_done: Callable[[object], None]) -> None:
        run_in_background(lambda: self._session.run(op), on_done, self._on_error)

    def _on_error(self, exc: Exception) -> None:
        self.notice_label.setText(MSG_LOST if isinstance(exc, ConnectionLostError) else str(exc))

    def _press(self, key: KeyCode) -> None:
        self._run(lambda c: c.press(key), lambda _: self.notice_label.setText(""))

    def _send_text(self) -> None:
        text = self.text_edit.text()
        if not text:
            return

        def done(result) -> None:
            self.text_edit.clear()
            self.notice_label.setText(
                f"Não foi possível enviar: {result.skipped}" if result.skipped else ""
            )

        self._run(lambda c: c.send_text(text), done)
