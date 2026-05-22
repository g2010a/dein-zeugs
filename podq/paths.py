import unicodedata
from dataclasses import dataclass
from pathlib import Path


def normalize_stem(stem: str) -> str:
    return unicodedata.normalize("NFC", stem)


@dataclass
class ProjectPaths:
    root: Path
    analysis_dir: str = "analysis"
    reports_dir: str = "reports"

    def __post_init__(self):
        if not self.root.exists():
            raise ValueError(f"Project root does not exist: {self.root}")

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def analysis(self) -> Path:
        return self.root / self.analysis_dir

    @property
    def aired(self) -> Path:
        return self.root / "aired"

    @property
    def reports(self) -> Path:
        return self.root / self.reports_dir

    def ensure_dirs(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.aired.mkdir(parents=True, exist_ok=True)
        self.analysis.mkdir(parents=True, exist_ok=True)
        self.reports.mkdir(parents=True, exist_ok=True)


def unprocessed_audio(paths: ProjectPaths) -> list[Path]:
    if not paths.inbox.exists():
        return []
    result = []
    for mp3 in paths.inbox.glob("*.mp3"):
        stem = normalize_stem(mp3.stem)
        if not (paths.analysis / f"{stem}.yaml").exists():
            result.append(mp3)
    return result
