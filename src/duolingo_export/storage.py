"""Reading and writing the CSV / JSON exports."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

FIELDNAMES = ["german", "english", "audio", "audio_file"]


def load_previous(json_file: Path) -> list[dict]:
    """Load the previous export (the "already extracted" record)."""
    if not json_file.exists():
        return []
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not read previous export (%s); starting fresh.", exc)
        return []


def save(rows: list[dict], json_file: Path, csv_file: Path) -> None:
    json_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    log.info("Unique vocabulary: %s", len(rows))
    log.info("CSV: %s", csv_file)
    log.info("JSON: %s", json_file)
