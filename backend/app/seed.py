"""Seed demo: dokumen SOP, riwayat query 14 hari, failure cases, hard negatives, dataset, training v2, A/B, eksperimen.
Jalankan: python -m app.seed [--reset]"""

from __future__ import annotations
import sys
import time
from datetime import datetime, timedelta

from app import models as M
from app.db import Base, SessionLocal, engine
from app import services as S
from app.config import ROOT, EMBEDDING_MODEL

sys.path.insert(0, str(ROOT))
from ml.ingestion import chunk_document  # noqa: E402
from ml.evaluation.runner import run_batch  # noqa: E402
from ml.experiments.closed_loop import load_eval, load_train_queries, run_experiment  # noqa: E402
from ml.hard_negative.miner import mine  # noqa: E402
from ml.reranking.reranker import BASE_WEIGHTS  # noqa: E402
from ml.training.trainer import train  # noqa: E402


def seed(reset: bool = False):
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if db.query(M.Document).count():
        print("Seed dilewati: data sudah ada (pakai --reset untuk ulang)")
        return
    for u, p, r in [("admin", "admin123", "admin"), ("researcher", "research123", "researcher"), ("viewer", "viewer123", "viewer")]:
        db.add(M.User(username=u, password_hash=S.hash_password(p), role=r))
    db.commit()
    for path in sorted((ROOT / "data" / "seed_docs").glob("*.md")):
        S.ingest_chunks(db, chunk_document(path))
    store = S.get_store(db)

    model = M.Model(name="rag-relearn-reranker", description="Reranker linear terlatih dari hard negative")
    db.add(model)
    db.flush()
    v1 = M.ModelVersion(model_id=model.id, version="v1", base_model="hashing-512-local", embedding_model=EMBEDDING_MODEL, reranker="none",
                        weights=BASE_WEIGHTS, config={"use_reranker": False}, status="production", trained_at=datetime.utcnow() - timedelta(days=20))
    db.add(v1)
    db.commit()

    eval_ds, train_q = load_eval(), load_train_queries()
    pool = train_q + eval_ds
    now = datetime.utcnow()

    def simulate(version, days, rt):
        for d in days:
            batch = [pool[(d * 5 + i) % len(pool)] for i in range(7)]
            out = run_batch(batch, store, weights=rt["weights"], use_reranker=rt["use_reranker"], model_version=version)
            for i, rec in enumerate(out["records"]):
                S.persist_record(db, rec, ts=now - timedelta(days=d, hours=2 + i), runtime=rt)

    simulate("v1", range(13, 6, -1), {"weights": None, "use_reranker": False, "reranker": "none"})

    # hard negative mining dari failure v1 (hanya query training -> tanpa leakage dengan dataset evaluasi)
    train_texts = {q["query"] for q in train_q}
    fails = db.query(M.FailureCase).filter_by(model_version="v1").all()
    seen = set()
    for f in fails:
        if f.query_text not in train_texts or (f.query_text, f.ground_truth) in seen:
            continue
        seen.add((f.query_text, f.ground_truth))
        for hn in mine(f.query_text, f.ground_truth, store):
            db.add(M.HardNegative(failure_id=f.id, failure_type=f.failure_type, **hn))
    db.commit()
    hns = db.query(M.HardNegative).order_by(M.HardNegative.id).all()
    for i, h in enumerate(hns):
        h.status = "pending" if i % 7 == 3 else "rejected" if i % 11 == 5 else "approved"
    db.commit()

    dset = S.build_dataset(db, "failure-mining-batch-1", ("approved",))
    samples = [{"query": s.query, "positive": s.positive, "hard_negative": s.hard_negative, "split": s.split} for s in dset.samples]
    tr = [s for s in samples if s["split"] == "train"] or samples
    va = [s for s in samples if s["split"] == "validation"]
    cfg = {"epochs": 40, "learning_rate": 0.5, "batch_size": 8, "base_model": "linear-reranker", "mode": "lightweight"}
    res = train(tr, va, store, epochs=40, lr=0.5, batch_size=8)
    job = M.TrainingJob(dataset_id=dset.id, config=cfg, status="completed", history=res["history"], result=res, model_version="v2",
                        created_at=now - timedelta(days=7), finished_at=now - timedelta(days=7) + timedelta(seconds=3))
    db.add(job)
    ev1 = run_batch(eval_ds, store, use_reranker=False, model_version="v1")["metrics"]
    ev2 = run_batch(eval_ds, store, weights=res["weights"], model_version="v2")["metrics"]
    v1.metrics = ev1
    v2 = M.ModelVersion(model_id=model.id, version="v2", base_model="linear-reranker", embedding_model=EMBEDDING_MODEL, reranker="linear-reranker-v2",
                        weights=res["weights"], config={"use_reranker": True}, training_dataset_id=dset.id, metrics=ev2, status="production",
                        trained_at=now - timedelta(days=7))
    v1.status = "archived"
    db.add(v2)
    db.commit()
    simulate("v2", range(6, -1, -1), {"weights": res["weights"], "use_reranker": True, "reranker": "linear-reranker-v2"})

    # evaluation runs + A/B test
    for ver, rt in [("v1", {"weights": None, "use_reranker": False}), ("v2", {"weights": res["weights"], "use_reranker": True})]:
        out = run_batch(eval_ds, store, weights=rt["weights"], use_reranker=rt["use_reranker"], model_version=ver)
        db.add(M.EvaluationRun(dataset="eval_default", model_version=ver, retriever="vector-cosine", reranker="none" if ver == "v1" else "linear-reranker-v2",
                               top_k=5, metrics=out["metrics"], per_query=[{"query": r["query"], "top1": r["reranked"][0]["chunk_id"], "ground_truth": r["ground_truth_chunk"],
                                                                         "failure_type": r["diagnosis"]["failure_type"] if r["diagnosis"] else None, **r["eval"]} for r in out["records"]]))
    from app.routers.evaluation import compute_ab
    db.add(M.AbTest(model_a="v1", model_b="v2", dataset="eval_default", results=compute_ab(db, "v1", "v2", "eval_default")))
    db.commit()

    exp = run_experiment(store, eval_ds, train_q, epochs=40, lr=0.5)
    base, cand = exp["summary"]["baseline"], exp["summary"]["rag_relearn"]
    db.add(M.Experiment(exp_id="EXP-001", baseline="baseline", candidate="rag_relearn", dataset="eval_default",
                        config={"epochs": 40, "learning_rate": 0.5, "train_queries": len(train_q), "n_samples": len(exp["samples"]), "seed": 42},
                        metrics=exp["summary"], improvement={k: round(cand[k] - base[k], 4) for k in base}))
    db.commit()
    print("Seed selesai:", {t: db.query(m).count() for t, m in [("docs", M.Document), ("chunks", M.DocumentChunk), ("queries", M.Query),
                                                                  ("failures", M.FailureCase), ("hard_negatives", M.HardNegative)]})


if __name__ == "__main__":
    t = time.time()
    seed("--reset" in sys.argv)
    print(f"{time.time() - t:.1f}s")
