import yaml
import os
import re
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

os.environ["PODQ_NO_OPEN"] = "1"


def make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "podq_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    return root


def test_report_sections(tmp_path):
    from podq.config import Config
    from podq.paths import ProjectPaths
    from podq.report import render_report

    root = make_fixture_root(tmp_path)

    # Aired: has MP3 + analysis
    (root / "aired" / "aired_q1.mp3").touch()
    (root / "analysis" / "aired_q1.yaml").write_text(yaml.dump({
        "stem": "aired_q1", "transcript": "Wie oft Sport machen?",
        "summary": "Frage über Sportfrequenz",
        "keywords": ["sport"], "similarity_score": 0.0, "novelty_score": 1.0,
        "nearest_aired_stem": None, "embedding": [0.1] * 384,
        "language": "de", "podq_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00"
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Processed: inbox MP3 with analysis
    (root / "inbox" / "caller_001.mp3").touch()
    (root / "analysis" / "caller_001.yaml").write_text(yaml.dump({
        "stem": "caller_001", "transcript": "Was empfehlen Sie gegen Erkältung?",
        "summary": "Frage über Erkältungsmittel",
        "keywords": ["erkältung"], "similarity_score": 0.3, "novelty_score": 0.7,
        "nearest_aired_stem": "aired_q1", "embedding": [0.2] * 384,
        "language": "de", "podq_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00"
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Unprocessed: inbox MP3 with no YAML in analysis
    (root / "inbox" / "caller_002.mp3").touch()

    config = Config()
    paths = ProjectPaths(root)

    report_path = render_report(paths, config)
    assert report_path.exists()

    soup = BeautifulSoup(report_path.read_text(), "html.parser")

    # Check sections exist
    assert soup.find(id="aired") is not None
    assert soup.find(id="processed") is not None
    assert soup.find(id="unprocessed") is not None

    # Check content placement
    aired_section = str(soup.find(id="aired"))
    assert "aired_q1" in aired_section

    processed_section = str(soup.find(id="processed"))
    assert "caller_001" in processed_section

    unprocessed_section = str(soup.find(id="unprocessed"))
    assert "caller_002" in unprocessed_section


def test_repeat_row_highlighted(tmp_path):
    from podq.config import Config
    from podq.paths import ProjectPaths
    from podq.report import render_report

    root = make_fixture_root(tmp_path)

    # High similarity item — should be marked as repeat
    (root / "inbox" / "caller_high.mp3").touch()
    (root / "analysis" / "caller_high.yaml").write_text(yaml.dump({
        "stem": "caller_high", "transcript": "Wiederholfrage",
        "summary": "Wiederholte Frage",
        "keywords": ["wiederholung"], "similarity_score": 0.9, "novelty_score": 0.1,
        "nearest_aired_stem": "some_aired", "embedding": [0.9] * 384,
        "language": "de", "podq_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00"
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    soup = BeautifulSoup(report_path.read_text(), "html.parser")
    repeat_rows = soup.find_all("tr", class_="repeat")
    assert len(repeat_rows) == 1
    assert "caller_high" in str(repeat_rows[0])


def test_no_external_urls(tmp_path):
    from podq.config import Config
    from podq.paths import ProjectPaths
    from podq.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    external = re.findall(r'https?://', html)
    assert len(external) == 0, f"Found external URLs: {external}"


def test_clusters_section_present(tmp_path):
    from podq.config import Config
    from podq.paths import ProjectPaths
    from podq.report import render_report

    root = make_fixture_root(tmp_path)

    # Two items with identical embeddings — should cluster together
    emb = [1.0] + [0.0] * 383
    for stem in ["q_a", "q_b"]:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(yaml.dump({
            "stem": stem, "transcript": "same question",
            "summary": "Same thing",
            "keywords": ["same"], "similarity_score": 0.0, "novelty_score": 1.0,
            "nearest_aired_stem": None, "embedding": emb,
            "language": "de", "podq_version": "1.0.0",
            "analyzed_at": "2026-05-18T00:00:00+00:00"
        }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    soup = BeautifulSoup(report_path.read_text(), "html.parser")
    clusters_section = str(soup.find(id="clusters"))
    assert "q_a" in clusters_section
    assert "q_b" in clusters_section


def test_processed_sorted_by_novelty_desc(tmp_path):
    from podq.config import Config
    from podq.paths import ProjectPaths
    from podq.report import render_report

    root = make_fixture_root(tmp_path)

    items = [
        ("low_novelty", 0.2),
        ("high_novelty", 0.9),
        ("mid_novelty", 0.5),
    ]
    for stem, novelty in items:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(yaml.dump({
            "stem": stem, "transcript": "question",
            "summary": "A question",
            "keywords": [], "similarity_score": 1.0 - novelty, "novelty_score": novelty,
            "nearest_aired_stem": None, "embedding": [0.1] * 384,
            "language": "de", "podq_version": "1.0.0",
            "analyzed_at": "2026-05-18T00:00:00+00:00"
        }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    html = report_path.read_text()
    pos_high = html.index("high_novelty")
    pos_mid = html.index("mid_novelty")
    pos_low = html.index("low_novelty")
    assert pos_high < pos_mid < pos_low, "Processed items not sorted by novelty descending"
