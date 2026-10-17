"""Aba Atividade: tempo por app em primeiro plano no Stick (histórico local)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from firetv.activity import ActivityLog, format_duration
from firetv.apps import KNOWN_APPS
from firetv.ui import theme
from firetv.ui.theme import accent_for
from firetv.ui.widgets import Card

EMPTY = "Ainda sem dados. O histórico começa a contar quando o Stick estiver conectado."
NOTE = "Histórico local. Conta o app em primeiro plano no Stick."
PERIODS = (("today", "Hoje"), ("7d", "7 dias"), ("30d", "30 dias"))


class _Bar(QWidget):
    """Barra proporcional: preenche `fraction` da largura, na cor do app."""

    def __init__(self, fraction: float, color: str) -> None:
        super().__init__()
        self.fraction = fraction
        self._color = color
        self.setFixedHeight(6)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.PANEL_BORDER))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), 6), 3, 3)
        painter.setBrush(QColor(self._color))
        painter.drawRoundedRect(QRectF(0, 0, self.width() * self.fraction, 6), 3, 3)


class ActivityRow(QFrame):
    def __init__(self, package: str, seconds: int, fraction: float) -> None:
        super().__init__()
        self.package = package
        self.bar_fraction = fraction
        name = KNOWN_APPS.get(package, (package, ""))[0]
        self.name_label = QLabel(name)
        self.duration_label = QLabel(format_duration(seconds))
        self.duration_label.setObjectName("help")
        top = QHBoxLayout()
        top.addWidget(self.name_label, 1)
        top.addWidget(self.duration_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addLayout(top)
        layout.addWidget(_Bar(fraction, accent_for(package)))


class ActivityTab(QWidget):
    def __init__(self, log: ActivityLog) -> None:
        super().__init__()
        self._log = log
        self._period = "today"

        self.period_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        periods = QHBoxLayout()
        for key, text in PERIODS:
            button = QPushButton(text)
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, k=key: self._select(k))
            group.addButton(button)
            self.period_buttons[key] = button
            periods.addWidget(button)
        self.period_buttons["today"].setChecked(True)

        self.total_label = QLabel("0 s")
        self.total_label.setObjectName("total")  # estilo (cor de destaque) vem do tema
        total_card = Card("Tempo na tela")
        total_card.body.addWidget(self.total_label)

        self.empty_label = QLabel(EMPTY)
        self.empty_label.setObjectName("help")
        self.empty_label.setWordWrap(True)
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setAlignment(Qt.AlignTop)
        host = QWidget()
        host.setLayout(self._rows_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(host)

        self.note_label = QLabel(NOTE)
        self.note_label.setObjectName("help")
        self.note_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(periods)
        layout.addWidget(total_card)
        layout.addWidget(self.empty_label)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.note_label)
        self.refresh()

    def rows(self) -> list[ActivityRow]:
        return [
            self._rows_layout.itemAt(i).widget()
            for i in range(self._rows_layout.count())
            if isinstance(self._rows_layout.itemAt(i).widget(), ActivityRow)
        ]

    def _select(self, period: str) -> None:
        self._period = period
        self.refresh()

    def refresh(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        totals = self._log.totals(self._period)
        self.total_label.setText(format_duration(sum(seconds for _, seconds in totals)))
        biggest = totals[0][1] if totals else 1
        for package, seconds in totals:
            self._rows_layout.addWidget(ActivityRow(package, seconds, seconds / biggest))
        self.empty_label.setHidden(bool(totals))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
