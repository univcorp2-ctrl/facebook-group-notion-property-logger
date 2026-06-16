from __future__ import annotations

import json
from typing import Any

import requests

from .models import SourcePost
from .parsers import extract_property_details, make_title

MAX_RICH_TEXT = 2000
MAX_BLOCKS_PER_REQUEST = 100


class NotionError(RuntimeError):
    pass


class NotionClient:
    def __init__(self, token: str, notion_version: str = "2022-06-28"):
        self.token = token
        self.notion_version = notion_version
        self.base_url = "https://api.notion.com/v1"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version,
        }

    def append_to_page(self, page_id: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
        last_response: dict[str, Any] = {}
        for index in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
            batch = blocks[index : index + MAX_BLOCKS_PER_REQUEST]
            response = requests.patch(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self.headers,
                data=json.dumps({"children": batch}, ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            if response.status_code >= 400:
                raise NotionError(f"Notion API error {response.status_code}: {response.text}")
            last_response = response.json()
        return last_response


def chunk_text(text: str, size: int = MAX_RICH_TEXT) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def rich_text(content: str, href: str | None = None) -> list[dict[str, Any]]:
    text_object: dict[str, Any] = {"content": content[:MAX_RICH_TEXT]}
    if href:
        text_object["link"] = {"url": href}
    return [{"type": "text", "text": text_object}]


def paragraph(content: str, href: str | None = None) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(content, href)}}


def bulleted_item(content: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text(content)},
    }


def build_notion_blocks(post: SourcePost) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    details = extract_property_details(post.content)
    title = post.title or make_title(post.content, details, post.url)

    blocks: list[dict[str, Any]] = [
        {"object": "block", "type": "divider", "divider": {}},
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": rich_text(title, post.url or None)},
        },
    ]

    if post.url:
        blocks.append(paragraph(f"投稿URL: {post.url}", post.url))
    if post.created_time:
        blocks.append(paragraph(f"投稿日時: {post.created_time}"))
    if post.author:
        blocks.append(paragraph(f"投稿者: {post.author}"))

    if details:
        blocks.append(paragraph("抽出した物件情報"))
        for key, value in details.items():
            if isinstance(value, list):
                value = ", ".join(value)
            blocks.append(bulleted_item(f"{key}: {value}"))

    blocks.append(paragraph("投稿本文"))
    for chunk in chunk_text(post.content):
        blocks.append(
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": rich_text(chunk)},
            }
        )

    if post.attachments:
        blocks.append(paragraph("添付/関連URL"))
        for url in post.attachments[:20]:
            blocks.append(bulleted_item(url))

    return title, details, blocks
