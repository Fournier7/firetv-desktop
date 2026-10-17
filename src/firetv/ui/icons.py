"""Ícones SVG embutidos no código (o .exe continua sendo um arquivo só)."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_SPEAKER = '<path d="M4 9h4l5-4v14l-5-4H4z"/>'
_STAR = '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>'

_BODIES = {
    "home": '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "remote": '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
    "apps": ('<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/>'
             '<rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/>'
             '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/>'
             '<rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>'),
    "activity": '<path d="M5 20V10M10 20V4M15 20v-8M20 20V7"/>',
    "settings": ('<path d="M4 7h8M18 7h2M4 17h2M12 17h8"/>'
                 '<circle cx="15" cy="7" r="2.2"/><circle cx="9" cy="17" r="2.2"/>'),
    "back": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "play_pause": '<path d="M5 4l9 8-9 8z"/><path d="M18 5v14"/>',
    "rewind": '<path d="M11 6l-8 6 8 6z"/><path d="M21 6l-8 6 8 6z"/>',
    "forward": '<path d="M13 6l8 6-8 6z"/><path d="M3 6l8 6-8 6z"/>',
    "volume_down": _SPEAKER + '<path d="M16 9.5a4 4 0 0 1 0 5"/>',
    "volume_up": _SPEAKER + '<path d="M16 9.5a4 4 0 0 1 0 5"/><path d="M18.5 7a8 8 0 0 1 0 10"/>',
    "mute": _SPEAKER + '<path d="M17 9l5 6M22 9l-5 6"/>',
    "star": _STAR,
    "star_filled": _STAR,
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>',
}

ICON_NAMES = tuple(_BODIES)


def icon(name: str, color: str = "#E8E8EA") -> QIcon:
    body = _BODIES[name]  # nome desconhecido levanta KeyError
    fill = color if name == "star_filled" else "none"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
