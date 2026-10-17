"""Aba Início: app em execução, volume e favoritos."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from firetv.apps import KNOWN_APPS, build_entries
from firetv.config import AppConfig
from firetv.session import POLL_INTERVAL_SECONDS, ConnectionState, Session
from firetv.ui.apps_tab import AppTile
from firetv.ui.theme import accent_for
from firetv.ui.widgets import AudioCard, Card, TvCard
from firetv.ui.worker import get_bridge, run_in_background

MAX_FAVORITES = 4
NO_FAVORITES = "Marque apps com a estrela na aba Apps."


class HomeTab(QWidget):
    see_all_requested = Signal()
    polled = Signal(object)  # pacote em primeiro plano, ou None

    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg
        self._polling = False

        self.tv_card = TvCard()
        self.audio_card = AudioCard(session, cfg)

        self.see_all_button = QPushButton("Ver todos")
        self.see_all_button.setFlat(True)
        self.see_all_button.clicked.connect(self.see_all_requested)
        self.favorites_empty_label = QLabel(NO_FAVORITES)
        self.favorites_empty_label.setObjectName("help")
        self.favorites_empty_label.setWordWrap(True)
        self._strip = QHBoxLayout()
        self._strip.setSpacing(8)

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

        layout = QVBoxLayout(self)
        layout.addWidget(self.tv_card)
        layout.addWidget(self.audio_card)
        layout.addWidget(favorites)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.setInterval(POLL_INTERVAL_SECONDS * 1000)
        self.timer.timeout.connect(self.poll)
        get_bridge(session).state_changed.connect(self._on_state_changed)
        self.refresh_favorites()
        if session.state is ConnectionState.CONNECTED:
            self._start_polling()

    # --- app em execução ---
    def _on_state_changed(self, state: ConnectionState) -> None:
        if state is ConnectionState.CONNECTED:
            self._start_polling()
        else:
            self.timer.stop()

    def _start_polling(self) -> None:
        self.timer.start()
        self.poll()

    def poll(self) -> None:
        if self._polling:
            return
        self._polling = True
        run_in_background(
            lambda: self._session.run(lambda c: c.current_app()),
            self._on_current_app,
            lambda exc: self._finish_poll(),
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
        for entry in shown:
            tile = AppTile(entry, show_star=False, compact=True)
            tile.launch_requested.connect(self._launch)
            self._strip.addWidget(tile)
        self._strip.addStretch(1)
        self.favorites_empty_label.setHidden(bool(shown))

    def _launch(self, package: str) -> None:
        run_in_background(
            lambda: self._session.run(lambda c: c.launch(package)),
            lambda _: None,
            lambda exc: None,
        )
