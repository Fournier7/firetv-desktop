"""Aba Início: app em execução na TV e faixa de favoritos."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from firetv.apps import KNOWN_APPS, build_entries
from firetv.config import AppConfig
from firetv.session import POLL_INTERVAL_SECONDS, ConnectionState, Session
from firetv.ui.apps_tab import AppTile
from firetv.ui.worker import get_bridge, run_in_background

NO_APP = "Nenhum app em primeiro plano"


class HomeTab(QWidget):
    def __init__(self, session: Session, cfg: AppConfig) -> None:
        super().__init__()
        self._session = session
        self._cfg = cfg
        self._polling = False

        title = QLabel("EM EXECUÇÃO NA TV")
        title.setObjectName("help")
        self.current_app_label = QLabel(NO_APP)
        self.current_app_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        favorites_title = QLabel("Favoritos")
        favorites_title.setObjectName("help")
        self._strip = QHBoxLayout()

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.current_app_label)
        layout.addWidget(favorites_title)
        layout.addLayout(self._strip)
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
        if package is None:
            self.current_app_label.setText(NO_APP)
        else:
            self.current_app_label.setText(KNOWN_APPS.get(package, (package, ""))[0])

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
        for entry in build_entries(self._cfg.favorites, self._cfg):
            tile = AppTile(entry)
            tile.launch_requested.connect(self._launch)
            self._strip.addWidget(tile)
        self._strip.addStretch(1)

    def _launch(self, package: str) -> None:
        run_in_background(
            lambda: self._session.run(lambda c: c.launch(package)),
            lambda _: None,
            lambda exc: None,
        )
