from __future__ import annotations

import re
from typing import Any

URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")
WHITESPACE_RE = re.compile(r"\s+")

PRICE_PATTERNS = [
    re.compile(r"(?:賃料|家賃|価格|売価|販売価格|売買価格)[:：\s]*([¥￥]?[0-9,.]+\s*(?:万円|万|円)?)"),
    re.compile(r"([¥￥][0-9,.]+\s*(?:万円|万|円)?)"),
]
LOCATION_PATTERNS = [
    re.compile(r"(?:住所|所在地|エリア|場所)[:：\s]*([^\n。]+)"),
    re.compile(r"((?:東京都|神奈川県|千葉県|埼玉県|大阪府|京都府|兵庫県|福岡県)[^\n、。]*)"),
]
STATION_PATTERNS = [
    re.compile(r"(?:最寄り駅|最寄駅|駅)[:：\s]*([^\n。]+)"),
    re.compile(r"([^\n、。]{1,20}駅\s*(?:徒歩|歩)[0-9０-９]+分)"),
]
SIZE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?\s*(?:㎡|m2|m²|平米|坪))", re.IGNORECASE)
LAYOUT_RE = re.compile(r"\b([1-9][0-9]?\s*(?:R|K|DK|LDK|SLDK))\b", re.IGNORECASE)

FEATURE_KEYWORDS = {
    "pet_friendly": ["ペット可", "ペット相談", "犬可", "猫可"],
    "parking": ["駐車場", "P有", "パーキング"],
    "furnished": ["家具付き", "家電付き", " furnished"],
    "renovated": ["リノベ", "リフォーム済", "新築", "築浅"],
    "viewing_available": ["内見可", "見学可", "即内見"],
}


def normalize_whitespace(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def extract_urls(text: str) -> list[str]:
    return [url.rstrip(".,、。") for url in URL_RE.findall(text or "")]


def first_match(patterns: list[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return normalize_whitespace(match.group(1))
    return None


def extract_property_details(text: str) -> dict[str, Any]:
    """Extract common Japanese real-estate fields from a post body.

    This is intentionally rule-based and transparent. It is not a legal or valuation parser.
    """
    normalized = normalize_whitespace(text)
    details: dict[str, Any] = {
        "price": first_match(PRICE_PATTERNS, text),
        "location": first_match(LOCATION_PATTERNS, text),
        "station": first_match(STATION_PATTERNS, text),
    }

    size_match = SIZE_RE.search(normalized)
    layout_match = LAYOUT_RE.search(normalized)
    details["size"] = normalize_whitespace(size_match.group(1)) if size_match else None
    details["layout"] = normalize_whitespace(layout_match.group(1).upper()) if layout_match else None

    features: list[str] = []
    lower_text = normalized.lower()
    for feature, keywords in FEATURE_KEYWORDS.items():
        if any(keyword.lower() in lower_text for keyword in keywords):
            features.append(feature)
    details["features"] = features

    return {key: value for key, value in details.items() if value not in (None, "", [])}


def make_title(content: str, details: dict[str, Any], fallback_url: str) -> str:
    parts = []
    for key in ("location", "layout", "price"):
        value = details.get(key)
        if value:
            parts.append(str(value))
    if parts:
        return " / ".join(parts)[:120]
    text = normalize_whitespace(content)
    if text:
        return text[:80]
    return fallback_url[:120] if fallback_url else "Untitled property post"
