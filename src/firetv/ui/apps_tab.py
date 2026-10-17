"""Aba Apps: grade de apps com busca, favoritos, esconder/mostrar e abrir."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    QVBoxLayout,
    QWidget,
)

from firetv.apps import AppEntry, search, toggle_favorite, toggle_hidden
from firetv.config import AppConfig, save_config
from firetv.connection import ConnectionLostError
from firetv.session import ConnectionState, Session
from firetv.ui import theme
from firetv.ui.icons import icon
from firetv.ui.worker import get_bridge, run_in_background

EMPTY_MESSAGE = "Nenhum app encontrado. Conecte ao Stick na aba Ajustes."
NO_RESULTS_MESSAGE = "Nenhum app encontrado."
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
ON_SCREEN = "NA TELA"
COLUMNS = 3


def initials(name: str) -> str:
    tokens = name.replace(".", " ").replace("+", " ").split()
    return "".join(t[0] for t in tokens[:2]).upper() or "?"


class AppTile(QFrame):
    """Tile na cor do app, com iniciais, nome, estrela e rótulo NA TELA (sem logos oficiais)."""

    launch_requested = Signal(str)
    favorite_requested = Signal(str)
    hidden_requested = Signal(str)

    def __init__(self, entry: AppEntry, show_star: bool = True, compact: bool = False) -> None:
        super().__init__()
        self.entry = entry
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(*((76, 92) if compact else (108, 128)))
        self._apply_style(on_screen=False)

        self.badge_label = QLabel(ON_SCREEN)
        self.badge_label.setStyleSheet(
            f"color: {entry.color}; font-size: 9px; font-weight: bold; background: transparent;"
        )
        self.badge_label.setHidden(True)

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
        self.mark.setFixedSize(mark_size, mark_size)
        self.mark.setStyleSheet(
            f"background: {entry.color}; color: white; border-radius: 12px; font-weight: bold;"
        )
        self.name_label = QLabel(entry.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            f"background: transparent; font-size: {'11px' if compact else '14px'};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.addLayout(top)
        layout.addWidget(self.mark, 0, Qt.AlignCenter)
        layout.addWidget(self.name_label)

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
        self.badge_label.setHidden(not on_screen)
        self._apply_style(on_screen)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.launch_requested.emit(self.entry.package)

    def contextMenuEvent(self, event) -> None:
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

        self.search_edit = QLineEdit()
        self.search_edit.addAction(icon("search", theme.MUTED), QLineEdit.LeadingPosition)
        self.show_hidden_check = QCheckBox("Mostrar apps escondidos")
        self.empty_label = QLabel(EMPTY_MESSAGE)
        self.empty_label.setObjectName("help")
        self.empty_label.setWordWrap(True)
        self.message_label = QLabel("")
        self.message_label.setObjectName("message")

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self._grid_host)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.show_hidden_check)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.message_label)
        layout.addWidget(scroll, 1)

        self.search_edit.textChanged.connect(lambda _: self._render())
        self.show_hidden_check.toggled.connect(lambda _: self._render())
        get_bridge(session).state_changed.connect(self._on_state_changed)
        self._render()
        if session.state is ConnectionState.CONNECTED:
            self.refresh()

    # --- dados ---
    def tiles(self) -> list[AppTile]:
        found = []
        for i in range(self._grid.count()):
            widget = self._grid.itemAt(i).widget()
            if isinstance(widget, AppTile):
                found.append(widget)
        return found

    def set_current_app(self, package: str | None) -> None:
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
        total = len(self._entries)
        self.search_edit.setPlaceholderText(f"Buscar nos {total} apps" if total else "Buscar apps")
        visible = self._entries
        if not self.show_hidden_check.isChecked():
            visible = [e for e in visible if not e.hidden]
        visible = search(visible, self.search_edit.text())
        for index, entry in enumerate(visible):
            tile = AppTile(entry)
            tile.set_on_screen(entry.package == self._current)
            tile.launch_requested.connect(self._launch)
            tile.favorite_requested.connect(self.toggle_favorite)
            tile.hidden_requested.connect(self.toggle_hidden)
            self._grid.addWidget(tile, index // COLUMNS, index % COLUMNS)
        if visible:
            self.empty_label.hide()
        else:
            self.empty_label.setText(EMPTY_MESSAGE if not self._entries else NO_RESULTS_MESSAGE)
            self.empty_label.show()
