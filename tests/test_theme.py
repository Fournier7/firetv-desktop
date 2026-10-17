import pytest

from firetv.apps import KNOWN_APPS
from firetv.ui.icons import ICON_NAMES, icon
from firetv.ui.theme import DEFAULT_ACCENT, STYLESHEET, accent_for, build_stylesheet, tint


def test_accent_for_known_unknown_and_none():
    assert accent_for("com.netflix.ninja") == KNOWN_APPS["com.netflix.ninja"][1]
    assert accent_for("x.y.z") == DEFAULT_ACCENT
    assert accent_for(None) == DEFAULT_ACCENT
    assert DEFAULT_ACCENT == "#3B82F6"


def test_stylesheet_contains_accent_and_default_constant():
    assert "#E50914" in build_stylesheet("#E50914")
    assert "#E50914" not in build_stylesheet("#00A8E1")
    assert STYLESHEET == build_stylesheet(DEFAULT_ACCENT)


def test_stylesheet_tints_derive_from_accent():
    a = build_stylesheet("#112233")
    assert "rgba(17, 34, 51, 0.22)" in a  # fundo da aba selecionada
    assert "rgba(17, 34, 51, 0.45)" in a  # brilho dos tiles


def test_tint_format():
    assert tint("#FF0000", 0.5) == "rgba(255, 0, 0, 0.5)"
    assert tint("#3b82f6", 1) == "rgba(59, 130, 246, 1)"


@pytest.mark.parametrize("bad", ["", "red", "#FFF", "#GGGGGG"])
def test_tint_rejects_invalid_colors(bad):
    with pytest.raises(ValueError):
        tint(bad, 0.5)


def test_icon_names_listed():
    assert {"home", "remote", "apps", "activity", "settings", "back", "menu", "play_pause",
            "rewind", "forward", "volume_down", "volume_up", "mute", "star", "star_filled",
            "search"} == set(ICON_NAMES)


@pytest.mark.parametrize("name", ICON_NAMES)
def test_every_icon_renders_non_null(qapp, name):
    image = icon(name).pixmap(48, 48).toImage()
    assert not image.isNull() and image.width() == 48
    opaque = sum(1 for x in range(48) for y in range(48) if image.pixelColor(x, y).alpha() > 0)
    assert opaque > 20


def test_unknown_icon_raises():
    with pytest.raises(KeyError):
        icon("nao_existe")


def test_icon_color_changes_pixels(qapp):
    red = icon("home", "#FF0000").pixmap(48, 48).toImage()
    blue = icon("home", "#0000FF").pixmap(48, 48).toImage()
    assert red != blue
