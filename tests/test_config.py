from pathlib import Path
from podq.config import Config


def test_load_or_create_creates_defaults_when_missing(tmp_path):
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.80
    assert cfg.ollama_model == "llama3.2:3b"
    assert cfg.whisper_model == "medium"
    assert cfg.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"
    assert cfg.ollama_url == "http://localhost:11434"
    assert (tmp_path / "config.toml").exists()


def test_load_or_create_reads_existing_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[analysis]\nsimilarity_threshold = 0.75\nollama_model = "mistral"\n',
        encoding="utf-8",
    )
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.75
    assert cfg.ollama_model == "mistral"


def test_missing_keys_fall_back_to_defaults(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[analysis]\nsimilarity_threshold = 0.65\n", encoding="utf-8")
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.65
    assert cfg.ollama_model == "llama3.2:3b"
    assert cfg.whisper_model == "medium"
    assert cfg.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"
    assert cfg.ollama_url == "http://localhost:11434"
