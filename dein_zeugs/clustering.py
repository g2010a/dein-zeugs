import numpy as np


def build_clusters(items: list[dict], threshold: float) -> list[list[str]]:
    """Single-link agglomerative clustering on cosine similarity >= threshold.
    items: list of dicts with 'stem' and 'embedding' keys.
    Returns list of clusters (each cluster is a list of stems).
    """
    if not items:
        return []

    stems = [item["stem"] for item in items]
    embeddings = [np.array(item["embedding"], dtype=np.float32) for item in items]
    n = len(stems)

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            sim = float(np.dot(embeddings[i], embeddings[j]))
            if sim >= threshold:
                union(i, j)

    groups: dict[int, list[str]] = {}
    for i, stem in enumerate(stems):
        root = find(i)
        groups.setdefault(root, []).append(stem)

    return list(groups.values())
