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


def test_new_fields_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(host="10.0.0.5", tv_name="Sala", volume_method="keyboard")
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded == cfg and loaded.tv_name == "Sala" and loaded.volume_method == "keyboard"


def test_new_field_defaults():
    cfg = AppConfig()
    assert cfg.tv_name == "Fire TV" and cfg.volume_method == ""


def test_old_file_without_new_fields_loads_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"host": "1.1.1.1", "favorites": ["a.b"], "hidden": []}', encoding="utf-8")
    cfg = load_config(path)
    assert cfg.host == "1.1.1.1" and cfg.favorites == ["a.b"]
    assert cfg.tv_name == "Fire TV" and cfg.volume_method == ""


@pytest.mark.parametrize("raw", ['""', '"   "', "null"])
def test_blank_or_null_tv_name_becomes_default(tmp_path, raw):
    path = tmp_path / "config.json"
    path.write_text('{"tv_name": %s}' % raw, encoding="utf-8")
    assert load_config(path).tv_name == "Fire TV"


def test_null_host_becomes_empty_string(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"host": null, "volume_method": null}', encoding="utf-8")
    cfg = load_config(path)
    assert cfg.host == "" and cfg.volume_method == ""
