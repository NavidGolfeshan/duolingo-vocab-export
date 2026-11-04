"""Fetching learned lexemes from Duolingo's (unofficial) HTTP API."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from .config import PAGE_SIZE, REQUEST_TIMEOUT
from .exceptions import ExportError

log = logging.getLogger(__name__)


def load_body(path: Path) -> dict:
    """Load the request body captured from the browser (see README)."""
    if not path.exists():
        raise ExportError(
            f"Request body file not found: {path}\n"
            "Capture it from your browser and save it there "
            "(see request_body.example.json and the README)."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExportError(f"{path} is not valid JSON: {exc}") from exc


def fetch_page(
    session: requests.Session,
    user_id: int,
    start_index: int,
    learning: str,
    from_lang: str,
    body: dict,
    page_size: int = PAGE_SIZE,
) -> dict:
    url = (
        f"https://www.duolingo.com/2017-06-30/users/{user_id}"
        f"/courses/{learning}/{from_lang}/learned-lexemes"
    )
    params = {"limit": page_size, "sortBy": "LEARNED_DATE", "startIndex": start_index}

    for attempt in range(3):
        r = session.post(url, params=params, json=body, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:  # rate limited: back off and retry
            time.sleep(3 * (attempt + 1))
            continue
        break

    if r.status_code != 200:
        raise ExportError(f"HTTP {r.status_code} at startIndex={start_index}: {r.text[:500]}")

    data = r.json()
    if data is None:
        raise ExportError(
            "Server returned null. The request body (progress snapshot) is probably "
            "stale or the token is rejected. Re-capture request_body.json from the browser."
        )
    return data


def fetch_all(
    session: requests.Session,
    user_id: int,
    learning: str,
    from_lang: str,
    body: dict,
    raw_debug_file: Path | None = None,
    page_size: int = PAGE_SIZE,
) -> list[dict]:
    """Walk through all pages and return every learned lexeme."""
    all_items: list[dict] = []
    start = 0

    while True:
        data = fetch_page(session, user_id, start, learning, from_lang, body, page_size)

        if start == 0:
            if raw_debug_file is not None:
                raw_debug_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            log.info("Pagination info: %s", data.get("pagination"))

        items = data.get("learnedLexemes", [])
        all_items.extend(items)
        log.info("startIndex=%s: got %s (total %s)", start, len(items), len(all_items))

        pagination = data.get("pagination") or {}
        next_index = pagination.get("nextStartIndex")

        if not items:
            break
        if next_index is not None and next_index >= 0:
            if next_index <= start:
                break
            start = next_index
        elif len(items) < page_size:
            break
        else:
            start += page_size

        time.sleep(0.3)

    return all_items
