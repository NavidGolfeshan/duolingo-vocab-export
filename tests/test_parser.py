from duolingo_export.parser import first_str, normalize, row_key, safe_name


def test_first_str_skips_empty_and_non_strings():
    assert first_str({"a": "", "b": 3, "c": "x"}, ["a", "b", "c"]) == "x"
    assert first_str({}, ["a"]) == ""


def test_normalize_list_translations():
    row = normalize({"text": "Hund", "translations": ["dog", "hound"], "audioURL": "http://a/b.mp3"})
    assert row == {"german": "Hund", "english": "dog, hound", "audio": "http://a/b.mp3", "audio_file": ""}


def test_normalize_string_translation_and_fallback_keys():
    row = normalize({"word": "Katze", "translation": "cat", "tts": "http://t"})
    assert (row["german"], row["english"], row["audio"]) == ("Katze", "cat", "http://t")


def test_row_key_is_case_insensitive_on_text():
    a = {"german": "Hund", "audio": "u"}
    b = {"german": "hund", "audio": "u"}
    assert row_key(a) == row_key(b)


def test_safe_name_uses_spaces_by_default():
    assert safe_name("gute_Nacht") == "gute Nacht"
    assert safe_name("Wie geht's?") == "Wie geht s"
    assert safe_name("???") == "word"


def test_safe_name_legacy_underscores():
    assert safe_name("gute Nacht", sep="_") == "gute_Nacht"
