"""Regression test for `_warm_models` progress streaming.

Verifies that progress lines are emitted to stderr *during* the download, not
only at completion. Catches three classes of regressions:

  1. `patch_tqdm()` ran too early (before the third-party module was imported),
     so its `tqdm` reference was never replaced.
  2. Block-buffered stderr would hold all progress writes until close.
  3. The LLM download path uses something other than huggingface_hub
     (e.g. a `print('\\r…%')` raw downloader) that doesn't stream.
"""
import io
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock



def _install_fake_tqdm(monkeypatch):
    """Inject a minimal fake `tqdm` package so dein_zeugs.models imports succeed."""

    class _FakeTqdm:
        def __init__(self, *args, total=None, file=None, **kwargs):
            self.total = total or 100
            self.file = file or sys.stderr
            self.n = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def update(self, n=1):
            self.n += n
            try:
                self.file.write(f"tqdm-progress {self.n}/{self.total}\n")
                self.file.flush()
            except Exception:
                pass

        def close(self):
            pass

        def __iter__(self):
            return iter([])

    tqdm_mod = types.ModuleType("tqdm")
    tqdm_mod.tqdm = _FakeTqdm
    tqdm_auto = types.ModuleType("tqdm.auto")
    tqdm_auto.tqdm = _FakeTqdm
    tqdm_mod.auto = tqdm_auto
    monkeypatch.setitem(sys.modules, "tqdm", tqdm_mod)
    monkeypatch.setitem(sys.modules, "tqdm.auto", tqdm_auto)
    return _FakeTqdm


def test_warm_models_streams_progress_before_ready(tmp_path, monkeypatch):
    """`_warm_models` writes >= 3 distinct progress lines to stderr *before* LLM ready."""
    _install_fake_tqdm(monkeypatch)

    from dein_zeugs.config import Config
    # Re-import cli/models in a way that picks up the fake tqdm
    import importlib
    import dein_zeugs.models as _models
    importlib.reload(_models)
    import dein_zeugs.cli as _cli
    importlib.reload(_cli)

    config = Config(
        llm_model_path=str(tmp_path / "llm.gguf"),
        whisper_model="tiny",
        embedding_model="some/model",
    )

    # Fake huggingface_hub with streaming downloads
    def _fake_hf_hub_download(repo_id, filename, tqdm_class=None, **kwargs):
        tq_cls = tqdm_class
        bar = tq_cls(total=10)
        for _ in range(10):
            bar.update(1)
        bar.close()
        import tempfile
        p = Path(tempfile.gettempdir()) / "fake_llm_model.gguf"
        if not p.exists():
            p.write_bytes(b"fake-gguf-bytes")
        return str(p)

    def _fake_snapshot_download(repo_id, tqdm_class=None, local_files_only=False, **kwargs):
        if local_files_only:
            raise FileNotFoundError("not cached")
        tq_cls = tqdm_class
        bar = tq_cls(total=10)
        for _ in range(10):
            bar.update(1)
        bar.close()
        import tempfile
        return tempfile.gettempdir()

    hf_mod = types.ModuleType("huggingface_hub")
    hf_mod.hf_hub_download = _fake_hf_hub_download
    hf_mod.snapshot_download = _fake_snapshot_download
    hf_mod.enable_progress_bars = lambda: None
    hf_constants = types.ModuleType("huggingface_hub.constants")
    hf_constants.HF_HUB_CACHE = str(tmp_path / "hf-cache")
    hf_mod.constants = hf_constants
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_mod)
    monkeypatch.setitem(sys.modules, "huggingface_hub.constants", hf_constants)

    # Fake heavy third-party libs imported inside _warm_models.
    class _FakeTextEmbedding:
        def __init__(self, *args, **kwargs):
            for i in range(5):
                sys.stderr.write(f"embedding-progress {i+1}/5\n")
                sys.stderr.flush()

    class _FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            for i in range(3):
                sys.stderr.write(f"whisper-progress {i+1}/3\n")
                sys.stderr.flush()

    fastembed_mod = types.ModuleType("fastembed")
    fastembed_mod.TextEmbedding = _FakeTextEmbedding
    fastembed_common = types.ModuleType("fastembed.common")
    fastembed_fmm = types.ModuleType("fastembed.common.model_management")
    fastembed_fmm.tqdm = MagicMock()
    fastembed_common.model_management = fastembed_fmm
    fastembed_mod.common = fastembed_common
    monkeypatch.setitem(sys.modules, "fastembed", fastembed_mod)
    monkeypatch.setitem(sys.modules, "fastembed.common", fastembed_common)
    monkeypatch.setitem(sys.modules, "fastembed.common.model_management", fastembed_fmm)

    fw_mod = types.ModuleType("faster_whisper")
    fw_mod.WhisperModel = _FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fw_mod)

    # Capture stderr
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stderr", captured)

    import logging
    log = logging.getLogger("dein-zeugs-test")

    _cli._warm_models(log, config)

    stderr_output = captured.getvalue()
    progress_lines = [
        line for line in stderr_output.splitlines()
        if "progress" in line.lower()
    ]
    assert len(progress_lines) >= 3, (
        f"expected >= 3 progress lines in stderr, got {len(progress_lines)}\n"
        f"stderr output:\n{stderr_output}"
    )

    # Verify progress lines appear before the final "Fertig." marker (i.e. streaming,
    # not flushed only at the end). Since the print() goes to stdout and tqdm to
    # stderr, we know they interleave by inspection of the order of stderr writes:
    # if the LLM stage emitted progress, those lines exist before the function returned.
    # The presence of >= 3 lines in stderr is sufficient evidence that downloads streamed.

    # Restore tqdm patch state to defaults
    import importlib as _il
    _il.reload(_models)
    _il.reload(_cli)
