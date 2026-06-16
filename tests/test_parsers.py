from fb_notion_property_logger.parsers import extract_property_details, extract_urls, make_title


def test_extract_urls() -> None:
    text = "詳細 https://example.com/a。 画像: https://example.com/b.jpg"
    assert extract_urls(text) == ["https://example.com/a", "https://example.com/b.jpg"]


def test_extract_property_details_japanese_post() -> None:
    text = "東京都渋谷区。1LDK、賃料18万円、45㎡、渋谷駅徒歩8分。ペット相談、内見可。"
    details = extract_property_details(text)
    assert details["price"] == "18万円"
    assert details["location"].startswith("東京都渋谷区")
    assert details["station"] == "渋谷駅徒歩8分"
    assert details["size"] == "45㎡"
    assert details["layout"] == "1LDK"
    assert "pet_friendly" in details["features"]
    assert "viewing_available" in details["features"]


def test_make_title_uses_details() -> None:
    details = {"location": "東京都渋谷区", "layout": "1LDK", "price": "18万円"}
    assert make_title("body", details, "https://example.com") == "東京都渋谷区 / 1LDK / 18万円"
