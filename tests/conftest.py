import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(autouse=True)
def isolated_appdata(tmp_path, monkeypatch):
    """Nenhum teste toca na configuração real do usuário."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))


@pytest.fixture(autouse=True)
def drain_thread_pool():
    """Espera as tarefas em segundo plano acabarem antes de o Qt ser desmontado."""
    yield
    from PySide6.QtCore import QThreadPool

    QThreadPool.globalInstance().waitForDone(3000)
