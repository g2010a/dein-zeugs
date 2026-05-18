import json
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
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": "sport, ernährung, gesundheit, bewegung, fitness"}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = keywords("some text", "llama3", "http://localhost:11434")

    assert result == ["sport", "ernährung", "gesundheit", "bewegung", "fitness"]


def test_keywords_newline_handling():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": "sport\nernährung\ngesundheit"}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = keywords("some text", "llama3", "http://localhost:11434")

    assert "sport" in result
    assert "ernährung" in result
    assert "gesundheit" in result


# ---------------------------------------------------------------------------
# analyze_all_unanalyzed() — JSON schema test
# ---------------------------------------------------------------------------

from podq.analysis import analyze_all_unanalyzed
from podq.paths import ProjectPaths


def test_analyze_all_unanalyzed_json_schema(tmp_path):
    # Set up directory structure
    (tmp_path / "inbox").mkdir()
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()
    (tmp_path / "reports").mkdir()

    transcript_text = "Wie oft sollte man Sport machen?"
    (tmp_path / "transcripts" / "ep001.txt").write_text(transcript_text, encoding="utf-8")

    paths = ProjectPaths(root=tmp_path)

    fake_embedding = _unit(np.array([0.5, 0.5, 0.0]))

    mock_config = MagicMock()
    mock_config.ollama_model = "llama3"
    mock_config.ollama_url = "http://localhost:11434"

    mock_model = MagicMock()
    mock_model.embed.return_value = fake_embedding
    mock_model.aired_corpus.return_value = []

    with patch("podq.analysis.summarize", return_value="Eine Frage über Sport."), \
         patch("podq.analysis.keywords", return_value=["sport", "fitness"]):
        count = analyze_all_unanalyzed(paths, mock_config, mock_model)

    assert count == 1

    result_file = tmp_path / "analysis" / "ep001.json"
    assert result_file.exists()
    data = json.loads(result_file.read_text(encoding="utf-8"))

    required_fields = [
        "stem", "summary", "keywords", "similarity_score", "novelty_score",
        "nearest_aired_stem", "embedding", "language", "podq_version", "analyzed_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    assert data["stem"] == "ep001"
    assert data["language"] == "auto"
    assert isinstance(data["embedding"], list)
    assert isinstance(data["keywords"], list)
    assert isinstance(data["similarity_score"], float)
    assert isinstance(data["novelty_score"], float)
