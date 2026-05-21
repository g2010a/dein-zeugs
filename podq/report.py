import json
import logging
import os
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from podq.paths import ProjectPaths, normalize_stem
from podq.clustering import build_clusters
from podq.util.atomic import atomic_write

log = logging.getLogger("podq")


def render_report(paths: ProjectPaths, config) -> Path:
    report_path = paths.reports / "report.html"
    templates_dir = Path(__file__).parent / "templates"

    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report.html.j2")

    # 1. Aired questions
    aired_items = []
    for mp3 in sorted(paths.aired.glob("*.mp3")):
        stem = normalize_stem(mp3.stem)
        analysis_path = paths.analysis / f"{stem}.json"
        if analysis_path.exists():
            data = json.loads(analysis_path.read_text())
            summary = data.get("summary", "(no analysis)")
        else:
            summary = "(no analysis)"
        aired_items.append({"stem": stem, "summary": summary})

    # 2. Processed questions (both .txt and .json)
    processed_items = []
    for txt in sorted(paths.transcripts.glob("*.txt")):
        stem = normalize_stem(txt.stem)
        analysis_path = paths.analysis / f"{stem}.json"
        if not analysis_path.exists():
            continue
        data = json.loads(analysis_path.read_text())
        processed_items.append({
            "stem": stem,
            "summary": data.get("summary", ""),
            "keywords": data.get("keywords", []),
            "similarity_score": data.get("similarity_score", 0.0),
            "novelty_score": data.get("novelty_score", 1.0),
            "nearest_aired_stem": data.get("nearest_aired_stem"),
        })
    processed_items.sort(key=lambda x: x["novelty_score"], reverse=True)

    # 3. Unprocessed
    unprocessed_items = []
    for mp3 in sorted(paths.inbox.glob("*.mp3")) if paths.inbox.exists() else []:
        stem = normalize_stem(mp3.stem)
        txt_path = paths.transcripts / f"{stem}.txt"
        analysis_path = paths.analysis / f"{stem}.json"
        if not txt_path.exists():
            unprocessed_items.append({"stem": stem, "status": "no transcript"})
        elif not analysis_path.exists():
            unprocessed_items.append({"stem": stem, "status": "transcribed, awaiting analysis"})

    # 4. Clusters — reload with embeddings
    processed_with_emb = []
    for txt in paths.transcripts.glob("*.txt"):
        stem = normalize_stem(txt.stem)
        ap = paths.analysis / f"{stem}.json"
        if ap.exists():
            d = json.loads(ap.read_text())
            if "embedding" in d:
                processed_with_emb.append(d)
    clusters = build_clusters(processed_with_emb, config.similarity_threshold)

    # Inline CSS and JS
    css_path = templates_dir / "report.css"
    js_path = templates_dir / "report.js"
    css = css_path.read_text() if css_path.exists() else ""
    js = js_path.read_text() if js_path.exists() else ""

    html = template.render(
        aired=aired_items,
        processed=processed_items,
        unprocessed=unprocessed_items,
        clusters=clusters,
        threshold=config.similarity_threshold,
        css=css,
        js=js,
    )

    atomic_write(report_path, html.encode("utf-8"))

    if not os.environ.get("PODQ_NO_OPEN"):
        subprocess.run(["open", str(report_path)], check=False)

    return report_path
