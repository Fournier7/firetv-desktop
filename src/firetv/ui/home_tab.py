"""Aba Início: app em execução, volume e favoritos."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from firetv.apps import KNOWN_APPS, build_entries
from firetv.config import AppConfig
from firetv.session import POLL_INTERVAL_SECONDS, ConnectionState, Session
from firetv.ui.apps_tab import AppTile
from firetv.ui.theme import accent_for
from firetv.ui.remote_tab import RemoteTab
from firetv.ui.widgets import AudioCard, Card, TvCard
from firetv.ui.worker import get_bridge, run_in_background

MAX_FAVORITES = 4
NO_FAVORITES = "Marque apps com a estrela na aba Apps."


class HomeTab(QWidget):
    see_all_requested = Signal()
    polled = Signal(object)  # pacote em primeiro plano, ou None
    configure_volume_requested = Signal()

    def __init__(self, session: Session, cfg: AppConfig, *, desktop_mode: bool = True) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg
        self._polling = False
        self._generation = 0
        self._desktop_mode = desktop_mode
        self._favorite_columns = 2
        self.quick_remote = RemoteTab(session, cfg, embedded=True)
        self.quick_remote.setVisible(desktop_mode)

        self.tv_card = TvCard()
        self.audio_card = AudioCard(session, cfg)
        self.audio_card.configure_requested.connect(self.configure_volume_requested)
        self.launch_notice = QLabel("")
        self.launch_notice.setObjectName("message")
        self.launch_notice.setWordWrap(True)
        self.launch_notice.hide()

        self.see_all_button = QPushButton("Ver todos")
        self.see_all_button.setFlat(True)
        self.see_all_button.clicked.connect(self.see_all_requested)
        self.favorites_empty_label = QLabel(NO_FAVORITES)
        self.favorites_empty_label.setObjectName("help")
        self.favorites_empty_label.setWordWrap(True)
        self._strip = QGridLayout()
        self._strip.setSpacing(8)
        self._strip.setColumnStretch(0, 1)
        self._strip.setColumnStretch(1, 1)

        self.favorites_title_label = QLabel("FAVORITOS")
        self.favorites_title_label.setObjectName("help")
        title_row = QHBoxLayout()
        title_row.addWidget(self.favorites_title_label)
        title_row.addStretch(1)
        title_row.addWidget(self.see_all_button)
        favorites = Card()
        favorites.body.addLayout(title_row)
        favorites.body.addLayout(self._strip)
        favorites.body.addWidget(self.favorites_empty_label)

        self.summary = QWidget()
        summary_layout = QVBoxLayout(self.summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(16)
        summary_layout.addWidget(self.tv_card)
        summary_layout.addWidget(favorites, 1)
        summary_layout.addWidget(self.launch_notice)
        summary_layout.addWidget(self.audio_card)
        self._columns = QBoxLayout(QBoxLayout.TopToBottom, self)
        self._columns.setContentsMargins(0, 0, 0, 0)
        self._columns.setSpacing(20)
        self._columns.addWidget(self.summary, 1)
        self._columns.addWidget(self.quick_remote, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(POLL_INTERVAL_SECONDS * 1000)
        self.timer.timeout.connect(self.poll)
        get_bridge(session).state_changed.connect(self._on_state_changed)
        self.refresh_favorites()
        if session.state is ConnectionState.CONNECTED:
            self._start_polling()

    def set_wide_layout(self, wide: bool) -> None:
        wide = wide and self._desktop_mode
        self._columns.setDirection(QBoxLayout.LeftToRight if wide else QBoxLayout.TopToBottom)
        first, second = (self.quick_remote, self.summary) if wide else (self.summary, self.quick_remote)
        if self._columns.itemAt(0).widget() is not first:
            self._columns.removeWidget(first)
            self._columns.removeWidget(second)
            self._columns.addWidget(first, 1)
            self._columns.addWidget(second, 1)
        self.quick_remote.dpad.set_diameter(240 if wide else 200)
        columns = 4 if wide else 2
        if columns != self._favorite_columns:
            self._favorite_columns = columns
            for column in range(4):
                self._strip.setColumnStretch(column, 1 if column < columns else 0)
            tiles = self.favorite_tiles()
            for tile in tiles:
                self._strip.removeWidget(tile)
            for index, tile in enumerate(tiles):
                self._strip.addWidget(tile, index // columns, index % columns, Qt.AlignTop)

    # --- app em execução ---
    def _on_state_changed(self, state: ConnectionState) -> None:
        self._generation += 1
        self._polling = False
        if state is ConnectionState.CONNECTED:
            self._start_polling()
        else:
            self.timer.stop()
            self.tv_card.set_app(None, accent_for(None))
            self.polled.emit(None)

    def _start_polling(self) -> None:
        self.timer.start()
        self.poll()

    def poll(self) -> None:
        if self._polling:
            return
        self._polling = True
        generation = self._generation
        run_in_background(
            lambda: self._session.run(lambda c: c.current_app()),
            lambda package: self._on_current_app(package) if generation == self._generation else None,
            lambda exc: self._finish_poll() if generation == self._generation else None,
        )

    def _finish_poll(self) -> None:
        self._polling = False

    def _on_current_app(self, package: str | None) -> None:
        self._finish_poll()
        name = None if package is None else KNOWN_APPS.get(package, (package, ""))[0]
        self.tv_card.set_app(name, accent_for(package))
        self.polled.emit(package)

    # --- favoritos ---
    def favorite_tiles(self) -> list[AppTile]:
        return [
            self._strip.itemAt(i).widget()
            for i in range(self._strip.count())
            if isinstance(self._strip.itemAt(i).widget(), AppTile)
        ]

    def refresh_favorites(self) -> None:
        while self._strip.count():
            item = self._strip.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        entries = build_entries(self._cfg.favorites, self._cfg)
        by_package = {e.package: e for e in entries}
        shown = [by_package[p] for p in self._cfg.favorites[:MAX_FAVORITES] if p in by_package]
        for index, entry in enumerate(shown):
            tile = AppTile(entry, show_star=False, compact=True, animated=True)
            tile.setMinimumWidth(64)
            tile.setMaximumWidth(16777215)
            tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tile.name_label.setStyleSheet("background: transparent; font-size: 12px;")
            tile.launch_requested.connect(self._launch)
            self._strip.addWidget(tile, index // self._favorite_columns, index % self._favorite_columns, Qt.AlignTop)
        self._strip.setAlignment(Qt.AlignTop)
        self.favorites_empty_label.setHidden(bool(shown))

    def _launch(self, package: str) -> None:
        run_in_background(
            lambda: self._session.run(lambda c: c.launch(package)),
            lambda _: self.launch_notice.hide(),
            self._on_launch_error,
        )

    def _on_launch_error(self, exc: Exception) -> None:
        self.launch_notice.setText("Não foi possível abrir o app. Confira a conexão com a TV.")
        self.launch_notice.show()
