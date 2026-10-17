"""Tema escuro, no estilo das telas de referência."""

BG = "#0b0b0d"
PANEL = "#17181b"
PANEL_BORDER = "#26272b"
TEXT = "#e8e8ea"
MUTED = "#8b8d93"
ACCENT = "#3b82f6"
ERROR = "#f87171"

STYLESHEET = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 14px; }}
QTabWidget::pane {{ border: 0; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; padding: 10px 18px;
    border-radius: 10px; margin: 4px; }}
QTabBar::tab:selected {{ background: #1c2a45; color: {ACCENT}; }}
QLineEdit {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 12px; }}
QPushButton {{ background: {PANEL}; border: 1px solid {PANEL_BORDER};
    border-radius: 10px; padding: 8px 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {MUTED}; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton[flat="true"] {{ border: 0; background: transparent; color: {ACCENT}; font-size: 16px; }}
QLabel#message {{ color: {ERROR}; }}
QLabel#help {{ color: {MUTED}; }}
QLabel#status {{ font-weight: bold; }}
"""
