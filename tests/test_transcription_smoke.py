import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from podq.transcription import WhisperTranscriber, transcribe_all_unprocessed
from podq.paths import ProjectPaths
from podq.config import Config


def _setup_paths(tmp_path: Path) -> ProjectPaths:
    (tmp_path / "inbox").mkdir()
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "analysis").mkdir()
    return ProjectPaths(root=tmp_path)


def test_transcriber_writes_txt_file(tmp_path):
    paths = _setup_paths(tmp_path)
    mp3 = paths.inbox / "episode1.mp3"
    mp3.touch()

    seg = MagicMock()
    seg.text = "  Hello world  "
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([seg], MagicMock())

    t = WhisperTranscriber(model_name="medium")
    t._model = fake_model

    text = t.transcribe(mp3)
    assert text == "Hello world"


def test_transcribe_all_unprocessed_returns_zero_on_empty_inbox(tmp_path):
    paths = _setup_paths(tmp_path)
    cfg = Config()
    count = transcribe_all_unprocessed(paths, cfg, transcriber=_make_transcriber())
    assert count == 0


def test_transcribe_all_unprocessed_returns_correct_count(tmp_path):
    paths = _setup_paths(tmp_path)
    (paths.inbox / "ep1.mp3").touch()
    (paths.inbox / "ep2.mp3").touch()
    (paths.inbox / "ep3.mp3").touch()

    cfg = Config()
    t = _make_transcriber(text="Test transcript")
    count = transcribe_all_unprocessed(paths, cfg, transcriber=t)
    assert count == 3
    assert (paths.transcripts / "ep1.txt").exists()
    assert (paths.transcripts / "ep2.txt").exists()
    assert (paths.transcripts / "ep3.txt").exists()


def _make_transcriber(text: str = "transcribed text") -> WhisperTranscriber:
    seg = MagicMock()
    seg.text = text
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([seg], MagicMock())
    t = WhisperTranscriber(model_name="medium")
    t._model = fake_model
    return t
