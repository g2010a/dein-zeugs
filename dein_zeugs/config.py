import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dein_zeugs.models import default_llm_path

_DEFAULT_TOML = """\
[analysis]
similarity_threshold = 0.60
"""


@dataclass
class Config:
    similarity_threshold: float = 0.80
    whisper_model: str = "medium"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    llm_model_path: str = field(default_factory=default_llm_path)
    analysis_dir: str = "analysis"
    reports_dir: str = "reports"

    @classmethod
    def load_or_create(cls, root: Path) -> "Config":
        config_path = root / "config.toml"
        if not config_path.exists():
            config_path.write_text(_DEFAULT_TOML, encoding="utf-8")
            return cls()
        with config_path.open("rb") as f:
            data = tomllib.load(f)
        analysis = data.get("analysis", {})
        paths = data.get("paths", {})
        path_overrides = {
            k: paths[k]
            for k in ("analysis_dir", "reports_dir")
            if k in paths
        }
        return cls(
            similarity_threshold=analysis.get("similarity_threshold", 0.80),
            whisper_model=analysis.get("whisper_model", "medium"),
            embedding_model=analysis.get(
                "embedding_model",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            ),
            llm_model_path=analysis.get("llm_model_path", default_llm_path()),
            **path_overrides,
        )
