import pytest

from fakes import FakeConnection
from firetv.apps import (
    AppEntry,
    build_entries,
    parse_packages,
    search,
    toggle_favorite,
    toggle_hidden,
)
from firetv.config import AppConfig
from firetv.controller import Controller

PM = "pm list packages"


def test_parse_packages():
    assert parse_packages("package:a.b\npackage:c.d\n") == ["a.b", "c.d"]


def test_parse_packages_ignores_noise_and_blank_lines():
    assert parse_packages("\nlixo\r\npackage:a.b\r\n\n") == ["a.b"]


def test_known_package_gets_name_and_color():
    [e] = build_entries(["com.netflix.ninja"], AppConfig())
    assert (e.name, e.color) == ("Netflix", "#E50914")


def test_unknown_package_uses_package_as_name():
    [e] = build_entries(["x.y.z"], AppConfig())
    assert (e.name, e.color) == ("x.y.z", "#6B7280")


def test_entries_sorted_case_insensitive():
    names = [e.name for e in build_entries(["x.y.z", "com.netflix.ninja", "a.b.c"], AppConfig())]
    assert names == ["a.b.c", "Netflix", "x.y.z"]


def test_entries_carry_favorite_and_hidden_flags():
    cfg = AppConfig(favorites=["a.b"], hidden=["c.d"])
    by_pkg = {e.package: e for e in build_entries(["a.b", "c.d"], cfg)}
    assert by_pkg["a.b"].favorite and not by_pkg["a.b"].hidden
    assert by_pkg["c.d"].hidden and not by_pkg["c.d"].favorite


def test_search_matches_name_and_package():
    entries = build_entries(["com.netflix.ninja", "x.y.z"], AppConfig())
    assert [e.name for e in search(entries, "NETF")] == ["Netflix"]
    assert [e.name for e in search(entries, "y.z")] == ["x.y.z"]
    assert len(search(entries, "")) == 2
    assert search(entries, "nada") == []


def test_toggle_favorite_and_hidden_are_reversible():
    cfg = AppConfig()
    toggle_favorite(cfg, "a.b")
    toggle_hidden(cfg, "a.b")
    assert cfg.favorites == ["a.b"] and cfg.hidden == ["a.b"]
    toggle_favorite(cfg, "a.b")
    toggle_hidden(cfg, "a.b")
    assert cfg.favorites == [] and cfg.hidden == []


@pytest.fixture
def conn():
    c = FakeConnection()
    c.connect("192.168.0.10")
    return c


def test_list_apps_hides_hidden_by_default_and_shows_on_request(conn):
    conn.responses[PM] = "package:com.netflix.ninja\npackage:x.y.z\n"
    cfg = AppConfig(hidden=["x.y.z"])
    ctl = Controller(conn)
    assert [e.package for e in ctl.list_apps(cfg)] == ["com.netflix.ninja"]
    shown = ctl.list_apps(cfg, show_hidden=True)
    assert [e.package for e in shown] == ["com.netflix.ninja", "x.y.z"]
    assert isinstance(shown[0], AppEntry)


def test_list_apps_empty_output_returns_empty_list(conn):
    conn.responses[PM] = ""
    assert Controller(conn).list_apps(AppConfig()) == []


def test_launch_command(conn):
    Controller(conn).launch("com.netflix.ninja")
    assert conn.commands[-1] == "monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1"


@pytest.mark.parametrize("ruim", ["", "a b", "a;rm -rf /", "a$(x)", "a'b"])
def test_launch_rejects_unsafe_package_names(conn, ruim):
    with pytest.raises(ValueError):
        Controller(conn).launch(ruim)
    assert conn.commands == []
