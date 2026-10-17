import os
from pathlib import Path

from firetv.main import main


def test_selftest_builds_the_window_and_checks_the_adb_key(qapp):
    assert main(["firetv", "--selftest"]) == 0
    assert (Path(os.environ["APPDATA"]) / "firetv-desktop" / "adbkey").exists()
