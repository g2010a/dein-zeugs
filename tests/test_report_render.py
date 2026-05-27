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
        "first_seen": "2026-05-17T10:00:00+00:00",
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
        "analyzed_at": "2026-05-18T00:00:00+00:00",
        "first_seen": "2026-05-17T10:00:00+00:00",
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Processed: inbox MP3 with analysis
    (root / "inbox" / "caller_001.mp3").touch()
    (root / "analysis" / "caller_001.yaml").write_text(yaml.dump({
        "stem": "caller_001", "transcript": "Was empfehlen Sie gegen Erkältung?",
        "summary": "Frage über Erkältungsmittel",
        "keywords": ["erkältung"], "similarity_score": 0.3, "novelty_score": 0.7,
        "nearest_aired_stem": "aired_q1", "embedding": [0.2] * 384,
        "language": "de", "dein_zeugs_version": "1.0.0",
        "analyzed_at": "2026-05-18T00:00:00+00:00",
        "first_seen": "2026-05-17T10:00:00+00:00",
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Unprocessed: inbox MP3 with no YAML in analysis
    (root / "inbox" / "caller_002.mp3").touch()

    config = Config()
    paths = ProjectPaths(root)

    report_path = render_report(paths, config)
    assert report_path.exists()

    soup = BeautifulSoup(report_path.read_text(), "html.parser")

    # New unified section exists; no separate aired/unprocessed sections
    assert soup.find(id="all-questions") is not None
    assert soup.find(id="clusters") is not None
    assert soup.find(id="unprocessed") is None

    # Both aired and processed items appear in the unified table
    main_section = str(soup.find(id="all-questions"))
    assert "aired_q1" in main_section
    assert "caller_001" in main_section

    # Aired item is marked with row-aired class
    aired_rows = soup.find_all("tr", class_="row-aired")
    assert any("aired_q1" in str(r) for r in aired_rows)


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
        "analyzed_at": "2026-05-18T00:00:00+00:00",
        "first_seen": "2026-05-17T10:00:00+00:00",
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
            "analyzed_at": "2026-05-18T00:00:00+00:00",
            "first_seen": "2026-05-17T10:00:00+00:00",
        }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    soup = BeautifulSoup(report_path.read_text(), "html.parser")
    clusters_section = str(soup.find(id="clusters"))
    assert "q_a" in clusters_section
    assert "q_b" in clusters_section


def test_clusters_have_names(tmp_path):
    """Each multi-item cluster shows a derived name, not just a raw stem."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)

    emb = [1.0] + [0.0] * 383
    for stem in ["q_a", "q_b"]:
        (root / "inbox" / f"{stem}.mp3").touch()
        (root / "analysis" / f"{stem}.yaml").write_text(yaml.dump({
            "stem": stem, "transcript": "Sportfrage",
            "summary": "Frage über Sport",
            "keywords": ["sport", "gesundheit"], "similarity_score": 0.0, "novelty_score": 1.0,
            "nearest_aired_stem": None, "embedding": emb,
            "language": "de", "dein_zeugs_version": "1.0.0",
            "analyzed_at": "2026-05-18T00:00:00+00:00",
            "first_seen": "2026-05-17T10:00:00+00:00",
        }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    clusters_html = html[html.index('id="clusters"'):]
    # Cluster name should be derived from shared keywords
    assert "sport" in clusters_html.lower()


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
            "analyzed_at": "2026-05-18T00:00:00+00:00",
            "first_seen": "2026-05-17T10:00:00+00:00",
        }, allow_unicode=True, default_flow_style=False, sort_keys=False))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    html = report_path.read_text()
    pos_high = html.index("high_novelty")
    pos_mid = html.index("mid_novelty")
    pos_low = html.index("low_novelty")
    assert pos_high < pos_mid < pos_low, "Processed items not sorted by novelty descending"


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
    """Banner contains file:// links for inbox and aired folders."""
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


def test_aired_items_have_date_columns(tmp_path):
    """Rows expose first_seen and analyzed_at as data attributes for sorting."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    (root / "inbox" / "q1.mp3").touch()
    (root / "analysis" / "q1.yaml").write_text(_yaml_item("q1", novelty=0.8))

    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)

    soup = BeautifulSoup(report_path.read_text(), "html.parser")
    rows = soup.find_all("tr", attrs={"data-stem": "q1"})
    assert rows, "Row for q1 not found"
    row = rows[0]
    assert row.get("data-first-seen"), "data-first-seen missing"
    assert row.get("data-analyzed-at"), "data-analyzed-at missing"


def test_no_gesehen_ui(tmp_path):
    """Gesehen/unseen tracking UI elements are not present."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    assert "btn-reset-seen" not in html
    assert "Gesehen" not in html
    assert "gesehen" not in html.lower() or "ausgestrahlt" in html.lower()  # only "ausgestrahlt" allowed


def test_no_ki_fehler_button(tmp_path):
    """KI-Fehler filter button is not present."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    assert 'data-filter="error"' not in html


def test_no_highlights_section(tmp_path):
    """Highlights/standouts section is removed."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    assert 'id="standouts"' not in html


def test_no_repeats_section(tmp_path):
    """Repeats section is removed."""
    from dein_zeugs.config import Config
    from dein_zeugs.paths import ProjectPaths
    from dein_zeugs.report import render_report

    root = make_fixture_root(tmp_path)
    config = Config()
    paths = ProjectPaths(root)
    report_path = render_report(paths, config)
    html = report_path.read_text()

    assert 'id="repeats"' not in html


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
