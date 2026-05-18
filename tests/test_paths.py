import unicodedata
from pathlib import Path
from podq.paths import ProjectPaths, normalize_stem, unprocessed_audio, unanalyzed_transcripts


def _make_paths(tmp_path: Path) -> ProjectPaths:
    (tmp_path / "inbox").mkdir()
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "analysis").mkdir()
    return ProjectPaths(root=tmp_path)


def test_unprocessed_audio_returns_mp3s_without_transcripts(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.inbox / "episode1.mp3").touch()
    (paths.inbox / "episode2.mp3").touch()
    (paths.transcripts / "episode1.txt").touch()

    result = unprocessed_audio(paths)
    stems = {p.stem for p in result}
    assert stems == {"episode2"}


def test_unprocessed_audio_skips_mp3s_with_transcripts(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.inbox / "episode.mp3").touch()
    (paths.transcripts / "episode.txt").touch()

    result = unprocessed_audio(paths)
    assert result == []


def test_unanalyzed_transcripts_returns_txt_without_json(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.transcripts / "ep1.txt").touch()
    (paths.transcripts / "ep2.txt").touch()
    (paths.analysis / "ep1.json").touch()

    result = unanalyzed_transcripts(paths)
    stems = {p.stem for p in result}
    assert stems == {"ep2"}


def test_unanalyzed_transcripts_skips_ones_with_json(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.transcripts / "ep.txt").touch()
    (paths.analysis / "ep.json").touch()

    result = unanalyzed_transcripts(paths)
    assert result == []


def test_nfc_normalization(tmp_path):
    decomposed = "ä"  # 'ä' as a + combining umlaut
    composed = "\xe4"       # 'ä' precomposed
    assert normalize_stem(decomposed) == composed
    assert normalize_stem(decomposed) == unicodedata.normalize("NFC", decomposed)
