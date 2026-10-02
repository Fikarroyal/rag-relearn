"""Trainer reranker pairwise (logistic loss) -- ringan, CPU only, benar-benar belajar dari hard negative.
Untuk fine-tuning cross-encoder sungguhan lihat ml/training/hf_lora_trainer.py (opsional, perlu torch/PEFT)."""

from __future__ import annotations
import math
import random
import time
import numpy as np
from ml.reranking.reranker import FEATURES, BASE_WEIGHTS, featurize
from ml.retrieval.retriever import VectorStore, latest_versions
from ml.common import embed


def build_pairs(samples: list[dict], store: VectorStore):
    by_id = {c["chunk_id"]: c for c in store.chunks}
    latest = latest_versions(store.chunks)
    pairs = []
    for s in samples:
        p, n = by_id.get(s["positive"]), by_id.get(s["hard_negative"])
        if not p or not n:
            continue
        qv = embed(s["query"])
        fp = featurize(s["query"], {**p, "similarity": float(np.dot(qv, p["vector"]))}, latest)
        fn = featurize(s["query"], {**n, "similarity": float(np.dot(qv, n["vector"]))}, latest)
        pairs.append(fp - fn)
    return np.array(pairs, dtype=np.float32)


def _loss(w, X):
    return float(np.mean(np.log1p(np.exp(-(X @ w))))) if len(X) else 0.0


def train(train_samples, val_samples, store, epochs=30, lr=0.2, batch_size=8, l2=1e-3, base_weights=None, seed=42, progress=None):
    rng = random.Random(seed)
    Xtr, Xva = build_pairs(train_samples, store), build_pairs(val_samples, store)
    w = np.array([(base_weights or BASE_WEIGHTS)[f] for f in FEATURES], dtype=np.float32)
    history, t0 = [], time.time()
    if len(Xtr) == 0:
        raise ValueError("Dataset training kosong atau chunk tidak valid")
    for ep in range(1, epochs + 1):
        idx = list(range(len(Xtr)))
        rng.shuffle(idx)
        for i in range(0, len(idx), batch_size):
            xb = Xtr[idx[i:i + batch_size]]
            margin = xb @ w
            grad = -(xb * (1 / (1 + np.exp(margin)))[:, None]).mean(axis=0) + l2 * w
            w = w - lr * grad
        row = {"epoch": ep, "loss": round(_loss(w, Xtr), 5), "val_loss": round(_loss(w, Xva), 5) if len(Xva) else None,
               "learning_rate": lr, "gpu_memory_mb": 0, "elapsed_s": round(time.time() - t0, 3)}
        history.append(row)
        if progress:
            progress(row)
    return {"weights": {f: round(float(x), 5) for f, x in zip(FEATURES, w)}, "history": history, "n_train": len(Xtr), "n_val": len(Xva)}
