import yaml
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return (v / norm).astype(np.float32)


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------

from podq.analysis import score


def test_score_identical_embeddings():
    emb = _unit(np.array([1.0, 0.0, 0.0]))
    sim, nov, nearest = score(emb, [("ep1", emb)])
    assert sim == pytest.approx(1.0, abs=1e-6)
    assert nov == pytest.approx(0.0, abs=1e-5)
    assert nearest == "ep1"


def test_score_orthogonal_embeddings():
    a = _unit(np.array([1.0, 0.0, 0.0]))
    b = _unit(np.array([0.0, 1.0, 0.0]))
    sim, nov, nearest = score(a, [("ep1", b)])
    assert sim == pytest.approx(0.0, abs=1e-6)
    assert nov == pytest.approx(1.0, abs=1e-6)
    assert nearest == "ep1"


def test_score_empty_aired():
    emb = _unit(np.array([1.0, 0.0, 0.0]))
    sim, nov, nearest = score(emb, [])
    assert sim == 0.0
    assert nov == 1.0
    assert nearest is None


def test_score_returns_correct_nearest_stem():
    query = _unit(np.array([1.0, 0.1, 0.0]))
    close = _unit(np.array([1.0, 0.0, 0.0]))
    far = _unit(np.array([0.0, 1.0, 0.0]))
    sim, nov, nearest = score(query, [("far_ep", far), ("close_ep", close)])
    assert nearest == "close_ep"
    assert sim > 0.9


# ---------------------------------------------------------------------------
# keywords()
# ---------------------------------------------------------------------------

from podq.analysis import keywords


def test_keywords_comma_split():
    with patch("podq.analysis._infer", return_value="sport, ernährung, gesundheit, bewegung, fitness"):
        result = keywords("some text", "/fake/model.gguf")
    assert result == ["sport", "ernährung", "gesundheit", "bewegung", "fitness"]


def test_keywords_newline_handling():
    with patch("podq.analysis._infer", return_value="sport\nernährung\ngesundheit"):
        result = keywords("some text", "/fake/model.gguf")
    assert "sport" in result
    assert "ernährung" in result
    assert "gesundheit" in result


# ---------------------------------------------------------------------------
# process_all_unprocessed() — YAML schema test
# ---------------------------------------------------------------------------

from podq.analysis import process_all_unprocessed
from podq.paths import ProjectPaths


def test_process_all_unprocessed_yaml_schema(tmp_path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    mp3 = tmp_path / "inbox" / "ep001.mp3"
    mp3.touch()

    paths = ProjectPaths(root=tmp_path)

    fake_embedding = _unit(np.array([0.5, 0.5, 0.0]))

    mock_config = MagicMock()
    mock_config.llm_model_path = "/fake/model.gguf"
    mock_config.whisper_model = "medium"

    mock_model = MagicMock()
    mock_model.embed.return_value = fake_embedding
    mock_model.aired_corpus.return_value = []

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = "Wie oft sollte man Sport machen?"

    with patch("podq.analysis.summarize", return_value="Eine Frage über Sport."), \
         patch("podq.analysis.keywords", return_value=["sport", "fitness"]), \
         patch("podq.transcription.WhisperTranscriber", return_value=mock_transcriber):
        count = process_all_unprocessed(paths, mock_config, mock_model)

    assert count == 1

    result_file = tmp_path / "analysis" / "ep001.yaml"
    assert result_file.exists()
    data = yaml.safe_load(result_file.read_text(encoding="utf-8"))

    required_fields = [
        "stem", "transcript", "summary", "keywords", "similarity_score",
        "novelty_score", "nearest_aired_stem", "embedding",
        "language", "podq_version", "analyzed_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    assert data["stem"] == "ep001"
    assert data["transcript"] == "Wie oft sollte man Sport machen?"
    assert data["language"] == "auto"
    assert isinstance(data["embedding"], list)
    assert isinstance(data["keywords"], list)
    assert isinstance(data["similarity_score"], float)
    assert isinstance(data["novelty_score"], float)
