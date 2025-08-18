from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import tldextract

from ..price_parser import extract_price_from_fields
from .base import SearchProviderBase


class SerperProvider(SearchProviderBase):
    BASE_URL = "https://google.serper.dev"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is required for SerperProvider")

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), retry=retry_if_exception_type(httpx.HTTPError))
    def search(self, query: str, shopping_only: bool = True) -> Dict:
        payload = {"q": query, "gl": self.gl, "hl": self.hl}
        url = f"{self.BASE_URL}/shopping" if shopping_only else f"{self.BASE_URL}/search"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    def parse_results(self, raw: Dict) -> List[Dict]:
        results: List[Dict] = []
        # Shopping results
        for item in raw.get("shopping", []) or raw.get("shopping_results", []) or []:
            link = item.get("link")
            domain = tldextract.extract((link or "")).registered_domain
            price, currency = extract_price_from_fields(
                str(item.get("price")).strip() if item.get("price") is not None else None,
                item.get("price_original"),
                item.get("price_fallback")
            )
            results.append({
                "domain": domain or None,
                "price": price,
                "currency": currency,
                "link": link,
                "source_type": "shopping",
            })

        # Organic fallback (sometimes includes price in snippet)
        for item in raw.get("organic", []) or raw.get("organic_results", []) or []:
            link = item.get("link")
            domain = tldextract.extract((link or "")).registered_domain
            price, currency = extract_price_from_fields(item.get("price"), item.get("snippet"))
            if price is None:
                continue
            results.append({
                "domain": domain or None,
                "price": price,
                "currency": currency,
                "link": link,
                "source_type": "organic",
            })

        # Filter invalids
        cleaned = [r for r in results if r.get("price") is not None and r.get("domain")]
        return cleaned
