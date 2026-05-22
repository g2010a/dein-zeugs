import json
import logging
import yaml
import numpy as np
from pathlib import Path
from podq.paths import ProjectPaths, normalize_stem

log = logging.getLogger("podq")


class EmbeddingModel:
    def __init__(self, name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.name = name
        self._model = None

    def _load(self):
        if self._model is None:
            import warnings
            from fastembed import TextEmbedding
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*mean pooling.*", category=UserWarning)
                self._model = TextEmbedding(self.name)

    def embed(self, text: str) -> np.ndarray:
        self._load()
        embeddings = list(self._model.embed([text]))
        vec = np.array(embeddings[0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def aired_corpus(self, paths: ProjectPaths) -> list[tuple[str, str, np.ndarray]]:
        """Returns (stem, text, embedding) for aired MP3s that have analysis YAMLs."""
        cache_path = paths.analysis / ".aired_cache.json"
        try:
            cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        except Exception:
            cache = {}

        result = []
        new_cache = {}
        for mp3 in sorted(paths.aired.glob("*.mp3")):
            stem = normalize_stem(mp3.stem)
            yaml_path = paths.analysis / f"{stem}.yaml"
            if not yaml_path.exists():
                continue
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            text = data.get("transcript", "")
            mtime = str(yaml_path.stat().st_mtime)
            cache_key = f"{stem}:{mtime}"
            if cache_key in cache:
                emb = np.array(cache[cache_key], dtype=np.float32)
            elif "embedding" in data:
                emb = np.array(data["embedding"], dtype=np.float32)
                cache[cache_key] = data["embedding"]
            else:
                emb = self.embed(text)
                cache[cache_key] = emb.tolist()
            new_cache[cache_key] = cache[cache_key]
            result.append((stem, text, emb))

        try:
            cache_path.write_text(json.dumps(new_cache))
        except Exception as e:
            log.warning(f"Could not write aired cache: {e}")

        return result
