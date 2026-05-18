import fcntl
import logging
import os
import traceback
from pathlib import Path

from podq.config import Config
from podq.paths import ProjectPaths
from podq.transcription import transcribe_all_unprocessed
from podq.analysis import analyze_all_unanalyzed
from podq.embedding import EmbeddingModel
from podq.report import render_report


def main(argv=None):
    import argparse
    from podq.util.logging import setup_logging
    log = setup_logging()

    parser = argparse.ArgumentParser(description="podq — podcast question manager")
    parser.add_argument("root", nargs="?", help="Root directory")
    parser.add_argument("--warm-models", action="store_true", help="Pre-warm model caches and exit")
    args = parser.parse_args(argv)

    if args.warm_models:
        _warm_models(log)
        return 0

    if not args.root:
        parser.error("root directory required")

    root = Path(args.root).resolve()

    try:
        paths = ProjectPaths(root)
        paths.ensure_dirs()
        config = Config.load_or_create(root)

        lock_path = root / ".podq.lock"
        lock_file = open(lock_path, "w")
        try:
            # flock: if another instance holds it, exit immediately.
            # Invariant: lock-holder completes at least one drain pass after any competing
            # instance exits on lock-contention (competing instances exit before writing to inbox).
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log.info("Another podq instance is running, exiting.")
            return 0

        try:
            embedding_model = EmbeddingModel(config.embedding_model)

            MAX_DRAIN = 10
            for i in range(MAX_DRAIN):
                transcribed = transcribe_all_unprocessed(paths, config)
                analyzed = analyze_all_unanalyzed(paths, config, embedding_model)
                log.info(f"Drain pass {i+1}: transcribed={transcribed}, analyzed={analyzed}")
                if transcribed == 0 and analyzed == 0:
                    break

            render_report(paths, config)
            return 0
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    except Exception:
        tb = traceback.format_exc()
        try:
            log.error(f"podq failed:\n{tb}")
        except Exception:
            pass
        _write_error_report(root, tb)
        return 1


def _warm_models(log):
    log.info("Warming model caches...")
    try:
        import whisper
        whisper.load_model("medium")
        log.info("Whisper medium loaded.")
    except Exception as e:
        log.warning(f"Whisper warm failed: {e}")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        log.info("Embedding model loaded.")
    except Exception as e:
        log.warning(f"Embedding warm failed: {e}")


def _write_error_report(root: Path, tb: str):
    import subprocess
    try:
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        html = (
            "<html><body>"
            "<h1>podq failed</h1>"
            f"<pre>{tb}</pre>"
            "<p>See ~/Library/Logs/podq/podq.log</p>"
            "</body></html>"
        )
        (reports / "report.html").write_text(html)
        if not os.environ.get("PODQ_NO_OPEN"):
            subprocess.run(["open", str(reports / "report.html")], check=False)
    except Exception:
        pass
