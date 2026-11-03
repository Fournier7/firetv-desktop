"""Aba Apps: grade de apps com busca, favoritos, esconder/mostrar e abrir."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, Property, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from firetv.apps import AppEntry, search, streaming_suggestions, toggle_favorite, toggle_hidden
from firetv.config import AppConfig, save_config
from firetv.connection import ConnectionLostError
from firetv.session import ConnectionState, Session
from firetv.ui import theme
from firetv.ui.icons import icon
from firetv.ui.worker import get_bridge, run_in_background

EMPTY_MESSAGE = "Nenhum app encontrado. Conecte ao Stick na aba Ajustes."
NO_RESULTS_MESSAGE = "Nenhum app encontrado."
NO_POPULAR_MESSAGE = 'Nenhum app popular encontrado. Marque "Mostrar todos os apps" para ver o resto.'
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
ON_SCREEN = "NA TELA"
COLUMNS = 3


def initials(name: str) -> str:
    tokens = name.replace(".", " ").replace("+", " ").split()
    return "".join(t[0] for t in tokens[:2]).upper() or "?"


class ElidedLabel(QLabel):
    """Rótulo de uma linha que corta o texto com reticências; o texto completo fica na dica."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setToolTip(text)

    def sizeHint(self) -> QSize:
        return QSize(10, self.fontMetrics().height() + 2)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        shown = self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, self.width())
        painter.drawText(self.rect(), int(self.alignment()), shown)


class AppTile(QFrame):
    """Tile na cor do app, com iniciais, nome, estrela e rótulo NA TELA (sem logos oficiais)."""

    launch_requested = Signal(str)
    favorite_requested = Signal(str)
    hidden_requested = Signal(str)

    def __init__(self, entry: AppEntry, show_star: bool = True, compact: bool = False,
                 *, animated: bool = False, suggestion: bool = False) -> None:
        super().__init__()
        self.entry = entry
        self._animated = animated
        self._suggestion = suggestion
        self._hover_progress = 0.0
        self.hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self.hover_animation.setDuration(160)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(*((76, 92) if compact else (100, 124)))
        self._apply_style(on_screen=False)

        self.badge_label = QLabel(ON_SCREEN)
        self.badge_label.setStyleSheet(
            f"color: {entry.color}; font-size: 9px; font-weight: bold; background: transparent;"
        )
        self.badge_label.setHidden(True)
        if suggestion:
            self.badge_label.setText("SUGESTÃO")
            self.badge_label.show()

        self.star_button: QPushButton | None = None
        top = QHBoxLayout()
        top.addWidget(self.badge_label)
        top.addStretch(1)
        if show_star:
            star = QPushButton()
            star.setFlat(True)
            star.setCheckable(True)
            star.setChecked(entry.favorite)
            star.setFixedSize(24, 24)
            star.setStyleSheet("background: transparent; border: 0;")
            self._paint_star(star)
            star.toggled.connect(lambda _: self._paint_star(star))
            star.clicked.connect(lambda: self.favorite_requested.emit(entry.package))
            self.star_button = star
            top.addWidget(star)

        self.mark = QLabel(initials(entry.name))
        self.mark.setAlignment(Qt.AlignCenter)
        mark_size = 36 if compact else 52
        self._base_mark_size = mark_size
        self.mark.setFixedSize(mark_size, mark_size)
        self.mark.setStyleSheet(
            f"background: {entry.color}; color: white; border-radius: 12px; font-weight: bold;"
        )
        self.name_label = ElidedLabel(entry.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            f"background: transparent; font-size: {'10px' if compact else '14px'};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.addLayout(top)
        layout.addWidget(self.mark, 0, Qt.AlignCenter)
        layout.addWidget(self.name_label)

    def _get_hover(self) -> float:
        return self._hover_progress

    def _set_hover(self, value: float) -> None:
        self._hover_progress = value
        font = self.mark.font()
        font.setPixelSize(round(14 + value * 4))
        self.mark.setFont(font)
        size = self._base_mark_size + round(value * 6)
        self.mark.setFixedSize(size, size)
        self.update()

    hoverProgress = Property(float, _get_hover, _set_hover)

    def _animate_hover(self, target: float) -> None:
        if self._animated:
            self.hover_animation.stop()
            self.hover_animation.setStartValue(self._hover_progress)
            self.hover_animation.setEndValue(target)
            self.hover_animation.start()

    def enterEvent(self, event) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        self.hover_animation.stop()
        self._set_hover(0.0)
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._hover_progress > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            color = QColor(self.entry.color)
            color.setAlphaF(self._hover_progress * 0.9)
            painter.setPen(QPen(color, 1.8))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)

    def _paint_star(self, star: QPushButton) -> None:
        on = star.isChecked()
        star.setIcon(icon("star_filled" if on else "star", self.entry.color if on else theme.MUTED))

    def _apply_style(self, on_screen: bool) -> None:
        color = self.entry.color
        border = theme.tint(color, 0.9 if on_screen else 0.4)
        self.setStyleSheet(
            f"QFrame#tile {{ background: {theme.tint(color, 0.14)};"
            f" border: 1px solid {border}; border-radius: 14px; }}"
        )

    def set_on_screen(self, on_screen: bool) -> None:
        if self._suggestion:
            return
        self.badge_label.setHidden(not on_screen)
        self._apply_style(on_screen)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._animated:
                self._set_hover(0.0)
                self._animate_hover(1.0)
            self.launch_requested.emit(self.entry.package)

    def contextMenuEvent(self, event) -> None:
        if self._suggestion:
            return
        menu = QMenu(self)
        action = menu.addAction("Mostrar" if self.entry.hidden else "Esconder")
        if menu.exec(event.globalPos()) is action:
            self.hidden_requested.emit(self.entry.package)


class AppsTab(QWidget):
    favorites_changed = Signal()

    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg
        self._entries: list[AppEntry] = []
        self._current: str | None = None
        self._columns = COLUMNS
        self.mode_tabs = QTabBar()
        self.mode_tabs.addTab("Na minha TV")
        self.mode_tabs.addTab("Descobrir streamings")
        self.mode_tabs.setExpanding(True)
        self.mode_tabs.setStyleSheet("QTabBar::tab { padding: 8px 10px; font-size: 12px; }")
        self.discovery_hint = QLabel("Sugestões para procurar na loja do Fire TV. A disponibilidade varia por modelo e região.")
        self.discovery_hint.setWordWrap(True)
        self.discovery_hint.setObjectName("help")
        self.discovery_hint.hide()

        self.search_edit = QLineEdit()
        self.search_edit.addAction(icon("search", theme.MUTED), QLineEdit.LeadingPosition)
        self.show_hidden_check = QCheckBox("Mostrar todos os apps (sistema e escondidos)")
        self.empty_label = QLabel(EMPTY_MESSAGE)
        self.empty_label.setObjectName("help")
        self.empty_label.setWordWrap(True)
        self.message_label = QLabel("")
        self.message_label.setObjectName("message")

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self._grid_host)
        self._scroll = scroll
        scroll.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.mode_tabs)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.discovery_hint)
        layout.addWidget(self.show_hidden_check)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.message_label)
        layout.addWidget(scroll, 1)

        self.search_edit.textChanged.connect(lambda _: self._render())
        self.show_hidden_check.toggled.connect(lambda _: self._render())
        self.mode_tabs.currentChanged.connect(self._change_mode)
        get_bridge(session).state_changed.connect(self._on_state_changed)
        self._render()
        if session.state is ConnectionState.CONNECTED:
            self.refresh()

    def _change_mode(self, index: int) -> None:
        self.show_hidden_check.setVisible(index == 0)
        self.discovery_hint.setVisible(index == 1)
        self.message_label.clear()
        self._render()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._scroll.viewport() and event.type() == QEvent.Resize:
            columns = max(1, (event.size().width() + 8) // 108)
            if columns != self._columns:
                self._columns = columns
                tiles = self.tiles()
                for tile in tiles:
                    self._grid.removeWidget(tile)
                for index, tile in enumerate(tiles):
                    self._grid.addWidget(tile, index // columns, index % columns)
        return super().eventFilter(obj, event)

    # --- dados ---
    def tiles(self) -> list[AppTile]:
        found = []
        for i in range(self._grid.count()):
            widget = self._grid.itemAt(i).widget()
            if isinstance(widget, AppTile):
                found.append(widget)
        return found

    def set_current_app(self, package: str | None) -> None:
        if package == self._current:
            return
        self._current = package
        for tile in self.tiles():
            tile.set_on_screen(tile.entry.package == package)

    def refresh(self) -> None:
        run_in_background(
            lambda: self._session.run(lambda c: c.list_apps(self._cfg, show_hidden=True)),
            self._on_loaded,
            self._on_load_error,
        )

    def _on_loaded(self, entries: list[AppEntry]) -> None:
        self._entries = entries
        self.message_label.setText("")
        self._render()

    def _on_load_error(self, exc: Exception) -> None:
        self._entries = []
        self._render()

    def _on_state_changed(self, state: ConnectionState) -> None:
        if state is ConnectionState.CONNECTED:
            self.refresh()

    # --- ações ---
    def toggle_favorite(self, package: str) -> None:
        toggle_favorite(self._cfg, package)
        self._persist()
        self.favorites_changed.emit()

    def toggle_hidden(self, package: str) -> None:
        toggle_hidden(self._cfg, package)
        self._persist()

    def _persist(self) -> None:
        save_config(self._cfg)
        for entry in self._entries:
            entry.favorite = entry.package in self._cfg.favorites
            entry.hidden = entry.package in self._cfg.hidden
        self._render()

    def _launch(self, package: str) -> None:
        if self.mode_tabs.currentIndex() == 1:
            suggestion = next((entry for entry in streaming_suggestions(self._entries) if entry.package == package), None)
            if suggestion is not None:
                self.message_label.setText(f'Na TV, abra Buscar e procure por "{suggestion.name}" para instalar pela loja.')
            return
        run_in_background(
            lambda: self._session.run(lambda c: c.launch(package)),
            lambda _: self.message_label.setText(""),
            lambda exc: self.message_label.setText(
                MSG_LOST if isinstance(exc, ConnectionLostError) else str(exc)
            ),
        )

    # --- desenho ---
    def _render(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        discovering = self.mode_tabs.currentIndex() == 1
        visible = streaming_suggestions(self._entries) if discovering else self._entries
        if not discovering and not self.show_hidden_check.isChecked():
            visible = [e for e in visible if e.featured and not e.hidden]
        count = len(visible)
        self.search_edit.setPlaceholderText(
            "Buscar streamings" if discovering else (f"Buscar nos {count} apps" if count else "Buscar apps")
        )
        query = self.search_edit.text()
        visible = search(visible, query)
        for index, entry in enumerate(visible):
            tile = AppTile(entry, show_star=not discovering, suggestion=discovering)
            tile.set_on_screen(entry.package == self._current)
            tile.launch_requested.connect(self._launch)
            tile.favorite_requested.connect(self.toggle_favorite)
            tile.hidden_requested.connect(self.toggle_hidden)
            self._grid.addWidget(tile, index // self._columns, index % self._columns)
        if visible:
            self.empty_label.hide()
        else:
            if discovering:
                message = NO_RESULTS_MESSAGE if query.strip() else "Os streamings deste catálogo já estão instalados."
            elif not self._entries:
                message = EMPTY_MESSAGE
            elif query.strip():
                message = NO_RESULTS_MESSAGE
            else:
                message = NO_POPULAR_MESSAGE
            self.empty_label.setText(message)
            self.empty_label.show()
