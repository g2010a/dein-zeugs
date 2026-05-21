import logging
import sys
import urllib.request
from pathlib import Path

log = logging.getLogger("podq")


def _make_forced_tqdm():
    import tqdm as _tqdm_module

    class _ForcedTqdm(_tqdm_module.tqdm):
        """Force tqdm display even when stdout/stderr is not a TTY (e.g. PyInstaller binary)."""
        def __init__(self, *args, **kwargs):
            kwargs['disable'] = False
            kwargs.setdefault('file', sys.stderr)
            kwargs.setdefault('dynamic_ncols', True)
            super().__init__(*args, **kwargs)

    return _ForcedTqdm


def patch_tqdm() -> None:
    """Monkey-patch tqdm so downloads inside third-party libs show progress bars."""
    import tqdm
    import tqdm.auto
    ForcedTqdm = _make_forced_tqdm()
    tqdm.tqdm = ForcedTqdm
    tqdm.auto.tqdm = ForcedTqdm
    # Patch already-imported fastembed internals if present
    try:
        import fastembed.common.model_management as _fmm
        if hasattr(_fmm, 'tqdm'):
            _fmm.tqdm = ForcedTqdm
    except Exception:
        pass

_MODEL_DIR = Path.home() / ".podq" / "models"
_MODEL_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
_MODEL_URL = (
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF"
    "/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)


def ensure_whisper_model(model_name: str = "medium") -> None:
    """Pre-download the faster-whisper model with a visible progress bar."""
    import huggingface_hub
    repo_id = f"Systran/faster-whisper-{model_name}"
    try:
        huggingface_hub.snapshot_download(repo_id, local_files_only=True)
        return  # already cached
    except Exception:
        pass
    log.info(f"Downloading Whisper {model_name} model...")
    huggingface_hub.enable_progress_bars()
    huggingface_hub.snapshot_download(repo_id, tqdm_class=_make_forced_tqdm())


def default_llm_path() -> str:
    return str(_MODEL_DIR / _MODEL_FILE)


def ensure_llm_model(model_path: str) -> str:
    path = Path(model_path)
    if path.exists():
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"Downloading LLM model to {path} (~2 GB, one-time)...")
    _download_with_progress(_MODEL_URL, path)
    log.info("Download complete.")
    return str(path)


def _download_with_progress(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    try:
        with urllib.request.urlopen(url) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1 << 20  # 1 MB
            with open(tmp, "wb") as f:
                while True:
                    data = resp.read(chunk_size)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if total:
                        pct = downloaded * 100 // total
                        print(
                            f"\r  {pct}% ({downloaded >> 20} MB / {total >> 20} MB)",
                            end="",
                            flush=True,
                        )
        print()
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
