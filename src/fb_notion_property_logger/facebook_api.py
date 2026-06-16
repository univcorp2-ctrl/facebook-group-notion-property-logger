from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

import requests

DEFAULT_FACEBOOK_API_VERSION = "v23.0"
DEFAULT_GROUP_ID = "1281008662437696"
GRAPH_BASE_URL = "https://graph.facebook.com"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class FacebookEndpointProbe:
    name: str
    method: str
    url: str
    status_code: int | None
    ok: bool | None
    response: dict[str, Any] | str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FacebookApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


def normalize_group_id(value: str) -> str:
    stripped = value.rstrip("/").split("/")[-1].strip()
    if not stripped:
        raise ValueError("group id is required")
    return stripped


def graph_url(api_version: str, path: str, params: dict[str, Any] | None = None) -> str:
    encoded = urlencode({k: v for k, v in (params or {}).items() if v is not None})
    base = f"{GRAPH_BASE_URL}/{api_version}/{path.lstrip('/')}"
    return f"{base}?{encoded}" if encoded else base


def build_group_probe_urls(group_id: str, api_version: str = DEFAULT_FACEBOOK_API_VERSION) -> dict[str, str]:
    gid = normalize_group_id(group_id)
    return {
        "group_metadata": graph_url(
            api_version,
            gid,
            {"fields": "id,name,privacy,link,updated_time"},
        ),
        "group_feed": graph_url(
            api_version,
            f"{gid}/feed",
            {
                "fields": "id,message,story,created_time,updated_time,permalink_url,attachments.limit(5)",
                "limit": 5,
            },
        ),
    }


def graph_get(
    url: str,
    access_token: str,
    timeout: int = 30,
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            try:
                payload: dict[str, Any] | str = response.json()
            except ValueError:
                payload = response.text
            if response.status_code < 400:
                if isinstance(payload, dict):
                    return payload
                raise FacebookApiError("Graph API returned a non-JSON success response", response.status_code, payload)
            if response.status_code not in RETRY_STATUS_CODES or attempt >= max_retries:
                raise FacebookApiError(f"Graph API error {response.status_code}", response.status_code, payload)
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries:
                raise FacebookApiError(str(exc)) from exc
        time.sleep(base_delay_seconds * (2**attempt))
    raise FacebookApiError(str(last_error or "Graph API request failed"))


def probe_group_api(
    group_id: str,
    access_token: str | None,
    api_version: str = DEFAULT_FACEBOOK_API_VERSION,
) -> list[FacebookEndpointProbe]:
    urls = build_group_probe_urls(group_id, api_version)
    probes: list[FacebookEndpointProbe] = []
    for name, url in urls.items():
        if not access_token:
            probes.append(
                FacebookEndpointProbe(
                    name=name,
                    method="GET",
                    url=url,
                    status_code=None,
                    ok=None,
                    response=None,
                    error="FACEBOOK_ACCESS_TOKEN is required to test this endpoint",
                )
            )
            continue
        try:
            payload = graph_get(url, access_token, max_retries=1, base_delay_seconds=0.1)
            probes.append(FacebookEndpointProbe(name, "GET", url, 200, True, payload))
        except FacebookApiError as exc:
            probes.append(FacebookEndpointProbe(name, "GET", url, exc.status_code, False, exc.response, str(exc)))
    return probes


def fetch_group_feed(
    group_id: str,
    access_token: str,
    api_version: str = DEFAULT_FACEBOOK_API_VERSION,
    page_size: int = 25,
    max_pages: int = 20,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    gid = normalize_group_id(group_id)
    url = graph_url(
        api_version,
        f"{gid}/feed",
        {
            "fields": "id,message,story,created_time,updated_time,permalink_url,attachments.limit(10)",
            "limit": max(1, min(page_size, 100)),
            "since": since,
            "until": until,
        },
    )
    posts: list[dict[str, Any]] = []
    page_count = 0
    while url and page_count < max_pages:
        payload = graph_get(url, access_token)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise FacebookApiError("Graph API feed response did not contain a data list", response=payload)
        posts.extend(item for item in data if isinstance(item, dict))
        next_url = payload.get("paging", {}).get("next")
        url = next_url if isinstance(next_url, str) else ""
        page_count += 1
    return posts


def _extract_attachment_urls(attachments: dict[str, Any] | None) -> list[str]:
    urls: list[str] = []
    if not attachments:
        return urls
    data = attachments.get("data", [])
    if not isinstance(data, list):
        return urls
    for item in data:
        if not isinstance(item, dict):
            continue
        target = item.get("target")
        media = item.get("media")
        for value in (item.get("url"), target.get("url") if isinstance(target, dict) else None, media.get("src") if isinstance(media, dict) else None):
            if isinstance(value, str) and value:
                urls.append(value)
        subattachments = item.get("subattachments")
        if isinstance(subattachments, dict):
            urls.extend(_extract_attachment_urls(subattachments))
    return sorted(set(urls))


def graph_posts_to_source_payload(posts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    for post in posts:
        content = str(post.get("message") or post.get("story") or "").strip()
        normalized.append(
            {
                "id": post.get("id"),
                "post_url": post.get("permalink_url") or "",
                "content": content,
                "created_time": post.get("created_time"),
                "updated_time": post.get("updated_time"),
                "attachments": _extract_attachment_urls(post.get("attachments")),
                "raw": post,
            }
        )
    return {"posts": normalized}
