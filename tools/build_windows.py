"""Empacota o app sem importar DLLs de outros programas presentes no PATH."""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
import subprocess
import sys


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("O executável Windows deve ser gerado no Windows.")
    root = Path(__file__).resolve().parents[1]
    windows = Path(os.environ["SystemRoot"])
    python = Path(sys.base_prefix)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(str(p) for p in (
        Path(sys.executable).parent, python, python / "DLLs",
        windows / "System32", windows,
    ))
    subprocess.run(
        [sys.executable, "tools/prepare_icon.py"], cwd=root, env=env, check=True,
    )
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
        "--onefile", "--noconsole", "--name", "FireTVDesktop",
        "--icon", "build/firetv.ico", "--paths", "src", "app.py",
    ], cwd=root, env=env, check=True)
    digest = hashlib.sha256()
    payload = root / "dist/FireTVDesktop.exe"
    with payload.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    digest_path = root / "build/app-sha256.txt"
    digest_path.write_text(digest.hexdigest(), encoding="ascii")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
        "--onefile", "--noconsole", "--name", "FireTVDesktopSetup",
        "--icon", "build/firetv.ico", "--paths", "src",
        "--add-data", str(payload) + os.pathsep + "payload",
        "--add-data", str(digest_path) + os.pathsep + "payload", "installer.py",
    ], cwd=root, env=env, check=True)


if __name__ == "__main__":
    main()
