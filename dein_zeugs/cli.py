import fcntl
import os
import subprocess
import sys
import traceback
from pathlib import Path

from dein_zeugs.config import Config
from dein_zeugs.paths import ProjectPaths, unprocessed_aired_audio
from dein_zeugs.analysis import process_all_unprocessed, transcribe_all, analyze_all, cluster_all
from dein_zeugs.embedding import EmbeddingModel
from dein_zeugs.models import ensure_llm_model, ensure_whisper_model, patch_tqdm, clean_downloads, clean_outputs
from dein_zeugs.report import render_report

_SUBCOMMANDS = frozenset({
    "initialize",
    "fetch-models",
    "transcribe",
    "analyze",
    "cluster",
    "report",
    "delete-downloads",
    "delete-outputs",
})


def _reconfigure_streams() -> None:
    for stream in (sys.stderr, sys.stdout):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass


def _open_report(report_path: Path) -> None:
    if os.environ.get("DEIN_ZEUGS_NO_OPEN"):
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


def _load_config_optional(root_arg: str | None) -> Config:
    if root_arg:
        try:
            return Config.load_or_create(Path(root_arg).resolve())
        except Exception as e:
            print(f"Warnung: Konfiguration konnte nicht geladen werden, verwende Standardwerte: {e}", file=sys.stderr)
    return Config()


def _resolve_root(root_arg: str | None) -> Path:
    if root_arg:
        return Path(root_arg).resolve()
    return (Path.home() / "DeinZeugs").resolve()


def _bootstrap(root_arg: str | None) -> tuple[Path, Config, ProjectPaths]:
    """Resolve root, load config, and build ProjectPaths. Shared by subcommand handlers."""
    root = _resolve_root(root_arg)
    root.mkdir(parents=True, exist_ok=True)
    config = Config.load_or_create(root)
    paths = ProjectPaths(root, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
    return root, config, paths



def _cmd_initialize(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs initialize",
        description="Verzeichnisstruktur und Konfigurationsdatei anlegen.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    args = p.parse_args(argv)

    root, config, paths = _bootstrap(args.root)
    paths.ensure_dirs()
    print(f"Initialisiert: {root}")
    return 0


def _cmd_fetch_models(argv: list[str]) -> int:
    import argparse
    from dein_zeugs.util.logging import setup_logging
    log = setup_logging()

    p = argparse.ArgumentParser(
        prog="dein-zeugs fetch-models",
        description="Modelle herunterladen und in den Cache laden.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis für Konfiguration (optional)")
    p.add_argument("--force", action="store_true", help="Bereits vorhandene Modelle erneut herunterladen")
    p.add_argument("--skip-llm", action="store_true", help="LLM-Modell überspringen")
    args = p.parse_args(argv)

    config = _load_config_optional(args.root)
    _warm_models(log, config, skip_llm=args.skip_llm, force=args.force)
    return 0


def _cmd_transcribe(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs transcribe",
        description="Audiodateien transkribieren und Transkripte speichern.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    p.add_argument("--force", action="store_true", help="Bereits transkribierte Dateien erneut verarbeiten")
    args = p.parse_args(argv)

    _root, config, paths = _bootstrap(args.root)
    paths.analysis.mkdir(parents=True, exist_ok=True)
    count = transcribe_all(paths, config, force=args.force)
    print(f"Transkribiert: {count} Datei(en)")
    return 0


def _cmd_analyze(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs analyze",
        description="Transkribierte Dateien analysieren (Zusammenfassung, Schlüsselwörter, Einbettung).",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    p.add_argument("--force", action="store_true", help="Bereits analysierte Dateien erneut verarbeiten")
    args = p.parse_args(argv)

    _root, config, paths = _bootstrap(args.root)
    ensure_llm_model(config.llm_model_path)
    embedding_model = EmbeddingModel(config.embedding_model)
    count = analyze_all(paths, config, embedding_model, force=args.force)
    print(f"Analysiert: {count} Datei(en)")
    return 0


def _cmd_cluster(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs cluster",
        description="Clustering neu berechnen und Bericht aktualisieren.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    args = p.parse_args(argv)

    _root, config, paths = _bootstrap(args.root)
    count = cluster_all(paths, config)
    print(f"Gruppiert: {count} Datei(en)")
    render_report(paths, config)
    _open_report(paths.reports / "report.html")
    return 0


def _cmd_report(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs report",
        description="HTML-Bericht aus vorhandenen Analysedaten erstellen.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    args = p.parse_args(argv)

    _root, config, paths = _bootstrap(args.root)
    render_report(paths, config)
    _open_report(paths.reports / "report.html")
    return 0


def _cmd_delete_downloads(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs delete-downloads",
        description="Heruntergeladene Modelldateien löschen.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis für Konfiguration (optional)")
    p.add_argument("--yes", "-y", action="store_true", help="Bestätigung überspringen")
    args = p.parse_args(argv)

    config = _load_config_optional(args.root)
    clean_downloads(config, yes=args.yes)
    return 0


def _cmd_delete_outputs(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="dein-zeugs delete-outputs",
        description="Ausgabeverzeichnisse leeren (analysis, reports). inbox/ bleibt erhalten.",
    )
    p.add_argument("root", nargs="?", help="Wurzelverzeichnis (Standard: ~/DeinZeugs)")
    p.add_argument("--yes", "-y", action="store_true", help="Bestätigung überspringen")
    args = p.parse_args(argv)

    _root, config, paths = _bootstrap(args.root)
    clean_outputs(paths, yes=args.yes)
    return 0



def _run_orchestrate(argv: list[str]) -> int:
    import argparse
    from dein_zeugs.util.logging import setup_logging
    log = setup_logging()

    parser = argparse.ArgumentParser(
        description="dein-zeugs — Podcast-Fragen-Verwalter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Erwartete Verzeichnisstruktur:\n"
            "  {root}/inbox/         MP3-Episoden hier ablegen\n"
            "  {root}/analysis/      Automatisch erstellte YAML-Analysen (inkl. Transkript)\n"
            "  {root}/reports/       HTML-Berichtausgabe\n"
            "  {root}/aired/         Bereits ausgestrahlte Episoden hierher verschieben\n"
            "\n"
            "Ohne Angabe eines Wurzelverzeichnisses verwendet dein-zeugs standardmäßig ~/DeinZeugs/ und legt fehlende Unterverzeichnisse automatisch an.\n"
            "\n"
            "Verfügbare Unterbefehle:\n"
            "  initialize          Verzeichnisstruktur anlegen\n"
            "  fetch-models        Modelle herunterladen\n"
            "  transcribe          Audiodateien transkribieren\n"
            "  analyze             Transkripte analysieren\n"
            "  cluster             Clustering neu berechnen und Bericht aktualisieren\n"
            "  report              HTML-Bericht erstellen\n"
            "  delete-downloads    Modelldateien löschen\n"
            "  delete-outputs      Ausgabeverzeichnisse leeren"
        ),
    )
    parser.add_argument(
        "root", nargs="?",
        help="Wurzelverzeichnis des Projekts (Standard: ~/DeinZeugs). Wird inklusive Unterverzeichnissen automatisch angelegt.",
    )
    args = parser.parse_args(argv)

    root = _resolve_root(args.root)

    try:
        root.mkdir(parents=True, exist_ok=True)
        config = Config.load_or_create(root)
        paths = ProjectPaths(root, analysis_dir=config.analysis_dir, reports_dir=config.reports_dir)
        paths.ensure_dirs()

        mp3s = list(paths.inbox.glob("*.mp3")) if paths.inbox.exists() else []
        if not mp3s and not unprocessed_aired_audio(paths):
            report_path = _render_getting_started(paths)
            _open_report(report_path)
            return 0

        ensure_llm_model(config.llm_model_path)

        lock_path = root / ".dein_zeugs.lock"
        lock_file = open(lock_path, "w")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log.info("Another dein-zeugs instance is running, exiting.")
            return 0

        try:
            embedding_model = EmbeddingModel(config.embedding_model)

            MAX_DRAIN = 10
            for i in range(MAX_DRAIN):
                processed = process_all_unprocessed(paths, config, embedding_model)
                log.info(f"Drain pass {i+1}: processed={processed}")
                if processed == 0:
                    break

            cluster_all(paths, config)
            render_report(paths, config)
            _open_report(paths.reports / "report.html")
            return 0
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    except Exception:
        tb = traceback.format_exc()
        try:
            log.error(f"dein-zeugs failed:\n{tb}")
        except Exception:
            pass
        _write_error_report(root, tb)
        return 1



def main(argv=None):
    _reconfigure_streams()
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] in _SUBCOMMANDS:
        cmd, rest = argv[0], argv[1:]
        dispatch = {
            "initialize": _cmd_initialize,
            "fetch-models": _cmd_fetch_models,
            "transcribe": _cmd_transcribe,
            "analyze": _cmd_analyze,
            "cluster": _cmd_cluster,
            "report": _cmd_report,
            "delete-downloads": _cmd_delete_downloads,
            "delete-outputs": _cmd_delete_outputs,
        }
        try:
            return dispatch[cmd](rest)
        except Exception:
            print(f"dein-zeugs {cmd} fehlgeschlagen:\n{traceback.format_exc()}", file=sys.stderr)
            return 1

    return _run_orchestrate(list(argv))


def _warm_models(log, config: Config, skip_llm: bool = False, force: bool = False):
    print("Modell-Cache wird vorbereitet...", flush=True)

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
        ensure_llm_model(config.llm_model_path, force=force)
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
            "<h1>Dein Zeugs fehlgeschlagen</h1>"
            f"<pre>{tb}</pre>"
            "<p>Details unter ~/Library/Logs/dein_zeugs/dein_zeugs.log</p>"
            "</body></html>"
        )
        (reports / "report.html").write_text(html)
        _open_report(reports / "report.html")
    except Exception:
        pass
