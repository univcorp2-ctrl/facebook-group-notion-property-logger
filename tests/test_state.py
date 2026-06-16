from fb_notion_property_logger.state import ProcessedStore


def test_processed_store_marks_key(tmp_path) -> None:
    store = ProcessedStore(tmp_path / "state.sqlite3")
    assert not store.has("abc")
    store.mark_processed("abc", "https://example.com", "1", "2026-06-16", "response")
    assert store.has("abc")
    assert store.count() == 1
    store.clear()
    assert store.count() == 0
