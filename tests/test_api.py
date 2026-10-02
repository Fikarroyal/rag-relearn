from __future__ import annotations

QUERY = "Bagaimana prosedur backup server?"


def test_health_and_dashboard(client):
    assert client.get("/api/health").json()["chunks_indexed"] > 0
    d = client.get("/api/dashboard/metrics").json()
    assert d["kpis"]["total_queries"] > 50 and d["kpis"]["total_failures"] > 0 and d["failure_distribution"]


def test_query_returns_diagnosis_for_old_model(client):
    r = client.post("/api/rag/query", json={"query": QUERY, "model_version": "v1"}).json()
    assert r["diagnosis"]["failure_type"] == "document_version_mismatch" and r["failure_id"]
    r2 = client.post("/api/rag/query", json={"query": QUERY, "model_version": "v2"}).json()
    assert r2["diagnosis"] is None and r2["reranked"][0]["chunk_id"] == "SOP_Backup_v4_section_3"


def test_evaluate_requires_ground_truth(client):
    assert client.post("/api/rag/evaluate", json={"query": "pertanyaan tanpa ground truth apapun"}).status_code == 422
    assert client.post("/api/rag/evaluate", json={"query": QUERY}).status_code == 200


def test_retrieval_and_history(client):
    qid = client.post("/api/rag/query", json={"query": QUERY, "model_version": "v1"}).json()["query_id"]
    r = client.get(f"/api/retrieval/{qid}").json()
    assert r["results"][0]["rank"] == 1 and any(x["correct"] for x in r["results"])
    assert client.get("/api/rag/history").json()


def test_failure_workflow(client):
    page = client.get("/api/failures", params={"failure_type": "document_version_mismatch", "page_size": 5}).json()
    assert page["total"] > 0
    fid = page["items"][0]["id"]
    d = client.get(f"/api/failures/{fid}").json()
    assert d["diagnosis"]["recommended_action"] and d["retrieved"]
    assert client.post(f"/api/failures/{fid}/hard-negative").status_code == 200
    assert client.post(f"/api/failures/{fid}/status", json={"status": "resolved"}).json()["status"] == "resolved"
    assert client.post(f"/api/failures/{fid}/status", json={"status": "bogus"}).status_code == 422
    assert client.get("/api/failures/999999").status_code == 404


def test_hard_negatives_actions(client):
    items = client.get("/api/hard-negatives", params={"status": "pending"}).json()["items"]
    hid = items[0]["id"]
    assert client.post(f"/api/hard-negatives/{hid}/approve").json()["status"] == "approved"
    assert client.post(f"/api/hard-negatives/{hid}/nope").status_code == 404


def test_dataset_export_and_validation(client):
    ds = client.get("/api/training/datasets").json()[0]
    assert ds["stats"]["n_samples"] > 0
    assert client.get(f"/api/training/datasets/{ds['id']}/export", params={"format": "jsonl"}).text.count("\n") >= 1
    assert "query,positive" in client.get(f"/api/training/datasets/{ds['id']}/export", params={"format": "csv"}).text
    new = client.post("/api/training/dataset", json={"name": "t"}).json()
    assert new["validation"]["train_test_leakage"] == 0


def test_training_job_registers_candidate(client):
    import time
    ds = client.get("/api/training/datasets").json()[0]["id"]
    jid = client.post("/api/training/start", json={"dataset_id": ds, "epochs": 5}).json()["job_id"]
    for _ in range(60):
        j = client.get(f"/api/training/{jid}").json()
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(0.2)
    assert j["status"] == "completed" and len(j["history"]) == 5
    mv = [m for m in client.get("/api/models").json() if m["version"] == j["model_version"]][0]
    assert mv["status"] == "candidate" and mv["metrics"]["mrr"] > 0


def test_models_ab_and_evaluation(client):
    ab = client.post("/api/ab-test", json={"model_a": "v1", "model_b": "v2"}).json()
    row = {r["metric"]: r for r in ab["rows"]}
    assert row["mrr"]["improved"] and "winner" not in ab
    assert client.get(f"/api/ab-test/{ab['id']}").status_code == 200
    ev = client.post("/api/evaluation/run", json={"model_version": "v2"}).json()
    assert client.get(f"/api/evaluation/{ev['id']}").json()["per_query"]
    assert client.post("/api/evaluation/run", json={"model_version": "zzz"}).status_code == 404


def test_registry_promotion_keeps_single_production(client):
    models = client.get("/api/models").json()
    cand = [m for m in models if m["status"] == "candidate"][0]
    client.post(f"/api/models/{cand['id']}/status", json={"status": "production"})
    assert sum(m["status"] == "production" for m in client.get("/api/models").json()) == 1
    assert client.post("/api/models/register", json={"version": "v1"}).status_code == 409


def test_upload_validation(client):
    assert client.post("/api/documents/upload", files={"file": ("x.exe", b"abc")}).status_code == 415
    ok = client.post("/api/documents/upload", files={"file": ("SOP_Test.md", "## Bagian 1: A\nIsi dokumen uji backup.".encode())}, data={"version": "1"})
    assert ok.status_code == 200 and ok.json()["chunks"] == 1


def test_experiments_never_deleted(client):
    before = len(client.get("/api/experiments").json())
    client.post("/api/experiments/run", params={"epochs": 10})
    assert len(client.get("/api/experiments").json()) == before + 1


def test_mcp_tools(client):
    tools = {t["name"] for t in client.get("/api/mcp/tools").json()}
    assert len(tools) == 12
    r = client.post("/api/mcp/invoke", json={"tool": "inspect_retrieval", "arguments": {"query": QUERY}}).json()
    assert r["results"][0]["rank"] == 1
    assert "total_queries" in client.post("/api/mcp/invoke", json={"tool": "get_rag_metrics"}).json()
    assert client.post("/api/mcp/invoke", json={"tool": "compare_models", "arguments": {"model_a": "v1", "model_b": "v2"}}).json()["delta"]["mrr"] > 0
    assert client.post("/api/mcp/invoke", json={"tool": "nope"}).status_code == 404


def test_auth_login_and_observability(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "salah"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "viewer", "password": "viewer123"}).json()["role"] == "viewer"
    assert client.get("/api/observability/summary").json()["request_count"] > 0
    assert "sk-" not in str(client.get("/api/settings").json())
