from __future__ import annotations

from typing import Literal

from .base import SearchProviderBase
from .serper import SerperProvider
from .serpapi import SerpApiProvider


def get_provider(name: Literal["serper", "serpapi"], **kwargs) -> SearchProviderBase:
    if name == "serper":
        return SerperProvider(**kwargs)
    if name == "serpapi":
        return SerpApiProvider(**kwargs)
    raise ValueError(f"Unknown provider: {name}")
