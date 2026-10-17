"""Aba Controle: direcionais, mídia, texto, volume e atalhos de teclado."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from firetv.connection import ConnectionLostError
from firetv.controller import Controller
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.worker import run_in_background

MSG_VOLUME = "O volume não respondeu neste aparelho. Este recurso é experimental."
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
VOLUME_LABEL = "Volume (experimental)"

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

_LABELS = {
    KeyCode.UP: "▲", KeyCode.DOWN: "▼", KeyCode.LEFT: "◀", KeyCode.RIGHT: "▶",
    KeyCode.OK: "OK", KeyCode.BACK: "Voltar", KeyCode.HOME: "Início", KeyCode.MENU: "Menu",
    KeyCode.REWIND: "⏪", KeyCode.PLAY_PAUSE: "⏯", KeyCode.FAST_FORWARD: "⏩",
    KeyCode.VOLUME_DOWN: "Vol −", KeyCode.MUTE: "Mudo", KeyCode.VOLUME_UP: "Vol +",
}
_GRID = {  # tecla -> (linha, coluna)
    KeyCode.UP: (0, 1), KeyCode.LEFT: (1, 0), KeyCode.OK: (1, 1), KeyCode.RIGHT: (1, 2),
    KeyCode.DOWN: (2, 1),
    KeyCode.BACK: (3, 0), KeyCode.HOME: (3, 1), KeyCode.MENU: (3, 2),
    KeyCode.REWIND: (4, 0), KeyCode.PLAY_PAUSE: (4, 1), KeyCode.FAST_FORWARD: (4, 2),
}


class RemoteTab(QWidget):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session

        self.notice_label = QLabel("")
        self.notice_label.setObjectName("message")
        self.notice_label.setWordWrap(True)

        grid = QGridLayout()
        self.buttons: dict[KeyCode, QPushButton] = {}
        for key, (row, col) in _GRID.items():
            button = QPushButton(_LABELS[key])
            button.setMinimumHeight(48)
            button.clicked.connect(lambda _=False, k=key: self._press(k))
            self.buttons[key] = button
            grid.addWidget(button, row, col)

        self.volume_label = QLabel(VOLUME_LABEL)
        self.volume_label.setObjectName("help")
        volume_row = QHBoxLayout()
        self.volume_buttons: dict[KeyCode, QPushButton] = {}
        for key in (KeyCode.VOLUME_DOWN, KeyCode.MUTE, KeyCode.VOLUME_UP):
            button = QPushButton(_LABELS[key])
            button.clicked.connect(lambda _=False, k=key: self._volume(k))
            self.volume_buttons[key] = button
            volume_row.addWidget(button)

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Digite aqui para enviar à TV")
        self.send_button = QPushButton("Enviar")
        text_row = QHBoxLayout()
        text_row.addWidget(self.text_edit, 1)
        text_row.addWidget(self.send_button)
        self.send_button.clicked.connect(self._send_text)
        self.text_edit.returnPressed.connect(self._send_text)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(self.volume_label)
        layout.addLayout(volume_row)
        layout.addLayout(text_row)
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
        if isinstance(exc, ConnectionLostError):
            self.notice_label.setText(MSG_LOST)
        else:
            self.notice_label.setText(str(exc))

    def _press(self, key: KeyCode) -> None:
        self._run(lambda c: c.press(key), lambda _: self.notice_label.setText(""))

    def _volume(self, key: KeyCode) -> None:
        def done(ok: object) -> None:
            self.notice_label.setText("" if ok else MSG_VOLUME)

        self._run(lambda c: c.volume(key), done)

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
