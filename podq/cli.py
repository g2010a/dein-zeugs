import fcntl
import os
import subprocess
import sys
import traceback
from pathlib import Path

from podq.config import Config
from podq.paths import ProjectPaths, unprocessed_aired_audio
from podq.analysis import process_all_unprocessed
from podq.embedding import EmbeddingModel
from podq.models import ensure_llm_model, ensure_whisper_model, patch_tqdm, clean_downloads, clean_outputs
from podq.report import render_report


def _reconfigure_streams() -> None:
    for stream in (sys.stderr, sys.stdout):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass


def _open_report(report_path: Path) -> None:
    if os.environ.get("PODQ_NO_OPEN"):
        return
    try:
        subprocess.run(["open", str(report_path)], check=False)
    except Exception:
        pass


def _render_getting_started(paths: ProjectPaths) -> Path:
    from jinja2 import Environment, FileSystemLoader

    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("getting_started.html.j2")
    html = template.render(inbox_path=str(paths.inbox))
    report_path = paths.reports / "report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    return report_path


def main(argv=None):
    _reconfigure_streams()

    import argparse
    from podq.util.logging import setup_logging
    log = setup_logging()

    parser = argparse.ArgumentParser(
        description="podq — Podcast-Fragen-Verwalter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Erwartete Verzeichnisstruktur:\n"
            "  {root}/inbox/         MP3-Episoden hier ablegen\n"
            "  {root}/analysis/      Automatisch erstellte YAML-Analysen (inkl. Transkript)\n"
            "  {root}/reports/       HTML-Berichtausgabe\n"
            "  {root}/aired/         Bereits ausgestrahlte Episoden hierher verschieben\n"
            "\n"
            "Ohne Angabe eines Wurzelverzeichnisses verwendet podq standardmäßig ~/Podq/ und legt fehlende Unterverzeichnisse automatisch an."
        ),
    )
    parser.add_argument(
        "root", nargs="?",
        help="Wurzelverzeichnis des Projekts (Standard: ~/Podq). Wird inklusive Unterverzeichnissen automatisch angelegt.",
    )
    parser.add_argument("--warm-models", action="store_true", help="Modell-Cache vorab aufwärmen und dann beenden")
    parser.add_argument("--skip-llm", action="store_true", help="Beim Aufwärmen das LLM-Modell überspringen (nur mit --warm-models sinnvoll)")
    parser.add_argument("--clean-downloads", action="store_true", help="Heruntergeladene Modelldateien löschen und dann beenden")
    parser.add_argument("--clean-outputs", action="store_true", help="Ausgabeverzeichnisse leeren (analysis, reports), inbox/ bleibt erhalten")
    parser.add_argument("--yes", "-y", action="store_true", help="Bestätigungsabfrage überspringen")
    args = parser.parse_args(argv)

    # For model-management flags, load config from root if provided, else use defaults.
    if args.warm_models or args.clean_downloads:
        config = _load_config_optional(args.root)
        if args.warm_models:
            _warm_models(log, config, skip_llm=args.skip_llm)
        else:
            clean_downloads(config, yes=args.yes)
        return 0

    # Default the root to ~/Podq when not provided (no model-management flag was set above).
    if args.root:
        root = Path(args.root).resolve()
    else:
        root = (Path.home() / "Podq").resolve()

    if args.clean_outputs:
        config = _load_config_optional(str(root))
        paths = ProjectPaths(root, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
        clean_outputs(paths, yes=args.yes)
        return 0

    try:
        root.mkdir(parents=True, exist_ok=True)
        config = Config.load_or_create(root)
        paths = ProjectPaths(root, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
        paths.ensure_dirs()

        # If there is nothing to process (no inbox MP3s and no unanalyzed aired items),
        # render the Getting Started welcome page and exit.
        mp3s = list(paths.inbox.glob("*.mp3")) if paths.inbox.exists() else []
        if not mp3s and not unprocessed_aired_audio(paths):
            report_path = _render_getting_started(paths)
            _open_report(report_path)
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
                processed = process_all_unprocessed(paths, config, embedding_model)
                log.info(f"Drain pass {i+1}: processed={processed}")
                if processed == 0:
                    break

            render_report(paths, config)
            _open_report(paths.reports / "report.html")
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


def _warm_models(log, config: Config, skip_llm: bool = False):
    print("Modell-Cache wird vorbereitet...", flush=True)

    try:
        import huggingface_hub
        huggingface_hub.enable_progress_bars()
    except Exception:
        pass

    total_stages = 2 if skip_llm else 3

    print(f"[1/{total_stages}] Whisper-Modell '{config.whisper_model}' (wird beim ersten Mal heruntergeladen)...", flush=True)
    try:
        ensure_whisper_model(config.whisper_model)
        from faster_whisper import WhisperModel
        patch_tqdm()
        WhisperModel(config.whisper_model, device="cpu", compute_type="int8")
        print(f"[1/{total_stages}] Whisper bereit.", flush=True)
    except Exception as e:
        print(f"[1/{total_stages}] Whisper fehlgeschlagen: {e}", flush=True)
        log.warning(f"Whisper warm failed: {e}")

    print(f"[2/{total_stages}] Einbettungsmodell '{config.embedding_model}' (wird beim ersten Mal heruntergeladen)...", flush=True)
    try:
        from fastembed import TextEmbedding
        patch_tqdm()
        TextEmbedding(config.embedding_model)
        print(f"[2/{total_stages}] Einbettungsmodell bereit.", flush=True)
    except Exception as e:
        print(f"[2/{total_stages}] Einbettungsmodell fehlgeschlagen: {e}", flush=True)
        log.warning(f"Embedding warm failed: {e}")

    if skip_llm:
        print("Fertig. LLM-Modell wurde übersprungen (--skip-llm).", flush=True)
        return

    print(f"[3/{total_stages}] LLM-Modell (~2 GB, wird beim ersten Mal heruntergeladen)...", flush=True)
    try:
        ensure_llm_model(config.llm_model_path)
        print(f"[3/{total_stages}] LLM-Modell bereit.", flush=True)
    except Exception as e:
        print(f"[3/{total_stages}] LLM-Modell fehlgeschlagen: {e}", flush=True)
        log.warning(f"LLM warm failed: {e}")

    print("Fertig.", flush=True)


def _write_error_report(root: Path, tb: str):
    try:
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        html = (
            "<html><body>"
            "<h1>podq fehlgeschlagen</h1>"
            f"<pre>{tb}</pre>"
            "<p>Details unter ~/Library/Logs/podq/podq.log</p>"
            "</body></html>"
        )
        (reports / "report.html").write_text(html)
        _open_report(reports / "report.html")
    except Exception:
        pass
