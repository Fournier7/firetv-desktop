import pytest
from PySide6.QtCore import QPoint, Qt

from fakes import FakeConnection
from firetv.config import AppConfig
from firetv.keys import KeyCode
from firetv.session import Session
from firetv.ui.widgets import AudioCard, Card, DPad, TvCard

MSG_VOLUME = "O volume não respondeu neste aparelho. Este recurso é experimental."
MSG_LOST = "Sem conexão com o Stick. Conecte na aba Ajustes."
MSG_NONE = "Volume indisponível: depende do controle físico da TV."


@pytest.fixture
def env():
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    session.connect("192.168.0.10")
    return conn, session


def make_audio(qtbot, session, cfg):
    card = AudioCard(session, cfg)
    qtbot.addWidget(card)
    return card


def test_card_has_object_name_and_optional_title(qtbot):
    card = Card("Teclado")
    untitled = Card()
    qtbot.addWidget(card)
    qtbot.addWidget(untitled)
    assert card.objectName() == "card"
    assert card.title_label.text() == "TECLADO" and not card.title_label.isHidden()
    assert untitled.title_label.isHidden()


def test_dpad_key_at_center_and_four_sectors(qapp):
    dpad = DPad()
    assert dpad.key_at(QPoint(100, 100)) == KeyCode.OK
    assert dpad.key_at(QPoint(100, 136)) == KeyCode.OK  # borda exata do centro (36%)
    assert dpad.key_at(QPoint(100, 15)) == KeyCode.UP
    assert dpad.key_at(QPoint(185, 100)) == KeyCode.RIGHT
    assert dpad.key_at(QPoint(100, 185)) == KeyCode.DOWN
    assert dpad.key_at(QPoint(15, 100)) == KeyCode.LEFT
    assert dpad.key_at(QPoint(100, 140)) == KeyCode.DOWN


def test_dpad_outside_circle_is_none(qapp):
    dpad = DPad()
    assert dpad.key_at(QPoint(2, 2)) is None
    assert dpad.key_at(QPoint(199, 199)) is None
    assert dpad.key_at(QPoint(-5, 100)) is None


def test_dpad_has_fixed_size(qapp):
    assert DPad().size().width() == 200 and DPad().size().height() == 200


def test_dpad_click_emits_pressed(qtbot):
    dpad = DPad()
    qtbot.addWidget(dpad)
    with qtbot.waitSignal(dpad.pressed, timeout=1000) as blocker:
        qtbot.mouseClick(dpad, Qt.LeftButton, pos=QPoint(100, 15))
    assert blocker.args == [KeyCode.UP]
    with qtbot.waitSignal(dpad.pressed, timeout=1000) as blocker:
        qtbot.mouseClick(dpad, Qt.LeftButton, pos=QPoint(100, 100))
    assert blocker.args == [KeyCode.OK]


def test_dpad_click_outside_circle_emits_nothing(qtbot):
    dpad = DPad()
    qtbot.addWidget(dpad)
    with qtbot.assertNotEmitted(dpad.pressed):
        qtbot.mouseClick(dpad, Qt.LeftButton, pos=QPoint(2, 2))


def test_dpad_set_accent_does_not_break(qtbot):
    dpad = DPad()
    qtbot.addWidget(dpad)
    dpad.set_accent("#E50914")
    dpad.grab()  # força o desenho


def test_audio_card_default_method_is_keyevent(qtbot, env):
    conn, session = env
    card = make_audio(qtbot, session, AppConfig())
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: "input keyevent 24" in conn.commands, timeout=3000)
    card.vol_down_button.click()
    card.mute_button.click()
    qtbot.waitUntil(lambda: {"input keyevent 25", "input keyevent 164"} <= set(conn.commands), timeout=3000)


def test_audio_card_sends_configured_method(qtbot, env):
    conn, session = env
    card = make_audio(qtbot, session, AppConfig(volume_method="media_session"))
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: "cmd media_session volume --show --adj raise" in conn.commands, timeout=3000)


def test_audio_card_none_hides_buttons_and_shows_message(qtbot, env):
    _, session = env
    card = make_audio(qtbot, session, AppConfig(volume_method="none"))
    assert all(b.isHidden() for b in (card.vol_down_button, card.mute_button, card.vol_up_button))
    assert not card.none_label.isHidden() and card.none_label.text() == MSG_NONE


def test_audio_card_refresh_picks_up_new_method(qtbot, env):
    conn, session = env
    cfg = AppConfig()
    card = make_audio(qtbot, session, cfg)
    cfg.volume_method = "none"
    card.refresh()
    assert card.vol_up_button.isHidden() and not card.none_label.isHidden()
    cfg.volume_method = "keyboard"
    card.refresh()
    assert not card.vol_up_button.isHidden() and card.none_label.isHidden()
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: "input keyboard keyevent 24" in conn.commands, timeout=3000)


def test_audio_card_unknown_method_in_config_falls_back_to_keyevent(qtbot, env):
    conn, session = env
    card = make_audio(qtbot, session, AppConfig(volume_method="inventado"))
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: "input keyevent 24" in conn.commands, timeout=3000)


def test_audio_card_failure_shows_notice_and_success_clears_it(qtbot, env):
    conn, session = env
    card = make_audio(qtbot, session, AppConfig())
    conn.responses["input keyevent 24"] = "Error: not supported"
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: card.notice_label.text() == MSG_VOLUME, timeout=3000)
    card.vol_down_button.click()
    qtbot.waitUntil(lambda: card.notice_label.text() == "", timeout=3000)


def test_audio_card_lost_connection_notice(qtbot):
    conn = FakeConnection()
    session = Session(lambda: conn, sleep=lambda s: None)
    card = make_audio(qtbot, session, AppConfig())
    card.vol_up_button.click()
    qtbot.waitUntil(lambda: card.notice_label.text() == MSG_LOST, timeout=3000)


def test_tv_card_texts(qtbot):
    card = TvCard()
    qtbot.addWidget(card)
    assert card.caption_label.text() == "AGORA NA TELA"
    assert card.name_label.text() == "Nada em primeiro plano"
    card.set_app("Netflix", "#E50914")
    assert card.name_label.text() == "Netflix"
    card.set_app(None, "#3B82F6")
    assert card.name_label.text() == "Nada em primeiro plano"
