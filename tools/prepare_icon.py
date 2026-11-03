"""Prepara o ícone do executável a partir do ícone já usado pelo aplicativo."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from firetv.ui.icons import icon


def main() -> None:
    app = QApplication.instance() or QApplication([])
    target = Path(__file__).resolve().parents[1] / "build" / "firetv.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not icon("remote", "#3B82F6").pixmap(48, 48).save(str(target), "ICO"):
        raise RuntimeError("Não foi possível preparar o ícone do executável")


if __name__ == "__main__":
    main()
