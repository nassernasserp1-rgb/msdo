from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import tldextract

from ..price_parser import extract_price_from_fields
from .base import SearchProviderBase


class SerpApiProvider(SearchProviderBase):
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY is required for SerpApiProvider")

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), retry=retry_if_exception_type(httpx.HTTPError))
    def search(self, query: str, shopping_only: bool = True) -> Dict:
        params = {
            "api_key": self.api_key,
            "engine": "google_shopping" if shopping_only else "google",
            "q": query,
            "hl": self.hl,
            "gl": self.gl,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    def parse_results(self, raw: Dict) -> List[Dict]:
        results: List[Dict] = []
        for item in raw.get("shopping_results", []) or []:
            link = item.get("link")
            domain = tldextract.extract((link or "")).registered_domain
            price = item.get("extracted_price")
            currency = item.get("currency")
            if price is None:
                price, currency = extract_price_from_fields(item.get("price"))
            results.append({
                "domain": domain or None,
                "price": price,
                "currency": currency,
                "link": link,
                "source_type": "shopping",
            })

        # Organic fallback
        for item in raw.get("organic_results", []) or []:
            link = item.get("link")
            domain = tldextract.extract((link or "")).registered_domain
            price, currency = extract_price_from_fields(item.get("snippet"))
            if price is None:
                continue
            results.append({
                "domain": domain or None,
                "price": price,
                "currency": currency,
                "link": link,
                "source_type": "organic",
            })

        cleaned = [r for r in results if r.get("price") is not None and r.get("domain")]
        return cleaned
