"""Ponto de entrada do app: painel na bandeja do sistema."""
from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from firetv.activity import ActivityLog
from firetv.config import load_config
from firetv.connection import AdbConnection, _load_signer
from firetv.session import Session
from firetv.ui.icons import ICON_NAMES, icon
from firetv.ui.panel import Panel, TrayController, auto_connect
from firetv.ui.theme import STYLESHEET

SAVE_INTERVAL_MS = 30_000


def main(argv: list[str] | None = None) -> int | None:
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(False)  # fechar o painel não encerra o app
    cfg = load_config()
    log = ActivityLog()
    session = Session(AdbConnection)
    panel = Panel(session, cfg, log)

    if "--selftest" in argv:  # confere que o app (ou o .exe) sobe, com ícones e chave ADB
        _load_signer()
        for name in ICON_NAMES:
            assert not icon(name).pixmap(48, 48).isNull(), name
        print("selftest ok")
        return 0

    tray = TrayController(app, panel)
    auto_connect(session, cfg)
    if not cfg.host:  # primeira vez: abre direto nos Ajustes
        panel.show_tab("settings")
        panel.show_panel()
    timer = QTimer()
    timer.timeout.connect(log.save)
    timer.start(SAVE_INTERVAL_MS)
    app.aboutToQuit.connect(panel.save)
    app._firetv_refs = (tray, timer, panel)  # mantém os objetos vivos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
