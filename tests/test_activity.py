import json
from datetime import date, timedelta

import pytest

from firetv.activity import (
    LAUNCHER_PACKAGES,
    MAX_SAMPLE_SECONDS,
    RETENTION_DAYS,
    ActivityLog,
    format_duration,
)

TODAY = date(2026, 10, 15)
NETFLIX = "com.netflix.ninja"
YOUTUBE = "com.amazon.firetv.youtube"


def make_log(tmp_path, today=TODAY):
    clock = {"today": today}
    log = ActivityLog(tmp_path / "activity.json", today=lambda: clock["today"])
    return log, clock


def test_constants():
    assert MAX_SAMPLE_SECONDS == 10 and RETENTION_DAYS == 90
    assert "com.amazon.tv.launcher" in LAUNCHER_PACKAGES


def test_first_sample_adds_nothing(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    assert log.totals("today") == [] and log.total_seconds("today") == 0


def test_adds_elapsed_between_samples(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 103.0)
    assert log.totals("today") == [(NETFLIX, 3)]


def test_elapsed_is_capped_at_ten_seconds(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 700.0)
    assert log.totals("today") == [(NETFLIX, 10)]


def test_launcher_does_not_count_but_advances_clock(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record("com.amazon.tv.launcher", 105.0)  # 5 s no launcher: não conta
    log.record(NETFLIX, 107.0)                   # só 2 s desde a última amostra
    assert log.totals("today") == [(NETFLIX, 2)]


def test_reset_clock_makes_next_sample_add_nothing(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.reset_clock()
    log.record(NETFLIX, 105.0)
    assert log.totals("today") == []


def test_clock_going_backwards_adds_nothing(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 90.0)
    assert log.totals("today") == []
    log.record(NETFLIX, 93.0)  # o relógio segue de 90
    assert log.totals("today") == [(NETFLIX, 3)]


def test_new_day_starts_a_new_bucket(tmp_path):
    log, clock = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 105.0)
    clock["today"] = TODAY + timedelta(days=1)
    log.record(NETFLIX, 108.0)
    assert log.totals("today") == [(NETFLIX, 3)]
    assert log.totals("7d") == [(NETFLIX, 8)]


def test_totals_by_period_include_today_and_sort_desc(tmp_path):
    path = tmp_path / "activity.json"
    days = {
        TODAY.isoformat(): {NETFLIX: 60, YOUTUBE: 120},
        (TODAY - timedelta(days=6)).isoformat(): {NETFLIX: 100},   # dentro de 7d
        (TODAY - timedelta(days=7)).isoformat(): {NETFLIX: 1000},  # só em 30d
        (TODAY - timedelta(days=29)).isoformat(): {YOUTUBE: 10},   # dentro de 30d
        (TODAY - timedelta(days=30)).isoformat(): {YOUTUBE: 9999},  # fora de 30d
    }
    path.write_text(json.dumps({"days": days}))
    log = ActivityLog(path, today=lambda: TODAY)
    assert log.totals("today") == [(YOUTUBE, 120), (NETFLIX, 60)]
    assert log.totals("7d") == [(NETFLIX, 160), (YOUTUBE, 120)]
    assert log.totals("30d") == [(NETFLIX, 1160), (YOUTUBE, 130)]
    assert log.total_seconds("30d") == 1290


def test_unknown_period_raises(tmp_path):
    log, _ = make_log(tmp_path)
    with pytest.raises(ValueError):
        log.totals("1y")


def test_save_and_reload_roundtrip(tmp_path):
    log, _ = make_log(tmp_path)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 104.0)
    log.save()
    again = ActivityLog(tmp_path / "activity.json", today=lambda: TODAY)
    assert again.totals("today") == [(NETFLIX, 4)]


def test_old_days_are_pruned_on_save_and_load(tmp_path):
    path = tmp_path / "activity.json"
    old = (TODAY - timedelta(days=RETENTION_DAYS + 1)).isoformat()
    edge = (TODAY - timedelta(days=RETENTION_DAYS)).isoformat()
    path.write_text(json.dumps({"days": {old: {NETFLIX: 5}, edge: {NETFLIX: 7}}}))
    log = ActivityLog(path, today=lambda: TODAY)
    log.save()
    saved = json.loads(path.read_text())["days"]
    assert old not in saved and edge in saved


def test_corrupt_file_becomes_bak_and_starts_empty(tmp_path):
    path = tmp_path / "activity.json"
    path.write_text("{ruim")
    log = ActivityLog(path, today=lambda: TODAY)
    assert log.totals("30d") == []
    assert (tmp_path / "activity.json.bak").read_text() == "{ruim"


def test_wrong_shape_becomes_bak_and_starts_empty(tmp_path):
    path = tmp_path / "activity.json"
    path.write_text("[1, 2, 3]")
    assert ActivityLog(path, today=lambda: TODAY).totals("30d") == []
    assert (tmp_path / "activity.json.bak").exists()


def test_invalid_day_keys_and_values_are_ignored(tmp_path):
    path = tmp_path / "activity.json"
    days = {
        "ontem": {NETFLIX: 10},
        "2026-13-45": {NETFLIX: 10},
        TODAY.isoformat(): {NETFLIX: 30, YOUTUBE: -5, "x.y": "muito", "a.b": True, "c.d": float("nan")},
    }
    path.write_text(json.dumps({"days": days}, allow_nan=True))
    log = ActivityLog(path, today=lambda: TODAY)
    assert log.totals("30d") == [(NETFLIX, 30)]


def test_save_creates_missing_folder(tmp_path):
    path = tmp_path / "pasta" / "nova" / "activity.json"
    log = ActivityLog(path, today=lambda: TODAY)
    log.save()
    assert path.exists()


@pytest.mark.parametrize(
    "seconds, text",
    [(0, "0 s"), (42, "42 s"), (59, "59 s"), (60, "1 min"), (3060, "51 min"), (3600, "1 h 00 min"), (3900, "1 h 05 min")],
)
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text
