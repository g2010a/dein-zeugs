import os
from pathlib import Path
from unittest.mock import patch

os.environ["DEIN_ZEUGS_NO_OPEN"] = "1"


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "dein_zeugs_root"
    root.mkdir()
    for d in ["inbox", "analysis", "reports"]:
        (root / d).mkdir()
    (root / "inbox" / "episode.mp3").touch()
    (root / "analysis" / "episode.json").write_text("{}")
    (root / "reports" / "report.html").write_text("<html/>")
    return root


def test_clean_outputs_removes_output_files(tmp_path):
    root = _make_root(tmp_path)
    from dein_zeugs.cli import main
    result = main([str(root), "--clean-outputs", "--yes"])
    assert result == 0
    assert not (root / "analysis" / "episode.json").exists()
    assert not (root / "reports" / "report.html").exists()


def test_clean_outputs_preserves_inbox(tmp_path):
    root = _make_root(tmp_path)
    from dein_zeugs.cli import main
    main([str(root), "--clean-outputs", "--yes"])
    assert (root / "inbox" / "episode.mp3").exists()


def test_clean_outputs_recreates_empty_dirs(tmp_path):
    root = _make_root(tmp_path)
    from dein_zeugs.cli import main
    main([str(root), "--clean-outputs", "--yes"])
    assert (root / "analysis").is_dir()
    assert (root / "reports").is_dir()


def test_clean_outputs_respects_config_dirs(tmp_path):
    root = tmp_path / "custom_root"
    root.mkdir()
    (root / "inbox").mkdir()
    (root / "inbox" / "ep.mp3").touch()
    (root / "my_analysis").mkdir()
    (root / "my_analysis" / "ep.yaml").write_text("stem: ep\n")
    (root / "config.toml").write_text(
        "[paths]\nanalysis_dir = \"my_analysis\"\n"
    )
    from dein_zeugs.cli import main
    result = main([str(root), "--clean-outputs", "--yes"])
    assert result == 0
    assert not (root / "my_analysis" / "ep.yaml").exists()
    assert (root / "my_analysis").is_dir()


def test_cli_clean_outputs_flag_calls_clean_outputs():
    """--clean-outputs calls clean_outputs with a ProjectPaths and returns 0."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with patch("dein_zeugs.cli.clean_outputs") as mock_clean:
            from dein_zeugs.cli import main
            result = main([str(root), "--clean-outputs"])
        assert result == 0
        mock_clean.assert_called_once()
        args, kwargs = mock_clean.call_args
        from dein_zeugs.paths import ProjectPaths
        assert isinstance(args[0], ProjectPaths)
        assert kwargs.get("yes", False) is False
