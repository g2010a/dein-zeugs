from unittest.mock import patch
from dein_zeugs.config import Config


def _config(**kwargs) -> Config:
    defaults = dict(
        llm_model_path="/nonexistent/model.gguf",
        whisper_model="medium",
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    defaults.update(kwargs)
    return Config(**defaults)


# huggingface_hub may not be installed in the test environment; clean_downloads falls back to
# Path.home() / ".cache" / "huggingface" / "hub".  We patch Path.home() in podq.models to point
# at tmp_path so the derived HF cache and fastembed paths land under a temp directory.

def test_clean_downloads_removes_llm_file(tmp_path):
    gguf = tmp_path / "model.gguf"
    gguf.write_text("fake")
    config = _config(llm_model_path=str(gguf))
    with patch("dein_zeugs.models.Path.home", return_value=tmp_path):
        from dein_zeugs.models import clean_downloads
        clean_downloads(config, yes=True)
    assert not gguf.exists()


def test_clean_downloads_skips_missing(tmp_path):
    config = _config(llm_model_path=str(tmp_path / "nope.gguf"))
    with patch("dein_zeugs.models.Path.home", return_value=tmp_path):
        from dein_zeugs.models import clean_downloads
        clean_downloads(config, yes=True)  # no exception


def test_clean_downloads_derives_whisper_path(tmp_path):
    hf_cache = tmp_path / ".cache" / "huggingface" / "hub"
    whisper_dir = hf_cache / "models--Systran--faster-whisper-tiny"
    whisper_dir.mkdir(parents=True)
    (whisper_dir / "model.bin").write_text("fake")
    config = _config(
        llm_model_path=str(tmp_path / "nope.gguf"),
        whisper_model="tiny",
    )
    with patch("dein_zeugs.models.Path.home", return_value=tmp_path), \
         patch("huggingface_hub.constants.HF_HUB_CACHE", str(hf_cache)):
        from dein_zeugs.models import clean_downloads
        clean_downloads(config, yes=True)
    assert not whisper_dir.exists()


def test_clean_downloads_derives_embedding_path(tmp_path):
    hf_cache = tmp_path / ".cache" / "huggingface" / "hub"
    embed_dir = hf_cache / "models--myorg--mymodel"
    embed_dir.mkdir(parents=True)
    (embed_dir / "model.onnx").write_text("fake")
    config = _config(
        llm_model_path=str(tmp_path / "nope.gguf"),
        embedding_model="myorg/mymodel",
    )
    with patch("dein_zeugs.models.Path.home", return_value=tmp_path), \
         patch("huggingface_hub.constants.HF_HUB_CACHE", str(hf_cache)):
        from dein_zeugs.models import clean_downloads
        clean_downloads(config, yes=True)
    assert not embed_dir.exists()
