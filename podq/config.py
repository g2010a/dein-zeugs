import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_TOML = """\
[analysis]
similarity_threshold = 0.80
ollama_model = "llama3.2:3b"
"""

@dataclass
class Config:
    similarity_threshold: float = 0.80
    ollama_model: str = "llama3.2:3b"
    whisper_model: str = "medium"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ollama_url: str = "http://localhost:11434"

    @classmethod
    def load_or_create(cls, root: Path) -> "Config":
        config_path = root / "config.toml"
        if not config_path.exists():
            config_path.write_text(_DEFAULT_TOML, encoding="utf-8")
            return cls()
        with config_path.open("rb") as f:
            data = tomllib.load(f)
        analysis = data.get("analysis", {})
        return cls(
            similarity_threshold=analysis.get("similarity_threshold", 0.80),
            ollama_model=analysis.get("ollama_model", "llama3.2:3b"),
            whisper_model=analysis.get("whisper_model", "medium"),
            embedding_model=analysis.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"),
            ollama_url=analysis.get("ollama_url", "http://localhost:11434"),
        )
