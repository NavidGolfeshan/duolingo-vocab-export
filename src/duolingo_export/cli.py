"""Command-line interface: `duolingo-export export` and `duolingo-export anki`."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .anki import build_deck
from .audio import sync_audio
from .auth import build_session
from .client import fetch_all, load_body
from .config import (
    DEFAULT_BODY_FILE,
    DEFAULT_FROM_LANG,
    DEFAULT_LEARNING,
    DEFAULT_OUTPUT_DIR,
    LANGUAGE_NAMES,
    OutputPaths,
    get_credentials,
)
from .exceptions import ExportError
from .parser import normalize, row_key
from .storage import load_previous, save

log = logging.getLogger("duolingo_export")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duolingo-export",
        description="Export your Duolingo vocabulary and turn it into an Anki deck.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--lang", default=DEFAULT_LEARNING, help="language you learn (default: de)")
    common.add_argument("--from-lang", default=DEFAULT_FROM_LANG, help="your UI language (default: en)")
    common.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="where files are written (default: data)")

    exp = sub.add_parser("export", parents=[common], help="fetch vocabulary and download audio")
    exp.add_argument("--body-file", type=Path, default=DEFAULT_BODY_FILE, help="captured request body (default: request_body.json)")
    exp.add_argument("--skip-audio", action="store_true", help="do not download audio files")
    exp.add_argument("--anki", action="store_true", help="also build the Anki deck afterwards")

    ank = sub.add_parser("anki", parents=[common], help="build an Anki deck from an existing export")
    ank.add_argument("--deck-name", help="deck name (default: 'Duolingo <Language>')")
    ank.add_argument("--reverse", action="store_true", help="also create English -> German cards")
    ank.add_argument("-o", "--output", type=Path, help="output .apkg path")
    return parser


def _default_deck_name(lang: str) -> str:
    return f"Duolingo {LANGUAGE_NAMES.get(lang, lang).title()}"


def cmd_export(args: argparse.Namespace) -> None:
    paths = OutputPaths(args.output_dir, args.lang)
    paths.ensure()

    jwt, username, password = get_credentials()
    session, uid = build_session(jwt, username, password)
    log.info("User ID: %s", uid)

    previous_rows = load_previous(paths.json_file)
    previous_keys = {row_key(p) for p in previous_rows}
    log.info("Previously exported words: %s", len(previous_rows))

    body = load_body(args.body_file)

    # Fetch + dedupe current vocabulary
    seen: dict = {}
    for item in fetch_all(session, uid, args.lang, args.from_lang, body, paths.raw_debug_file):
        row = normalize(item)
        seen[row_key(row)] = row
    rows = list(seen.values())

    if rows and not rows[0]["german"]:
        log.warning("Field names didn't match. Check %s and adjust parser.normalize().", paths.raw_debug_file)

    log.info("New words this run: %s", sum(1 for r in rows if row_key(r) not in previous_keys))

    if args.skip_audio:
        previous = {row_key(p): p for p in previous_rows}
        for r in rows:
            r["audio_file"] = previous.get(row_key(r), {}).get("audio_file", "")
    else:
        sync_audio(rows, previous_rows, paths.audio_dir)

    # Keep words from earlier exports that Duolingo no longer returns
    current_keys = {row_key(r) for r in rows}
    for p in previous_rows:
        if row_key(p) not in current_keys:
            p.setdefault("audio_file", "")
            rows.append(p)

    save(rows, paths.json_file, paths.csv_file)

    if args.anki:
        build_deck(rows, paths.audio_dir, paths.anki_file, _default_deck_name(args.lang))


def cmd_anki(args: argparse.Namespace) -> None:
    paths = OutputPaths(args.output_dir, args.lang)
    rows = load_previous(paths.json_file)
    if not rows:
        raise ExportError(f"No export found at {paths.json_file}. Run `duolingo-export export` first.")
    build_deck(
        rows,
        paths.audio_dir,
        args.output or paths.anki_file,
        args.deck_name or _default_deck_name(args.lang),
        reverse=args.reverse,
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    try:
        {"export": cmd_export, "anki": cmd_anki}[args.command](args)
    except ExportError as exc:
        sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
