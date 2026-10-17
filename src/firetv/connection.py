"""Camada de conexão: a única que fala com o Stick (ADB por rede)."""
from __future__ import annotations

from typing import Protocol

from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import (
    AdbConnectionError,
    AdbTimeoutError,
    DeviceAuthError,
    TcpTimeoutException,
)

from firetv.config import config_dir

CONNECT_TIMEOUT_SECONDS = 5.0
_NETWORK_ERRORS = (OSError, TcpTimeoutException, AdbConnectionError, AdbTimeoutError)


class FireTvError(Exception):
    """Base de todos os erros do app."""


class ConnectionFailedError(FireTvError):
    """Não foi possível alcançar o Stick."""


class AuthRequiredError(FireTvError):
    """O Stick pediu autorização que ainda não foi aceita na TV."""


class ConnectionLostError(FireTvError):
    """A conexão caiu ou não existe."""


class Connection(Protocol):
    def connect(self, host: str, port: int = 5555) -> None: ...

    def disconnect(self) -> None: ...

    def is_connected(self) -> bool: ...

    def shell(self, command: str) -> str: ...


def _load_signer() -> PythonRSASigner:
    key_path = config_dir() / "adbkey"
    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        keygen(str(key_path))
    priv = key_path.read_text()
    pub = key_path.with_name("adbkey.pub").read_text()
    return PythonRSASigner(pub, priv)


class AdbConnection:
    def __init__(self) -> None:
        self._device = None

    def connect(self, host: str, port: int = 5555) -> None:
        self.disconnect()
        device = AdbDeviceTcp(host, port, default_transport_timeout_s=CONNECT_TIMEOUT_SECONDS)
        try:
            device.connect(rsa_keys=[_load_signer()], auth_timeout_s=CONNECT_TIMEOUT_SECONDS)
        except DeviceAuthError as exc:
            raise AuthRequiredError(str(exc)) from exc
        except _NETWORK_ERRORS as exc:
            raise ConnectionFailedError(str(exc)) from exc
        self._device = device

    def disconnect(self) -> None:
        if self._device is not None:
            try:
                self._device.close()
            except Exception:  # fechar nunca deve quebrar o app
                pass
            self._device = None

    def is_connected(self) -> bool:
        return self._device is not None

    def shell(self, command: str) -> str:
        if self._device is None:
            raise ConnectionLostError("sem conexão")
        try:
            return self._device.shell(command)
        except _NETWORK_ERRORS as exc:
            self.disconnect()
            raise ConnectionLostError(str(exc)) from exc
