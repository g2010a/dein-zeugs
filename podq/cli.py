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
from podq.models import ensure_llm_model, ensure_whisper_model, patch_tqdm, clean_downloads, clean_outputs
from podq.report import render_report


def main(argv=None):
    import argparse
    from podq.util.logging import setup_logging
    log = setup_logging()

    parser = argparse.ArgumentParser(
        description="podq — Podcast-Fraag-Verwolter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Erwartete Verzeichnisstruktur:\n"
            "  {root}/inbox/        MP3-Episoden hier ablegen\n"
            "  {root}/transcripts/  Automatisch erstellte Transkripte\n"
            "  {root}/analysis/     Automatisch erstellte Analyse-JSON\n"
            "  {root}/reports/      HTML-Berichtausgabe\n"
            "\n"
            "podq legt kein inbox/ an – bitte selbst anlegen und MP3-Dateien hineinstellen, bevor podq gestartet wird."
        ),
    )
    parser.add_argument(
        "root", nargs="?",
        help="Wurzelverzeichnis des Projekts (muss ein inbox/-Unterverzeichnis mit MP3-Dateien enthalten)",
    )
    parser.add_argument("--warm-models", action="store_true", help="Modell-Cache aufwärmen und dann beenden")
    parser.add_argument("--clean-downloads", action="store_true", help="Heruntergeladene Modelldateien löschen und dann beenden")
    parser.add_argument("--clean-outputs", action="store_true", help="Ausgabeverzeichnisse leeren (transcripts, analysis, reports), inbox/ bleibt erhalten")
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

    if args.clean_outputs:
        config = _load_config_optional(args.root)
        paths = ProjectPaths(root, transcripts_dir=config.transcripts_dir, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
        clean_outputs(paths, yes=args.yes)
        return 0

    try:
        config = Config.load_or_create(root)
        paths = ProjectPaths(root, transcripts_dir=config.transcripts_dir, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
        paths.ensure_dirs()

        if not paths.inbox.exists():
            print(f"Kein inbox-Verzeichnis bei {paths.inbox} gefunden.")
            print("Bitte anlegen und MP3-Dateien hineinstellen, dann podq erneut ausführen.")
            print("'podq --help' für die Verzeichnisübersicht ausführen.")
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
    print("Modell-Cache wird aufgewärmt...", flush=True)

    patch_tqdm()

    print(f"[1/2] Whisper-Modell '{config.whisper_model}' (wird beim ersten Mal heruntergeladen)...", flush=True)
    try:
        ensure_whisper_model(config.whisper_model)
        from faster_whisper import WhisperModel
        WhisperModel(config.whisper_model, device="cpu", compute_type="int8")
        print("[1/2] Whisper bereit.", flush=True)
    except Exception as e:
        print(f"[1/2] Whisper fehlgeschlagen: {e}", flush=True)
        log.warning(f"Whisper warm failed: {e}")

    print(f"[2/2] Einbettungsmodell '{config.embedding_model}' (wird beim ersten Mal heruntergeladen)...", flush=True)
    try:
        from fastembed import TextEmbedding
        TextEmbedding(config.embedding_model)
        print("[2/2] Einbettungsmodell bereit.", flush=True)
    except Exception as e:
        print(f"[2/2] Einbettungsmodell fehlgeschlagen: {e}", flush=True)
        log.warning(f"Embedding warm failed: {e}")

    print("Fertig. LLM-Modell (~2 GB) wird beim ersten Einsatz automatisch heruntergeladen.", flush=True)


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
