import json
import logging
import numpy as np
from datetime import datetime, timezone
from podq.util.atomic import atomic_write
from podq.paths import ProjectPaths, unanalyzed_transcripts, normalize_stem
from podq.embedding import EmbeddingModel
from podq import __version__

log = logging.getLogger("podq")

SUMMARY_PROMPT = (
    "Fasse die folgende Hörerfrage in 2-3 Sätzen zusammen. "
    "Antworte auf Deutsch. "
    "Wenn der Text nicht auf Deutsch ist, antworte in der Originalsprache. "
    "Text: {transcript}"
)

KEYWORDS_PROMPT = (
    "Extrahiere 5-8 Schlüsselwörter aus dem folgenden Text. "
    "Gib nur die Schlüsselwörter kommagetrennt zurück, keine Erklärungen. "
    "Text: {transcript}"
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
    return _infer(SUMMARY_PROMPT.format(transcript=text), model_path, max_tokens=256)


def keywords(text: str, model_path: str) -> list[str]:
    raw = _infer(KEYWORDS_PROMPT.format(transcript=text), model_path, max_tokens=64)
    if not raw:
        return []
    parts = [p.strip().lower() for p in raw.replace("\n", ",").split(",") if p.strip()]
    return list(dict.fromkeys(parts))[:8]


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


def analyze_all_unanalyzed(
    paths: ProjectPaths,
    config,
    embedding_model: EmbeddingModel,
) -> int:
    aired = embedding_model.aired_corpus(paths)
    aired_embeddings = [(stem, emb) for stem, _text, emb in aired]

    count = 0
    for txt_path in unanalyzed_transcripts(paths):
        stem = normalize_stem(txt_path.stem)
        log.info(f"Analyzing {stem}")
        text = txt_path.read_text(encoding="utf-8")

        emb = embedding_model.embed(text)
        sim, nov, nearest = score(emb, aired_embeddings)
        summary = summarize(text, config.llm_model_path)
        kws = keywords(text, config.llm_model_path)

        data = {
            "stem": stem,
            "summary": summary,
            "keywords": kws,
            "similarity_score": sim,
            "novelty_score": nov,
            "nearest_aired_stem": nearest,
            "embedding": emb.tolist(),
            "language": "auto",
            "podq_version": __version__,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write(
            paths.analysis / f"{stem}.json",
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        count += 1
    return count
