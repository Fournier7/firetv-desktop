"""Tema escuro com cor de destaque que muda conforme o app em execução."""
from __future__ import annotations

from firetv.apps import KNOWN_APPS

BG = "#0b0b0d"
PANEL = "#17181b"
PANEL_BORDER = "#26272b"
TEXT = "#e8e8ea"
MUTED = "#8b8d93"
ERROR = "#f87171"
DEFAULT_ACCENT = "#3B82F6"
ACCENT = DEFAULT_ACCENT  # nome antigo, mantido enquanto as telas são refeitas


def accent_for(package: str | None) -> str:
    if package is None:
        return DEFAULT_ACCENT
    return KNOWN_APPS.get(package, ("", DEFAULT_ACCENT))[1]


def tint(color: str, alpha: float) -> str:
    """'#RRGGBB' + transparência -> 'rgba(r, g, b, a)'."""
    if len(color) != 7 or not color.startswith("#"):
        raise ValueError(f"cor inválida: {color!r}")
    try:
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        raise ValueError(f"cor inválida: {color!r}") from None
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def build_stylesheet(accent: str) -> str:
    selected = tint(accent, 0.22)
    glow = tint(accent, 0.45)
    return f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 14px; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {PANEL_BORDER}; border-radius: 14px; }}
QFrame#card QLabel {{ background: transparent; }}
QTabWidget::pane {{ border: 0; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; padding: 10px 18px;
    border-radius: 10px; margin: 4px; }}
QTabBar::tab:selected {{ background: {selected}; color: {accent}; }}
QToolButton#tab {{ background: transparent; border: 0; border-radius: 10px; padding: 8px; }}
QToolButton#tab:hover {{ background: {PANEL}; }}
QToolButton#tab:checked {{ background: {selected}; }}
QLineEdit {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 12px; }}
QLineEdit:focus {{ border-color: {accent}; }}
QPushButton {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 14px; }}
QPushButton:hover {{ border-color: {accent}; }}
QPushButton:checked {{ background: {selected}; border-color: {accent}; color: {accent}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {MUTED}; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QPushButton[flat="true"] {{ border: 0; background: transparent; color: {accent}; font-size: 16px; }}
QFrame#bar {{ background: {accent}; border-radius: 3px; }}
QFrame#glow {{ border: 1px solid {glow}; border-radius: 14px; }}
QLabel#message {{ color: {ERROR}; }}
QLabel#help {{ color: {MUTED}; }}
QLabel#status {{ font-weight: bold; }}
"""


STYLESHEET = build_stylesheet(DEFAULT_ACCENT)
