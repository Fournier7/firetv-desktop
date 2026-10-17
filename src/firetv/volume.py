"""Jeitos de mandar volume ao Stick. Os comandos são candidatos: precisam ser
conferidos no aparelho real (ver o diagnóstico de volume nos Ajustes)."""
from __future__ import annotations

from firetv.keys import KeyCode

DEFAULT_METHOD = "keyevent"
NONE = "none"
METHOD_ORDER = ("keyevent", "keyboard", "media_session", "media")

_ADJUST = {
    KeyCode.VOLUME_UP: "raise",
    KeyCode.VOLUME_DOWN: "lower",
    KeyCode.MUTE: "toggle-mute",
}


def normalize_method(value: str) -> str:
    """Vazio ou desconhecido vira o método padrão; 'none' significa sem volume."""
    if value == NONE or value in METHOD_ORDER:
        return value
    return DEFAULT_METHOD


def volume_command(method: str, key: KeyCode) -> str:
    if key not in _ADJUST:
        raise ValueError(f"{key!r} não é uma tecla de volume")
    if method == "keyevent":
        return f"input keyevent {int(key)}"
    if method == "keyboard":
        return f"input keyboard keyevent {int(key)}"
    if method == "media_session":
        return f"cmd media_session volume --show --adj {_ADJUST[key]}"
    if method == "media":
        return f"media volume --show --adj {_ADJUST[key]}"
    raise ValueError(f"método de volume sem comando: {method!r}")
