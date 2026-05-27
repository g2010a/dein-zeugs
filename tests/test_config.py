from dein_zeugs.config import Config


def test_load_or_create_creates_defaults_when_missing(tmp_path):
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.80
    assert cfg.whisper_model == "medium"
    assert cfg.embedding_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert cfg.llm_model_path.endswith("Llama-3.2-3B-Instruct-Q4_K_M.gguf")
    assert (tmp_path / "config.toml").exists()


def test_load_or_create_reads_existing_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[analysis]\nsimilarity_threshold = 0.75\nllm_model_path = "/custom/model.gguf"\n',
        encoding="utf-8",
    )
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.75
    assert cfg.llm_model_path == "/custom/model.gguf"


def test_missing_keys_fall_back_to_defaults(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[analysis]\nsimilarity_threshold = 0.65\n", encoding="utf-8")
    cfg = Config.load_or_create(tmp_path)
    assert cfg.similarity_threshold == 0.65
    assert cfg.whisper_model == "medium"
    assert cfg.embedding_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert cfg.llm_model_path.endswith("Llama-3.2-3B-Instruct-Q4_K_M.gguf")
