"""Hard negative mining: Top-20 -> positif -> kandidat negatif berkemiripan tinggi -> dedup -> alasan -> quality check."""

from __future__ import annotations
from ml.common import overlap
from ml.retrieval.retriever import VectorStore


def classify_negative(pos: dict, neg: dict, query: str) -> tuple[str, str, float]:
    if neg["family"] == pos["family"] and neg["version"] != pos["version"]:
        return "wrong_version", "document version mismatch", 0.95
    if neg["document_id"] == pos["document_id"]:
        return "wrong_section", "salah section/chunk pada dokumen yang sama", 0.85
    if overlap(query, neg["content"]) > 0.5:
        return "keyword_overlap", "keyword overlap tinggi tetapi konteks salah", 0.75
    return "topical", "topik terkait tetapi tidak menjawab query", 0.65


def mine(query: str, positive_chunk_id: str, store: VectorStore, min_similarity: float = 0.2, max_negatives: int = 5) -> list[dict]:
    cands = store.search(query, top_k=20)
    pos = next((c for c in cands if c["chunk_id"] == positive_chunk_id), None)
    if pos is None:
        pos = next((c for c in store.chunks if c["chunk_id"] == positive_chunk_id), None)
        if pos is None:
            return []
        pos = {**{k: v for k, v in pos.items() if k != "vector"}, "similarity": 0.0}
    seen, out = set(), []
    for c in cands:
        if c["chunk_id"] == positive_chunk_id or c["content_hash"] in seen or c["content_hash"] == pos["content_hash"]:
            continue
        seen.add(c["content_hash"])
        if c["similarity"] < min_similarity:
            continue
        ntype, reason, conf = classify_negative(pos, c, query)
        quality = round(min(1.0, 0.5 * c["similarity"] + 0.5 * conf), 3)
        out.append({"query": query, "positive": positive_chunk_id, "hard_negative": c["chunk_id"], "similarity": round(c["similarity"], 4),
                    "negative_type": ntype, "reason": reason, "confidence": conf, "quality_score": quality})
    prio = {"wrong_version": 0, "wrong_section": 1, "keyword_overlap": 2, "topical": 3}
    out.sort(key=lambda x: (prio[x["negative_type"]], -x["similarity"]))
    # Keragaman: batasi per tipe agar reranker belajar versi DAN section (bukan hanya salah versi).
    cap, used, picked = {"wrong_version": 2, "wrong_section": 2, "keyword_overlap": 1, "topical": 1}, {}, []
    for h in out:
        if used.get(h["negative_type"], 0) < cap[h["negative_type"]]:
            used[h["negative_type"]] = used.get(h["negative_type"], 0) + 1
            picked.append(h)
    return picked[:max_negatives]
