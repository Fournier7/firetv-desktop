"""Códigos de tecla do Android usados pelo controle remoto."""
from enum import IntEnum


class KeyCode(IntEnum):
    UP = 19
    DOWN = 20
    LEFT = 21
    RIGHT = 22
    OK = 23
    BACK = 4
    HOME = 3
    MENU = 82
    PLAY_PAUSE = 85
    REWIND = 89
    FAST_FORWARD = 90
    VOLUME_UP = 24
    VOLUME_DOWN = 25
    MUTE = 164
