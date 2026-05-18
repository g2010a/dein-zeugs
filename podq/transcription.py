import os
import logging
from pathlib import Path
from podq.util.atomic import atomic_write
from podq.paths import ProjectPaths, unprocessed_audio, normalize_stem

log = logging.getLogger("podq")

_model_cache = {}

class WhisperTranscriber:
    def __init__(self, model_name: str = "medium", device: str | None = None):
        self.model_name = model_name
        self._device = device or self._select_device()
        self._model = None

    def _select_device(self) -> str:
        if os.environ.get("PODQ_FORCE_CPU"):
            return "cpu"
        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        log.warning("MPS not available, falling back to CPU")
        return "cpu"

    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name, device=self._device)

    def transcribe(self, path: Path) -> str:
        self._load_model()
        result = self._model.transcribe(str(path), fp16=False)
        return result["text"].strip()


def transcribe_all_unprocessed(paths: ProjectPaths, config, transcriber: WhisperTranscriber | None = None) -> int:
    if transcriber is None:
        transcriber = WhisperTranscriber(model_name=config.whisper_model)
    count = 0
    for mp3 in unprocessed_audio(paths):
        stem = normalize_stem(mp3.stem)
        log.info(f"Transcribing {mp3.name}")
        text = transcriber.transcribe(mp3)
        atomic_write(paths.transcripts / f"{stem}.txt", text.encode("utf-8"))
        count += 1
    return count
