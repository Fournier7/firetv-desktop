"""Garante uma instância por perfil e encaminha pedidos de abrir a janela."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEventLoop, QLockFile, QObject, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    def __init__(self, directory: Path) -> None:
        super().__init__()
        directory.mkdir(parents=True, exist_ok=True)
        identity = str(directory.resolve()).casefold().encode("utf-8")
        self._name = "firetv-desktop-" + hashlib.sha256(identity).hexdigest()[:24]
        self._lock = QLockFile(str(directory / "instance.lock"))
        self._lock.setStaleLockTime(0)
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.UserAccessOption)
        self._server.newConnection.connect(self._accept)
        self._callback: Callable[[], None] | None = None
        self._pending = False
        self._owns_lock = False

    def acquire_or_activate(self) -> bool:
        if self._lock.tryLock(0):
            self._owns_lock = True
            QLocalServer.removeServer(self._name)
            if not self._server.listen(self._name):
                self.close()
                raise RuntimeError("Não foi possível preparar a janela do aplicativo.")
            return True
        for _ in range(3):
            client = QLocalSocket()
            client.connectToServer(self._name)
            if client.waitForConnected(500):
                client.write(b"activate\n")
                client.flush()
                loop = QEventLoop()
                timeout = QTimer()
                timeout.setSingleShot(True)
                timeout.timeout.connect(loop.quit)
                client.readyRead.connect(loop.quit)
                timeout.start(2000)
                if not client.bytesAvailable():
                    loop.exec()
                timeout.stop()
                acknowledged = bytes(client.readAll()).strip() == b"ok"
                client.disconnectFromServer()
                if acknowledged:
                    return False
        raise RuntimeError("O aplicativo já está abrindo. Aguarde um instante e tente novamente.")

    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        if self._pending:
            self._pending = False
            callback()

    def _accept(self) -> None:
        while self._server.hasPendingConnections():
            peer = self._server.nextPendingConnection()
            buffer = bytearray()

            def receive(peer=peer, buffer=buffer) -> None:
                buffer.extend(bytes(peer.readAll()))
                if len(buffer) > 64:
                    peer.abort()
                elif b"\n" in buffer:
                    if bytes(buffer).strip() == b"activate":
                        peer.write(b"ok\n")
                        peer.flush()
                        if self._callback is None:
                            self._pending = True
                        else:
                            self._callback()
                    peer.disconnectFromServer()

            peer.readyRead.connect(receive)
            peer.disconnected.connect(peer.deleteLater)
            if peer.bytesAvailable():
                receive()

    def close(self) -> None:
        self._server.close()
        if self._owns_lock:
            self._lock.unlock()
            self._owns_lock = False
