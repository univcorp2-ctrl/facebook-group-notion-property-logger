from __future__ import annotations

from typing import Any

import pytest

from fb_notion_property_logger.facebook_api import (
    FacebookApiError,
    build_group_probe_urls,
    fetch_group_feed,
    graph_get,
    graph_posts_to_source_payload,
    normalize_group_id,
    probe_group_api,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


def test_normalize_group_id_accepts_url() -> None:
    assert normalize_group_id("https://www.facebook.com/groups/1281008662437696") == "1281008662437696"


def test_build_group_probe_urls_contains_group_id() -> None:
    urls = build_group_probe_urls("1281008662437696", "v23.0")
    assert "1281008662437696" in urls["group_metadata"]
    assert "feed" in urls["group_feed"]


def test_probe_group_api_without_token_returns_actionable_errors() -> None:
    probes = probe_group_api("1281008662437696", None)
    assert all(probe.ok is None for probe in probes)
    assert all("FACEBOOK_ACCESS_TOKEN" in (probe.error or "") for probe in probes)


def test_graph_get_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        assert headers["Authorization"] == "Bearer token"
        return FakeResponse(200, {"data": [{"id": "1"}]})

    monkeypatch.setattr("requests.get", fake_get)
    assert graph_get("https://graph.facebook.com/v23.0/1", "token") == {"data": [{"id": "1"}]}


def test_graph_get_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        return FakeResponse(400, {"error": {"message": "Bad request"}})

    monkeypatch.setattr("requests.get", fake_get)
    with pytest.raises(FacebookApiError):
        graph_get("https://graph.facebook.com/v23.0/1", "token", max_retries=0)


def test_fetch_group_feed_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {"data": [{"id": "1", "message": "a"}], "paging": {"next": "https://next"}},
        {"data": [{"id": "2", "message": "b"}], "paging": {}},
    ]

    def fake_graph_get(url: str, access_token: str, **kwargs: Any) -> dict[str, Any]:
        return responses.pop(0)

    monkeypatch.setattr("fb_notion_property_logger.facebook_api.graph_get", fake_graph_get)
    posts = fetch_group_feed("1281008662437696", "token", max_pages=5)
    assert [post["id"] for post in posts] == ["1", "2"]


def test_graph_posts_to_source_payload_extracts_attachments() -> None:
    payload = graph_posts_to_source_payload(
        [
            {
                "id": "1",
                "message": "東京都渋谷区 1LDK",
                "permalink_url": "https://facebook.com/post/1",
                "attachments": {"data": [{"url": "https://example.com/a", "target": {"url": "https://example.com/b"}}]},
            }
        ]
    )
    post = payload["posts"][0]
    assert post["post_url"] == "https://facebook.com/post/1"
    assert post["attachments"] == ["https://example.com/a", "https://example.com/b"]
