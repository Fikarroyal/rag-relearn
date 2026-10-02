"""RAG orchestrator: query -> classify -> embed -> search -> rerank -> context -> LLM -> citation -> verify."""

from __future__ import annotations
import re
import time
import uuid
from ml.common import embed, overlap
from ml.providers import get_llm
from ml.retrieval.classifier import classify, expand_query
from ml.retrieval.retriever import VectorStore, latest_versions
from ml.reranking.reranker import LinearReranker


def verify(answer: str, context: list[dict]) -> dict:
    body = re.sub(r"\[[^\]]+\]", "", answer)
    ctx = " ".join(c["content"] for c in context)
    faith = overlap(body, ctx) if body.strip() else 0.0
    cited = re.findall(r"\[([^\]]+)\]", answer)
    return {"faithfulness": faith, "citations": cited}


def run_rag(query: str, store: VectorStore, weights: dict | None = None, top_k: int = 5, threshold: float = 0.0,
            use_reranker: bool = True, version_guard: bool = False, llm: str | None = None, ground_truth_chunk: str | None = None,
            model_version: str = "v1") -> dict:
    t0 = time.perf_counter()
    cls = classify(query)
    q = expand_query(query) if cls["strategy"].get("expand_query") else query
    t1 = time.perf_counter()
    qv = embed(q)
    t2 = time.perf_counter()
    cands = store.search(q, top_k=20, threshold=threshold, query_vec=qv)
    t3 = time.perf_counter()
    latest = latest_versions(store.chunks)
    guard = version_guard and cls["strategy"].get("prefer_latest", False)
    if use_reranker:
        reranked = LinearReranker(weights).rerank(query, cands, latest, version_guard=guard)
    else:
        reranked = [{**c, "reranking_score": c["similarity"]} for c in cands]
    t4 = time.perf_counter()
    reranked = reranked[:max(top_k, 1)]
    selected = reranked[:3]
    answer = get_llm(llm).generate(query, selected)
    t5 = time.perf_counter()
    ver = verify(answer, selected)
    ms = lambda a, b: round((b - a) * 1000, 3)
    metrics = {"preprocess_ms": ms(t0, t1), "embedding_ms": ms(t1, t2), "retrieval_ms": ms(t2, t3), "reranking_ms": ms(t3, t4),
               "generation_ms": ms(t4, t5), "total_ms": ms(t0, t5), "faithfulness": ver["faithfulness"]}
    conf = float(reranked[0]["reranking_score"]) if reranked else 0.0
    return {"request_id": uuid.uuid4().hex[:12], "query": query, "query_class": cls, "retrieved": cands[:top_k], "reranked": reranked,
            "selected": selected, "answer": answer, "citations": ver["citations"], "ground_truth_chunk": ground_truth_chunk,
            "metrics": metrics, "confidence_score": round(conf, 4), "model_version": model_version}
