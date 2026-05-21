import logging
from pathlib import Path

log = logging.getLogger("podq")


class WhisperTranscriber:
    def __init__(self, model_name: str = "medium"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")

    def transcribe(self, path: Path) -> str:
        self._load_model()
        segments, _ = self._model.transcribe(str(path))
        return " ".join(seg.text for seg in segments).strip()
