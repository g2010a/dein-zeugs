import logging
from pathlib import Path
from podq.util.atomic import atomic_write
from podq.paths import ProjectPaths, unprocessed_audio, normalize_stem

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


def transcribe_all_unprocessed(paths: ProjectPaths, config, transcriber: "WhisperTranscriber | None" = None) -> int:
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
