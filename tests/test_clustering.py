import numpy as np
from dein_zeugs.clustering import build_clusters


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return (v / norm).astype(np.float32)


# Three fixed unit embeddings:
#   A and B are close (cosine sim ~0.995)
#   A/B and C are orthogonal (cosine sim = 0.0)
A = np.array([1.0, 0.0, 0.0], dtype=np.float32)
# B is at cosine distance ~0.90 from A (separates at threshold 0.95, merges at 0.80)
B = np.array([0.9, 0.43589, 0.0], dtype=np.float32)  # |B| ≈ 1.0, dot(A,B) = 0.9
C = _unit(np.array([0.0, 0.0, 1.0]))


def _items(*pairs):
    return [{"stem": stem, "embedding": emb.tolist()} for stem, emb in pairs]


def test_similar_pair_merges_at_threshold_080():
    items = _items(("ep_a", A), ("ep_b", B), ("ep_c", C))
    clusters = build_clusters(items, threshold=0.80)

    assert len(clusters) == 2

    merged = next(c for c in clusters if len(c) == 2)
    singleton = next(c for c in clusters if len(c) == 1)

    assert set(merged) == {"ep_a", "ep_b"}
    assert singleton == ["ep_c"]


def test_all_separate_at_threshold_095():
    # Verify A/B similarity is below 0.95 so they split
    sim_ab = float(np.dot(A, B))
    assert sim_ab < 0.95, f"Expected A-B sim < 0.95, got {sim_ab}"

    items = _items(("ep_a", A), ("ep_b", B), ("ep_c", C))
    clusters = build_clusters(items, threshold=0.95)

    assert len(clusters) == 3
    stems_in_clusters = {s for c in clusters for s in c}
    assert stems_in_clusters == {"ep_a", "ep_b", "ep_c"}
    for c in clusters:
        assert len(c) == 1


def test_empty_input_returns_empty():
    assert build_clusters([], threshold=0.80) == []


def test_single_item_returns_one_cluster():
    items = _items(("ep_a", A))
    clusters = build_clusters(items, threshold=0.80)
    assert clusters == [["ep_a"]]


def test_identical_embeddings_always_merge():
    items = _items(("ep_x", A), ("ep_y", A))
    clusters = build_clusters(items, threshold=0.99)
    assert len(clusters) == 1
    assert set(clusters[0]) == {"ep_x", "ep_y"}
