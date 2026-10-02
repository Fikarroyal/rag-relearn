"""Failure detector rule-based + verifier-assisted. Output: type, confidence, evidence, root_cause, recommended_action."""

from __future__ import annotations
FAILURE_TYPES = [
    "false_positive_retrieval", "false_negative_retrieval", "missing_context", "contradictory_context", "wrong_chunk",
    "document_version_mismatch", "low_semantic_similarity", "poor_reranking", "insufficient_context", "irrelevant_context",
    "citation_error", "hallucination", "answer_grounding_failure", "answer_relevance_failure", "retrieval_latency_problem",
]
SEVERITY = {"document_version_mismatch": "high", "hallucination": "high", "false_negative_retrieval": "high", "contradictory_context": "high",
            "false_positive_retrieval": "medium", "wrong_chunk": "medium", "poor_reranking": "medium", "citation_error": "medium",
            "answer_grounding_failure": "medium", "retrieval_latency_problem": "low", "low_semantic_similarity": "medium"}
ACTION = {
    "document_version_mismatch": "Tambahkan hard negative versi lama dan fitur is_latest pada reranker; terapkan version guard.",
    "false_positive_retrieval": "Mining hard negative dengan similarity tinggi; latih ulang reranker.",
    "false_negative_retrieval": "Perbaiki chunking/embedding atau naikkan Top K; periksa indeks dokumen.",
    "wrong_chunk": "Perbaiki section detection dan tambahkan hard negative antar-section.",
    "poor_reranking": "Latih reranker dengan pasangan positif/negatif dari kasus ini.",
    "low_semantic_similarity": "Aktifkan query expansion atau ganti embedding model.",
    "hallucination": "Perketat prompt grounding dan aktifkan answer verifier.",
    "citation_error": "Validasi sitasi terhadap chunk pada context window.",
    "answer_grounding_failure": "Tingkatkan context precision sebelum generation.",
    "retrieval_latency_problem": "Optimalkan indeks vektor / kurangi Top K.",
    "missing_context": "Tambahkan dokumen sumber yang memuat informasi.",
    "contradictory_context": "Resolusikan konflik versi dokumen sebelum generation.",
    "insufficient_context": "Perbesar context window atau multi-document retrieval.",
    "irrelevant_context": "Naikkan similarity threshold.",
    "answer_relevance_failure": "Periksa query classifier dan prompt generator.",
}


def _diag(ftype, conf, evidence, root):
    return {"failure_type": ftype, "confidence": round(conf, 2), "evidence": evidence, "root_cause": root,
            "recommended_action": ACTION[ftype], "severity": SEVERITY.get(ftype, "low")}


def detect(rec: dict, latency_budget_ms: float = 2000.0) -> dict | None:
    """rec: retrieved (list urut hasil retrieval awal), reranked, selected, ground_truth_chunk, answer, citations, metrics."""
    gt = rec.get("ground_truth_chunk")
    reranked, retrieved, selected = rec["reranked"], rec["retrieved"], rec["selected"]
    top = reranked[0] if reranked else None
    gt_ids = [c["chunk_id"] for c in reranked]
    gt_doc = gt.rsplit("_section_", 1)[0] if gt else None
    gt_family = gt_doc.rsplit("_v", 1)[0] if gt_doc else None
    m = rec.get("metrics", {})

    if gt:
        if gt not in gt_ids:
            if top and top["similarity"] < 0.15:
                return _diag("low_semantic_similarity", 0.8, [f"top similarity={top['similarity']:.2f}"], "Embedding gagal menangkap makna query.")
            return _diag("false_negative_retrieval", 0.9, [f"ground truth {gt} tidak ada di Top-{len(reranked)}"], "Dokumen benar tidak ter-retrieve.")
        if top and top["chunk_id"] != gt:
            versions = {c["version"] for c in reranked if c["family"] == gt_family}
            if top["family"] == gt_family and top["version"] != int(gt_doc.rsplit("_v", 1)[1]):
                ev = [f"dipilih {top['chunk_id']} (v{top['version']}), seharusnya {gt}", f"similarity salah={top['similarity']:.2f}", f"versi tersedia: {sorted(versions)}"]
                return _diag("document_version_mismatch", 0.95, ev, "Reranker tidak mempertimbangkan versi dokumen terbaru.")
            if top["document_id"] == gt_doc:
                return _diag("wrong_chunk", 0.85, [f"dokumen benar, chunk salah: {top['chunk_id']}"], "Section detection/chunking kurang presisi.")
            gt_item = next(c for c in reranked if c["chunk_id"] == gt)
            orig_rank = next((i for i, c in enumerate(retrieved) if c["chunk_id"] == gt), 99)
            if orig_rank < reranked.index(gt_item):
                return _diag("poor_reranking", 0.85, [f"rank retrieval={orig_rank + 1}, rank setelah rerank={reranked.index(gt_item) + 1}"], "Reranker menurunkan dokumen benar.")
            return _diag("false_positive_retrieval", 0.88, [f"{top['chunk_id']} similarity={top['similarity']:.2f} tetapi bukan jawaban"], "Dokumen terkait topik tetapi tidak menjawab query.")
    faith = m.get("faithfulness", 1.0)
    if faith < 0.5:
        return _diag("hallucination", 0.8, [f"faithfulness={faith:.2f}"], "Jawaban memuat klaim di luar context.")
    if rec.get("citations") and not set(rec["citations"]) <= {c["chunk_id"] for c in selected}:
        return _diag("citation_error", 0.9, [f"sitasi {rec['citations']} tidak ada pada context"], "Citation engine menunjuk chunk di luar context.")
    if gt and gt not in [c["chunk_id"] for c in selected]:
        return _diag("insufficient_context", 0.75, ["ground truth tidak masuk selected context"], "Context selection terlalu sempit.")
    if m.get("total_ms", 0) > latency_budget_ms:
        return _diag("retrieval_latency_problem", 0.7, [f"total={m['total_ms']:.0f}ms"], "Latency melebihi budget.")
    return None
