from __future__ import annotations

import json

from fb_notion_property_logger.cli import main


def test_sync_dry_run_cli_writes_output(tmp_path) -> None:
    source = tmp_path / "posts.json"
    output = tmp_path / "result.json"
    state_db = tmp_path / "state.sqlite3"
    source.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "id": "1",
                        "post_url": "https://facebook.com/groups/g/posts/p/",
                        "content": "東京都渋谷区 1LDK 賃料18万円 45㎡",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    status = main(
        [
            "sync",
            "--source",
            str(source),
            "--state-db",
            str(state_db),
            "--dry-run",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["results"][0]["status"] == "dry_run"


def test_probe_facebook_without_token(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FACEBOOK_ACCESS_TOKEN", raising=False)
    output = tmp_path / "probe.json"

    status = main(
        [
            "probe-facebook",
            "--group-id",
            "https://www.facebook.com/groups/1281008662437696",
            "--output",
            str(output),
        ]
    )

    assert status == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["token_provided"] is False
    assert payload["ok"] is False


def test_fetch_facebook_requires_token(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FACEBOOK_ACCESS_TOKEN", raising=False)
    output = tmp_path / "fetch.json"

    status = main(["fetch-facebook", "--output", str(output)])

    assert status == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["error"] == "FACEBOOK_ACCESS_TOKEN is required"
