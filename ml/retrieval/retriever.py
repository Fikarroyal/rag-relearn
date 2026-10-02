"""Vector retriever (cosine) di atas index in-memory. Interface VectorStore bisa diganti Qdrant/pgvector."""

from __future__ import annotations
import numpy as np
from ml.common import embed


class VectorStore:
    def __init__(self, chunks: list[dict]):
        """chunks: chunk_id, document_id, family, version, section, page, title, content, vector."""
        self.chunks = chunks
        self.matrix = np.array([np.asarray(c["vector"], dtype=np.float32) for c in chunks]) if chunks else np.zeros((0, 512), dtype=np.float32)

    def search(self, query: str, top_k: int = 20, threshold: float = 0.0, query_vec=None):
        if not len(self.chunks):
            return []
        qv = embed(query) if query_vec is None else query_vec
        sims = self.matrix @ qv
        out = []
        for i in np.argsort(-sims)[:top_k]:
            if sims[i] >= threshold:
                out.append({**{k: v for k, v in self.chunks[i].items() if k != "vector"}, "similarity": float(sims[i])})
        return out


def latest_versions(chunks: list[dict]) -> dict:
    """family SOP -> versi terbaru."""
    best: dict = {}
    for c in chunks:
        best[c["family"]] = max(best.get(c["family"], 0), c["version"])
    return best
