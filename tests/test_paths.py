import unicodedata
from pathlib import Path
from podq.paths import ProjectPaths, normalize_stem, unprocessed_audio


def _make_paths(tmp_path: Path) -> ProjectPaths:
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    return ProjectPaths(root=tmp_path)


def test_ensure_dirs_creates_all_required_subdirs(tmp_path):
    paths = ProjectPaths(root=tmp_path)
    paths.ensure_dirs()
    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "aired").is_dir()
    assert (tmp_path / "analysis").is_dir()
    assert (tmp_path / "reports").is_dir()


def test_ensure_dirs_is_idempotent(tmp_path):
    paths = ProjectPaths(root=tmp_path)
    paths.ensure_dirs()
    paths.ensure_dirs()  # second call must not raise
    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "aired").is_dir()


def test_unprocessed_audio_returns_mp3s_without_yaml(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.inbox / "episode1.mp3").touch()
    (paths.inbox / "episode2.mp3").touch()
    (paths.analysis / "episode1.yaml").touch()  # already processed

    result = unprocessed_audio(paths)
    stems = {p.stem for p in result}
    assert stems == {"episode2"}


def test_unprocessed_audio_skips_mp3s_with_yaml(tmp_path):
    paths = _make_paths(tmp_path)
    (paths.inbox / "episode.mp3").touch()
    (paths.analysis / "episode.yaml").touch()

    result = unprocessed_audio(paths)
    assert result == []


def test_nfc_normalization(tmp_path):
    decomposed = "ä"  # 'ä' as a + combining umlaut
    composed = "\xe4"       # 'ä' precomposed
    assert normalize_stem(decomposed) == composed
    assert normalize_stem(decomposed) == unicodedata.normalize("NFC", decomposed)
