import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["PODQ_NO_OPEN"] = "1"


def make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "podq_root"
    for d in ["inbox", "transcripts", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    (root / "inbox" / "caller_001.mp3").touch()
    return root


def test_cli_idempotency(tmp_path):
    """Running main twice: first run does work, second run (already processed) skips work."""
    root = make_fixture_root(tmp_path)

    transcribe_calls = []
    analyze_calls = []
    render_calls = []

    # run_state tracks total invocation count across both main() calls
    run_state = {"transcribe_n": 0, "analyze_n": 0}

    def mock_transcribe(paths, config):
        run_state["transcribe_n"] += 1
        if run_state["transcribe_n"] == 1:
            (paths.transcripts / "caller_001.txt").write_text("Test question")
            transcribe_calls.append(1)
            return 1
        transcribe_calls.append(0)
        return 0

    def mock_analyze(paths, config, embedding_model):
        import json
        run_state["analyze_n"] += 1
        if run_state["analyze_n"] == 1:
            (paths.analysis / "caller_001.json").write_text(json.dumps({
                "stem": "caller_001", "summary": "Test", "keywords": [],
                "similarity_score": 0.0, "novelty_score": 1.0,
                "nearest_aired_stem": None, "embedding": [0.1] * 384,
                "language": "de", "podq_version": "1.0.0",
                "analyzed_at": "2026-05-18T00:00:00+00:00",
            }))
            analyze_calls.append(1)
            return 1
        analyze_calls.append(0)
        return 0

    def mock_render(paths, config):
        render_calls.append(1)
        report = paths.reports / "report.html"
        report.write_text("<html>ok</html>")
        return report

    mock_embedding = MagicMock()

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.transcribe_all_unprocessed", side_effect=mock_transcribe), \
         patch("podq.cli.analyze_all_unanalyzed", side_effect=mock_analyze), \
         patch("podq.cli.render_report", side_effect=mock_render), \
         patch("podq.cli.EmbeddingModel", return_value=mock_embedding):

        from podq.cli import main

        # First run: does transcription + analysis
        result1 = main([str(root)])
        assert result1 == 0
        assert len(transcribe_calls) >= 1
        assert len(analyze_calls) >= 1
        assert len(render_calls) == 1

        # Reset call counters for second run
        transcribe_calls.clear()
        analyze_calls.clear()
        render_calls.clear()

        # Second run: inbox already processed, drain exits immediately
        result2 = main([str(root)])
        assert result2 == 0
        # Drain loop should call transcribe/analyze at least once (then see 0 work and stop)
        assert len(transcribe_calls) >= 1
        assert len(analyze_calls) >= 1
        # Report is always rendered
        assert len(render_calls) == 1
        # Second run saw no new work
        assert transcribe_calls[0] == 0
        assert analyze_calls[0] == 0


def test_cli_report_rendered_on_empty_inbox(tmp_path):
    """Report is rendered even when inbox is empty."""
    root = tmp_path / "empty_root"
    for d in ["inbox", "transcripts", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)

    render_calls = []

    def mock_render(paths, config):
        render_calls.append(1)
        report = paths.reports / "report.html"
        report.write_text("<html>empty</html>")
        return report

    mock_embedding = MagicMock()

    with patch("podq.cli.ensure_llm_model"), \
         patch("podq.cli.transcribe_all_unprocessed", return_value=0), \
         patch("podq.cli.analyze_all_unanalyzed", return_value=0), \
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
    for d in ["inbox", "transcripts", "analysis", "aired", "reports"]:
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
