"""Apps do Stick: tabela de conhecidos, interpretação da lista, busca, favoritos e escondidos."""
from __future__ import annotations

from dataclasses import dataclass

from firetv.config import AppConfig

UNKNOWN_COLOR = "#6B7280"

# pacote -> (nome, cor). Sem logos oficiais: só nome e cor.
KNOWN_APPS: dict[str, tuple[str, str]] = {
    "com.netflix.ninja": ("Netflix", "#E50914"),
    "com.amazon.firetv.youtube": ("YouTube", "#FF0000"),
    "com.amazon.avod": ("Prime Video", "#00A8E1"),
    "com.disney.disneyplus": ("Disney+", "#113CCF"),
}


@dataclass
class AppEntry:
    package: str
    name: str
    color: str
    favorite: bool
    hidden: bool


def parse_packages(output: str) -> list[str]:
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("package:") and len(line) > len("package:"):
            packages.append(line[len("package:"):])
    return packages


def build_entries(packages: list[str], cfg: AppConfig) -> list[AppEntry]:
    entries = []
    for package in packages:
        name, color = KNOWN_APPS.get(package, (package, UNKNOWN_COLOR))
        entries.append(
            AppEntry(
                package=package,
                name=name,
                color=color,
                favorite=package in cfg.favorites,
                hidden=package in cfg.hidden,
            )
        )
    return sorted(entries, key=lambda e: e.name.lower())


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
