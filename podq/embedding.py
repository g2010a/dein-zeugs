import json
import logging
import numpy as np
from pathlib import Path
from podq.paths import ProjectPaths, normalize_stem

log = logging.getLogger("podq")


class EmbeddingModel:
    def __init__(self, name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.name = name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                import torch
                device = "mps" if torch.backends.mps.is_available() else "cpu"
            except Exception:
                device = "cpu"
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.name, device=device)

    def embed(self, text: str) -> np.ndarray:
        self._load()
        vec = self._model.encode(text, convert_to_numpy=True).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def aired_corpus(self, paths: ProjectPaths) -> list[tuple[str, str, np.ndarray]]:
        """Returns (stem, text, embedding) for aired MP3s that have transcripts."""
        cache_path = paths.analysis / ".aired_cache.json"
        try:
            cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        except Exception:
            cache = {}

        result = []
        new_cache = {}
        for mp3 in sorted(paths.aired.glob("*.mp3")):
            stem = normalize_stem(mp3.stem)
            txt_path = paths.transcripts / f"{stem}.txt"
            if not txt_path.exists():
                continue
            mtime = str(txt_path.stat().st_mtime)
            cache_key = f"{stem}:{mtime}"
            if cache_key in cache:
                emb = np.array(cache[cache_key], dtype=np.float32)
            else:
                text = txt_path.read_text(encoding="utf-8")
                emb = self.embed(text)
                cache[cache_key] = emb.tolist()
            new_cache[cache_key] = cache[cache_key]
            text = txt_path.read_text(encoding="utf-8")
            result.append((stem, text, emb))

        try:
            cache_path.write_text(json.dumps(new_cache))
        except Exception as e:
            log.warning(f"Could not write aired cache: {e}")

        return result
