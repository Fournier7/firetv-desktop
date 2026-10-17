"""Conexão falsa para testes: nenhum teste usa rede de verdade."""
from __future__ import annotations

from firetv.connection import ConnectionLostError


class FakeConnection:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.responses: dict[str, str] = {}
        self.fail_connect: Exception | None = None
        self.drop_next = False
        self.connected = False
        self.host = ""
        self.connect_calls = 0

    def connect(self, host: str, port: int = 5555) -> None:
        self.connect_calls += 1
        if self.fail_connect is not None:
            raise self.fail_connect
        self.host = host
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def shell(self, command: str) -> str:
        if self.drop_next:
            self.drop_next = False
            self.connected = False
            raise ConnectionLostError("conexão perdida")
        if not self.connected:
            raise ConnectionLostError("sem conexão")
        self.commands.append(command)
        return self.responses.get(command, "")
