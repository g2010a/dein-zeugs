from pathlib import Path
from unittest.mock import MagicMock
from podq.transcription import WhisperTranscriber


def test_transcriber_returns_text(tmp_path):
    seg = MagicMock()
    seg.text = "  Hello world  "
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([seg], MagicMock())

    t = WhisperTranscriber(model_name="medium")
    t._model = fake_model

    mp3 = tmp_path / "episode.mp3"
    mp3.touch()
    text = t.transcribe(mp3)
    assert text == "Hello world"
