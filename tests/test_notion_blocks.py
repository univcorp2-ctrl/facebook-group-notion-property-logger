from fb_notion_property_logger.models import SourcePost
from fb_notion_property_logger.notion import build_notion_blocks, chunk_text


def test_build_notion_blocks_contains_url_and_details() -> None:
    post = SourcePost(
        id="1",
        url="https://facebook.com/groups/x/posts/y/",
        content="東京都渋谷区。1LDK 賃料18万円 45㎡ 渋谷駅徒歩8分",
    )
    title, details, blocks = build_notion_blocks(post)
    assert "東京都渋谷区" in title
    assert details["price"] == "18万円"
    assert any(block["type"] == "heading_2" for block in blocks)
    assert any("投稿URL" in str(block) for block in blocks)


def test_chunk_text_splits_large_content() -> None:
    chunks = chunk_text("a" * 4500, size=2000)
    assert [len(chunk) for chunk in chunks] == [2000, 2000, 500]
