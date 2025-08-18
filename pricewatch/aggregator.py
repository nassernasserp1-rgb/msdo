from __future__ import annotations

import statistics
from typing import Dict, Iterable, List, Optional

import tldextract


def median_market_price(items: List[Dict]) -> Optional[float]:
    prices = [float(r["price"]) for r in items if r.get("price") is not None]
    if not prices:
        return None
    prices.sort()
    # Use median of top-k if many results (trim extremes)
    k = min(8, len(prices))
    trimmed = prices[:k]
    return statistics.median(trimmed)


def select_target_merchants(items: List[Dict], targets: Iterable[str]) -> List[Dict]:
    target_domains = {tldextract.extract(t).registered_domain for t in targets}
    out: List[Dict] = []
    seen = set()
    for r in items:
        d = r.get("domain")
        if d in target_domains and d not in seen and r.get("price") is not None:
            out.append({"domain": d, "price": float(r["price"]), "link": r.get("link")})
            seen.add(d)
    return out


def annotate_discounts(targets: List[Dict], market_median: Optional[float]) -> List[Dict]:
    if not market_median:
        return targets
    enriched: List[Dict] = []
    for t in targets:
        price = float(t["price"])
        discount_pct = round(max(0.0, (market_median - price) / market_median * 100.0), 2)
        enriched.append({**t, "discount_pct_vs_median": discount_pct})
    return enriched
