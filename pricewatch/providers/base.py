from __future__ import annotations

import abc
from typing import Dict, Iterable, List, Optional


class SearchProviderBase(abc.ABC):
    def __init__(self, hl: str = "ar", gl: str = "eg", timeout_seconds: int = 30):
        self.hl = hl
        self.gl = gl
        self.timeout_seconds = timeout_seconds

    @abc.abstractmethod
    def search(self, query: str, shopping_only: bool = True) -> Dict:
        raise NotImplementedError

    @abc.abstractmethod
    def parse_results(self, raw: Dict) -> List[Dict]:
        """Normalize results to a list of {domain, price, currency, link, source_type}."""
        raise NotImplementedError

    def batch_search(self, queries: Iterable[str], shopping_only: bool = True) -> List[List[Dict]]:
        return [self.parse_results(self.search(q, shopping_only=shopping_only)) for q in queries]
