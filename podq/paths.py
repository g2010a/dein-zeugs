import unicodedata
from dataclasses import dataclass
from pathlib import Path


def normalize_stem(stem: str) -> str:
    return unicodedata.normalize("NFC", stem)


@dataclass
class ProjectPaths:
    root: Path

    def __post_init__(self):
        if not self.root.exists():
            raise ValueError(f"Project root does not exist: {self.root}")

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def transcripts(self) -> Path:
        return self.root / "transcripts"

    @property
    def analysis(self) -> Path:
        return self.root / "analysis"

    @property
    def aired(self) -> Path:
        return self.root / "aired"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    def ensure_dirs(self) -> None:
        self.transcripts.mkdir(parents=True, exist_ok=True)
        self.analysis.mkdir(parents=True, exist_ok=True)
        self.reports.mkdir(parents=True, exist_ok=True)


def unprocessed_audio(paths: ProjectPaths) -> list[Path]:
    if not paths.inbox.exists():
        return []
    result = []
    for mp3 in paths.inbox.glob("*.mp3"):
        stem = normalize_stem(mp3.stem)
        if not (paths.transcripts / f"{stem}.txt").exists():
            result.append(mp3)
    return result


def unanalyzed_transcripts(paths: ProjectPaths) -> list[Path]:
    if not paths.transcripts.exists():
        return []
    result = []
    for txt in paths.transcripts.glob("*.txt"):
        stem = normalize_stem(txt.stem)
        if not (paths.analysis / f"{stem}.json").exists():
            result.append(txt)
    return result
