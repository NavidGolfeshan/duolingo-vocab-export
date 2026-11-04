# Duolingo Vocab Export

Export the words you have learned on Duolingo, together with their audio, to CSV and JSON, and turn them into an Anki deck.

> **Disclaimer:** This tool uses unofficial, undocumented Duolingo endpoints that can change or break at any time. It is not affiliated with Duolingo. Use it only on your own account, keep the request rate low, and check Duolingo's terms of service.

## Features

- Fetches all learned words (paged) for any course, default German from English
- Saves `CSV` (opens in Excel, UTF-8 with BOM) and `JSON`
- Downloads one `.mp3` per word, with retries and a second pass for failures
- Incremental: words and audio that were already exported are skipped on the next run
- Keeps words from older exports even if Duolingo no longer returns them
- Builds an Anki `.apkg` deck with audio (optional reverse cards)

## Project layout

```
src/duolingo_export/
├── cli.py        command-line entry point
├── config.py     defaults, output paths, environment variables
├── auth.py       JWT / login, builds the HTTP session
├── client.py     paged requests to the learned-lexemes endpoint
├── parser.py     raw item -> row, keys, safe file names
├── audio.py      audio download and sync
├── storage.py    CSV / JSON read and write
└── anki.py       Anki deck builder
tests/            pytest unit tests
```

## Installation

```bash
git clone https://github.com/<your-user>/duolingo-vocab-export.git
cd duolingo-vocab-export
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Setup

### 1. Your token

1. Log in at <https://www.duolingo.com> in your browser.
2. Open DevTools (F12) -> **Application** (Chrome) or **Storage** (Firefox) -> **Cookies** -> `https://www.duolingo.com`.
3. Copy the value of `jwt_token`.
4. Copy `.env.example` to `.env` and paste it as `DUOLINGO_JWT=...`.

The token expires after a while. If you get HTTP 401/403 or `null`, copy a fresh one.

Username/password login (`DUOLINGO_USER`, `DUOLINGO_PASS`) is supported as a fallback, but Duolingo often blocks it.

### 2. The request body

The words endpoint expects a snapshot of your course progress. Capture it once:

1. Open <https://www.duolingo.com/practice-hub/words> with DevTools -> **Network** open.
2. Find the `POST` request ending in `learned-lexemes`.
3. Copy its **request payload** (JSON) and save it as `request_body.json` in the project root.

See `request_body.example.json` for the shape. This file contains your own progress data and is git-ignored. If the export fails with `null` or an error later, re-capture it.

## Usage

```bash
# Fetch words + download audio into ./data
duolingo-export export

# Same, and build the Anki deck right away
duolingo-export export --anki

# Only the words, no audio
duolingo-export export --skip-audio

# Another course (Spanish, for English speakers) and another folder
duolingo-export export --lang es --output-dir out/spanish

# Build the deck from an existing export (add English -> German cards too)
duolingo-export anki --reverse
```

Without installing, you can also run `python -m duolingo_export export` (from `src/`, or after `pip install -e .`).

Resuming an older export: point `--output-dir` at the folder that already contains `duolingo_german.json` and `audio/`; existing audio is reused.

### Output

```
data/
├── duolingo_german.csv     german, english, audio, audio_file
├── duolingo_german.json    same data, used as the "already exported" record
├── duolingo_german.apkg    Anki deck (after `--anki` / `anki`)
├── duolingo_first_response.json   raw first API page, for debugging field names
└── audio/                  one .mp3 per word, e.g. "gute Nacht.mp3"
```

## Importing into Anki

1. In Anki: **File -> Import** and choose `duolingo_german.apkg`.
2. Audio is bundled and attached with Anki's built-in `[sound:...]` tag, so it plays automatically when a card is shown. Press `r` to replay. No add-on is needed.
3. Re-importing an updated deck updates existing notes instead of duplicating them (notes are matched by the German word).

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `DUOLINGO_JWT` | `jwt_token` cookie (recommended) | |
| `DUOLINGO_USER` / `DUOLINGO_PASS` | fallback login | |
| `DUOLINGO_OUTPUT_DIR` | output folder | `data` |
| `DUOLINGO_BODY_FILE` | captured request body | `request_body.json` |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Troubleshooting

- **Server returned null**: the request body is stale or the token was rejected. Refresh both.
- **HTTP 429**: rate limited. The script retries with a delay; wait a few minutes and run again.
- **Empty German column**: Duolingo renamed fields. Check `duolingo_first_response.json` and adjust `TEXT_KEYS` / `AUDIO_KEYS` in `parser.py`.

## License

MIT, see [LICENSE](LICENSE).
