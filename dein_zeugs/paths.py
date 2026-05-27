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


def _unprocessed_in(directory: Path, analysis: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [
        mp3 for mp3 in directory.glob("*.mp3")
        if not (analysis / f"{normalize_stem(mp3.stem)}.yaml").exists()
    ]


def unprocessed_audio(paths: ProjectPaths) -> list[Path]:
    return _unprocessed_in(paths.inbox, paths.analysis)


def unprocessed_aired_audio(paths: ProjectPaths) -> list[Path]:
    return _unprocessed_in(paths.aired, paths.analysis)
