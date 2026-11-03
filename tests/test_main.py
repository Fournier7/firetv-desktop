import os
from pathlib import Path

from firetv.main import main
from firetv import main as main_module
from firetv.config import AppConfig
from fakes import FakeConnection


def test_desktop_startup_opens_window_even_with_saved_ip(qapp, monkeypatch):
    monkeypatch.setattr(main_module, "load_config", lambda: AppConfig(host="192.168.0.10"))
    monkeypatch.setattr(main_module, "AdbConnection", FakeConnection)
    monkeypatch.setattr(qapp, "exec", lambda: 0)
    assert main(["firetv"]) == 0
    panel, timer, tray = qapp._firetv_refs
    assert panel.isVisible() and not panel.tray_mode
    assert qapp.quitOnLastWindowClosed()
    assert tray is None
    timer.stop()
    panel.close()


def test_first_start_opens_settings(qapp, monkeypatch):
    monkeypatch.setattr(main_module, "load_config", AppConfig)
    monkeypatch.setattr(qapp, "exec", lambda: 0)
    assert main(["firetv"]) == 0
    panel, timer, _ = qapp._firetv_refs
    assert panel.isVisible() and panel.current_page() is panel.settings_tab
    timer.stop()
    panel.close()


def test_selftest_builds_panel_icons_and_key(qapp):
    assert main(["firetv", "--selftest"]) == 0
    assert (Path(os.environ["APPDATA"]) / "firetv-desktop" / "adbkey").exists()
