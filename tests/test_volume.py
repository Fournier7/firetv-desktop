import pytest

from firetv.keys import KeyCode
from firetv.volume import DEFAULT_METHOD, METHOD_ORDER, NONE, normalize_method, volume_command


def test_constants():
    assert DEFAULT_METHOD == "keyevent" and NONE == "none"
    assert METHOD_ORDER == ("keyevent", "keyboard", "media_session", "media")


@pytest.mark.parametrize(
    "value, expected",
    [("", "keyevent"), ("xyz", "keyevent"), ("none", "none"), ("keyboard", "keyboard"),
     ("media_session", "media_session"), ("media", "media"), ("keyevent", "keyevent")],
)
def test_normalize_method(value, expected):
    assert normalize_method(value) == expected


def test_volume_command_strings():
    expected = {
        ("keyevent", KeyCode.VOLUME_UP): "input keyevent 24",
        ("keyevent", KeyCode.VOLUME_DOWN): "input keyevent 25",
        ("keyevent", KeyCode.MUTE): "input keyevent 164",
        ("keyboard", KeyCode.VOLUME_UP): "input keyboard keyevent 24",
        ("keyboard", KeyCode.VOLUME_DOWN): "input keyboard keyevent 25",
        ("keyboard", KeyCode.MUTE): "input keyboard keyevent 164",
        ("media_session", KeyCode.VOLUME_UP): "cmd media_session volume --show --adj raise",
        ("media_session", KeyCode.VOLUME_DOWN): "cmd media_session volume --show --adj lower",
        ("media_session", KeyCode.MUTE): "cmd media_session volume --show --adj toggle-mute",
        ("media", KeyCode.VOLUME_UP): "media volume --show --adj raise",
        ("media", KeyCode.VOLUME_DOWN): "media volume --show --adj lower",
        ("media", KeyCode.MUTE): "media volume --show --adj toggle-mute",
    }
    for (method, key), command in expected.items():
        assert volume_command(method, key) == command


def test_volume_command_rejects_non_volume_key():
    with pytest.raises(ValueError):
        volume_command("keyevent", KeyCode.UP)


@pytest.mark.parametrize("method", ["none", "xyz", ""])
def test_volume_command_rejects_unusable_methods(method):
    with pytest.raises(ValueError):
        volume_command(method, KeyCode.VOLUME_UP)
