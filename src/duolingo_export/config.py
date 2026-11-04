"""Configuration: defaults, output paths and environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional: load variables from a local .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

DEFAULT_LEARNING = "de"
DEFAULT_FROM_LANG = "en"
PAGE_SIZE = 50
REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

DEFAULT_OUTPUT_DIR = Path(os.environ.get("DUOLINGO_OUTPUT_DIR", "data"))
DEFAULT_BODY_FILE = Path(os.environ.get("DUOLINGO_BODY_FILE", "request_body.json"))

# Used for file names (duolingo_german.csv). Unknown codes fall back to the code itself.
LANGUAGE_NAMES = {
    "de": "german",
    "es": "spanish",
    "fr": "french",
    "it": "italian",
    "pt": "portuguese",
    "nl": "dutch",
    "ja": "japanese",
    "ko": "korean",
    "zh": "chinese",
    "ru": "russian",
    "sv": "swedish",
    "tr": "turkish",
}


def get_credentials() -> tuple[str, str, str]:
    """Return (jwt, username, password) from the environment."""
    return (
        os.environ.get("DUOLINGO_JWT", ""),
        os.environ.get("DUOLINGO_USER", ""),
        os.environ.get("DUOLINGO_PASS", ""),
    )


@dataclass(frozen=True)
class OutputPaths:
    """All files written for one course, e.g. <root>/duolingo_german.csv."""

    root: Path
    learning: str

    @property
    def stem(self) -> str:
        return f"duolingo_{LANGUAGE_NAMES.get(self.learning, self.learning)}"

    @property
    def csv_file(self) -> Path:
        return self.root / f"{self.stem}.csv"

    @property
    def json_file(self) -> Path:
        # Also the "already extracted" record used to skip existing audio.
        return self.root / f"{self.stem}.json"

    @property
    def anki_file(self) -> Path:
        return self.root / f"{self.stem}.apkg"

    @property
    def raw_debug_file(self) -> Path:
        return self.root / "duolingo_first_response.json"

    @property
    def audio_dir(self) -> Path:
        return self.root / "audio"

    def ensure(self) -> None:
        self.audio_dir.mkdir(parents=True, exist_ok=True)
