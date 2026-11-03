"""Tema escuro com cor de destaque que muda conforme o app em execução."""
from __future__ import annotations

from firetv.apps import KNOWN_APPS

BG = "#0D1119"
PANEL = "#151C28"
PANEL_BORDER = "#293346"
TEXT = "#EDF2FA"
MUTED = "#A1ADC1"
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
QWidget {{ background: {BG}; color: {TEXT}; font-family: 'Segoe UI'; font-size: 14px; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {PANEL_BORDER}; border-radius: 14px; }}
QFrame#card QLabel {{ background: transparent; }}
QLabel#connectionTitle {{ font-size: 15px; font-weight: 600; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {PANEL_BORDER}; padding: 6px; }}
QScrollArea {{ border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {PANEL_BORDER}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QTabWidget::pane {{ border: 0; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; padding: 10px 18px;
    border-radius: 10px; margin: 4px; }}
QTabBar::tab:selected {{ background: {selected}; color: {accent}; }}
QToolButton#tab {{ background: transparent; border: 0; border-radius: 10px; padding: 6px; font-size: 12px; color: {MUTED}; }}
QToolButton#tab:hover {{ background: {PANEL}; }}
QToolButton#tab:checked {{ background: {selected}; color: {TEXT}; }}
QToolButton#tab:focus {{ border: 1px solid {accent}; }}
QLineEdit {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 12px; }}
QLineEdit:focus {{ border-color: {accent}; }}
QPushButton {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 14px; }}
QPushButton:hover {{ border-color: {accent}; background: {selected}; }}
QPushButton:pressed {{ background: {glow}; border-color: {accent}; }}
QPushButton:focus {{ border-color: {accent}; }}
QPushButton#primary {{ background: {selected}; border-color: {accent}; font-weight: 600; }}
QPushButton:checked {{ background: {selected}; border-color: {accent}; color: {accent}; }}
QPushButton:disabled {{ color: #667286; border-color: {PANEL_BORDER}; background: {BG}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {MUTED}; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QPushButton[flat="true"] {{ border: 0; background: transparent; color: {accent}; font-size: 13px; }}
QFrame#bar {{ background: {accent}; border-radius: 3px; }}
QFrame#glow {{ border: 1px solid {glow}; border-radius: 14px; }}
QLabel#total {{ font-size: 34px; font-weight: bold; color: {accent}; }}
QLabel#message {{ color: {ERROR}; }}
QLabel#help {{ color: {MUTED}; font-size: 12px; }}
QLabel#status {{ font-weight: bold; }}
"""


STYLESHEET = build_stylesheet(DEFAULT_ACCENT)
