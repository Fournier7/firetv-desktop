"""Componentes visuais: cartão, direcional circular, cartão de áudio e cartão da TV."""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from firetv.config import AppConfig
from firetv.connection import ConnectionLostError
from firetv.keys import KeyCode
from firetv.session import ConnectionState, Session
from firetv.ui import theme
from firetv.ui.icons import icon
from firetv.ui.worker import get_bridge, run_in_background
from firetv.volume import METHOD_ORDER, NONE, normalize_method

MSG_VOLUME = "O volume não respondeu neste aparelho. Este recurso é experimental."
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
MSG_NO_VOLUME = "Volume indisponível: depende do controle físico da TV."
NO_APP = "Nada em primeiro plano"
DPAD_SIZE = 200
CENTER_RATIO = 0.36


class Card(QFrame):
    """Cartão escuro de cantos arredondados; o conteúdo vai em `body`."""

    def __init__(self, title: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(12)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("help")
        self.title_label.setVisible(bool(title))
        self.body.addWidget(self.title_label)


class DPad(QWidget):
    """Direcional circular: OK no centro e quatro setores ao redor."""

    pressed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(DPAD_SIZE, DPAD_SIZE)
        self._accent = theme.DEFAULT_ACCENT
        self._hover_key = None
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Direcional: setas e botão OK")

    def set_diameter(self, size: int) -> None:
        if size != self.width():
            self.setFixedSize(size, size)

    def mouseMoveEvent(self, event) -> None:
        key = self.key_at(event.position().toPoint())
        if key != self._hover_key:
            self._hover_key = key
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover_key = None
        self.update()
        super().leaveEvent(event)

    def set_accent(self, color: str) -> None:
        self._accent = color
        self.update()

    def key_at(self, pos: QPoint) -> KeyCode | None:
        radius = self.width() / 2
        dx, dy = pos.x() - radius, pos.y() - radius
        distance = math.hypot(dx, dy)
        if distance > radius:
            return None
        if distance <= radius * CENTER_RATIO:
            return KeyCode.OK
        if abs(dx) > abs(dy):
            return KeyCode.RIGHT if dx > 0 else KeyCode.LEFT
        return KeyCode.DOWN if dy > 0 else KeyCode.UP

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        key = self.key_at(event.position().toPoint())
        if key is not None:
            self.pressed.emit(key)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = self.width()
        c = size / 2
        painter.setPen(QPen(QColor(theme.PANEL_BORDER), 1.5))
        painter.setBrush(QBrush(QColor(theme.PANEL)))
        outer = QRectF(2, 2, size - 4, size - 4)
        painter.drawEllipse(outer)
        accent = QColor(self._accent)
        fill = QColor(accent)
        fill.setAlphaF(0.14)
        angles = {KeyCode.UP: 45, KeyCode.LEFT: 135, KeyCode.DOWN: 225, KeyCode.RIGHT: 315}
        if self._hover_key in angles:
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawPie(outer, angles[self._hover_key] * 16, 90 * 16)
        fill.setAlphaF(0.22)
        if self._hover_key == KeyCode.OK:
            fill.setAlphaF(0.4)
        painter.setPen(QPen(accent, 1.5))
        painter.setBrush(QBrush(fill))
        r = c * CENTER_RATIO
        painter.drawEllipse(QRectF(c - r, c - r, 2 * r, 2 * r))
        painter.setPen(accent)
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(c - r, c - r, 2 * r, 2 * r), Qt.AlignCenter, "OK")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(theme.TEXT)))
        d, s = c * 0.72, 7
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            tip = QPointF(c + dx * (d + s), c + dy * (d + s))
            base = QPointF(c + dx * (d - s), c + dy * (d - s))
            px, py = -dy * s, dx * s
            painter.drawPolygon(QPolygonF([tip, QPointF(base.x() + px, base.y() + py),
                                           QPointF(base.x() - px, base.y() - py)]))


class AudioCard(Card):
    """Menos, mudo e mais. O método vem de `cfg.volume_method`, lido a cada clique."""

    configure_requested = Signal()

    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__("Áudio da TV")
        self._session = session
        self._cfg = cfg
        self.vol_down_button = self._button("volume_down", KeyCode.VOLUME_DOWN)
        self.mute_button = self._button("mute", KeyCode.MUTE)
        self.vol_up_button = self._button("volume_up", KeyCode.VOLUME_UP)
        row = QHBoxLayout()
        for button in (self.vol_down_button, self.mute_button, self.vol_up_button):
            row.addWidget(button)
        self.none_label = QLabel(MSG_NO_VOLUME)
        self.none_label.setObjectName("help")
        self.none_label.setWordWrap(True)
        self.notice_label = QLabel("")
        self.notice_label.setObjectName("message")
        self.notice_label.setWordWrap(True)
        self.availability_label = QLabel("")
        self.availability_label.setObjectName("help")
        self.availability_label.setWordWrap(True)
        self.configure_button = QPushButton("Configurar volume")
        self.configure_button.setFlat(True)
        self.configure_button.clicked.connect(self.configure_requested)
        self.body.addLayout(row)
        self.body.addWidget(self.none_label)
        self.body.addWidget(self.availability_label)
        self.body.addWidget(self.configure_button)
        self.body.addWidget(self.notice_label)
        get_bridge(session).state_changed.connect(lambda _state: self.refresh())
        self.refresh()

    def _button(self, icon_name: str, key: KeyCode) -> QPushButton:
        button = QPushButton()
        button.setIcon(icon(icon_name))
        label = {"volume_up": "Aumentar volume", "volume_down": "Diminuir volume", "mute": "Silenciar"}[icon_name]
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.setMinimumHeight(40)
        button.clicked.connect(lambda _=False, k=key: self._volume(k))
        return button

    def refresh(self) -> None:
        unavailable = normalize_method(self._cfg.volume_method) == NONE
        confirmed = self._cfg.volume_method in METHOD_ORDER
        connected = self._session.state is ConnectionState.CONNECTED
        for button in (self.vol_down_button, self.mute_button, self.vol_up_button):
            button.setHidden(unavailable)
            button.setEnabled(confirmed and connected)
        self.none_label.setHidden(not unavailable)
        self.availability_label.setHidden(unavailable)
        self.availability_label.setText(
            "Volume não configurado. Faça o teste para verificar se sua TV aceita este controle."
            if not confirmed else ("Volume configurado para esta TV." if connected else "Conecte a TV para usar o volume.")
        )
        self.configure_button.setText("Testar novamente" if unavailable else "Configurar volume")

    def _volume(self, key: KeyCode) -> None:
        if self._cfg.volume_method not in METHOD_ORDER or self._session.state is not ConnectionState.CONNECTED:
            return
        method = normalize_method(self._cfg.volume_method)

        def done(ok: object) -> None:
            self.notice_label.setText("" if ok else MSG_VOLUME)

        def failed(exc: Exception) -> None:
            self.notice_label.setText(MSG_LOST if isinstance(exc, ConnectionLostError) else str(exc))

        run_in_background(
            lambda: self._session.run(lambda c: c.volume(key, method)), done, failed
        )


class TvCard(Card):
    """Cartão da TV: mostra o app em execução, pintado com a cor do app."""

    def __init__(self) -> None:
        super().__init__()
        self.caption_label = QLabel("AGORA NA TELA")
        self.name_label = QLabel(NO_APP)
        self.name_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.name_label.setWordWrap(True)
        self.setMinimumHeight(140)
        self.body.addWidget(self.caption_label)
        self.body.addWidget(self.name_label)
        self.body.addStretch(1)
        self.set_app(None, theme.DEFAULT_ACCENT)

    def set_app(self, name: str | None, accent: str) -> None:
        self.name_label.setText(name or NO_APP)
        self.caption_label.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: bold;")
        self.setStyleSheet(
            f"QFrame#card {{ background: {theme.tint(accent, 0.16)};"
            f" border: 1px solid {theme.tint(accent, 0.45)}; border-radius: 14px; }}"
        )
