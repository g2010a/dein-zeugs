import logging
import yaml
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from podq.util.atomic import atomic_write
from podq.paths import ProjectPaths, unprocessed_audio, normalize_stem
from podq.embedding import EmbeddingModel
from podq import __version__

log = logging.getLogger("podq")

SUMMARY_PROMPT = (
    "Fasse die folgende Hörerfrage in 1-2 Sätzen zusammen. "
    "Verwende NUR Informationen aus dem Text – erfinde nichts dazu. "
    "Antworte auf Deutsch. Wenn der Text nicht auf Deutsch ist, antworte in der Originalsprache.\n"
    "Text: {transcript}\n"
    "Zusammenfassung:"
)

KEYWORDS_PROMPT = (
    "Extrahiere 3-5 einzelne Schlüsselwörter (keine Sätze oder Phrasen) aus dem folgenden Text. "
    "Gib nur die Wörter kommagetrennt zurück, keine Erklärungen.\n"
    "Text: {transcript}\n"
    "Schlüsselwörter:"
)

_llm_instance = None


def _get_llm(model_path: str):
    global _llm_instance
    if _llm_instance is None:
        from llama_cpp import Llama
        _llm_instance = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            verbose=False,
        )
    return _llm_instance


def _infer(prompt: str, model_path: str, max_tokens: int = 256) -> str:
    try:
        llm = _get_llm(model_path)
        output = llm(prompt, max_tokens=max_tokens, stop=["\n\n", "###"])
        return output["choices"][0]["text"].strip()
    except Exception as e:
        log.error(f"LLM inference failed: {e}")
        return ""


def summarize(text: str, model_path: str) -> str:
    return _infer(SUMMARY_PROMPT.format(transcript=text), model_path, max_tokens=100)


def keywords(text: str, model_path: str) -> list[str]:
    raw = _infer(KEYWORDS_PROMPT.format(transcript=text), model_path, max_tokens=64)
    if not raw:
        return []
    parts = [p.strip().lower() for p in raw.replace("\n", ",").split(",") if p.strip()]
    return list(dict.fromkeys(parts))[:5]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors (assumed unit-normalised)."""
    return float(np.dot(a, b))


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
                _cosine(emb_i, emb_j)
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


def process_all_unprocessed(
    paths: ProjectPaths,
    config,
    embedding_model: EmbeddingModel,
) -> int:
    from podq.transcription import WhisperTranscriber
    transcriber = WhisperTranscriber(model_name=config.whisper_model)

    aired = embedding_model.aired_corpus(paths)
    aired_embeddings = [(stem, emb) for stem, _text, emb in aired]
    aired_stems = {stem for stem, _text, _emb in aired}

    count = 0
    for mp3 in unprocessed_audio(paths):
        stem = normalize_stem(mp3.stem)
        log.info(f"Transkription und Analyse: {mp3.name}")
        text = transcriber.transcribe(mp3)

        emb = embedding_model.embed(text)
        sim, nov, nearest = score(emb, aired_embeddings)
        summary_text = summarize(text, config.llm_model_path)
        kws = keywords(text, config.llm_model_path)

        data = {
            "stem": stem,
            "transcript": text,
            "summary": summary_text,
            "keywords": kws,
            "similarity_score": sim,
            "novelty_score": nov,
            "nearest_aired_stem": nearest,
            "language": "auto",
            "podq_version": __version__,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "embedding": emb.tolist(),
        }
        yaml_bytes = yaml.dump(
            data, allow_unicode=True, default_flow_style=False, sort_keys=False
        ).encode("utf-8")
        atomic_write(paths.analysis / f"{stem}.yaml", yaml_bytes)
        count += 1

    compute_intra_batch_scores(paths, aired_stems)
    return count
