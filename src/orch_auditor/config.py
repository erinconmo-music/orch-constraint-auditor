# src/orch_auditor/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "default_config.yaml"


@dataclass
class Config:
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(raw=data)

    def get_enabled_checks(self) -> List[str]:
        return list(self.raw.get("checks", {}).get("enabled", []))

    def ranges_for_part(self, part_id: str) -> Optional[Dict[str, Any]]:
        return self.raw.get("ranges", {}).get(part_id)

    @property
    def bass_pitch_mode(self) -> str:
        return self.raw.get("bass_pitch_mode", "written")
