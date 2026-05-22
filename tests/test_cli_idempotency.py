import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["PODQ_NO_OPEN"] = "1"


def make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "podq_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    (root / "inbox" / "caller_001.mp3").touch()
    return root


def test_cli_idempotency(tmp_path):
    """Running main twice: first run does work, second run (already processed) skips work."""
    root = make_fixture_root(tmp_path)
    process_calls = []
    render_calls = []
    run_state = {"n": 0}

    def mock_process(paths, config, embedding_model):
        run_state["n"] += 1
        if run_state["n"] == 1:
            import yaml
            data = {"stem": "caller_001", "transcript": "Test question",
                    "summary": "Test", "keywords": [],
                    "similarity_score": 0.0, "novelty_score": 1.0,
                    "nearest_aired_stem": None, "embedding": [0.1] * 384,
                    "language": "de", "podq_version": "1.0.0",
                    "analyzed_at": "2026-05-18T00:00:00+00:00"}
            (paths.analysis / "caller_001.yaml").write_text(
                yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False))
            process_calls.append(1)
            return 1
        process_calls.append(0)
        return 0

    def mock_render(paths, config):
        render_calls.append(1)
        report = paths.reports / "report.html"
        report.write_text("<html>ok</html>")
        return report

    mock_embedding = MagicMock()

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.process_all_unprocessed", side_effect=mock_process), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=mock_embedding):

        from podq.cli import main

        result1 = main([str(root)])
        assert result1 == 0
        assert len(process_calls) >= 1
        assert len(render_calls) == 1

        process_calls.clear()
        render_calls.clear()

        result2 = main([str(root)])
        assert result2 == 0
        assert len(process_calls) >= 1
        assert len(render_calls) == 1
        assert process_calls[0] == 0


def test_cli_empty_inbox_renders_getting_started(tmp_path):
    """Empty inbox renders the Getting Started page (not render_report) and exits 0."""
    root = tmp_path / "empty_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)

    render_calls = []

    def mock_render(paths, config):
        render_calls.append(1)
        report = paths.reports / "report.html"
        report.write_text("<html>empty</html>")
        return report

    mock_embedding = MagicMock()

    with patch("podq.cli.ensure_llm_model") as mock_llm, \
         patch("podq.cli.process_all_unprocessed", return_value=0), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=mock_embedding):

        from podq.cli import main
        result = main([str(root)])
        assert result == 0
        # Getting Started page is rendered directly; render_report is NOT called.
        assert len(render_calls) == 0
        mock_llm.assert_not_called()
        report = root / "reports" / "report.html"
        assert report.exists()
        # Welcome content
        content = report.read_text(encoding="utf-8")
        assert "Willkommen" in content
        assert "inbox" in content


def test_cli_warm_models_exits_early(tmp_path):
    """--warm-models flag returns 0 without requiring root."""
    with patch("podq.cli._warm_models") as mock_warm:
        from podq.cli import main
        result = main(["--warm-models"])
        assert result == 0
        mock_warm.assert_called_once()


def test_cli_warm_models_skip_llm(tmp_path):
    """--warm-models --skip-llm passes skip_llm=True."""
    with patch("podq.cli._warm_models") as mock_warm:
        from podq.cli import main
        result = main(["--warm-models", "--skip-llm"])
        assert result == 0
        _, kwargs = mock_warm.call_args
        assert kwargs.get("skip_llm") is True


def test_cli_default_root_uses_home_podq(tmp_path, monkeypatch):
    """Calling main with no root defaults to ~/Podq and auto-creates the tree."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Path.home() also honours HOME on POSIX, but ensure expanduser/Path.home use tmp.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.process_all_unprocessed", return_value=0), \
         patch("podq.cli.render_report"), \
         patch("podq.cli.EmbeddingModel", return_value=MagicMock()):
        from podq.cli import main
        result = main([])
        assert result == 0
    # Auto-created the default root and subdirs
    default_root = tmp_path / "Podq"
    assert default_root.is_dir()
    assert (default_root / "inbox").is_dir()
    assert (default_root / "aired").is_dir()
    assert (default_root / "analysis").is_dir()
    assert (default_root / "reports").is_dir()


def test_cli_opens_report_on_success(tmp_path, monkeypatch):
    """When PODQ_NO_OPEN is unset, subprocess.run(['open', ...]) is invoked after render."""
    root = make_fixture_root(tmp_path)
    monkeypatch.delenv("PODQ_NO_OPEN", raising=False)

    def mock_render(paths, config):
        (paths.reports / "report.html").write_text("<html>ok</html>")
        return paths.reports / "report.html"

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.process_all_unprocessed", return_value=0), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=MagicMock()), \
         patch("podq.cli.subprocess.run") as mock_run:
        from podq.cli import main
        result = main([str(root)])
        assert result == 0
        # cli._open_report should have invoked subprocess.run with "open"
        calls = [c for c in mock_run.call_args_list if c.args and c.args[0] and c.args[0][0] == "open"]
        assert len(calls) >= 1

    # Reset for other tests
    os.environ["PODQ_NO_OPEN"] = "1"


def test_cli_no_open_env_suppresses_open(tmp_path, monkeypatch):
    """PODQ_NO_OPEN=1 prevents 'open' from being invoked."""
    root = make_fixture_root(tmp_path)
    monkeypatch.setenv("PODQ_NO_OPEN", "1")

    def mock_render(paths, config):
        (paths.reports / "report.html").write_text("<html>ok</html>")
        return paths.reports / "report.html"

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.process_all_unprocessed", return_value=0), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=MagicMock()), \
         patch("podq.cli.subprocess.run") as mock_run:
        from podq.cli import main
        result = main([str(root)])
        assert result == 0
        calls = [c for c in mock_run.call_args_list if c.args and c.args[0] and c.args[0][0] == "open"]
        assert len(calls) == 0


def test_cli_exception_returns_1(tmp_path):
    """Top-level exception causes exit code 1 and error report written."""
    root = make_fixture_root(tmp_path)

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.EmbeddingModel", side_effect=RuntimeError("model crash")):
        from podq.cli import main
        result = main([str(root)])
        assert result == 1


def test_cli_clean_downloads_flag():
    """--clean-downloads calls clean_downloads with a Config and returns 0."""
    with patch("podq.cli.clean_downloads") as mock_clean:
        from podq.cli import main
        result = main(["--clean-downloads"])
        assert result == 0
        mock_clean.assert_called_once()
        args, kwargs = mock_clean.call_args
        from podq.config import Config
        assert isinstance(args[0], Config)
        assert kwargs.get("yes", False) is False


def test_cli_no_inbox_exits_0_without_model_download(tmp_path):
    """If root exists but inbox/ does not, exit 0 (Getting Started) before downloading any model."""
    root = tmp_path / "no_inbox_root"
    root.mkdir()

    with patch("podq.cli.ensure_llm_model") as mock_llm:
        from podq.cli import main
        result = main([str(root)])
    assert result == 0
    mock_llm.assert_not_called()
    # ensure_dirs auto-creates the inbox now
    assert (root / "inbox").is_dir()
