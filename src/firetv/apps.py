"""Apps do Stick: tabela de conhecidos, interpretação da lista, busca, favoritos e escondidos."""
from __future__ import annotations

from dataclasses import dataclass

from firetv.config import AppConfig

UNKNOWN_COLOR = "#6B7280"

# pacote -> (nome, cor). Sem logos oficiais: só nome e cor. A ordem importa: quando o mesmo
# app existe com mais de um pacote, vale o primeiro da lista que estiver instalado.
KNOWN_APPS: dict[str, tuple[str, str]] = {
    "com.netflix.ninja": ("Netflix", "#E50914"),
    "com.amazon.firetv.youtube": ("YouTube", "#FF0000"),
    "com.google.android.youtube.tv": ("YouTube", "#FF0000"),
    "com.amazon.firebat": ("Prime Video", "#00A8E1"),
    "com.amazon.avod": ("Prime Video", "#00A8E1"),
    "com.amazon.avod.thirdpartyclient": ("Prime Video", "#00A8E1"),
    "com.amazon.amazonvideo.livingroom": ("Prime Video", "#00A8E1"),
    "com.disney.disneyplus": ("Disney+", "#113CCF"),
    "com.hbo.hbonow": ("HBO Max", "#7C3AED"),
    "com.wbd.stream": ("HBO Max", "#7C3AED"),
    "com.spotify.tv.android": ("Spotify", "#1DB954"),
    "com.apple.atve.amazon.appletv": ("Apple TV", "#9CA3AF"),
    "com.cbs.ott": ("Paramount+", "#0064FF"),
    "tv.pluto.android": ("Pluto TV", "#D4A017"),
    "tv.twitch.android.viewer": ("Twitch", "#9146FF"),
    "tv.twitch.android.app": ("Twitch", "#9146FF"),
    "com.globo.globotv": ("Globoplay", "#F45B39"),
    "com.kick.mobile": ("Kick", "#53FC18"),
    "com.esaba.downloader": ("Downloader", "#F59E0B"),
    "com.global.unitviptv": ("UniTV", "#06B6D4"),
    "com.amazon.bueller.music": ("Amazon Music", "#25D1DA"),
}
_KNOWN_ORDER = {package: index for index, package in enumerate(KNOWN_APPS)}
STREAMING_NAMES = {
    "Netflix", "YouTube", "Prime Video", "Disney+", "HBO Max", "Globoplay",
    "Spotify", "Apple TV", "Paramount+", "Pluto TV", "Twitch", "Kick", "Amazon Music",
}


def is_internal_package(package: str) -> bool:
    return package == "android" or package.startswith(("com.amazon.", "com.android.", "amazon."))


@dataclass
class AppEntry:
    package: str
    name: str
    color: str
    favorite: bool
    hidden: bool
    featured: bool = True  # app famoso ou instalado pelo usuário (não é do sistema)


def parse_packages(output: str) -> list[str]:
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("package:") and len(line) > len("package:"):
            packages.append(line[len("package:"):])
    return packages


def build_entries(
    packages: list[str], cfg: AppConfig, third_party: set[str] | None = None
) -> list[AppEntry]:
    """Monta as entradas. `third_party` são os pacotes instalados pelo usuário; sem ele
    (None), preserva os desconhecidos, mas omite componentes internos do destaque."""
    ordered = sorted(dict.fromkeys(packages), key=lambda p: _KNOWN_ORDER.get(p, len(_KNOWN_ORDER)))
    seen_known: set[str] = set()
    entries = []
    for package in ordered:
        known = package in KNOWN_APPS
        name, color = KNOWN_APPS.get(package, (package, UNKNOWN_COLOR))
        if known:
            if name in seen_known:  # mesmo app com outro pacote: fica só o primeiro da lista
                continue
            seen_known.add(name)
        entries.append(
            AppEntry(
                package=package,
                name=name,
                color=color,
                favorite=package in cfg.favorites,
                hidden=package in cfg.hidden,
                featured=known or (not is_internal_package(package) and
                                   (third_party is None or package in third_party)),
            )
        )
    return sorted(entries, key=lambda e: e.name.lower())


def streaming_suggestions(installed: list[AppEntry]) -> list[AppEntry]:
    names = {entry.name for entry in installed}
    suggestions = []
    for package, (name, color) in KNOWN_APPS.items():
        if name in STREAMING_NAMES and name not in names:
            names.add(name)
            suggestions.append(AppEntry(package, name, color, False, False))
    return sorted(suggestions, key=lambda entry: entry.name.lower())


def search(entries: list[AppEntry], query: str) -> list[AppEntry]:
    q = query.strip().lower()
    if not q:
        return list(entries)
    return [e for e in entries if q in e.name.lower() or q in e.package.lower()]


def _toggle(items: list[str], package: str) -> None:
    if package in items:
        items.remove(package)
    else:
        items.append(package)


def toggle_favorite(cfg: AppConfig, package: str) -> None:
    _toggle(cfg.favorites, package)


def toggle_hidden(cfg: AppConfig, package: str) -> None:
    _toggle(cfg.hidden, package)
