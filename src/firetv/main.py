"""Ponto de entrada do app."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from firetv.config import load_config
from firetv.connection import AdbConnection
from firetv.session import Session
from firetv.ui.main_window import MainWindow
from firetv.ui.theme import STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    cfg = load_config()
    session = Session(AdbConnection)
    window = MainWindow(session, cfg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
