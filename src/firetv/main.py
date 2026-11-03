"""Abre a janela desktop; --tray mantém o painel de bandeja opcional."""
from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from firetv.activity import ActivityLog
from firetv.config import config_dir, load_config
from firetv.connection import AdbConnection, _load_signer
from firetv.session import Session
from firetv.ui.icons import ICON_NAMES, icon
from firetv.ui.instance import SingleInstance
from firetv.ui.panel import Panel, TrayController, auto_connect
from firetv.ui.theme import STYLESHEET

SAVE_INTERVAL_MS = 30_000


def main(argv: list[str] | None = None) -> int | None:
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("FireTVDesktop")
    app.setApplicationDisplayName("Fire TV Desktop")
    app.setStyleSheet(STYLESHEET)
    tray_mode = "--tray" in argv
    app.setQuitOnLastWindowClosed(not tray_mode)
    app.setWindowIcon(icon("remote"))
    instance = None
    if "--selftest" not in argv:
        instance = SingleInstance(config_dir())
        try:
            if not instance.acquire_or_activate():
                return 0
        except RuntimeError as exc:
            QMessageBox.information(None, "Fire TV Desktop", str(exc))
            return 1
    cfg = load_config()
    log = ActivityLog()
    session = Session(AdbConnection)
    panel = Panel(session, cfg, log, tray_mode=tray_mode)
    if instance is not None:
        instance.set_activation_callback(panel.show_panel)

    if "--selftest" in argv:  # confere que o app (ou o .exe) sobe, com ícones e chave ADB
        _load_signer()
        for name in ICON_NAMES:
            assert not icon(name).pixmap(48, 48).isNull(), name
        print("selftest ok")
        panel.deleteLater()
        return 0

    tray = TrayController(app, panel) if tray_mode else None
    if cfg.host:
        panel.reconnect()
    if not cfg.host:  # primeira vez: abre direto nos Ajustes
        panel.show_tab("settings")
    if not tray_mode or not cfg.host:
        panel.show_panel()
    timer = QTimer()
    timer.timeout.connect(log.save)
    timer.start(SAVE_INTERVAL_MS)
    if tray_mode:
        app.aboutToQuit.connect(panel.save)
    app._firetv_refs = (panel, timer, tray)  # mantém os objetos vivos
    try:
        return app.exec()
    finally:
        if instance is not None:
            instance.close()


if __name__ == "__main__":
    sys.exit(main())
