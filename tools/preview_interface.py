"""Gera capturas da interface com dados fictícios, sem acessar a TV."""
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
if fonts.exists():
    os.environ.setdefault("QT_QPA_FONTDIR", str(fonts))

from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from fakes import FakeConnection
from firetv.activity import ActivityLog
from firetv.config import AppConfig
from firetv.session import Session
from firetv.ui.panel import Panel
from firetv.ui.theme import STYLESHEET


def main() -> None:
    app = QApplication([])
    app.setStyleSheet(STYLESHEET)
    output = ROOT / "docs/screenshots"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="firetv-preview-") as directory:
        os.environ["APPDATA"] = directory
        for filename, width, connected, tab in [
            ("desktop.png", 1000, True, "home"),
            ("desktop-narrow.png", 420, True, "home"),
            ("desktop-disconnected.png", 1000, False, "home"),
            ("home.png", 1000, True, "home"),
            ("remote.png", 1000, True, "remote"),
            ("apps.png", 1000, True, "apps"),
            ("activity.png", 1000, True, "activity"),
            ("settings.png", 1000, True, "settings"),
        ]:
            conn = FakeConnection()
            conn.responses["dumpsys window | grep mCurrentFocus"] = (
                "mCurrentFocus=Window{a u0 com.amazon.firetv.youtube/x.Main}"
            )
            packages = ["com.netflix.ninja", "com.amazon.firetv.youtube", "com.amazon.firebat", "com.disney.disneyplus"]
            conn.responses["pm list packages"] = "\n".join("package:" + p for p in packages)
            conn.responses["pm list packages -3"] = conn.responses["pm list packages"]
            session = Session(lambda: conn)
            if connected:
                session.connect("192.0.2.10")
            cfg = AppConfig(host="192.0.2.10", tv_name="TV da sala", favorites=packages)
            log = ActivityLog(Path(directory) / (filename + ".json"))
            now = 0
            log.record(packages[1], now)
            for package, seconds in [(packages[1], 900), (packages[0], 600), (packages[2], 180)]:
                for _ in range(seconds // 10):
                    now += 10
                    log.record(package, now)
            panel = Panel(session, cfg, log)
            panel.resize(width, 820)
            panel.show_tab(tab)
            panel.show()
            panel.tab_buttons[tab].setFocus()
            QTest.qWait(200)
            if not panel.grab().save(str(output / filename)):
                raise RuntimeError(f"Não foi possível salvar {filename}")
            panel.close()
            QThreadPool.globalInstance().waitForDone(5000)
        sys.path.insert(0, str(ROOT))
        from installer import Installer

        os.environ["LOCALAPPDATA"] = "C:/Users/Usuario/AppData/Local"
        setup = Installer(ROOT / "dist/FireTVDesktop.exe")
        setup.show()
        app.processEvents()
        if not setup.grab().save(str(output / "installer.png")):
            raise RuntimeError("Não foi possível salvar a captura do instalador")
        setup.close()
    print("Capturas geradas com dados fictícios.")


if __name__ == "__main__":
    main()
