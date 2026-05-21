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


def test_cli_report_rendered_on_empty_inbox(tmp_path):
    """Report is rendered even when inbox is empty."""
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

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.process_all_unprocessed", return_value=0), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=mock_embedding):

        from podq.cli import main
        result = main([str(root)])
        assert result == 0
        assert len(render_calls) == 1


def test_cli_warm_models_exits_early(tmp_path):
    """--warm-models flag returns 0 without requiring root."""
    with patch("podq.cli._warm_models") as mock_warm:
        from podq.cli import main
        result = main(["--warm-models"])
        assert result == 0
        mock_warm.assert_called_once()


def test_cli_missing_root_exits_nonzero():
    """Calling main with no root and no --warm-models should call parser.error."""
    from podq.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_cli_exception_returns_1(tmp_path):
    """Top-level exception causes exit code 1 and error report written."""
    root = tmp_path / "err_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)

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
    """If root exists but inbox/ does not, exit 0 before downloading any model."""
    root = tmp_path / "no_inbox_root"
    root.mkdir()

    with patch("podq.cli.ensure_llm_model") as mock_llm:
        from podq.cli import main
        result = main([str(root)])
    assert result == 0
    mock_llm.assert_not_called()
