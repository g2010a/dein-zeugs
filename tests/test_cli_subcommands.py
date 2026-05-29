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
