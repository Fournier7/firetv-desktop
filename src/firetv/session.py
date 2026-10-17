"""Sessão: estado da conexão e reconexão automática."""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable, TypeVar

from firetv.connection import Connection, ConnectionLostError, FireTvError
from firetv.controller import Controller

T = TypeVar("T")

POLL_INTERVAL_SECONDS = 3
RECONNECT_DELAYS = (1, 2, 4)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class Session:
    def __init__(
        self,
        conn_factory: Callable[[], Connection],
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._conn = conn_factory()
        self._sleep = sleep
        self._host: str | None = None
        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.RLock()  # um comando por vez na conexão ADB
        self.controller = Controller(self._conn)
        self.on_state_change: Callable[[ConnectionState], None] | None = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    def _set_state(self, state: ConnectionState) -> None:
        if state is self._state:
            return
        self._state = state
        if self.on_state_change is not None:
            self.on_state_change(state)

    def connect(self, host: str) -> None:
        with self._lock:
            self._conn.connect(host)
            self._host = host
            self._set_state(ConnectionState.CONNECTED)

    def run(self, op: Callable[[Controller], T]) -> T:
        with self._lock:
            try:
                return op(self.controller)
            except ConnectionLostError:
                self._reconnect()
            try:
                return op(self.controller)
            except ConnectionLostError:
                self._set_state(ConnectionState.DISCONNECTED)
                raise

    def _reconnect(self) -> None:
        if self._host is None:
            self._set_state(ConnectionState.DISCONNECTED)
            raise ConnectionLostError("sem conexão")
        self._set_state(ConnectionState.RECONNECTING)
        for delay in RECONNECT_DELAYS:
            self._sleep(delay)
            try:
                self._conn.connect(self._host)
            except FireTvError:
                continue
            self._set_state(ConnectionState.CONNECTED)
            return
        self._set_state(ConnectionState.DISCONNECTED)
        raise ConnectionLostError("não foi possível reconectar")
