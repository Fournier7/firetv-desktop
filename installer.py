"""Instalador por usuário do Fire TV Desktop, com aplicativo embutido."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

from firetv.installation import default_install_dir, install_payload
from firetv.ui.icons import icon
from firetv.ui.theme import STYLESHEET
from firetv.ui.worker import run_in_background


def bundled_payload() -> Path:
    if hasattr(sys, "_MEIPASS"):
        payload = Path(sys._MEIPASS) / "payload/FireTVDesktop.exe"
        digest_path = Path(sys._MEIPASS) / "payload/app-sha256.txt"
    else:
        payload = Path(__file__).resolve().parent / "dist/FireTVDesktop.exe"
        digest_path = Path(__file__).resolve().parent / "build/app-sha256.txt"
    expected = digest_path.read_text(encoding="ascii").strip()
    digest = hashlib.sha256()
    with payload.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise ValueError("O instalador está incompleto. Gere ou obtenha uma nova cópia.")
    return payload


class Installer(QWidget):
    def __init__(self, payload: Path) -> None:
        super().__init__()
        self._payload = payload
        self._busy = False
        self._installed: Path | None = None
        self.setWindowTitle("Instalar Fire TV Desktop")
        self.setWindowIcon(icon("remote"))
        self.setMinimumSize(500, 300)
        title = QLabel("Fire TV Desktop")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.status = QLabel("Instala no seu usuário, com atalhos na Área de Trabalho e no menu Iniciar.")
        self.status.setWordWrap(True)
        location = QLabel(str(default_install_dir()))
        location.setWordWrap(True)
        self.open_check = QCheckBox("Abrir o aplicativo ao concluir")
        self.open_check.setChecked(True)
        self.button = QPushButton("Instalar")
        self.button.clicked.connect(self._clicked)
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.status)
        layout.addWidget(location)
        layout.addStretch(1)
        layout.addWidget(self.open_check)
        layout.addWidget(self.button)

    def _clicked(self) -> None:
        if self._installed is not None:
            if self.open_check.isChecked():
                QProcess.startDetached(str(self._installed), [])
            self.close()
            return
        self._busy = True
        self.button.setEnabled(False)
        self.status.setText("Instalando e criando os atalhos…")
        run_in_background(
            lambda: install_payload(self._payload, default_install_dir()), self._done, self._failed,
        )

    def _done(self, installed: Path) -> None:
        self._busy = False
        self._installed = installed
        self.status.setText("Instalação concluída. Abra pelo menu Iniciar ou pelo atalho Fire TV Desktop.")
        self.button.setText("Concluir")
        self.button.setEnabled(True)

    def _failed(self, exc: Exception) -> None:
        self._busy = False
        self.button.setEnabled(True)
        self.status.setText(
            "Não foi possível concluir. Feche o Fire TV Desktop se estiver aberto e tente novamente."
        )

    def closeEvent(self, event) -> None:
        if self._busy:
            event.ignore()
        else:
            super().closeEvent(event)


def main() -> int:
    payload = bundled_payload()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = Installer(payload)
    if "--selftest" in sys.argv:
        assert not window.windowIcon().isNull()
        window.deleteLater()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
