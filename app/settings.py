"""Persistent user settings (small JSON file in the per-user config dir)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.localization import DEFAULT_LANGUAGE, LANGUAGES
from app.paths import config_dir


@dataclass
class Settings:
    language: str = DEFAULT_LANGUAGE
    last_folder: str = ""

    @staticmethod
    def default_path() -> Path:
        return config_dir() / "settings.json"

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or cls.default_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        lang = data.get("language")
        folder = data.get("last_folder")
        return cls(
            language=lang if lang in LANGUAGES else DEFAULT_LANGUAGE,
            last_folder=folder if isinstance(folder, str) else "",
        )

    def save(self, path: Path | None = None) -> bool:
        path = path or self.default_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False
