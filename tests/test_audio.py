from duolingo_export import audio
from duolingo_export.audio import audio_exists, sync_audio, unique_filename


def _row(german="Hallo", url="http://x/a.mp3", audio_file=""):
    return {"german": german, "english": "Hello", "audio": url, "audio_file": audio_file}


def test_unique_filename_avoids_collisions_case_insensitively():
    used = set()
    assert unique_filename("Hallo", used) == "Hallo.mp3"
    assert unique_filename("hallo", used) == "hallo 2.mp3"


def test_audio_exists_requires_non_empty_file(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"")
    (tmp_path / "b.mp3").write_bytes(b"x")
    assert not audio_exists(tmp_path, "a.mp3")
    assert audio_exists(tmp_path, "b.mp3")
    assert not audio_exists(tmp_path, "")


def test_sync_downloads_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(audio.time, "sleep", lambda s: None)

    def fake_download(url, path, attempts=3):
        path.write_bytes(b"mp3")

    monkeypatch.setattr(audio, "download_file", fake_download)
    rows = [_row()]
    summary = sync_audio(rows, [], tmp_path)
    assert rows[0]["audio_file"] == "Hallo.mp3"
    assert summary.downloaded == 1 and summary.failed == 0


def test_sync_reuses_existing_file(tmp_path, monkeypatch):
    (tmp_path / "Hallo.mp3").write_bytes(b"mp3")

    def boom(*a, **k):
        raise AssertionError("should not download")

    monkeypatch.setattr(audio, "download_file", boom)
    rows = [_row()]
    summary = sync_audio(rows, [_row(audio_file="Hallo.mp3")], tmp_path)
    assert rows[0]["audio_file"] == "Hallo.mp3"
    assert summary.reused == 1


def test_sync_counts_rows_without_audio_url(tmp_path):
    rows = [_row(url="")]
    summary = sync_audio(rows, [], tmp_path)
    assert summary.no_audio == 1
