"""Downloading and tracking mp3 audio files."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import REQUEST_TIMEOUT, USER_AGENT
from .parser import row_key, safe_name

log = logging.getLogger(__name__)


@dataclass
class AudioSummary:
    reused: int = 0
    downloaded: int = 0
    failed: int = 0
    no_audio: int = 0


def download_file(url: str, path: Path, attempts: int = 3) -> Exception | None:
    """Download `url` to `path`. Returns None on success, or the last exception."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            if not r.content:
                raise ValueError("empty response")
            # Write to a temp file so a broken download never looks complete.
            tmp = path.with_suffix(".part")
            tmp.write_bytes(r.content)
            tmp.replace(path)
            return None
        except Exception as exc:  # noqa: BLE001 - we report it to the caller
            last_exc = exc
            if attempt < attempts:
                time.sleep(2 * attempt)  # wait 2s, then 4s, ...
    return last_exc


def audio_exists(audio_dir: Path, filename: str) -> bool:
    if not filename:
        return False
    p = audio_dir / filename
    return p.exists() and p.stat().st_size > 0


def unique_filename(german: str, used: set[str]) -> str:
    """Pick a free .mp3 name. `used` holds lower-cased names (Windows is case-insensitive)."""
    base = safe_name(german)
    name, n = base, 2
    while f"{name}.mp3".lower() in used:
        name = f"{base} {n}"
        n += 1
    filename = f"{name}.mp3"
    used.add(filename.lower())
    return filename


def sync_audio(rows: list[dict], previous_rows: list[dict], audio_dir: Path) -> AudioSummary:
    """Fill in `audio_file` for every row, downloading only what is missing."""
    previous = {row_key(r): r for r in previous_rows}
    used = {r["audio_file"].lower() for r in previous_rows if r.get("audio_file")}

    summary = AudioSummary()
    todo: list[dict] = []

    for row in rows:
        prev = previous.get(row_key(row))

        # Already extracted and the file is on disk: nothing to do.
        if prev and audio_exists(audio_dir, prev.get("audio_file", "")):
            row["audio_file"] = prev["audio_file"]
            summary.reused += 1
            continue

        # Older export without audio_file: adopt a file from an earlier run if present.
        if prev:
            legacy = next(
                (
                    f"{safe_name(row['german'], sep=sep)}.mp3"
                    for sep in (" ", "_")
                    if audio_exists(audio_dir, f"{safe_name(row['german'], sep=sep)}.mp3")
                ),
                None,
            )
            if legacy:
                row["audio_file"] = legacy
                used.add(legacy.lower())
                summary.reused += 1
                continue

        if not row["audio"]:
            summary.no_audio += 1
            continue

        todo.append(row)

    log.info("Audio: %s already downloaded, %s to download", summary.reused, len(todo))

    # Pass 1: every file, 3 attempts each
    failed_items: list[tuple[dict, str]] = []
    for i, row in enumerate(todo, 1):
        filename = unique_filename(row["german"], used)
        err = download_file(row["audio"], audio_dir / filename, attempts=3)
        if err is None:
            row["audio_file"] = filename
            summary.downloaded += 1
            log.info("[%s/%s] %s", i, len(todo), filename)
        else:
            failed_items.append((row, filename))
            log.warning("[%s/%s] FAILED %s (will retry at the end)", i, len(todo), row["german"])
        time.sleep(0.2)

    # Pass 2: retry the failures after a pause, 5 attempts each
    if failed_items:
        log.info("Retrying %s failed downloads in 5 seconds...", len(failed_items))
        time.sleep(5)
        still_failed = []
        for row, filename in failed_items:
            err = download_file(row["audio"], audio_dir / filename, attempts=5)
            if err is None:
                row["audio_file"] = filename
                summary.downloaded += 1
                log.info("Recovered: %s", filename)
            else:
                still_failed.append(row)
                log.error("STILL FAILED %s: %s", row["german"], err)
            time.sleep(0.5)
        failed_items = still_failed

    summary.failed = len(failed_items)
    log.info(
        "Audio summary: %s downloaded, %s reused, %s failed, %s without audio URL",
        summary.downloaded, summary.reused, summary.failed, summary.no_audio,
    )
    log.info("Folder: %s", audio_dir)
    return summary
