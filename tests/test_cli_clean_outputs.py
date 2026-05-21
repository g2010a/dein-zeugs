import os
import pytest
from pathlib import Path
from unittest.mock import patch

os.environ["PODQ_NO_OPEN"] = "1"


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "podq_root"
    root.mkdir()
    for d in ["inbox", "transcripts", "analysis", "reports"]:
        (root / d).mkdir()
    (root / "inbox" / "episode.mp3").touch()
    (root / "transcripts" / "episode.txt").write_text("hello")
    (root / "analysis" / "episode.json").write_text("{}")
    (root / "reports" / "report.html").write_text("<html/>")
    return root


def test_clean_outputs_removes_output_files(tmp_path):
    root = _make_root(tmp_path)
    from podq.cli import main
    result = main([str(root), "--clean-outputs", "--yes"])
    assert result == 0
    assert not (root / "transcripts" / "episode.txt").exists()
    assert not (root / "analysis" / "episode.json").exists()
    assert not (root / "reports" / "report.html").exists()


def test_clean_outputs_preserves_inbox(tmp_path):
    root = _make_root(tmp_path)
    from podq.cli import main
    main([str(root), "--clean-outputs", "--yes"])
    assert (root / "inbox" / "episode.mp3").exists()


def test_clean_outputs_recreates_empty_dirs(tmp_path):
    root = _make_root(tmp_path)
    from podq.cli import main
    main([str(root), "--clean-outputs", "--yes"])
    assert (root / "transcripts").is_dir()
    assert (root / "analysis").is_dir()
    assert (root / "reports").is_dir()


def test_clean_outputs_respects_config_dirs(tmp_path):
    root = tmp_path / "custom_root"
    root.mkdir()
    (root / "inbox").mkdir()
    (root / "inbox" / "ep.mp3").touch()
    (root / "my_transcripts").mkdir()
    (root / "my_transcripts" / "ep.txt").write_text("hello")
    (root / "config.toml").write_text(
        "[paths]\ntranscripts_dir = \"my_transcripts\"\n"
    )
    from podq.cli import main
    result = main([str(root), "--clean-outputs", "--yes"])
    assert result == 0
    assert not (root / "my_transcripts" / "ep.txt").exists()
    assert (root / "my_transcripts").is_dir()


def test_cli_clean_outputs_flag_calls_clean_outputs():
    """--clean-outputs calls clean_outputs with a ProjectPaths and returns 0."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with patch("podq.cli.clean_outputs") as mock_clean:
            from podq.cli import main
            result = main([str(root), "--clean-outputs"])
        assert result == 0
        mock_clean.assert_called_once()
        args, kwargs = mock_clean.call_args
        from podq.paths import ProjectPaths
        assert isinstance(args[0], ProjectPaths)
        assert kwargs.get("yes", False) is False
