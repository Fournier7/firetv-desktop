from firetv.keys import KeyCode


def test_keycode_values():
    assert KeyCode.UP == 19 and KeyCode.OK == 23 and KeyCode.MUTE == 164


def test_keycode_full_table():
    assert {k.name: int(k) for k in KeyCode} == {
        "UP": 19, "DOWN": 20, "LEFT": 21, "RIGHT": 22, "OK": 23, "BACK": 4,
        "HOME": 3, "MENU": 82, "PLAY_PAUSE": 85, "REWIND": 89,
        "FAST_FORWARD": 90, "VOLUME_UP": 24, "VOLUME_DOWN": 25, "MUTE": 164,
    }
