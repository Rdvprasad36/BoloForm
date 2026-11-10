"""Settings from environment variables (and an optional .env file). No extra dependencies."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if not v.startswith(("{", '"')) and "  #" in v:      # strip inline comments (not inside JSON)
            v = v.split("  #", 1)[0].strip()
        os.environ.setdefault(k.strip(), v)


ROOT = Path(__file__).resolve().parent.parent
_load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    provider: str = "mock"
    debug: bool = False
    confirm_policy: str = "adaptive"
    max_audio_bytes: int = 2_000_000
    max_turns_per_session: int = 200

    @staticmethod
    def load() -> "Settings":
        return Settings(
            provider=os.environ.get("PROVIDER", "mock").strip().lower(),
            debug=os.environ.get("DEBUG", "0").strip() == "1",
            confirm_policy=os.environ.get("CONFIRM_POLICY", "adaptive").strip().lower(),
        )
