import logging
import yaml
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from dein_zeugs.util.atomic import atomic_write
from dein_zeugs.paths import ProjectPaths, normalize_stem
from dein_zeugs.embedding import EmbeddingModel
from dein_zeugs import __version__

log = logging.getLogger("dein_zeugs")

SUMMARY_PROMPT = ("""\
Du fasst Transkripte von Kinderfragen an einen Podcast in einem einzigen deutschen Satz zusammen. Nenne dabei, wer fragt (Name, Alter, Herkunft – nur falls angegeben) und was gefragt oder gewünscht wird.

Transkript: Hallo, ich bin Felix, ich bin acht Jahre alt und komme aus München. Meine Frage ist, mögt ihr lieber Pizza oder Pasta? Tschüss!
Zusammenfassung: Felix (8, München) fragt, ob Pizza oder Pasta bevorzugt wird.

Transkript: Hallo deine Freunde, hier ist Emma, ich bin neun Jahre alt und wollte fragen, was ihr am liebsten in eurer Freizeit macht. Tschüss, ihr seid super!
Zusammenfassung: Emma (9) möchte wissen, was die Gastgeber in ihrer Freizeit am liebsten machen.

Transkript: Hallo, ich bin Noah und bin zehn Jahre alt und komme aus Hamburg. Ich wollte euch fragen, was ihr macht, wenn ihr traurig seid. Danke und tschüss!
Zusammenfassung: Noah (10, Hamburg) fragt, wie die Gastgeber mit Traurigkeit umgehen.

Transkript: Hi deine Freunde, ich bin Theo, 9 Jahre alt, und ich wollte fragen: Wenn man rückwärts läuft, kommt man dann früher an? Tschüss!
Zusammenfassung: Theo (9) stellt die scherzhafte Frage, ob man rückwärts laufend schneller ans Ziel kommt.

Transkript: Hallo, ich bin Sarah aus Köln und finde euren Podcast richtig toll. Könnt ihr bitte meinen Bruder Tobi grüßen? Der würde sich so freuen! Tschüss!
Zusammenfassung: Sarah aus Köln lobt den Podcast und bittet darum, ihren Bruder Tobi zu grüßen.

Transkript: {transcript}
Zusammenfassung:\
""")

KEYWORDS_PROMPT = ("""\
Du extrahierst aus Podcast-Transkripten 4–6 aussagekräftige Schlüsselwörter auf Deutsch, die den Inhalt treffend charakterisieren. Verwende auch semantisch passende Begriffe, die nicht wörtlich im Transkript stehen – z. B. einen Oberbegriff, eine Kategorie oder ein verwandtes Konzept.

Transkript: Hallo, ich bin Felix, ich bin acht Jahre alt und komme aus München. Meine Frage ist, mögt ihr lieber Pizza oder Pasta? Tschüss!
Schlüsselwörter: Lieblingsessen, Präferenz, Pizza, Pasta, München

Transkript: Hallo deine Freunde, ich bin Marlene, ich bin elf Jahre alt und ich wollte euch fragen, was ihr so macht, wenn ihr wütend seid. Tschüss!
Schlüsselwörter: Wut, Emotionsregulation, Gefühle, Bewältigungsstrategie, Ratschlag

Transkript: Hi deine Freunde, ich bin Theo, 9 Jahre alt, und ich wollte fragen: Wenn man rückwärts läuft, kommt man dann früher an? Tschüss!
Schlüsselwörter: Denkrätsel, Logik, Bewegung, Humor, Paradoxon

Transkript: Hallo, ich bin Sarah aus Köln und finde euren Podcast richtig toll. Könnt ihr bitte meinen Bruder Tobi grüßen? Der würde sich so freuen! Tschüss!
Schlüsselwörter: Grußbotschaft, Geschwister, Fanbindung, Köln

Transkript: Hallo, mein Name ist Klara, ich bin zwölf und komme aus Dresden. Ich wollte fragen, wie ihr mit Lampenfieber umgeht, bevor ihr auf die Bühne geht. Das würde mir helfen, weil ich nächste Woche ein Schulreferat halten muss. Tschüss!
Schlüsselwörter: Lampenfieber, Auftrittsangst, Nervosität, Schulreferat, Tipps, Dresden

Transkript: {transcript}
Schlüsselwörter:\
""")

_llm_instance = None
_llm_error: Exception | None = None


def _get_llm(model_path: str):
    global _llm_instance, _llm_error
    if _llm_error is not None:
        raise _llm_error
    if _llm_instance is None:
        from llama_cpp import Llama
        try:
            _llm_instance = Llama(
                model_path=model_path,
                n_ctx=8192,
                n_threads=4,
                verbose=False,
            )
        except Exception as e:
            _llm_error = e
            raise
    return _llm_instance


def get_llm_error() -> str | None:
    return str(_llm_error) if _llm_error is not None else None


def _infer(prompt: str, model_path: str, max_tokens: int = 256, extra_stop: list[str] | None = None) -> str:
    was_known_error = _llm_error is not None
    try:
        llm = _get_llm(model_path)
        stop = ["\n\n", "###"] + (extra_stop or [])
        output = llm(prompt, max_tokens=max_tokens, stop=stop)
        return output["choices"][0]["text"].strip()
    except Exception as e:
        if not was_known_error:
            log.error(f"LLM inference failed: {e}")
        return ""


def summarize(text: str, model_path: str) -> str:
    return _infer(SUMMARY_PROMPT.format(transcript=text), model_path, max_tokens=100)


def keywords(text: str, model_path: str) -> list[str]:
    raw = _infer(KEYWORDS_PROMPT.format(transcript=text), model_path, max_tokens=64, extra_stop=["\n"])
    if not raw:
        return []
    parts = [p.strip().lower() for p in raw.replace("\n", ",").split(",") if p.strip()]
    return list(dict.fromkeys(parts))[:5]


def score(
    new_embedding: np.ndarray,
    aired_embeddings: list[tuple[str, np.ndarray]],
) -> tuple[float, float, str | None]:
    """Returns (similarity, novelty, nearest_aired_stem)."""
    if not aired_embeddings:
        return 0.0, 1.0, None
    sims = [(stem, float(np.dot(new_embedding, emb))) for stem, emb in aired_embeddings]
    best_stem, best_sim = max(sims, key=lambda x: x[1])
    best_sim = max(0.0, min(1.0, best_sim))
    return best_sim, round(1.0 - best_sim, 6), best_stem


def compute_intra_batch_scores(paths: ProjectPaths, aired_stems: set[str]) -> None:
    """Second pass: write intra_batch_uniqueness and standout_score to each unaired YAML.

    Safe to re-run: skips a file if both fields already match the computed values.
    """
    if not paths.analysis.exists():
        return

    # Collect (stem, embedding, yaml_path) for all unaired items that have a YAML.
    inbox_stems: set[str] = set()
    if paths.inbox.exists():
        for mp3 in paths.inbox.glob("*.mp3"):
            inbox_stems.add(normalize_stem(mp3.stem))

    batch_items: list[tuple[str, np.ndarray, Path]] = []
    for stem in inbox_stems:
        yaml_path = paths.analysis / f"{stem}.yaml"
        if not yaml_path.exists():
            continue
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "embedding" not in data:
            continue
        emb = np.array(data["embedding"], dtype=np.float32)
        batch_items.append((stem, emb, yaml_path))

    n = len(batch_items)

    for i, (stem, emb_i, yaml_path) in enumerate(batch_items):
        if n == 1:
            intra = 1.0
        else:
            max_sim = max(
                float(np.dot(emb_i, emb_j))
                for j, (_, emb_j, _) in enumerate(batch_items)
                if j != i
            )
            max_sim = max(0.0, min(1.0, max_sim))
            intra = round(1.0 - max_sim, 6)

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        novelty = data.get("novelty_score", 0.0)
        standout = round(min(float(novelty), intra), 6)

        # Idempotency: skip write if values are already correct.
        existing_intra = data.get("intra_batch_uniqueness")
        existing_standout = data.get("standout_score")
        if (
            existing_intra is not None
            and existing_standout is not None
            and abs(existing_intra - intra) < 1e-9
            and abs(existing_standout - standout) < 1e-9
        ):
            continue

        data["intra_batch_uniqueness"] = intra
        data["standout_score"] = standout

        yaml_bytes = yaml.dump(
            data, allow_unicode=True, default_flow_style=False, sort_keys=False
        ).encode("utf-8")
        atomic_write(yaml_path, yaml_bytes)
        log.info(f"Batch-Einzigartigkeit berechnet: {stem} → {intra:.4f}")


def _needs_full_analysis(directory: Path, paths: ProjectPaths) -> list[Path]:
    """MP3s that need analysis: no YAML at all, or YAML present but missing embedding."""
    if not directory.exists():
        return []
    result = []
    for mp3 in directory.glob("*.mp3"):
        stem = normalize_stem(mp3.stem)
        yaml_path = paths.analysis / f"{stem}.yaml"
        if not yaml_path.exists():
            result.append(mp3)
            continue
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not data or not data.get("embedding"):
                result.append(mp3)
        except Exception:
            result.append(mp3)
    return result


def _analyze_one(
    mp3: Path,
    stem: str,
    paths: ProjectPaths,
    config,
    transcriber,
    embedding_model: EmbeddingModel,
    aired_embeddings: list[tuple[str, np.ndarray]],
) -> np.ndarray:
    yaml_path = paths.analysis / f"{stem}.yaml"
    existing: dict = {}
    if yaml_path.exists():
        try:
            existing = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    # Reuse an existing transcript written by a prior `transcribe` step.
    text = existing.get("transcript") or transcriber.transcribe(mp3)
    first_seen = existing.get("first_seen") or datetime.fromtimestamp(
        mp3.stat().st_mtime, timezone.utc
    ).isoformat()

    emb = embedding_model.embed(text)
    sim, nov, nearest = score(emb, aired_embeddings)
    summary_text = summarize(text, config.llm_model_path)
    kws = keywords(text, config.llm_model_path)
    data: dict = {
        "stem": stem,
        "first_seen": first_seen,
        "transcript": text,
        "summary": summary_text,
        "keywords": kws,
        "similarity_score": sim,
        "novelty_score": nov,
        "nearest_aired_stem": nearest,
        "language": "auto",
        "dein_zeugs_version": __version__,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "embedding": emb.tolist(),
    }
    llm_err = get_llm_error()
    if llm_err:
        data["llm_error"] = llm_err
    yaml_bytes = yaml.dump(
        data, allow_unicode=True, default_flow_style=False, sort_keys=False
    ).encode("utf-8")
    atomic_write(yaml_path, yaml_bytes)
    return emb


def transcribe_all(paths: ProjectPaths, config, force: bool = False) -> int:
    """Transcribe audio and write partial YAMLs containing only the transcript.

    Already-transcribed files are skipped unless *force* is True, in which case
    the transcript is refreshed and any analysis fields are cleared so a
    subsequent ``analyze`` step starts from a clean slate.
    """
    from dein_zeugs.transcription import WhisperTranscriber
    transcriber = WhisperTranscriber(model_name=config.whisper_model)
    paths.analysis.mkdir(parents=True, exist_ok=True)

    count = 0
    for directory in (paths.inbox, paths.aired):
        if not directory.exists():
            continue
        for mp3 in sorted(directory.glob("*.mp3")):
            stem = normalize_stem(mp3.stem)
            yaml_path = paths.analysis / f"{stem}.yaml"

            if not force and yaml_path.exists():
                try:
                    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                    if data and data.get("transcript"):
                        continue
                except Exception:
                    pass

            log.info(f"Transkription: {mp3.name}")
            text = transcriber.transcribe(mp3)
            first_seen = datetime.fromtimestamp(mp3.stat().st_mtime, timezone.utc).isoformat()

            existing: dict = {}
            if yaml_path.exists():
                try:
                    existing = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    pass

            partial: dict = {
                "stem": stem,
                "first_seen": existing.get("first_seen", first_seen),
                "transcript": text,
                "dein_zeugs_version": __version__,
            }
            yaml_bytes = yaml.dump(
                partial, allow_unicode=True, default_flow_style=False, sort_keys=False
            ).encode("utf-8")
            atomic_write(yaml_path, yaml_bytes)
            count += 1

    return count


def analyze_all(
    paths: ProjectPaths,
    config,
    embedding_model: EmbeddingModel,
    force: bool = False,
) -> int:
    """Run LLM analysis on every YAML that has a transcript but no embedding yet.

    With *force*, re-analyze all transcribed YAMLs regardless of whether they
    already have an embedding.

    Aired items are processed before inbox items and their embeddings are
    progressively added to the reference corpus so that scoring matches the
    ordering semantics of the default orchestration.
    """
    if not paths.analysis.exists():
        return 0

    aired = embedding_model.aired_corpus(paths)
    aired_embeddings = [(stem, emb) for stem, _text, emb in aired]
    aired_stems = {stem for stem, _text, _emb in aired}

    # Determine which stems correspond to aired files so we can process them
    # first and grow the reference corpus progressively (matching the ordering
    # in process_all_unprocessed).
    aired_mp3_stems: set[str] = set()
    if paths.aired.exists():
        aired_mp3_stems = {normalize_stem(p.stem) for p in paths.aired.glob("*.mp3")}

    def _needs_analysis(data: dict) -> bool:
        return bool(data.get("transcript")) and (force or not data.get("embedding"))

    def _load_candidates() -> list[tuple[Path, dict]]:
        result = []
        for yaml_path in sorted(paths.analysis.glob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data and _needs_analysis(data):
                result.append((yaml_path, data))
        return result

    def _run_one(yaml_path: Path, data: dict) -> np.ndarray:
        stem = data.get("stem") or normalize_stem(yaml_path.stem)
        text = data["transcript"]
        log.info(f"Analyse: {stem}")

        emb = embedding_model.embed(text)
        sim, nov, nearest = score(emb, aired_embeddings)
        summary_text = summarize(text, config.llm_model_path)
        kws = keywords(text, config.llm_model_path)

        data.update({
            "stem": stem,
            "summary": summary_text,
            "keywords": kws,
            "similarity_score": sim,
            "novelty_score": nov,
            "nearest_aired_stem": nearest,
            "language": data.get("language", "auto"),
            "dein_zeugs_version": __version__,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "embedding": emb.tolist(),
        })
        llm_err = get_llm_error()
        if llm_err:
            data["llm_error"] = llm_err

        yaml_bytes = yaml.dump(
            data, allow_unicode=True, default_flow_style=False, sort_keys=False
        ).encode("utf-8")
        atomic_write(yaml_path, yaml_bytes)
        return emb

    count = 0
    candidates = _load_candidates()

    # Pass 1: aired items — each expands the reference corpus for later items.
    for yaml_path, data in candidates:
        stem = data.get("stem") or normalize_stem(yaml_path.stem)
        if stem not in aired_mp3_stems:
            continue
        emb = _run_one(yaml_path, data)
        aired_embeddings.append((stem, emb))
        aired_stems.add(stem)
        count += 1

    # Pass 2: inbox items — scored against the now-complete aired corpus.
    for yaml_path, data in candidates:
        stem = data.get("stem") or normalize_stem(yaml_path.stem)
        if stem in aired_mp3_stems:
            continue
        _run_one(yaml_path, data)
        count += 1

    compute_intra_batch_scores(paths, aired_stems)
    return count


def process_all_unprocessed(
    paths: ProjectPaths,
    config,
    embedding_model: EmbeddingModel,
) -> int:
    """Transcribe and analyse every audio file that is not yet fully processed.

    Picks up both completely unprocessed files (no YAML) and files that were
    transcribed separately but not yet analysed (YAML present, no embedding).
    """
    from dein_zeugs.transcription import WhisperTranscriber
    transcriber = WhisperTranscriber(model_name=config.whisper_model)

    aired = embedding_model.aired_corpus(paths)
    aired_embeddings = [(stem, emb) for stem, _text, emb in aired]
    aired_stems = {stem for stem, _text, _emb in aired}

    count = 0
    for mp3 in _needs_full_analysis(paths.inbox, paths):
        stem = normalize_stem(mp3.stem)
        log.info(f"Transkription und Analyse: {mp3.name}")
        _analyze_one(mp3, stem, paths, config, transcriber, embedding_model, aired_embeddings)
        count += 1

    for mp3 in _needs_full_analysis(paths.aired, paths):
        stem = normalize_stem(mp3.stem)
        log.info(f"Transkription und Analyse (gesendet): {mp3.name}")
        emb = _analyze_one(mp3, stem, paths, config, transcriber, embedding_model, aired_embeddings)
        # Keep the corpus current so subsequent aired items in this pass see each other.
        aired_embeddings.append((stem, emb))
        aired_stems.add(stem)
        count += 1

    compute_intra_batch_scores(paths, aired_stems)
    return count
