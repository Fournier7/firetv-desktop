"""Controle: ações de alto nível sobre uma Connection."""
from __future__ import annotations

from dataclasses import dataclass

from firetv.connection import Connection
from firetv.keys import KeyCode
from firetv.text import prepare_text

_VOLUME_KEYS = (KeyCode.VOLUME_UP, KeyCode.VOLUME_DOWN, KeyCode.MUTE)


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

    def volume(self, key: KeyCode) -> bool:
        if key not in _VOLUME_KEYS:
            raise ValueError(f"{key!r} não é uma tecla de volume")
        output = self.conn.shell(f"input keyevent {int(key)}").lower()
        return "error" not in output and "exception" not in output
