"""Controle: ações de alto nível sobre uma Connection."""
from __future__ import annotations

import re
from dataclasses import dataclass

from firetv.apps import AppEntry, build_entries, parse_packages
from firetv.config import AppConfig
from firetv.connection import Connection
from firetv.keys import KeyCode
from firetv.text import prepare_text
from firetv.volume import NONE, normalize_method, volume_command

_FOCUS_RE = re.compile(r"mCurrentFocus=.*?([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+\}")
_PACKAGE_RE = re.compile(r"[A-Za-z0-9._]+")
_VOLUME_KEYS = (KeyCode.VOLUME_UP, KeyCode.VOLUME_DOWN, KeyCode.MUTE)


def parse_focus(output: str) -> str | None:
    match = _FOCUS_RE.search(output)
    return match.group(1) if match else None


@dataclass
class SendTextResult:
    sent: int
    skipped: str


class Controller:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def press(self, key: KeyCode) -> None:
        self.conn.shell(f"input keyevent {int(key)}")

    def send_text(self, text: str) -> SendTextResult:
        ready, skipped = prepare_text(text)
        sent = len(text) - len(skipped)
        if ready:
            self.conn.shell(f"input text '{ready}'")
        return SendTextResult(sent=sent if ready else 0, skipped=skipped)

    def volume(self, key: KeyCode, method: str = "") -> bool:
        if key not in _VOLUME_KEYS:
            raise ValueError(f"{key!r} não é uma tecla de volume")
        method = normalize_method(method)
        if method == NONE:
            return False
        output = self.conn.shell(volume_command(method, key)).lower()
        return "error" not in output and "exception" not in output

    def list_apps(self, cfg: AppConfig, show_hidden: bool = False) -> list[AppEntry]:
        packages = parse_packages(self.conn.shell("pm list packages"))
        entries = build_entries(packages, cfg)
        return entries if show_hidden else [e for e in entries if not e.hidden]

    def launch(self, package: str) -> None:
        if not _PACKAGE_RE.fullmatch(package):
            raise ValueError(f"nome de pacote inválido: {package!r}")
        self.conn.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    def current_app(self) -> str | None:
        return parse_focus(self.conn.shell("dumpsys window | grep mCurrentFocus"))
