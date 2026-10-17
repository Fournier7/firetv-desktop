import json
from datetime import date, timedelta

import pytest

from firetv.activity import ActivityLog
from firetv.ui.activity_tab import ActivityTab

TODAY = date(2026, 10, 15)
NETFLIX = "com.netflix.ninja"
YOUTUBE = "com.amazon.firetv.youtube"
UNKNOWN = "x.y.z"
EMPTY = "Ainda sem dados. O histórico começa a contar quando o Stick estiver conectado."
NOTE = "Histórico local. Conta o app em primeiro plano no Stick."


def make_log(tmp_path, days):
    path = tmp_path / "activity.json"
    path.write_text(json.dumps({"days": days}))
    return ActivityLog(path, today=lambda: TODAY)


def iso(offset):
    return (TODAY - timedelta(days=offset)).isoformat()


@pytest.fixture
def log(tmp_path):
    return make_log(tmp_path, {
        iso(0): {YOUTUBE: 1020, NETFLIX: 60, UNKNOWN: 30},
        iso(3): {NETFLIX: 3000},
        iso(20): {NETFLIX: 600},
    })


def make_tab(qtbot, log):
    tab = ActivityTab(log)
    qtbot.addWidget(tab)
    tab.show()
    return tab


def rows(tab):
    return [(r.name_label.text(), r.duration_label.text()) for r in tab.rows()]


def test_today_is_the_default_period_and_shows_formatted_total(qtbot, log):
    tab = make_tab(qtbot, log)
    assert tab.total_label.text() == "18 min"          # 1110 s
    assert rows(tab) == [("YouTube", "17 min"), ("Netflix", "1 min"), ("x.y.z", "30 s")]


def test_unknown_package_shows_package_name(qtbot, log):
    tab = make_tab(qtbot, log)
    assert "x.y.z" in [name for name, _ in rows(tab)]


def test_switching_period_changes_total_and_rows(qtbot, log):
    tab = make_tab(qtbot, log)
    tab.period_buttons["7d"].click()
    assert tab.total_label.text() == "1 h 08 min"      # 4110 s
    assert rows(tab)[0] == ("Netflix", "51 min")
    tab.period_buttons["30d"].click()
    assert rows(tab)[0] == ("Netflix", "1 h 01 min")   # 3660 s
    tab.period_buttons["today"].click()
    assert tab.total_label.text() == "18 min"


def test_only_the_selected_period_button_is_checked(qtbot, log):
    tab = make_tab(qtbot, log)
    assert tab.period_buttons["today"].isChecked()
    tab.period_buttons["7d"].click()
    assert tab.period_buttons["7d"].isChecked() and not tab.period_buttons["today"].isChecked()


def test_period_button_texts(qtbot, log):
    tab = make_tab(qtbot, log)
    assert {k: b.text() for k, b in tab.period_buttons.items()} == {
        "today": "Hoje", "7d": "7 dias", "30d": "30 dias"}


def test_empty_state(qtbot, tmp_path):
    tab = make_tab(qtbot, make_log(tmp_path, {}))
    assert not tab.empty_label.isHidden() and tab.empty_label.text() == EMPTY
    assert tab.rows() == [] and tab.total_label.text() == "0 s"


def test_empty_state_hides_when_there_is_data(qtbot, log):
    tab = make_tab(qtbot, log)
    assert tab.empty_label.isHidden()


def test_footer_note(qtbot, log):
    assert make_tab(qtbot, log).note_label.text() == NOTE


def test_bars_are_proportional_to_the_largest(qtbot, log):
    tab = make_tab(qtbot, log)
    widths = [r.bar_fraction for r in tab.rows()]
    assert widths[0] == pytest.approx(1.0)
    assert widths[1] == pytest.approx(60 / 1020, rel=1e-3)
    assert all(0 < w <= 1 for w in widths)


def test_refresh_picks_up_new_samples(qtbot, log):
    tab = make_tab(qtbot, log)
    log.record(NETFLIX, 100.0)
    log.record(NETFLIX, 108.0)
    tab.refresh()
    assert dict(rows(tab))["Netflix"] == "1 min"  # 60 + 8 = 68 s


def test_showing_the_tab_refreshes_it(qtbot, log):
    tab = make_tab(qtbot, log)
    tab.hide()
    log.record(UNKNOWN, 100.0)
    log.record(UNKNOWN, 110.0)
    tab.show()
    assert dict(rows(tab))["x.y.z"] == "40 s"


def test_total_label_uses_the_themed_object_name(qtbot, log):
    assert make_tab(qtbot, log).total_label.objectName() == "total"
