from __future__ import annotations

import re
from typing import Optional, Tuple


_ARABIC_INDIC_DIGITS = str.maketrans({
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
})


def normalize_digits(text: str) -> str:
    if not text:
        return text
    return text.translate(_ARABIC_INDIC_DIGITS)


def detect_currency(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["egp", "جنيه", "ج.م", "جنيه مصري", "جنيه مصرى", "ج م"]):
        return "EGP"
    if any(k in t for k in ["sar", "ريال سعودي", "ريال سعودى"]):
        return "SAR"
    if any(k in t for k in ["aed", "درهم", "درهم إماراتي", "درهم اماراتي"]):
        return "AED"
    if any(k in t for k in ["usd", "$", "دولار"]):
        return "USD"
    return None


_PRICE_REGEX = re.compile(r"(\d{1,3}(?:[,\s]\d{3})*(?:[\.\,]\d+)?|\d+(?:[\.\,]\d+)?)")


def parse_price_string(text: str) -> Tuple[Optional[float], Optional[str]]:
    if not text:
        return None, None
    normalized = normalize_digits(text)
    currency = detect_currency(normalized)
    # Remove thousand separators like "," or narrow spaces
    m = _PRICE_REGEX.search(normalized)
    if not m:
        return None, currency
    num = m.group(1)
    num = num.replace(",", "").replace(" ", "")
    num = num.replace("٫", ".").replace("،", ".")
    try:
        value = float(num)
    except ValueError:
        return None, currency
    return value, currency


def extract_price_from_fields(*fields: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    for field in fields:
        price, currency = parse_price_string(field or "")
        if price is not None:
            return price, currency
    return None, None
