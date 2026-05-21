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
from podq.models import ensure_llm_model, ensure_whisper_model, patch_tqdm, clean_downloads
from podq.report import render_report


def main(argv=None):
    import argparse
    from podq.util.logging import setup_logging
    log = setup_logging()

    parser = argparse.ArgumentParser(
        description="podq — Podcast-Fraag-Verwolter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Verwachten Orner-Üvversicht:\n"
            "  {root}/inbox/        Smiet hier MP3-Episoden rinner\n"
            "  {root}/transcripts/  Automaatsch makte Transskrippen\n"
            "  {root}/analysis/     Automaatsch makte Analyse-JSON\n"
            "  {root}/reports/      HTML-Bericht-Ütgoov\n"
            "\n"
            "podq leggt keen inbox/ an – maak em sülvst an un smiet MP3-Datein rinner, vördem du podq startest."
        ),
    )
    parser.add_argument(
        "root", nargs="?",
        help="Woortelmapp vum Projekt (mutt en inbox/-Unnermapp mit MP3-Datein enthoolen)",
    )
    parser.add_argument("--warm-models", action="store_true", help="Modellspeicher vörmaken un denn afgahn")
    parser.add_argument("--clean-downloads", action="store_true", help="Downloade Modelldatein wegsmieten un denn afgahn")
    parser.add_argument("--yes", "-y", action="store_true", help="Bestätigungsafraag överspringen")
    args = parser.parse_args(argv)

    # For model-management flags, load config from root if provided, else use defaults.
    if args.warm_models or args.clean_downloads:
        config = _load_config_optional(args.root)
        if args.warm_models:
            _warm_models(log, config)
        else:
            clean_downloads(config, yes=args.yes)
        return 0

    if not args.root:
        parser.error("root directory required")

    root = Path(args.root).resolve()

    try:
        paths = ProjectPaths(root)
        paths.ensure_dirs()
        config = Config.load_or_create(root)

        if not paths.inbox.exists():
            print(f"Keen inbox-Orner bi {paths.inbox} funnen.")
            print("Leg em an un smiet MP3-Datein rinner, denn loop podq nochmal.")
            print("Loop 'podq --help' för de Orner-Üvversicht.")
            return 0

        ensure_llm_model(config.llm_model_path)

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


def _load_config_optional(root_arg: str | None) -> Config:
    if root_arg:
        try:
            return Config.load_or_create(Path(root_arg).resolve())
        except Exception:
            pass
    return Config()


def _warm_models(log, config: Config):
    print("Modellspeicher warrt vörmakt...", flush=True)

    patch_tqdm()

    print(f"[1/2] Whisper-Modell '{config.whisper_model}' (kann bi't eerste Maol downloadt warrn)...", flush=True)
    try:
        ensure_whisper_model(config.whisper_model)
        from faster_whisper import WhisperModel
        WhisperModel(config.whisper_model, device="cpu", compute_type="int8")
        print("[1/2] Whisper klaar.", flush=True)
    except Exception as e:
        print(f"[1/2] Whisper misslungen: {e}", flush=True)
        log.warning(f"Whisper warm failed: {e}")

    print(f"[2/2] Embeddin-Modell '{config.embedding_model}' (kann bi't eerste Maol downloadt warrn)...", flush=True)
    try:
        from fastembed import TextEmbedding
        TextEmbedding(config.embedding_model)
        print("[2/2] Embeddin-Modell klaar.", flush=True)
    except Exception as e:
        print(f"[2/2] Embeddin misslungen: {e}", flush=True)
        log.warning(f"Embedding warm failed: {e}")

    print("Klaar. LLM-Modell (~2 GB) warrt bi't eerste Bruuk automaatsch downloadt.", flush=True)


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
