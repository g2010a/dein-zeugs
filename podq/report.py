import logging
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from podq.paths import ProjectPaths, normalize_stem
from podq.clustering import build_clusters
from podq.util.atomic import atomic_write

log = logging.getLogger("podq")

_DEFAULT_STANDOUTS_COUNT = 10


def render_report(paths: ProjectPaths, config) -> Path:
    report_path = paths.reports / "report.html"
    templates_dir = Path(__file__).parent / "templates"

    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report.html.j2")

    # 1. Aired questions
    aired_items = []
    aired_stems: set[str] = set()
    if paths.aired.exists():
        for mp3 in sorted(paths.aired.glob("*.mp3")):
            stem = normalize_stem(mp3.stem)
            aired_stems.add(stem)
            yaml_path = paths.analysis / f"{stem}.yaml"
            if yaml_path.exists():
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                summary = data.get("summary", "(keine Analyse)")
                transcript = data.get("transcript", "")
            else:
                summary = "(keine Analyse)"
                transcript = ""
            aired_items.append({"stem": stem, "summary": summary, "transcript": transcript})

    # 2. Processed questions (yaml)
    processed_items = []
    for yaml_file in sorted(paths.analysis.glob("*.yaml")):
        stem = normalize_stem(yaml_file.stem)
        if stem in aired_stems:
            continue
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        processed_items.append({
            "stem": stem,
            "summary": data.get("summary", ""),
            "transcript": data.get("transcript", ""),
            "keywords": data.get("keywords", []),
            "similarity_score": data.get("similarity_score", 0.0),
            "novelty_score": data.get("novelty_score", 1.0),
            "standout_score": data.get("standout_score", data.get("novelty_score", 1.0)),
            "nearest_aired_stem": data.get("nearest_aired_stem"),
            "llm_error": data.get("llm_error"),
        })
    processed_items.sort(key=lambda x: x["novelty_score"], reverse=True)

    # 3. Standouts — top-N by standout_score (fallback to novelty_score)
    standouts_count = getattr(config, "standouts_count", _DEFAULT_STANDOUTS_COUNT)
    standouts = sorted(
        processed_items,
        key=lambda x: x["standout_score"],
        reverse=True,
    )[:standouts_count]

    # 4. Possible repeats — items with similarity >= threshold
    possible_repeats = [
        item for item in processed_items
        if item["similarity_score"] >= config.similarity_threshold
    ]

    # 5. Unprocessed
    unprocessed_items = []
    for mp3 in sorted(paths.inbox.glob("*.mp3")) if paths.inbox.exists() else []:
        stem = normalize_stem(mp3.stem)
        yaml_path = paths.analysis / f"{stem}.yaml"
        if not yaml_path.exists():
            unprocessed_items.append({"stem": stem, "status": "noch nicht verarbeitet"})

    # 6. Clusters — reload with embeddings
    processed_with_emb = []
    for yaml_file in paths.analysis.glob("*.yaml"):
        try:
            d = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if "embedding" in d:
                processed_with_emb.append(d)
        except Exception:
            continue
    clusters = build_clusters(processed_with_emb, config.similarity_threshold)

    # Split clusters into new-only and mixed
    new_only_clusters = []
    mixed_clusters = []
    for cluster in clusters:
        if len(cluster) <= 1:
            continue
        if all(stem not in aired_stems for stem in cluster):
            new_only_clusters.append(cluster)
        else:
            mixed_clusters.append(cluster)

    # Count metrics
    aired_count = len(aired_items)
    total_questions_count = len(aired_items) + len(processed_items)

    # Paths for file:// links
    inbox_path = str(paths.inbox)
    aired_path = str(paths.aired)

    # Inline CSS and JS
    css_path = templates_dir / "report.css"
    js_path = templates_dir / "report.js"
    css = css_path.read_text() if css_path.exists() else ""
    js = js_path.read_text() if js_path.exists() else ""

    llm_error_count = sum(1 for item in processed_items if item.get("llm_error"))

    html = template.render(
        aired=aired_items,
        processed=processed_items,
        unprocessed=unprocessed_items,
        clusters=clusters,
        standouts=standouts,
        standouts_count=standouts_count,
        possible_repeats=possible_repeats,
        aired_count=aired_count,
        total_questions_count=total_questions_count,
        new_only_clusters=new_only_clusters,
        mixed_clusters=mixed_clusters,
        inbox_path=inbox_path,
        aired_path=aired_path,
        threshold=config.similarity_threshold,
        llm_error_count=llm_error_count,
        css=css,
        js=js,
    )

    atomic_write(report_path, html.encode("utf-8"))
    return report_path
