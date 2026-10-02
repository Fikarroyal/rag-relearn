"""MCP server RAG-Relearn. Semua tool diteruskan ke backend (/api/mcp/invoke) sehingga logikanya satu sumber.
Jalankan: python server.py   (stdio, untuk Claude Desktop/agent)  |  MCP_TRANSPORT=sse python server.py  (HTTP)"""
import os

import httpx
from mcp.server.fastmcp import FastMCP

API = os.getenv("BACKEND_URL", "http://localhost:8000")
TOKEN = os.getenv("MCP_API_TOKEN", "")
mcp = FastMCP("rag-relearn", host=os.getenv("MCP_HOST", "0.0.0.0"), port=int(os.getenv("MCP_PORT", "8765")))


def call(tool: str, **arguments):
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    r = httpx.post(f"{API}/api/mcp/invoke", json={"tool": tool, "arguments": arguments}, headers=headers, timeout=120)
    if r.status_code >= 400:
        return {"error": r.json().get("detail", r.text), "status": r.status_code}
    return r.json()


@mcp.tool()
def evaluate_rag(query: str, model_version: str | None = None) -> dict:
    """Jalankan query RAG, evaluasi terhadap ground truth, dan deteksi kegagalan."""
    return call("evaluate_rag", query=query, model_version=model_version)


@mcp.tool()
def inspect_retrieval(query: str) -> dict:
    """Lihat ranking retrieval (similarity + reranking score) untuk sebuah query."""
    return call("inspect_retrieval", query=query)


@mcp.tool()
def get_failure_cases(filters: dict | None = None) -> dict:
    """Daftar failure case. filters: failure_type, model_version, severity, status, search, page, page_size."""
    return call("get_failure_cases", filters=filters or {})


@mcp.tool()
def get_failure_case(failure_id: int) -> dict:
    """Detail lengkap satu failure case."""
    return call("get_failure_case", failure_id=failure_id)


@mcp.tool()
def generate_training_set() -> dict:
    """Bangun dataset training dari hard negative berstatus approved."""
    return call("generate_training_set")


@mcp.tool()
def generate_hard_negatives(query: str) -> dict:
    """Mining hard negative untuk failure case terbaru dari query tersebut."""
    return call("generate_hard_negatives", query=query)


@mcp.tool()
def run_ab_test(model_a: str, model_b: str, dataset: str = "eval_default") -> dict:
    """A/B test dua versi model pada dataset yang sama; hasil berupa metrik mentah (tanpa pemenang otomatis)."""
    return call("run_ab_test", model_a=model_a, model_b=model_b, dataset=dataset)


@mcp.tool()
def compare_models(model_a: str, model_b: str) -> dict:
    """Bandingkan metrik tersimpan dua versi model."""
    return call("compare_models", model_a=model_a, model_b=model_b)


@mcp.tool()
def get_model_metrics(model_version: str) -> dict:
    """Metrik dan status satu versi model."""
    return call("get_model_metrics", model_version=model_version)


@mcp.tool()
def get_rag_metrics() -> dict:
    """KPI sistem RAG (success rate, failure rate, grounding, latency)."""
    return call("get_rag_metrics")


@mcp.tool()
def trigger_retraining(dataset_id: int) -> dict:
    """Mulai job training dari dataset tertentu. Hasilnya berstatus candidate (tidak otomatis production)."""
    return call("trigger_retraining", dataset_id=dataset_id)


@mcp.tool()
def get_training_status(job_id: int) -> dict:
    """Status dan progres job training."""
    return call("get_training_status", job_id=job_id)


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
