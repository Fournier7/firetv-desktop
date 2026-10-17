"""Configuração local do app: IP do Stick, favoritos e apps escondidos."""
from __future__ import annotations

import ipaddress
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    host: str = ""
    favorites: list[str] = field(default_factory=list)
    hidden: list[str] = field(default_factory=list)


def config_dir() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home()
    return root / "firetv-desktop"


def _config_path(path: Path | None) -> Path:
    return path if path is not None else config_dir() / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    target = _config_path(path)
    if not target.exists():
        return AppConfig()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return AppConfig(
            host=str(data.get("host", "")),
            favorites=list(data.get("favorites", [])),
            hidden=list(data.get("hidden", [])),
        )
    except (ValueError, AttributeError, TypeError):
        target.replace(target.with_name(target.name + ".bak"))
        return AppConfig()


def save_config(cfg: AppConfig, path: Path | None = None) -> None:
    target = _config_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")


def validate_host(value: str) -> str:
    host = value.strip()
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        raise ValueError(f"IP inválido: {value!r}") from None
    return host
