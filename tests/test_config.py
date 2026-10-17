import pytest

from firetv.config import AppConfig, load_config, save_config, validate_host


def test_config_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(host="192.168.0.10", favorites=["a.b"], hidden=["c.d"])
    save_config(cfg, path)
    assert load_config(path) == cfg


def test_load_missing_returns_defaults(tmp_path):
    assert load_config(tmp_path / "config.json") == AppConfig()


def test_load_corrupt_returns_defaults_and_keeps_bak(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ruim")
    assert load_config(path) == AppConfig()
    assert (tmp_path / "config.json.bak").read_text() == "{ruim"


def test_defaults_are_not_shared():
    a, b = AppConfig(), AppConfig()
    a.favorites.append("x")
    assert b.favorites == []


def test_validate_host():
    assert validate_host(" 192.168.0.10 ") == "192.168.0.10"
    for ruim in ["", "abc", "999.1.1.1", "192.168.0"]:
        with pytest.raises(ValueError):
            validate_host(ruim)
