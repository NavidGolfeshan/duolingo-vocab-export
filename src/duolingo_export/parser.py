"""Pure helpers: turn raw API items into rows, build keys and file names."""
from __future__ import annotations

import re

AUDIO_KEYS = ["audioURL", "audioUrl", "tts"]
TEXT_KEYS = ["text", "word", "lexeme", "surfaceForm"]


def first_str(d: dict, keys: list[str]) -> str:
    """Return the first non-empty string value found under any of `keys`."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def normalize(item: dict) -> dict:
    """Convert one API item into {german, english, audio, audio_file}."""
    german = first_str(item, TEXT_KEYS)
    tr = item.get("translations") or item.get("translation") or ""
    if isinstance(tr, list):
        english = ", ".join(str(t) for t in tr)
    else:
        english = str(tr)
    return {
        "german": german,
        "english": english,
        "audio": first_str(item, AUDIO_KEYS),
        "audio_file": "",
    }


def row_key(row: dict) -> tuple[str, str]:
    """A word counts as "already extracted" if the same text + audio URL was seen before."""
    return (row["german"].casefold(), row["audio"])


def safe_name(text: str, sep: str = " ") -> str:
    """Make `text` usable as a file name.

    Runs of unsafe characters (and underscores) become `sep`. The default is a
    space ("gute Nacht"); pass sep="_" for the legacy underscore style that
    older exports used ("gute_Nacht").
    """
    name = re.sub(r"(?:[^\w\-]|_)+", sep, text, flags=re.UNICODE).strip(sep)
    return name or "word"
