"""Build an Anki deck (.apkg) from the exported vocabulary.

Audio is attached with Anki's built-in `[sound:file.mp3]` tag, so Anki's own
player handles it: it plays automatically when the card is shown, and you can
replay it with the "r" key. No extra add-on is needed.
"""
from __future__ import annotations

import logging
import zlib
from pathlib import Path

from .exceptions import ExportError

log = logging.getLogger(__name__)

CSS = """
.card { font-family: Arial, sans-serif; font-size: 24px; text-align: center; }
"""


def _stable_id(label: str) -> int:
    """Stable 31-bit id so re-importing updates the deck instead of duplicating it."""
    return (1 << 30) + (zlib.crc32(label.encode("utf-8")) % (1 << 30))


def build_deck(
    rows: list[dict],
    audio_dir: Path,
    output_file: Path,
    deck_name: str = "Duolingo German",
    reverse: bool = False,
) -> tuple[int, int]:
    """Write an .apkg file. Returns (number of notes, number of audio files bundled)."""
    try:
        import genanki
    except ImportError as exc:
        raise ExportError("genanki is not installed. Run: pip install genanki") from exc

    class VocabNote(genanki.Note):
        @property
        def guid(self):  # same word -> same note, even if the audio file changes
            return genanki.guid_for(self.fields[0])

    forward = {
        "name": "German -> English",
        "qfmt": "{{German}}<br>{{Audio}}",
        "afmt": '{{FrontSide}}<hr id="answer">{{English}}',
    }
    backward = {
        "name": "English -> German",
        "qfmt": "{{English}}",
        "afmt": '{{FrontSide}}<hr id="answer">{{German}}<br>{{Audio}}',
    }
    templates = [forward, backward] if reverse else [forward]

    model = genanki.Model(
        _stable_id(f"model:{deck_name}:{'rev' if reverse else 'fwd'}"),
        "Duolingo Vocabulary" + (" (both ways)" if reverse else ""),
        fields=[{"name": "German"}, {"name": "English"}, {"name": "Audio"}],
        templates=templates,
        css=CSS,
    )
    deck = genanki.Deck(_stable_id(f"deck:{deck_name}"), deck_name)

    media: list[str] = []
    seen: set[str] = set()
    for row in rows:
        german = row.get("german", "")
        if not german or german.casefold() in seen:
            continue
        seen.add(german.casefold())

        audio_field = ""
        audio_file = row.get("audio_file", "")
        if audio_file and (audio_dir / audio_file).exists():
            audio_field = f"[sound:{audio_file}]"
            media.append(str(audio_dir / audio_file))

        deck.add_note(VocabNote(model=model, fields=[german, row.get("english", ""), audio_field]))

    package = genanki.Package(deck)
    package.media_files = media
    output_file.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_file))

    log.info("Anki deck: %s notes, %s audio files -> %s", len(deck.notes), len(media), output_file)
    return len(deck.notes), len(media)
