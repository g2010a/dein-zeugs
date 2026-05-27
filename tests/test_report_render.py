import yaml
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

os.environ["PODQ_NO_OPEN"] = "1"


def make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "podq_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    return root


def _yaml_item(stem, novelty=1.0, similarity=0.0, nearest=None, emb=None, standout_score=None):
    d = {
        "stem": stem,
        "transcript": "Testfrage",
        "summary": f"Zusammenfassung von {stem}",
        "keywords": ["test"],
        "similarity_score": similarity,
        "novelty_score": novelty,
        "nearest_aired_stem": nearest,
        "embedding": emb or ([0.1] * 384),
        "language": "de",
        "dein_zeugs_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00",
    }
    if standout_score is not None:
        d["standout_score"] = standout_score
    return yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False)


def test_report_sections(tmp_path):
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    # Aired: has MP3 + analysis
    (root / "aired" / "aired_q1.mp3").touch()
    (root / "analysis" / "aired_q1.yaml").write_text(yaml.dump({
        "stem": "aired_q1", "transcript": "Wie oft Sport machen?",
        "summary": "Frage über Sportfrequenz",
        "keywords": ["sport"], "similarity_score": 0.0, "novelty_score": 1.0,
        "nearest_aired_stem": None, "embedding": [0.1] * 384,
        "language": "de", "dein_zeugs_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00"
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Processed: inbox MP3 with analysis
    (root / "inbox" / "caller_001.mp3").touch()
    (root / "analysis" / "caller_001.yaml").write_text(yaml.dump({
        "stem": "caller_001", "transcript": "Was empfehlen Sie gegen Erkältung?",
        "summary": "Frage über Erkältungsmittel",
        "keywords": ["erkältung"], "similarity_score": 0.3, "novelty_score": 0.7,
        "nearest_aired_stem": "aired_q1", "embedding": [0.2] * 384,
        "language": "de", "dein_zeugs_version": "1.0.0",
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
    assert soup.find(id="unprocessed") is None

    # Check content placement
    aired_section = str(soup.find(id="aired"))
    assert "aired_q1" in aired_section

    processed_section = str(soup.find(id="processed"))
    assert "caller_001" in processed_section


def test_repeat_row_highlighted(tmp_path):
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    # High similarity item — should be marked as repeat
    (root / "inbox" / "caller_high.mp3").touch()
    (root / "analysis" / "caller_high.yaml").write_text(yaml.dump({
        "stem": "caller_high", "transcript": "Wiederholfrage",
        "summary": "Wiederholte Frage",
        "keywords": ["wiederholung"], "similarity_score": 0.9, "novelty_score": 0.1,
        "nearest_aired_stem": "some_aired", "embedding": [0.9] * 384,
        "language": "de", "dein_zeugs_version": "1.0.0",
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
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    external = re.findall(r'https?://', html)
    assert len(external) == 0, f"Found external URLs: {external}"


def test_clusters_section_present(tmp_path):
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

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
            "language": "de", "dein_zeugs_version": "1.0.0",
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
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

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
            "language": "de", "dein_zeugs_version": "1.0.0",
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


# ── New tests for P2, P5, P7 ──

def test_standouts_section_is_first(tmp_path):
    """Standouts section appears before processed/aired/clusters in the HTML."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    (root / "inbox" / "q1.mp3").touch()
    (root / "analysis" / "q1.yaml").write_text(_yaml_item("q1", novelty=0.8))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    pos_standouts = html.index('id="standouts"')
    pos_processed = html.index('id="processed"')
    pos_aired = html.index('id="aired"')

    assert pos_standouts < pos_processed, "Standouts must come before processed table"
    assert pos_standouts < pos_aired, "Standouts must come before aired section"


def test_standouts_sorted_by_standout_score(tmp_path):
    """Standouts are ordered by standout_score desc when it is present."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    items = [
        ("low_stand",  0.3, 0.7, 0.2),   # stem, novelty, similarity, standout_score
        ("high_stand", 0.6, 0.4, 0.9),
        ("mid_stand",  0.5, 0.5, 0.55),
    ]
    for stem, novelty, sim, standout in items:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(
            _yaml_item(stem, novelty=novelty, similarity=sim, standout_score=standout)
        )

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    # Within the standouts section the high-score item should appear first
    standouts_html = html[html.index('id="standouts"'):html.index('id="repeats"')]
    pos_high = standouts_html.index("high_stand")
    pos_mid  = standouts_html.index("mid_stand")
    pos_low  = standouts_html.index("low_stand")
    assert pos_high < pos_mid < pos_low, "Standouts not sorted by standout_score descending"


def test_standouts_fallback_to_novelty_score(tmp_path):
    """When standout_score is absent, novelty_score is used for ranking."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    items = [
        ("low_nov",  0.1),
        ("high_nov", 0.95),
        ("mid_nov",  0.5),
    ]
    for stem, novelty in items:
        (root / "inbox" / f"{stem}.mp3").touch()
        # No standout_score field — fallback to novelty_score
        (root / "analysis" / f"{stem}.yaml").write_text(
            _yaml_item(stem, novelty=novelty)
        )

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    standouts_html = html[html.index('id="standouts"'):html.index('id="repeats"')]
    pos_high = standouts_html.index("high_nov")
    pos_mid  = standouts_html.index("mid_nov")
    pos_low  = standouts_html.index("low_nov")
    assert pos_high < pos_mid < pos_low, "Standout fallback to novelty_score not working"


def test_banner_shows_correct_counts(tmp_path):
    """Banner displays correct aired and total counts."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    # 2 aired
    for stem in ["aired_a", "aired_b"]:
        (root / "aired" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(
            _yaml_item(stem, novelty=1.0)
        )

    # 3 processed (inbox only)
    for stem in ["new_a", "new_b", "new_c"]:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(
            _yaml_item(stem, novelty=0.8)
        )

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    # Banner: "2 von 5 Fragen wurden bereits ausgestrahlt."
    assert "2 von 5" in html, "Banner should show '2 von 5'"


def test_aired_folder_links_present(tmp_path):
    """Each standout card contains file:// links for inbox and aired folders."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    (root / "inbox" / "q1.mp3").touch()
    (root / "analysis" / "q1.yaml").write_text(_yaml_item("q1", novelty=0.8))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    assert f"file://{root}/inbox/" in html, "inbox file:// link missing"
    assert f"file://{root}/aired/" in html, "aired file:// link missing"


def test_new_only_clusters(tmp_path):
    """Clusters with all-unaired members appear under 'Neue Cluster'."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    # Two unaired items with identical embeddings — new-only cluster
    emb = [1.0] + [0.0] * 383
    for stem in ["new_q1", "new_q2"]:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(
            _yaml_item(stem, emb=emb)
        )

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    clusters_html = html[html.index('id="clusters"'):]
    assert "Neue Cluster" in clusters_html
    assert "new_q1" in clusters_html
    assert "new_q2" in clusters_html


def test_mixed_clusters(tmp_path):
    """Clusters spanning aired + unaired appear under 'Gemischte Cluster'."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    emb = [1.0] + [0.0] * 383

    # One aired item
    (root / "aired" / "aired_q.mp3").touch()
    (root / "analysis" / "aired_q.yaml").write_text(_yaml_item("aired_q", emb=emb))

    # One unaired item with identical embedding
    (root / "inbox" / "new_q.mp3").touch()
    (root / "analysis" / "new_q.yaml").write_text(_yaml_item("new_q", emb=emb))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    clusters_html = html[html.index('id="clusters"'):]
    assert "Gemischte Cluster" in clusters_html
    assert "aired_q" in clusters_html
    assert "new_q" in clusters_html
