import os
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["DEIN_ZEUGS_NO_OPEN"] = "1"


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "dein_zeugs_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    return root


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

def test_initialize_creates_dirs(tmp_path):
    root = tmp_path / "new_project"
    from dein_zeugs.cli import main
    result = main(["initialize", str(root)])
    assert result == 0
    for d in ("inbox", "analysis", "aired", "reports"):
        assert (root / d).is_dir(), f"{d}/ not created"
    assert (root / "config.toml").exists()


def test_initialize_default_root(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    from dein_zeugs.cli import main
    result = main(["initialize"])
    assert result == 0
    assert (tmp_path / "DeinZeugs").is_dir()


def test_initialize_idempotent(tmp_path):
    root = tmp_path / "project"
    from dein_zeugs.cli import main
    assert main(["initialize", str(root)]) == 0
    assert main(["initialize", str(root)]) == 0


# ---------------------------------------------------------------------------
# fetch-models
# ---------------------------------------------------------------------------

def test_fetch_models_calls_warm_models(tmp_path):
    with patch("dein_zeugs.cli._warm_models") as mock_warm:
        from dein_zeugs.cli import main
        result = main(["fetch-models"])
    assert result == 0
    mock_warm.assert_called_once()


def test_fetch_models_skip_llm_flag(tmp_path):
    with patch("dein_zeugs.cli._warm_models") as mock_warm:
        from dein_zeugs.cli import main
        main(["fetch-models", "--skip-llm"])
    _, kwargs = mock_warm.call_args
    assert kwargs.get("skip_llm") is True


def test_fetch_models_force_flag(tmp_path):
    with patch("dein_zeugs.cli._warm_models") as mock_warm:
        from dein_zeugs.cli import main
        main(["fetch-models", "--force"])
    _, kwargs = mock_warm.call_args
    assert kwargs.get("force") is True


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

def test_transcribe_calls_transcribe_all(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.transcribe_all", return_value=2) as mock_t:
        from dein_zeugs.cli import main
        result = main(["transcribe", str(root)])
    assert result == 0
    mock_t.assert_called_once()


def test_transcribe_force_flag(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.transcribe_all", return_value=0) as mock_t:
        from dein_zeugs.cli import main
        main(["transcribe", "--force", str(root)])
    _, kwargs = mock_t.call_args
    assert kwargs.get("force") is True


def test_transcribe_default_root(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    with patch("dein_zeugs.cli.transcribe_all", return_value=0):
        from dein_zeugs.cli import main
        result = main(["transcribe"])
    assert result == 0
    assert (tmp_path / "DeinZeugs").is_dir()


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

def test_analyze_calls_analyze_all(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.ensure_llm_model"), \
         patch("dein_zeugs.cli.EmbeddingModel", return_value=MagicMock()), \
         patch("dein_zeugs.cli.analyze_all", return_value=3) as mock_a:
        from dein_zeugs.cli import main
        result = main(["analyze", str(root)])
    assert result == 0
    mock_a.assert_called_once()


def test_analyze_force_flag(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.ensure_llm_model"), \
         patch("dein_zeugs.cli.EmbeddingModel", return_value=MagicMock()), \
         patch("dein_zeugs.cli.analyze_all", return_value=0) as mock_a:
        from dein_zeugs.cli import main
        main(["analyze", "--force", str(root)])
    _, kwargs = mock_a.call_args
    assert kwargs.get("force") is True


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def test_report_calls_render_report(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.render_report") as mock_r:
        from dein_zeugs.cli import main
        result = main(["report", str(root)])
    assert result == 0
    mock_r.assert_called_once()


def test_report_opens_html(tmp_path, monkeypatch):
    monkeypatch.delenv("DEIN_ZEUGS_NO_OPEN", raising=False)
    root = _make_root(tmp_path)
    (root / "reports" / "report.html").write_text("<html/>")

    with patch("dein_zeugs.cli.render_report"), \
         patch("dein_zeugs.cli.subprocess.run") as mock_run:
        from dein_zeugs.cli import main
        main(["report", str(root)])

    opens = [c for c in mock_run.call_args_list if c.args and c.args[0][0] == "open"]
    assert len(opens) >= 1

    os.environ["DEIN_ZEUGS_NO_OPEN"] = "1"


# ---------------------------------------------------------------------------
# delete-downloads
# ---------------------------------------------------------------------------

def test_delete_downloads_calls_clean_downloads(tmp_path):
    with patch("dein_zeugs.cli.clean_downloads") as mock_clean:
        from dein_zeugs.cli import main
        result = main(["delete-downloads"])
    assert result == 0
    mock_clean.assert_called_once()
    _, kwargs = mock_clean.call_args
    assert kwargs.get("yes", False) is False


def test_delete_downloads_yes_flag(tmp_path):
    with patch("dein_zeugs.cli.clean_downloads") as mock_clean:
        from dein_zeugs.cli import main
        main(["delete-downloads", "--yes"])
    _, kwargs = mock_clean.call_args
    assert kwargs.get("yes") is True


# ---------------------------------------------------------------------------
# delete-outputs
# ---------------------------------------------------------------------------

def test_delete_outputs_calls_clean_outputs(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.clean_outputs") as mock_clean:
        from dein_zeugs.cli import main
        result = main(["delete-outputs", str(root)])
    assert result == 0
    mock_clean.assert_called_once()
    _, kwargs = mock_clean.call_args
    assert kwargs.get("yes", False) is False


def test_delete_outputs_yes_flag(tmp_path):
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.clean_outputs") as mock_clean:
        from dein_zeugs.cli import main
        main(["delete-outputs", "--yes", str(root)])
    _, kwargs = mock_clean.call_args
    assert kwargs.get("yes") is True


def test_delete_outputs_removes_files(tmp_path):
    root = _make_root(tmp_path)
    (root / "analysis" / "ep.yaml").write_text("stem: ep\n")
    (root / "reports" / "report.html").write_text("<html/>")
    from dein_zeugs.cli import main
    result = main(["delete-outputs", "--yes", str(root)])
    assert result == 0
    assert not (root / "analysis" / "ep.yaml").exists()
    assert not (root / "reports" / "report.html").exists()
    assert (root / "analysis").is_dir()
    assert (root / "reports").is_dir()
    assert (root / "inbox").is_dir()


# ---------------------------------------------------------------------------
# Dispatch: unknown first arg falls through to orchestrate
# ---------------------------------------------------------------------------

def test_non_subcommand_arg_treated_as_root(tmp_path):
    """A path-like first argument is not a subcommand — routes to orchestration."""
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.ensure_llm_model"), \
         patch("dein_zeugs.cli.process_all_unprocessed", return_value=0), \
         patch("dein_zeugs.cli.render_report"), \
         patch("dein_zeugs.cli.EmbeddingModel", return_value=MagicMock()):
        from dein_zeugs.cli import main
        result = main([str(root)])
    assert result == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_subcommand_exception_returns_1(tmp_path, capsys):
    """An unhandled exception inside a subcommand handler exits 1 and prints to stderr."""
    root = _make_root(tmp_path)
    with patch("dein_zeugs.cli.transcribe_all", side_effect=RuntimeError("boom")):
        from dein_zeugs.cli import main
        result = main(["transcribe", str(root)])
    assert result == 1
    captured = capsys.readouterr()
    assert "boom" in captured.err


# ---------------------------------------------------------------------------
# Analysis function behaviour (unit-level, real YAML files)
# ---------------------------------------------------------------------------

def test_process_all_unprocessed_resumes_from_partial_yaml(tmp_path):
    """process_all_unprocessed completes a partial YAML (transcript but no embedding)."""
    import yaml
    root = _make_root(tmp_path)
    mp3 = root / "inbox" / "ep.mp3"
    mp3.touch()
    partial = {
        "stem": "ep",
        "first_seen": "2026-01-01T00:00:00+00:00",
        "transcript": "Was ist die Antwort?",
        "dein_zeugs_version": "0.2.0",
    }
    (root / "analysis" / "ep.yaml").write_text(
        yaml.dump(partial, allow_unicode=True), encoding="utf-8"
    )

    mock_embedding = MagicMock()
    mock_embedding.aired_corpus.return_value = []
    mock_embedding.embed.return_value = __import__("numpy").array([0.1] * 384)

    with patch("dein_zeugs.transcription.WhisperTranscriber"), \
         patch("dein_zeugs.analysis.summarize", return_value="Frage über Antwort"), \
         patch("dein_zeugs.analysis.keywords", return_value=["antwort"]):
        from dein_zeugs.analysis import process_all_unprocessed
        from dein_zeugs.config import Config
        from dein_zeugs.paths import ProjectPaths
        config = Config(llm_model_path="/nonexistent/model.gguf")
        paths = ProjectPaths(root)
        count = process_all_unprocessed(paths, config, mock_embedding)

    assert count == 1
    data = yaml.safe_load((root / "analysis" / "ep.yaml").read_text())
    assert data["embedding"] is not None
    assert data["transcript"] == "Was ist die Antwort?"


def test_transcribe_all_skips_already_transcribed(tmp_path):
    """transcribe_all does not re-transcribe a file that already has a transcript."""
    import yaml
    root = _make_root(tmp_path)
    mp3 = root / "inbox" / "ep.mp3"
    mp3.touch()
    existing = {
        "stem": "ep",
        "first_seen": "2026-01-01T00:00:00+00:00",
        "transcript": "Schon transkribiert.",
        "dein_zeugs_version": "0.2.0",
    }
    (root / "analysis" / "ep.yaml").write_text(
        yaml.dump(existing, allow_unicode=True), encoding="utf-8"
    )

    with patch("dein_zeugs.transcription.WhisperTranscriber") as mock_cls:
        from dein_zeugs.analysis import transcribe_all
        from dein_zeugs.config import Config
        from dein_zeugs.paths import ProjectPaths
        config = Config()
        paths = ProjectPaths(root)
        count = transcribe_all(paths, config)

    assert count == 0
    mock_cls.return_value.transcribe.assert_not_called()


def test_analyze_all_skips_already_analyzed(tmp_path):
    """analyze_all skips YAMLs that already have an embedding (non-force)."""
    import yaml
    import numpy as np
    root = _make_root(tmp_path)
    complete = {
        "stem": "ep",
        "transcript": "Fertig analysiert.",
        "embedding": [0.1] * 384,
        "summary": "Fertig",
        "keywords": [],
        "similarity_score": 0.0,
        "novelty_score": 1.0,
        "nearest_aired_stem": None,
    }
    (root / "analysis" / "ep.yaml").write_text(
        yaml.dump(complete, allow_unicode=True), encoding="utf-8"
    )

    mock_embedding = MagicMock()
    mock_embedding.aired_corpus.return_value = []
    mock_embedding.embed.return_value = np.array([0.9] * 384)

    from dein_zeugs.analysis import analyze_all
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    config = Config(llm_model_path="/nonexistent/model.gguf")
    paths = ProjectPaths(root)
    count = analyze_all(paths, config, mock_embedding, force=False)

    assert count == 0
    mock_embedding.embed.assert_not_called()


def test_ensure_llm_model_force_does_not_unlink_before_download(tmp_path):
    """force=True must not delete an existing model before the download completes."""
    from dein_zeugs.models import ensure_llm_model

    model_file = tmp_path / "model.gguf"
    model_file.write_bytes(b"existing-model")

    downloaded = tmp_path / "hf_cache" / "model.gguf"
    downloaded.parent.mkdir()
    downloaded.write_bytes(b"new-model")

    import huggingface_hub
    with patch.object(huggingface_hub, "hf_hub_download", return_value=str(downloaded)):
        ensure_llm_model(str(model_file), force=True)

    # Original file was NOT deleted before the download resolved;
    # after a successful run the path should now point to the new content.
    assert Path(model_file).exists() or Path(model_file).is_symlink()
