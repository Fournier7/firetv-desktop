from fakes import FakeConnection
from firetv.controller import Controller, parse_focus

CMD = "dumpsys window | grep mCurrentFocus"
LINE = "  mCurrentFocus=Window{abc u0 com.netflix.ninja/com.netflix.ninja.MainActivity}"


def test_parse_focus_extracts_package():
    assert parse_focus(LINE) == "com.netflix.ninja"


def test_parse_focus_none_when_no_match():
    assert parse_focus("") is None


def test_parse_focus_none_when_focus_is_null():
    assert parse_focus("  mCurrentFocus=null") is None


def test_current_app_runs_dumpsys_and_parses():
    conn = FakeConnection()
    conn.connect("192.168.0.10")
    conn.responses[CMD] = LINE
    assert Controller(conn).current_app() == "com.netflix.ninja"
    assert conn.commands == [CMD]
