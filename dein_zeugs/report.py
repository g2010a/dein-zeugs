import json
import logging
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from dein_zeugs.paths import ProjectPaths, normalize_stem
from dein_zeugs.clustering import build_clusters
from dein_zeugs.util.atomic import atomic_write

log = logging.getLogger("dein_zeugs")


def _derive_cluster_name(cluster_stems: list[str], items_by_stem: dict) -> str:
    """Derive a short human-readable label from the cluster members' keywords/summaries."""
    kw_count: dict[str, int] = {}
    for stem in cluster_stems:
        item = items_by_stem.get(stem, {})
        for kw in item.get("keywords", []):
            kw = kw.strip()
            if kw:
                kw_count[kw] = kw_count.get(kw, 0) + 1

    if kw_count:
        top = sorted(kw_count.items(), key=lambda x: (-x[1], x[0]))[:3]
        return ", ".join(kw for kw, _ in top)

    # Fallback: truncated summary of first item, then stem if still empty
    first = items_by_stem.get(cluster_stems[0], {})
    summary = first.get("summary", "").strip()
    if not summary:
        return cluster_stems[0]
    words = summary.split()
    return (" ".join(words[:6]) + "…") if len(words) > 6 else summary


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
                kws = data.get("keywords", [])
                similarity_score = data.get("similarity_score", 0.0)
                novelty_score = data.get("novelty_score", 0.0)
                nearest_aired_stem = data.get("nearest_aired_stem")
                llm_error = data.get("llm_error")
                first_seen = data.get("first_seen", data.get("analyzed_at", ""))
                analyzed_at = data.get("analyzed_at", "")
            else:
                summary = "(keine Analyse)"
                transcript = ""
                kws = []
                similarity_score = 0.0
                novelty_score = 0.0
                nearest_aired_stem = None
                llm_error = None
                first_seen = ""
                analyzed_at = ""
            aired_items.append({
                "stem": stem,
                "summary": summary,
                "transcript": transcript,
                "keywords": kws,
                "similarity_score": similarity_score,
                "novelty_score": novelty_score,
                "nearest_aired_stem": nearest_aired_stem,
                "llm_error": llm_error,
                "first_seen": first_seen,
                "analyzed_at": analyzed_at,
                "is_aired": True,
            })

    # 2. Processed questions (yaml, inbox only)
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
            "first_seen": data.get("first_seen", data.get("analyzed_at", "")),
            "analyzed_at": data.get("analyzed_at", ""),
            "is_aired": False,
        })
    processed_items.sort(key=lambda x: x["novelty_score"], reverse=True)

    # 3. Build stem → item lookup for cluster naming
    items_by_stem: dict[str, dict] = {}
    for item in processed_items + aired_items:
        items_by_stem[item["stem"]] = item

    # 4. Clusters — reload with embeddings
    processed_with_emb = []
    for yaml_file in paths.analysis.glob("*.yaml"):
        try:
            d = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if "embedding" in d:
                processed_with_emb.append(d)
        except Exception:
            continue
    clusters = build_clusters(processed_with_emb, config.similarity_threshold)

    # Split clusters into new-only and mixed (for template)
    new_only_clusters = []
    mixed_clusters = []
    for cluster in clusters:
        if len(cluster) <= 1:
            continue
        if all(stem not in aired_stems for stem in cluster):
            new_only_clusters.append(cluster)
        else:
            mixed_clusters.append(cluster)

    # Generate named cluster objects and stem→cluster mapping
    named_clusters = []
    stem_to_cluster_id: dict[str, str] = {}
    for i, cluster in enumerate(clusters):
        if len(cluster) <= 1:
            continue
        cid = f"cluster_{i}"
        name = _derive_cluster_name(cluster, items_by_stem)
        is_mixed = any(stem in aired_stems for stem in cluster)
        named_clusters.append({
            "id": cid,
            "name": name,
            "stems": cluster,
            "is_mixed": is_mixed,
        })
        for stem in cluster:
            stem_to_cluster_id[stem] = cid

    # Attach cluster_id to every item
    for item in processed_items + aired_items:
        item["cluster_id"] = stem_to_cluster_id.get(item["stem"])

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
    cluster_names_json = (
        json.dumps({c["id"]: c["name"] for c in named_clusters})
        .replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )

    html = template.render(
        aired=aired_items,
        processed=processed_items,
        named_clusters=named_clusters,
        aired_stems=aired_stems,
        aired_count=aired_count,
        total_questions_count=total_questions_count,
        inbox_path=inbox_path,
        aired_path=aired_path,
        threshold=config.similarity_threshold,
        llm_error_count=llm_error_count,
        cluster_names_json=cluster_names_json,
        css=css,
        js=js,
    )

    atomic_write(report_path, html.encode("utf-8"))
    return report_path
