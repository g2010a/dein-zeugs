import logging
import shutil
import sys
from pathlib import Path

log = logging.getLogger("dein_zeugs")


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

_MODEL_DIR = Path.home() / ".dein_zeugs" / "models"
_MODEL_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
_MODEL_REPO_ID = "bartowski/Llama-3.2-3B-Instruct-GGUF"


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

    import huggingface_hub
    huggingface_hub.enable_progress_bars()
    downloaded = huggingface_hub.hf_hub_download(
        repo_id=_MODEL_REPO_ID,
        filename=_MODEL_FILE,
        tqdm_class=_make_forced_tqdm(),
    )
    downloaded_path = Path(downloaded)
    if downloaded_path.resolve() != path.resolve():
        try:
            if path.exists() or path.is_symlink():
                path.unlink()
            path.symlink_to(downloaded_path)
        except OSError:
            shutil.copy2(downloaded_path, path)
    log.info("Download complete.")
    return str(path)


def _dir_size(path: Path) -> int:
    """Return total bytes of a file or directory tree, 0 if missing."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _fmt_size(nbytes: int) -> str:
    if nbytes >= 1 << 20:
        return f"{nbytes / (1 << 20):.1f} MB"
    return f"{nbytes >> 10} KB"


def clean_downloads(config, yes: bool = False) -> None:
    """Delete all downloaded model files, optionally prompting for confirmation."""
    import shutil

    try:
        import huggingface_hub.constants as _hfc
        hf_cache = Path(_hfc.HF_HUB_CACHE)
    except Exception:
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"

    llm_path = Path(config.llm_model_path)
    llm_tmp = llm_path.with_suffix(".tmp")

    emb_parts = config.embedding_model.split("/", 1)
    emb_dir_name = "models--" + "--".join(emb_parts)

    targets = [
        (llm_path, f"LLM model file ({llm_path.name})"),
        (llm_tmp, f"LLM temp orphan ({llm_tmp.name})"),
        (hf_cache / f"models--Systran--faster-whisper-{config.whisper_model}", f"Whisper model ({config.whisper_model})"),
        (hf_cache / emb_dir_name, f"Embedding model HF cache ({config.embedding_model})"),
        (Path.home() / ".cache" / "fastembed", "Embedding model fastembed cache"),
    ]

    present = [(p, label) for p, label in targets if p.exists()]
    if not present:
        print("Keine heruntergeladenen Modelle gefunden. Nichts zu löschen.")
        return

    print("Die folgenden Dateien werden gelöscht:")
    for path, label in present:
        print(f"  {label}: {path}  ({_fmt_size(_dir_size(path))})")

    if not yes:
        answer = input("Löschen? [j/N] ").strip().lower()
        if answer not in ("j", "y"):
            print("Abgebrochen.")
            return

    total_freed = 0
    failed = False
    for path, label in present:
        size = _dir_size(path)
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
            total_freed += size
            print(f"  {label} gelöscht ({_fmt_size(size)} freigegeben)")
        except Exception as e:
            print(f"  Fehler beim Löschen von {path}: {e}")
            failed = True

    print(f"\nInsgesamt freigegeben: {_fmt_size(total_freed)}")
    if failed:
        raise SystemExit(1)


def clean_outputs(paths, yes: bool = False) -> None:
    """Delete all generated output dirs (transcripts, analysis, reports), preserving inbox/."""
    import shutil

    targets = [
        (paths.analysis, "Analysis"),
        (paths.reports, "Reports"),
    ]

    present = [(p, label) for p, label in targets if p.exists()]
    if not present:
        print("Keine Ausgabedateien gefunden. Nichts zu löschen.")
        return

    print("Die folgenden Ausgabeverzeichnisse werden geleert:")
    for path, label in present:
        print(f"  {label}: {path}  ({_fmt_size(_dir_size(path))})")

    if not yes:
        answer = input("Leeren? [j/N] ").strip().lower()
        if answer not in ("j",):
            print("Abgebrochen.")
            return

    total_freed = 0
    failed = False
    for path, label in present:
        size = _dir_size(path)
        try:
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
            total_freed += size
            print(f"  {label} geleert ({_fmt_size(size)} freigegeben)")
        except Exception as e:
            print(f"  Fehler beim Leeren von {path}: {e}")
            failed = True

    print(f"\nInsgesamt freigegeben: {_fmt_size(total_freed)}")
    if failed:
        raise SystemExit(1)


