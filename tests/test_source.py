import json

from fb_notion_property_logger.source import load_posts_from_file, normalize_record


def test_load_posts_from_json(tmp_path) -> None:
    path = tmp_path / "posts.json"
    path.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "id": "1",
                        "post_url": "https://facebook.com/groups/x/posts/y/",
                        "content": "東京都渋谷区 1LDK 賃料18万円",
                        "attachments": ["https://example.com/listing"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    posts = load_posts_from_file(path)
    assert len(posts) == 1
    assert posts[0].id == "1"
    assert posts[0].url.endswith("/y/")
    assert posts[0].attachments == ["https://example.com/listing"]


def test_load_posts_from_csv(tmp_path) -> None:
    path = tmp_path / "posts.csv"
    path.write_text(
        "id,post_url,content\n1,https://facebook.com/post,東京都渋谷区 1LDK\n",
        encoding="utf-8",
    )
    posts = load_posts_from_file(path)
    assert len(posts) == 1
    assert posts[0].content == "東京都渋谷区 1LDK"


def test_normalize_record_uses_url_from_content() -> None:
    post = normalize_record({"message": "詳細 https://example.com/property/1 東京都港区 2LDK"})
    assert post.url == "https://example.com/property/1"
    assert "東京都港区" in post.content
