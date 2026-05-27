import yaml
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dein_zeugs.analysis import compute_intra_batch_scores, score, keywords, process_all_unprocessed
from dein_zeugs.paths import ProjectPaths


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return (v / norm).astype(np.float32)


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------


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


def test_keywords_comma_split():
    with patch("dein_zeugs.analysis._infer", return_value="sport, ernährung, gesundheit, bewegung, fitness"):
        result = keywords("some text", "/fake/model.gguf")
    assert result == ["sport", "ernährung", "gesundheit", "bewegung", "fitness"]


def test_keywords_newline_handling():
    with patch("dein_zeugs.analysis._infer", return_value="sport\nernährung\ngesundheit"):
        result = keywords("some text", "/fake/model.gguf")
    assert "sport" in result
    assert "ernährung" in result
    assert "gesundheit" in result


# ---------------------------------------------------------------------------
# process_all_unprocessed() — YAML schema test
# ---------------------------------------------------------------------------


def test_process_all_unprocessed_analyzes_aired_without_yaml(tmp_path):
    """Aired MP3s without a YAML are transcribed and analyzed."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    mp3 = tmp_path / "aired" / "aired_ep.mp3"
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
    mock_transcriber.transcribe.return_value = "Hallo aus der Sendung."

    with patch("dein_zeugs.analysis.summarize", return_value="Begrüßung."), \
         patch("dein_zeugs.analysis.keywords", return_value=["begrüßung"]), \
         patch("dein_zeugs.transcription.WhisperTranscriber", return_value=mock_transcriber):
        count = process_all_unprocessed(paths, mock_config, mock_model)

    assert count == 1
    yaml_path = tmp_path / "analysis" / "aired_ep.yaml"
    assert yaml_path.exists()
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert data["stem"] == "aired_ep"
    assert data["transcript"] == "Hallo aus der Sendung."
    assert "embedding" in data
    assert "summary" in data
    assert "keywords" in data
    assert "similarity_score" in data
    assert "novelty_score" in data
    # Aired items are not part of an inbox batch; these fields must be absent.
    assert "intra_batch_uniqueness" not in data
    assert "standout_score" not in data


def test_process_all_unprocessed_aired_items_see_each_other_in_same_pass(tmp_path):
    """Two aired items in the same pass: the second should be scored against the first."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    mp3_a = tmp_path / "aired" / "aired_a.mp3"
    mp3_b = tmp_path / "aired" / "aired_b.mp3"
    mp3_a.touch()
    mp3_b.touch()

    paths = ProjectPaths(root=tmp_path)

    # near-identical embeddings — should produce high similarity between them
    emb_a = _unit(np.array([1.0, 0.0, 0.0]))
    emb_b = _unit(np.array([1.0, 0.01, 0.0]))

    mock_config = MagicMock()
    mock_config.llm_model_path = "/fake/model.gguf"
    mock_config.whisper_model = "medium"

    mock_model = MagicMock()
    mock_model.embed.side_effect = [emb_a, emb_b]
    mock_model.aired_corpus.return_value = []  # nothing pre-existing

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = "Irgendein Text."

    with patch("dein_zeugs.analysis.summarize", return_value="Test."), \
         patch("dein_zeugs.analysis.keywords", return_value=["test"]), \
         patch("dein_zeugs.transcription.WhisperTranscriber", return_value=mock_transcriber):
        count = process_all_unprocessed(paths, mock_config, mock_model)

    assert count == 2
    data_b = yaml.safe_load(
        (tmp_path / "analysis" / "aired_b.yaml").read_text(encoding="utf-8")
    )
    # aired_b should recognise aired_a as its nearest neighbor (high similarity)
    assert data_b["nearest_aired_stem"] == "aired_a"
    assert data_b["similarity_score"] > 0.9


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

    with patch("dein_zeugs.analysis.summarize", return_value="Eine Frage über Sport."), \
         patch("dein_zeugs.analysis.keywords", return_value=["sport", "fitness"]), \
         patch("dein_zeugs.transcription.WhisperTranscriber", return_value=mock_transcriber):
        count = process_all_unprocessed(paths, mock_config, mock_model)

    assert count == 1

    result_file = tmp_path / "analysis" / "ep001.yaml"
    assert result_file.exists()
    data = yaml.safe_load(result_file.read_text(encoding="utf-8"))

    required_fields = [
        "stem", "transcript", "summary", "keywords", "similarity_score",
        "novelty_score", "nearest_aired_stem", "embedding",
        "language", "dein_zeugs_version", "analyzed_at",
        "intra_batch_uniqueness", "standout_score",
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
    assert isinstance(data["intra_batch_uniqueness"], float)
    assert isinstance(data["standout_score"], float)


# ---------------------------------------------------------------------------
# Helper: write a minimal YAML into analysis/ for a given stem + MP3 in inbox/
# ---------------------------------------------------------------------------

def _write_fake_yaml(analysis_dir: Path, stem: str, emb: np.ndarray, novelty: float) -> Path:
    data = {
        "stem": stem,
        "transcript": f"Transcript for {stem}",
        "summary": "Zusammenfassung.",
        "keywords": ["test"],
        "similarity_score": round(1.0 - novelty, 6),
        "novelty_score": novelty,
        "nearest_aired_stem": None,
        "language": "auto",
        "dein_zeugs_version": "0.0.0",
        "analyzed_at": "2024-01-01T00:00:00+00:00",
        "embedding": emb.tolist(),
    }
    yaml_path = analysis_dir / f"{stem}.yaml"
    yaml_path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return yaml_path


# ---------------------------------------------------------------------------
# compute_intra_batch_scores() tests
# ---------------------------------------------------------------------------

def test_intra_batch_uniqueness_values(tmp_path):
    """Unique item gets high uniqueness; near-duplicates get low uniqueness."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    from dein_zeugs.paths import ProjectPaths

    # Two near-duplicates: almost identical embeddings.
    dup_a = _unit(np.array([1.0, 0.01, 0.0]))
    dup_b = _unit(np.array([1.0, 0.02, 0.0]))
    # One unique: orthogonal to the duplicates.
    unique = _unit(np.array([0.0, 0.0, 1.0]))

    # Create inbox MP3 stubs + analysis YAMLs.
    for stem, emb in [("dup_a", dup_a), ("dup_b", dup_b), ("unique_q", unique)]:
        (tmp_path / "inbox" / f"{stem}.mp3").touch()
        _write_fake_yaml(tmp_path / "analysis", stem, emb, novelty=1.0)

    paths = ProjectPaths(root=tmp_path)
    compute_intra_batch_scores(paths, aired_stems=set())

    def _load(stem):
        return yaml.safe_load(
            (tmp_path / "analysis" / f"{stem}.yaml").read_text(encoding="utf-8")
        )

    data_dup_a = _load("dup_a")
    data_dup_b = _load("dup_b")
    data_unique = _load("unique_q")

    # Unique item should have high intra-batch uniqueness.
    assert data_unique["intra_batch_uniqueness"] > 0.8, (
        f"Expected unique item > 0.8, got {data_unique['intra_batch_uniqueness']}"
    )

    # Near-duplicates should penalise each other.
    assert data_dup_a["intra_batch_uniqueness"] < 0.3, (
        f"Expected dup_a < 0.3, got {data_dup_a['intra_batch_uniqueness']}"
    )
    assert data_dup_b["intra_batch_uniqueness"] < 0.3, (
        f"Expected dup_b < 0.3, got {data_dup_b['intra_batch_uniqueness']}"
    )

    # standout_score = min(novelty_score, intra_batch_uniqueness) for each item.
    for stem, data in [("dup_a", data_dup_a), ("dup_b", data_dup_b), ("unique_q", data_unique)]:
        expected = round(min(data["novelty_score"], data["intra_batch_uniqueness"]), 6)
        assert abs(data["standout_score"] - expected) < 1e-9, (
            f"{stem}: standout_score {data['standout_score']} != min({data['novelty_score']}, "
            f"{data['intra_batch_uniqueness']}) = {expected}"
        )


def test_intra_batch_single_item(tmp_path):
    """A batch with a single unaired item gets intra_batch_uniqueness = 1.0."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    from dein_zeugs.paths import ProjectPaths

    emb = _unit(np.array([1.0, 0.0, 0.0]))
    (tmp_path / "inbox" / "solo.mp3").touch()
    _write_fake_yaml(tmp_path / "analysis", "solo", emb, novelty=0.7)

    paths = ProjectPaths(root=tmp_path)
    compute_intra_batch_scores(paths, aired_stems=set())

    data = yaml.safe_load(
        (tmp_path / "analysis" / "solo.yaml").read_text(encoding="utf-8")
    )
    assert data["intra_batch_uniqueness"] == pytest.approx(1.0)
    assert data["standout_score"] == pytest.approx(min(0.7, 1.0), abs=1e-6)


def test_intra_batch_scores_idempotent(tmp_path):
    """Running compute_intra_batch_scores twice produces identical YAML."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "aired").mkdir()

    from dein_zeugs.paths import ProjectPaths

    dup_a = _unit(np.array([1.0, 0.01, 0.0]))
    dup_b = _unit(np.array([1.0, 0.02, 0.0]))
    unique = _unit(np.array([0.0, 0.0, 1.0]))

    for stem, emb in [("dup_a", dup_a), ("dup_b", dup_b), ("unique_q", unique)]:
        (tmp_path / "inbox" / f"{stem}.mp3").touch()
        _write_fake_yaml(tmp_path / "analysis", stem, emb, novelty=1.0)

    paths = ProjectPaths(root=tmp_path)

    compute_intra_batch_scores(paths, aired_stems=set())
    # Snapshot YAML contents after first run.
    first_pass = {
        stem: (tmp_path / "analysis" / f"{stem}.yaml").read_text(encoding="utf-8")
        for stem in ("dup_a", "dup_b", "unique_q")
    }

    compute_intra_batch_scores(paths, aired_stems=set())
    # Second run must not change any file.
    for stem in ("dup_a", "dup_b", "unique_q"):
        second = (tmp_path / "analysis" / f"{stem}.yaml").read_text(encoding="utf-8")
        assert second == first_pass[stem], f"YAML changed on second run for {stem}"
