"""Ponto de entrada do app."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from firetv.config import load_config
from firetv.connection import AdbConnection, _load_signer
from firetv.session import Session
from firetv.ui.main_window import MainWindow
from firetv.ui.theme import STYLESHEET


def main(argv: list[str] | None = None) -> int | None:
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow(Session(AdbConnection), load_config())
    if "--selftest" in argv:  # confere que o app (ou o .exe) sobe e que a chave ADB funciona
        _load_signer()
        print("selftest ok")
        return 0
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
