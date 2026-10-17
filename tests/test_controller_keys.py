import pytest

from fakes import FakeConnection
from firetv.controller import Controller, SendTextResult
from firetv.keys import KeyCode


@pytest.fixture
def conn():
    c = FakeConnection()
    c.connect("192.168.0.10")
    return c


@pytest.fixture
def ctl(conn):
    return Controller(conn)


def test_press_sends_keyevent(ctl, conn):
    ctl.press(KeyCode.UP)
    assert conn.commands == ["input keyevent 19"]


def test_send_text_command(ctl, conn):
    r = ctl.send_text("it's")
    assert conn.commands == ["input text 'it'\\''s'"]
    assert r == SendTextResult(sent=4, skipped="")


def test_send_text_reports_skipped(ctl, conn):
    r = ctl.send_text("ação")
    assert r.skipped == "çã" and r.sent == 2
    assert conn.commands == ["input text 'ao'"]


def test_send_text_empty_sends_nothing(ctl, conn):
    assert ctl.send_text("").sent == 0
    assert conn.commands == []


def test_send_text_only_skipped_chars_sends_nothing(ctl, conn):
    r = ctl.send_text("çã")
    assert r.sent == 0 and r.skipped == "çã" and conn.commands == []


def test_volume_sends_key_and_returns_true(ctl, conn):
    assert ctl.volume(KeyCode.VOLUME_UP) is True
    assert conn.commands == ["input keyevent 24"]


def test_volume_false_on_error_output(ctl, conn):
    conn.responses["input keyevent 24"] = "Error: not supported"
    assert ctl.volume(KeyCode.VOLUME_UP) is False


def test_volume_false_on_exception_output_any_case(ctl, conn):
    conn.responses["input keyevent 164"] = "java.lang.SecurityException: x"
    assert ctl.volume(KeyCode.MUTE) is False


def test_volume_rejects_non_volume_key(ctl):
    with pytest.raises(ValueError):
        ctl.volume(KeyCode.UP)
