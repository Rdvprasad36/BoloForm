from __future__ import annotations

from ..config import Settings
from .base import Provider


def get_provider(settings: Settings) -> Provider:
    if settings.provider == "gnani":
        from .gnani import GnaniProvider
        return GnaniProvider()
    from .mock import MockProvider
    return MockProvider()
