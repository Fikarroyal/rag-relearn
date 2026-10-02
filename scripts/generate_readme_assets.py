"""Membuat diagram/grafik SVG untuk README dari data NYATA (database seed + pipeline).
Pakai: (setelah `python -m app.seed`)  python scripts/generate_readme_assets.py"""
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT, ICONS = ROOT / "docs" / "assets", ROOT / "docs" / "assets" / "icons"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
INK, BR, MUTE, LINE, BG50, STONE, AMBER = "#23262B", "#E0560D", "#6B7078", "#E5E4E0", "#FFF4EC", "#A8A29E", "#D9A441"
esc = html.escape


def icon(name, x, y, size=22, color=BR):
    s = (ICONS / f"{name}.svg").read_text()
    inner = re.sub(r"^<svg.*?>", "", s, count=1, flags=re.S).replace("</svg>", "").strip()
    return (f'<g transform="translate({x} {y}) scale({size / 24:.3f})" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{inner}</g>')


def text(x, y, s, size=13, weight=400, fill=INK, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(str(s))}</text>'


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}" font-family="{FONT}">'
            f'<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{MUTE}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>'
            f'<marker id="arb" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{BR}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="#FFFFFF" stroke="{LINE}"/>{body}</svg>')


def arrow(x1, y1, x2, y2, hot=False):
    c, m = (BR, "arb") if hot else (MUTE, "ar")
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#{m})"/>'


def card(x, y, w, h, hot=False, fill=None):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill or (BG50 if hot else "#FFFFFF")}" stroke="{BR if hot else LINE}" stroke-width="{1.6 if hot else 1.2}"/>'


def step(x, y, w, h, n, ic, title, s1, s2, hot=False):
    return (card(x, y, w, h, hot) + f'<circle cx="{x + 30}" cy="{y + 32}" r="19" fill="{BG50 if not hot else "#FFFFFF"}"/>' + icon(ic, x + 19, y + 21)
            + f'<circle cx="{x + w - 18}" cy="{y + 18}" r="10" fill="{INK}"/>' + text(x + w - 18, y + 22, n, 11, 600, "#FFFFFF", "middle")
            + text(x + 14, y + 68, title, 14.5, 600) + text(x + 14, y + 86, s1, 11.5, 400, MUTE) + text(x + 14, y + 101, s2, 11.5, 400, MUTE))


def load_db():
    con = sqlite3.connect(ROOT / "data" / "rag_relearn.db")
    q = lambda sql: con.execute(sql).fetchall()
    return {
        "exp": json.loads(q("select metrics from experiments order by id limit 1")[0][0]),
        "w2": json.loads(q("select weights from model_versions where version='v2'")[0][0]),
    }


# ---------- 1. closed loop ----------
def closed_loop():
    bw, bh, gap, x0, y1, y2 = 168, 112, 30, 21, 92, 330
    colx = lambda c: x0 + c * (bw + gap)
    r1 = [("search", "Query + Classify", "Preprocess, klasifikasi", "8 tipe query"), ("database", "Vector Search", "Embedding + cosine", "Top-20 kandidat"),
          ("sliders-horizontal", "Rerank", "Reranker linear", "fitur versi & section"), ("layers", "Context Builder", "3 chunk terbaik", "beserta metadata versi"),
          ("bot", "LLM + Citation", "Jawaban bersitasi", "mock / OpenAI / Claude"), ("chart-column", "Evaluate", "Recall, MRR, NDCG", "faithfulness, sitasi")]
    r2 = [("shield-alert", "Failure Detector", "15 jenis kegagalan", "evidence + root cause"), ("network", "Hard Negative Miner", "salah versi / section", "similarity tinggi"),
          ("database", "Training Dataset", "query-positive-negative", "validasi + split"), ("cpu", "Train Reranker", "pairwise loss", "atau LoRA (HF/PEFT)"),
          ("git-compare-arrows", "A/B Evaluation", "dataset yang sama", "metrik mentah"), ("rocket", "Production", "promosi manual", "dengan konfirmasi")]
    b = [f'<rect x="21" y="26" width="104" height="26" rx="13" fill="{INK}"/>', text(73, 43, "SERVE", 12.5, 600, "#FFFFFF", "middle"), text(136, 44, "menjawab query & mencatat evaluation record", 13, 400, MUTE),
         f'<rect x="21" y="264" width="104" height="26" rx="13" fill="{BR}"/>', text(73, 281, "LEARN", 12.5, 600, "#FFFFFF", "middle"), text(136, 282, "belajar dari kegagalan, lalu memperbaiki retrieval", 13, 400, MUTE)]
    for i, (ic, t, a, c) in enumerate(r1):
        b.append(step(colx(i), y1, bw, bh, i + 1, ic, t, a, c))
        if i < 5:
            b.append(arrow(colx(i) + bw + 3, y1 + 56, colx(i + 1) - 3, y1 + 56))
    for i, (ic, t, a, c) in enumerate(r2):
        col = 5 - i
        b.append(step(colx(col), y2, bw, bh, i + 7, ic, t, a, c, hot=i == 0))
        if i < 5:
            b.append(arrow(colx(col) - 3, y2 + 56, colx(col - 1) + bw + 3, y2 + 56, hot=True))
    cx5, cx0 = colx(5) + bw / 2, colx(0) + bw / 2
    b += [arrow(cx5, y1 + bh + 3, cx5, y2 - 3, True), text(cx5 - 10, 238, "gagal?", 12, 600, BR, "end"),
          arrow(cx0, y2 - 3, cx0, y1 + bh + 3, True), text(cx0 + 12, 238, "model baru melayani query berikutnya", 12, 600, BR)]
    b += [card(21, 468, 1158, 66, fill="#FAFAF9"), icon("file-search", 40, 488, 24, INK),
          text(78, 492, "Evaluation record", 13.5, 600), text(78, 512, "query - retrieved_documents - retrieval/reranking scores - selected_context - answer - citations - ground_truth - failure_type - latency - model_version", 12, 400, MUTE)]
    (OUT / "closed-loop.svg").write_text(svg(1200, 556, "".join(b), "Alur closed-loop RAG-Relearn: serve lalu learn"), encoding="utf-8")


# ---------- 2. architecture ----------
def architecture():
    b = []
    def box(x, y, w, h, ic, t, s1, s2=None, hot=False):
        b.append(card(x, y, w, h, hot) + icon(ic, x + 16, y + 16, 24) + text(x + 52, y + 33, t, 14.5, 600) + text(x + 52, y + 51, s1, 12, 400, MUTE) + (text(x + 52, y + 66, s2, 12, 400, MUTE) if s2 else ""))
    box(30, 40, 210, 76, "bot", "AI Agent", "Claude / klien MCP")
    box(30, 170, 210, 84, "plug", "MCP Server", "12 tools (FastMCP)", "stdio atau SSE")
    box(30, 330, 210, 110, "layout-dashboard", "Frontend", "React + TypeScript", "14 halaman, Recharts", hot=True)
    b.append(card(330, 40, 370, 400, fill="#FAFAF9") + icon("server", 346, 56, 24) + text(382, 74, "FastAPI Backend", 15, 600) + text(382, 92, "routers + SQLAlchemy + JWT", 12, 400, MUTE))
    rows = [("/api/rag", "query, evaluate, history"), ("/api/failures", "diagnosis, hard negative"), ("/api/training", "dataset, job, export"), ("/api/models", "registry & promosi"),
            ("/api/evaluation", "batch, A/B, experiments"), ("/api/documents", "upload & ingestion"), ("/api/mcp", "invoke 12 tools"), ("middleware", "JWT, role, request_id, log")]
    for i, (a, c) in enumerate(rows):
        y = 112 + i * 40
        b.append(f'<rect x="346" y="{y}" width="338" height="32" rx="7" fill="#FFFFFF" stroke="{LINE}"/>' + text(358, y + 21, a, 12.5, 600, BR) + text(470, y + 21, c, 12.5, 400, MUTE))
    b.append(card(790, 40, 380, 400, fill="#FAFAF9") + icon("brain-circuit", 806, 56, 24) + text(842, 74, "ml/  (logika RAG murni)", 15, 600) + text(842, 92, "tanpa dependensi web, mudah diuji", 12, 400, MUTE))
    mods = [("pipeline", "orchestrator"), ("retrieval", "classifier + vector"), ("reranking", "reranker linear"), ("failure_detection", "15 jenis"), ("hard_negative", "miner + dataset"),
            ("training", "pairwise / LoRA"), ("evaluation", "metrik + runner"), ("experiments", "closed-loop"), ("ingestion", "PDF DOCX TXT MD"), ("providers", "mock/OpenAI/Claude")]
    for i, (a, c) in enumerate(mods):
        x, y = 806 + (i % 2) * 176, 112 + (i // 2) * 64
        b.append(f'<rect x="{x}" y="{y}" width="164" height="54" rx="8" fill="#FFFFFF" stroke="{LINE}"/>' + text(x + 12, y + 23, a, 13, 600) + text(x + 12, y + 41, c, 12, 400, MUTE))
    box(330, 490, 180, 74, "database", "Database", "PostgreSQL / SQLite")
    box(520, 490, 180, 74, "hard-drive" if (ICONS / "hard-drive.svg").exists() else "package", "Vector store", "numpy / Qdrant")
    box(790, 490, 380, 74, "package", "Data & artefak", "data/seed_docs, datasets/, models/, uploads")
    b += [arrow(135, 120, 135, 166), arrow(244, 212, 326, 212), text(285, 204, "HTTP", 11.5, 600, MUTE, "middle"), arrow(244, 385, 326, 385), text(285, 377, "REST", 11.5, 600, MUTE, "middle"),
          arrow(704, 240, 786, 240, True), text(745, 232, "import", 11.5, 600, BR, "middle"), arrow(420, 444, 420, 486), arrow(610, 444, 610, 486), arrow(980, 444, 980, 486)]
    (OUT / "architecture.svg").write_text(svg(1200, 596, "".join(b), "Arsitektur RAG-Relearn"), encoding="utf-8")


# ---------- 3. demo: version mismatch (data nyata) ----------
def failure_demo(w2):
    from ml.experiments.closed_loop import load_store
    from ml.pipeline import run_rag
    store, q, gt = load_store(), "Bagaimana prosedur backup server?", "SOP_Backup_v4_section_3"
    before = run_rag(q, store, use_reranker=False, top_k=5, ground_truth_chunk=gt)["reranked"]
    after = run_rag(q, store, weights=w2, use_reranker=True, top_k=5, ground_truth_chunk=gt)["reranked"]
    b = [icon("search", 30, 28, 22, INK), text(62, 46, q, 17, 600), text(30, 74, "Ground truth: ", 13, 400, MUTE), text(118, 74, gt, 13, 600, "#047857")]
    def panel(x, title, key, rows, tag, ok):
        mx = max(r[key] for r in rows)
        out = [card(x, 96, 560, 340, fill="#FAFAF9"), text(x + 18, 126, title, 14.5, 600)]
        out.append(f'<rect x="{x + 560 - 18 - len(tag) * 7.4 - 20}" y="110" width="{len(tag) * 7.4 + 20}" height="24" rx="12" fill="{"#ECFDF5" if ok else "#FEF2F2"}"/>' + text(x + 560 - 28 - len(tag) * 3.7, 126, tag, 12, 600, "#047857" if ok else "#B91C1C", "middle"))
        for i, r in enumerate(rows):
            y, good = 150 + i * 56, r["chunk_id"] == gt
            out.append(f'<rect x="{x + 14}" y="{y}" width="532" height="46" rx="8" fill="{"#ECFDF5" if good else "#FFFFFF"}" stroke="{"#6EE7B7" if good else LINE}"/>')
            out.append(f'<circle cx="{x + 38}" cy="{y + 23}" r="12" fill="{INK if i == 0 else "#EFEDE9"}"/>' + text(x + 38, y + 27.5, i + 1, 12, 600, "#FFFFFF" if i == 0 else INK, "middle"))
            out.append(text(x + 62, y + 28, r["chunk_id"], 12.5, 600) + f'<rect x="{x + 300}" y="{y + 18}" width="120" height="8" rx="4" fill="#EFEDE9"/><rect x="{x + 300}" y="{y + 18}" width="{max(4, 120 * r[key] / mx):.0f}" height="8" rx="4" fill="{BR if good else INK}"/>')
            out.append(text(x + 432, y + 28, f"{r[key]:.3f}", 12.5, 500, MUTE))
            out.append(text(x + 532, y + 28, "benar" if good else "salah", 12, 600, "#047857" if good else "#B91C1C", "end"))
        return "".join(out)
    b += [panel(30, "Sebelum: model v1 (similarity saja)", "similarity", before, "document_version_mismatch", False),
          panel(610, "Sesudah: model v2 (reranker terlatih)", "reranking_score", after, "rank 1 benar", after[0]["chunk_id"] == gt),
          arrow(592, 266, 606, 266, True)]
    (OUT / "failure-demo.svg").write_text(svg(1200, 460, "".join(b), "Contoh kegagalan version mismatch sebelum dan sesudah training"), encoding="utf-8")
    return before[0]["chunk_id"], after[0]["chunk_id"]


# ---------- 4. hasil eksperimen ----------
def results(exp):
    arms = [("baseline", "Baseline RAG", STONE), ("rag_reranker", "+ Reranker", AMBER), ("rag_failure_detection", "+ Failure Detection", INK), ("rag_relearn", "RAG-Relearn", BR)]
    mets = [("recall@1", "Recall@1"), ("recall@3", "Recall@3"), ("mrr", "MRR"), ("ndcg", "NDCG"), ("failure_rate", "Failure rate")]
    x0, x1, y0, y1 = 80, 960, 90, 380
    b = [text(30, 40, "Eksperimen EXP-001: empat konfigurasi pada dataset evaluasi yang sama", 17, 600), text(30, 62, "12 query evaluasi, query training terpisah. Failure rate: lebih rendah lebih baik.", 12.5, 400, MUTE)]
    for i in range(6):
        y = y1 - i * (y1 - y0) / 5
        b += [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#EDEBE7"/>', text(x0 - 10, y + 4, f"{i / 5:.1f}", 11.5, 400, MUTE, "end")]
    gw = (x1 - x0) / len(mets)
    for gi, (k, name) in enumerate(mets):
        gx = x0 + gi * gw + (gw - 4 * 34 - 3 * 6) / 2
        for ai, (ak, an, col) in enumerate(arms):
            v = exp[ak][k]
            h = (y1 - y0) * v
            x = gx + ai * 40
            b += [f'<rect x="{x:.1f}" y="{y1 - h:.1f}" width="34" height="{h:.1f}" rx="4" fill="{col}"/>', text(x + 17, y1 - h - 6, f"{v:.2f}", 11, 600, INK, "middle")]
        b.append(text(x0 + gi * gw + gw / 2, y1 + 24, name, 13, 600, INK, "middle"))
    lx = 30
    for ak, an, col in arms:
        b += [f'<rect x="{lx}" y="418" width="14" height="14" rx="3" fill="{col}"/>', text(lx + 22, 430, an, 12.5, 500)]
        lx += 40 + len(an) * 7.2
    (OUT / "results.svg").write_text(svg(1000, 452, "".join(b), "Grafik hasil eksperimen EXP-001"), encoding="utf-8")


# ---------- 5. bobot reranker ----------
def weights(w2):
    base = {"similarity": 1.0, "keyword_overlap": 0.25, "is_latest": 0.0, "section_match": 0.0, "title_overlap": 0.15}
    feats = list(base)
    mx = max(max(abs(v) for v in base.values()), max(abs(v) for v in w2.values()))
    x0, sc = 210, 520 / mx
    b = [text(30, 40, "Bobot reranker: sebelum vs sesudah training", 17, 600), text(30, 62, "Reranker belajar memberi bobot pada fitur versi terbaru (is_latest) dan kecocokan section.", 12.5, 400, MUTE)]
    for i, f in enumerate(feats):
        y = 92 + i * 52
        hot = f in ("is_latest", "section_match")
        if hot:
            b.append(f'<rect x="20" y="{y - 8}" width="960" height="52" rx="8" fill="{BG50}"/>')
        b.append(text(36, y + 22, f, 13.5, 600))
        for j, (val, col) in enumerate([(base[f], STONE), (w2[f], BR)]):
            yy = y + j * 18
            b += [f'<rect x="{x0}" y="{yy}" width="{max(2, abs(val) * sc):.0f}" height="12" rx="3" fill="{col}"/>', text(x0 + max(2, abs(val) * sc) + 8, yy + 11, f"{val:.2f}", 12, 500, MUTE)]
    b += [f'<rect x="30" y="368" width="14" height="14" rx="3" fill="{STONE}"/>', text(52, 380, "Model v1 (bobot dasar)", 12.5), f'<rect x="230" y="368" width="14" height="14" rx="3" fill="{BR}"/>', text(252, 380, "Model v2 (hasil training dari hard negative)", 12.5)]
    (OUT / "learned-weights.svg").write_text(svg(1000, 404, "".join(b), "Perbandingan bobot reranker"), encoding="utf-8")


if __name__ == "__main__":
    d = load_db()
    closed_loop(); architecture(); results(d["exp"]); weights(d["w2"])
    print("demo rank-1 sebelum/sesudah:", failure_demo(d["w2"]))
    print("db v2 weights:", d["w2"])
