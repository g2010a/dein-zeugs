import logging
import urllib.request
from pathlib import Path

log = logging.getLogger("podq")

_MODEL_DIR = Path.home() / ".podq" / "models"
_MODEL_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
_MODEL_URL = (
    "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF"
    "/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)


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
