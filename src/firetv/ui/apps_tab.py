"""Aba Apps: grade de apps com busca, favoritos, esconder/mostrar e abrir."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
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
from firetv.ui.worker import get_bridge, run_in_background

EMPTY_MESSAGE = "Nenhum app encontrado. Conecte ao Stick na aba Ajustes."
NO_RESULTS_MESSAGE = "Nenhum app encontrado."
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
COLUMNS = 3


def initials(name: str) -> str:
    tokens = name.replace(".", " ").replace("+", " ").split()
    return "".join(t[0] for t in tokens[:2]).upper() or "?"


class AppTile(QFrame):
    """Quadrado colorido com iniciais, nome e estrela (sem logos oficiais)."""

    launch_requested = Signal(str)
    favorite_requested = Signal(str)
    hidden_requested = Signal(str)

    def __init__(self, entry: AppEntry) -> None:
        super().__init__()
        self.entry = entry
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(110, 130)

        self.badge = QLabel(initials(entry.name))
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedSize(56, 56)
        self.badge.setStyleSheet(
            f"background: {entry.color}; color: white; border-radius: 12px; font-weight: bold;"
        )
        self.name_label = QLabel(entry.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.star_button = QPushButton("★" if entry.favorite else "☆")
        self.star_button.setFlat(True)
        self.star_button.setFixedWidth(28)
        self.star_button.clicked.connect(lambda: self.favorite_requested.emit(entry.package))

        layout = QVBoxLayout(self)
        layout.addWidget(self.star_button, 0, Qt.AlignRight)
        layout.addWidget(self.badge, 0, Qt.AlignCenter)
        layout.addWidget(self.name_label)

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

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar apps")
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
        visible = self._entries
        if not self.show_hidden_check.isChecked():
            visible = [e for e in visible if not e.hidden]
        visible = search(visible, self.search_edit.text())
        for index, entry in enumerate(visible):
            tile = AppTile(entry)
            tile.launch_requested.connect(self._launch)
            tile.favorite_requested.connect(self.toggle_favorite)
            tile.hidden_requested.connect(self.toggle_hidden)
            self._grid.addWidget(tile, index // COLUMNS, index % COLUMNS)
        if visible:
            self.empty_label.hide()
        else:
            self.empty_label.setText(EMPTY_MESSAGE if not self._entries else NO_RESULTS_MESSAGE)
            self.empty_label.show()
