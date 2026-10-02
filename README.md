<div align="center">

<img src="docs/assets/logo.svg" width="72" alt="RAG-Relearn logo">

# RAG-Relearn

**Retrieval Failure Analysis and Continuous RAG Improvement**

Platform riset AI Engineering yang mendiagnosis *kenapa* RAG salah, lalu **belajar dari kesalahan itu** secara terukur, terdokumentasi, dan bisa direproduksi.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-12_tools-E0560D)
![Tests](https://img.shields.io/badge/tests-26_passed-2F8F6B)

<img src="docs/assets/closed-loop.svg" alt="Alur closed-loop RAG-Relearn" width="100%">

</div>

## <img src="docs/assets/icons/lightbulb.svg" width="26" align="center"> Ringkasan

Kebanyakan proyek RAG berhenti di "chatbot yang menjawab dari dokumen". Masalahnya, RAG sering **gagal diam-diam**: dokumen yang diambil salah versi, salah section, atau mirip secara topik tetapi tidak menjawab pertanyaan, dan tidak ada yang tahu.

RAG-Relearn berfokus pada hal itu:

| Pertanyaan | Jawaban RAG-Relearn |
|---|---|
| Kenapa jawaban ini salah? | **Failure Detector** menandai salah satu dari 15 jenis kegagalan, lengkap dengan *evidence*, *root cause*, dan *recommended action*. |
| Dokumen apa yang menyesatkan retriever? | **Hard Negative Miner** mencari chunk yang mirip tetapi salah (versi lama, section lain, keyword overlap). |
| Bagaimana memperbaikinya? | **Dataset generator** + **trainer** melatih reranker dari pasangan positif/negatif. |
| Apakah model baru benar-benar lebih baik? | **A/B test** dan **Experiments** menampilkan metrik mentah pada dataset yang sama, tanpa memilih pemenang otomatis. |
| Bisakah agen AI memantau ini? | **MCP server** dengan 12 tool untuk observasi dan evaluasi. |

Kasus demo: **SOP Backup Server v1 sampai v4** sengaja ditulis sangat mirip. Baseline memilih versi lama; setelah belajar dari kegagalannya, model memilih versi terbaru.

## <img src="docs/assets/icons/repeat.svg" width="26" align="center"> Cara kerja

Sistem berjalan dalam dua jalur: **Serve** (menjawab dan mencatat) dan **Learn** (belajar dari kegagalan). Setiap query disimpan sebagai *evaluation record* yang bisa dianalisis ulang.

| # | Tahap | Modul | Keluaran |
|---|---|---|---|
| 1 | Query + Classify | `ml/retrieval/classifier.py` | tipe query (procedural, version-sensitive, ...) menentukan strategi |
| 2 | Vector Search | `ml/retrieval/retriever.py` | Top-20 kandidat + similarity |
| 3 | Rerank | `ml/reranking/reranker.py` | skor akhir dari fitur: similarity, keyword, **is_latest**, section |
| 4 | Context Builder | `ml/pipeline.py` | 3 chunk terbaik dengan metadata versi |
| 5 | LLM + Citation | `ml/providers.py` | jawaban bersitasi (mock lokal, OpenAI, atau Claude) |
| 6 | Evaluate | `ml/evaluation/` | Recall@K, MRR, NDCG, faithfulness, citation accuracy, latency |
| 7 | Failure Detector | `ml/failure_detection/` | `failure_type`, confidence, evidence, root cause, action |
| 8 | Hard Negative Miner | `ml/hard_negative/miner.py` | negatif sulit + tipe + alasan + quality score |
| 9 | Training Dataset | `ml/hard_negative/dataset.py` | dataset tervalidasi, split tanpa leakage query |
| 10 | Train Reranker | `ml/training/` | bobot baru (pairwise loss) atau LoRA via HF/PEFT |
| 11 | A/B Evaluation | `backend/app/routers/evaluation.py` | selisih metrik antar model |
| 12 | Production | Model Registry | promosi manual dengan konfirmasi |

```mermaid
sequenceDiagram
    autonumber
    participant UI as Frontend
    participant API as FastAPI
    participant ML as ml.pipeline
    participant DB as Database
    UI->>API: POST /api/rag/query
    API->>ML: run_rag(query, store, bobot model)
    ML-->>API: retrieved, reranked, answer, citations
    API->>ML: evaluate_record() + detect()
    API->>DB: simpan query, retrieval_results, rag_evaluations, failure_cases
    API-->>UI: jawaban, ranking, diagnosis
```

Siklus hidup model di registry:

```mermaid
stateDiagram-v2
    [*] --> training
    training --> candidate: job selesai
    candidate --> staging: lolos A/B test
    staging --> production: promosi (konfirmasi)
    candidate --> production: promosi (konfirmasi)
    production --> archived: digantikan
    candidate --> archived
```

## <img src="docs/assets/icons/layout-dashboard.svg" width="26" align="center"> Fitur

| | Fitur | Halaman UI |
|---|---|---|
| <img src="docs/assets/icons/layout-dashboard.svg" width="20"> | KPI, grafik success rate, distribusi kegagalan, latency, perbandingan model | Dashboard |
| <img src="docs/assets/icons/terminal.svg" width="20"> | Jalankan query, lihat ranking, context window, sitasi, dan diagnosis langsung | RAG Playground |
| <img src="docs/assets/icons/search.svg" width="20"> | Dokumen yang diharapkan vs hasil retrieval (tangga peringkat) | Retrieval Analysis |
| <img src="docs/assets/icons/shield-alert.svg" width="20"> | Tabel kegagalan dengan filter, sort, pagination, dan halaman detail diagnosis | Failure Cases |
| <img src="docs/assets/icons/network.svg" width="20"> | Review hard negative: Approve, Reject, Regenerate | Hard Negatives |
| <img src="docs/assets/icons/database.svg" width="20"> | Dataset, split train/val/test, validasi kualitas, export JSON/JSONL/CSV | Training Dataset |
| <img src="docs/assets/icons/sliders-horizontal.svg" width="20"> | Konfigurasi training, kurva loss langsung, mode lightweight atau HF/LoRA | Training Center |
| <img src="docs/assets/icons/boxes.svg" width="20"> | Registry versi model dan promosi status | Models |
| <img src="docs/assets/icons/git-compare-arrows.svg" width="20"> | Model A vs B pada dataset sama, delta per metrik | A/B Testing |
| <img src="docs/assets/icons/chart-column.svg" width="20"> | Evaluasi batch: retrieval, generation, latency, kegagalan | Evaluation |
| <img src="docs/assets/icons/flask-conical.svg" width="20"> | Empat konfigurasi dibandingkan, hasil lama tidak pernah dihapus | Experiments |
| <img src="docs/assets/icons/file-text.svg" width="20"> | Upload PDF/DOCX/TXT/MD, chunking, metadata versi | Documents |
| <img src="docs/assets/icons/layers.svg" width="20"> | Coba 12 tool MCP langsung dari UI | MCP Tools |
| <img src="docs/assets/icons/settings.svg" width="20"> | Konfigurasi aktif dan observabilitas (request, error rate, token) | System Settings |

Pendukung: JWT + role (viewer, researcher, admin), validasi upload (tipe dan 10 MB), sanitasi konten, `request_id` pada setiap request, structured logging, provider LLM yang bisa diganti.

## <img src="docs/assets/icons/triangle-alert.svg" width="26" align="center"> Demo version mismatch

Query: **"Bagaimana prosedur backup server?"**. Ground truth adalah `SOP_Backup_v4_section_3`. Angka di bawah diambil dari data seed asli.

<img src="docs/assets/failure-demo.svg" alt="Ranking sebelum dan sesudah training" width="100%">

Yang terjadi:

1. Model v1 hanya memakai similarity, jadi `SOP_Backup_v3` (0.859) mengalahkan `v4` (0.497). Detector menandai `document_version_mismatch`.
2. Dari kegagalan v1 pada query-query training yang serupa (misalnya "Prosedur pencadangan data server rumah sakit"), versi lama (v1, v2, v3) ditambang sebagai **hard negative**. Query demo di atas sendiri tidak dipakai untuk training.
3. Reranker dilatih dari pasangan tersebut. Bobot fitur `is_latest` naik dari 0 ke sekitar 3, dan `section_match` juga naik:

<img src="docs/assets/learned-weights.svg" alt="Bobot reranker sebelum dan sesudah training" width="100%">

4. Model v2 menaruh `SOP_Backup_v4_section_3` di rank 1.

## <img src="docs/assets/icons/chart-column.svg" width="26" align="center"> Hasil eksperimen

<img src="docs/assets/results.svg" alt="Hasil eksperimen EXP-001" width="100%">

| Metrik | Baseline | + Reranker | + Failure Detection | **RAG-Relearn** |
|---|---|---|---|---|
| Recall@1 | 0.42 | 0.42 | 0.75 | **0.75** |
| Recall@3 | 0.50 | 0.50 | 0.75 | **1.00** |
| MRR | 0.55 | 0.55 | 0.81 | **0.86** |
| NDCG | 0.64 | 0.64 | 0.86 | **0.90** |
| Failure rate (lebih rendah lebih baik) | 0.58 | 0.58 | 0.25 | **0.25** |

Cara membaca hasil ini dengan jujur:

- **+ Reranker** identik dengan baseline karena bobot dasarnya belum punya sinyal versi. Reranker baru berguna setelah dilatih.
- **+ Failure Detection** adalah heuristik runtime (*version guard*), bukan hasil training. Ia sudah menyelesaikan sebagian besar kasus versi, sedangkan RAG-Relearn unggul di Recall@3, MRR, dan NDCG.
- Query **training** (`data/train_queries.json`) dipisah dari query **evaluasi** (`data/eval_dataset.json`), jadi tidak ada kebocoran query.
- Dataset evaluasi hanya 12 query dan didominasi kasus versi, jadi ini bukti konsep pipeline, bukan klaim performa umum. Pada demo di atas, rank 2 dan 3 juga diisi section lain dari v4 karena model sangat condong ke `is_latest`.

## <img src="docs/assets/icons/layout-dashboard.svg" width="26" align="center"> Tampilan aplikasi

Screenshot di bawah diambil dari aplikasi yang berjalan dengan data seed.

<img src="docs/assets/screens/dashboard.png" alt="Dashboard" width="100%">

<img src="docs/assets/screens/playground.png" alt="RAG Playground menampilkan kegagalan version mismatch" width="100%">

<img src="docs/assets/screens/failure-detail.png" alt="Detail failure case" width="100%">

<details>
<summary><b>Lihat halaman lainnya</b></summary>

<br>

**Hard Negatives**

<img src="docs/assets/screens/hard-negatives.png" alt="Hard negatives" width="100%">

**Training Center**

<img src="docs/assets/screens/training-center.png" alt="Training center" width="100%">

**A/B Testing**

<img src="docs/assets/screens/ab-testing.png" alt="A/B testing" width="100%">

**Experiments**

<img src="docs/assets/screens/experiments.png" alt="Experiments" width="100%">

**Documents**

<img src="docs/assets/screens/documents.png" alt="Documents" width="100%">

</details>

## <img src="docs/assets/icons/server.svg" width="26" align="center"> Arsitektur

<img src="docs/assets/architecture.svg" alt="Arsitektur RAG-Relearn" width="100%">

## <img src="docs/assets/icons/rocket.svg" width="26" align="center"> Quick start

**Prasyarat:** Python (conda atau venv) dan Node.js 18+.

```bash
# 1. Masuk ke root proyek (folder yang berisi backend/, frontend/, ml/)
cd rag-relearn

# 2. Buat environment (sekali saja)
conda create -n ragrelearn python=3.11 -y
conda activate ragrelearn

# 3. Install dependensi backend - jalankan dari ROOT proyek
python -m pip install -r backend/requirements.txt

# 4. Seed database demo (SQLite)
cd backend
python -m app.seed

# 5. Jalankan backend
uvicorn app.main:app --reload --port 8000
```

Buka **terminal kedua** untuk frontend:

```bash
cd rag-relearn/frontend
npm install
npm run dev
```

Buka **http://localhost:5173**. Dokumentasi API interaktif ada di http://localhost:8000/docs.

**Checklist berhasil:**

- [ ] `python -m app.seed` mencetak `Seed selesai: {'docs': 9, 'chunks': 44, 'queries': 98, ...}`
- [ ] http://localhost:8000/api/health menampilkan `{"status":"ok", ...}`
- [ ] Dashboard terisi grafik, dan navbar menampilkan `Sistem normal` serta model `v2`

**Alternatif tanpa conda:** `python3 -m venv .venv && source .venv/bin/activate`, lalu langkah 3 dan seterusnya sama. Skrip `./scripts/dev.sh` menjalankan semuanya sekaligus.

**Alternatif Docker** (PostgreSQL + Qdrant + backend + MCP + frontend):

```bash
cp .env.example .env     # opsional; tanpa API key otomatis memakai provider mock
docker compose up --build
```

Frontend di http://localhost:3000. Konfigurasi Docker belum diverifikasi end-to-end oleh penulis, jadi jalur lokal di atas adalah yang teruji.

## <img src="docs/assets/icons/wrench.svg" width="26" align="center"> Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `No module named 'sqlalchemy'` atau pesan "Dependensi belum terpasang" | Paket belum di-install di environment aktif | `python -m pip install -r backend/requirements.txt` dari **root** proyek |
| `Could not open requirements file: requirements.txt` | Salah folder | File ada di `backend/`. Dari root: `-r backend/requirements.txt`; dari dalam `backend/`: `-r requirements.txt` |
| `unsupported operand type(s) for \|` | Python lama dengan kode versi sebelumnya | Pakai versi proyek terbaru (sudah kompatibel Python 3.9+) atau Python 3.11 |
| `psycopg2-binary` gagal build | Hanya dibutuhkan untuk PostgreSQL | Hapus baris itu dari `backend/requirements.txt` untuk mode SQLite |
| Frontend: "Data gagal dimuat" | Backend belum jalan | Jalankan `uvicorn app.main:app --reload --port 8000` |
| Dashboard kosong | Seed belum dijalankan | `cd backend && python -m app.seed --reset` |
| `mcp` tidak bisa di-install | SDK MCP butuh Python 3.10+ | Jalankan MCP server di environment Python 3.11 |
| Terminal macOS: `chsh` / pesan zsh | Hanya pemberitahuan shell | Abaikan, atau `conda init zsh` lalu buka terminal baru |

## <img src="docs/assets/icons/plug.svg" width="26" align="center"> MCP server

Agen AI dapat mengamati dan mengevaluasi sistem lewat 12 tool: `evaluate_rag`, `inspect_retrieval`, `get_failure_cases`, `get_failure_case`, `generate_training_set`, `generate_hard_negatives`, `run_ab_test`, `compare_models`, `get_model_metrics`, `get_rag_metrics`, `trigger_retraining`, `get_training_status`.

```bash
pip install -r mcp-server/requirements.txt          # Python 3.10+
BACKEND_URL=http://localhost:8000 python mcp-server/server.py     # stdio
MCP_TRANSPORT=sse python mcp-server/server.py                     # HTTP :8765
```

Konfigurasi klien MCP (stdio):

```json
{ "mcpServers": { "rag-relearn": { "command": "python", "args": ["mcp-server/server.py"], "env": { "BACKEND_URL": "http://localhost:8000" } } } }
```

`trigger_retraining` hanya menghasilkan model `candidate`. Promosi ke production tetap keputusan manusia.

## <img src="docs/assets/icons/network.svg" width="26" align="center"> API

Dokumentasi lengkap di `/docs` (Swagger). Endpoint utama:

| Area | Endpoint |
|---|---|
| RAG | `POST /api/rag/query`, `POST /api/rag/evaluate`, `GET /api/rag/history`, `GET /api/retrieval/{query_id}` |
| Failure | `GET /api/failures`, `GET /api/failures/{id}`, `POST /api/failures/{id}/hard-negative` |
| Training | `POST /api/training/dataset`, `GET /api/training/datasets`, `POST /api/training/start`, `GET /api/training/{job_id}` |
| Model | `GET /api/models`, `POST /api/models/register`, `POST /api/models/{id}/status` |
| Evaluasi | `POST /api/evaluation/run`, `GET /api/evaluation/{id}`, `POST /api/ab-test`, `GET /api/ab-test/{id}`, `GET /api/experiments` |
| Lainnya | `POST /api/documents/upload`, `GET /api/dashboard/metrics`, `POST /api/mcp/invoke`, `POST /api/auth/login` |

Contoh evaluasi dan A/B dari terminal:

```bash
curl -X POST localhost:8000/api/evaluation/run -H 'content-type: application/json' -d '{"model_version":"v2"}'
curl -X POST localhost:8000/api/ab-test -H 'content-type: application/json' -d '{"model_a":"v1","model_b":"v2"}'
curl -X POST "localhost:8000/api/experiments/run?epochs=40"
```

## Konfigurasi

Salin `.env.example` menjadi `.env`. Tanpa `OPENAI_API_KEY` atau `ANTHROPIC_API_KEY`, aplikasi memakai embedding hashing lokal dan generator extractive mock, jadi tetap berjalan penuh. Provider LLM berpola `ml/providers.py` (tambah Ollama atau HF dengan mengimplementasikan `LLMProvider.generate`). Aktifkan `AUTH_ENABLED=true` dan ganti `JWT_SECRET` untuk penggunaan di luar demo.

Fine-tuning cross-encoder LoRA nyata: `pip install -r ml/requirements-train.txt`, lalu `python -m ml.training.hf_lora_trainer datasets/train.jsonl`. Tanpa GPU otomatis memakai CPU.

## <img src="docs/assets/icons/list-checks.svg" width="26" align="center"> Pengujian

```bash
python -m pip install -r backend/requirements.txt
python -m pytest -q      # 26 test
```

Mencakup ingestion, chunking, embedding, retrieval, reranking, failure detection, hard negative mining, dataset (termasuk leakage), evaluasi, API, tool MCP, dan satu **integrasi closed-loop** (query, retrieval, evaluasi, deteksi kegagalan, dataset, training, evaluasi ulang). Test dijalankan lulus di Python 3.9 dan 3.12.

Regenerasi aset README: `python scripts/generate_readme_assets.py` (diagram dari data seed) dan `python scripts/capture_screenshots.py` (screenshot, butuh Playwright dan kedua server berjalan).

## <img src="docs/assets/icons/scale.svg" width="26" align="center"> Batasan yang jujur

- Embedding hashing lokal dan reranker linear dipilih agar berjalan tanpa GPU atau API key. Kualitas absolutnya bukan state of the art.
- Dataset evaluasi kecil (12 query) dan didominasi kasus versi dokumen. Hasil eksperimen adalah bukti konsep pipeline, bukan klaim generalisasi.
- Reranker hasil training sangat condong ke fitur `is_latest`; ia bisa menaikkan section lain dari versi terbaru di atas section yang benar dari versi lama. Dataset yang lebih beragam diperlukan untuk menyeimbangkannya.
- Vector store default berupa numpy in-memory dari tabel `document_chunks`. Antarmuka `VectorStore` siap diganti Qdrant atau pgvector, tetapi adapter-nya belum dibuat.
- Mode HF/LoRA tersedia sebagai modul terpisah dan belum dijalankan pada seed karena membutuhkan torch.
- Docker Compose belum diverifikasi end-to-end.

## Roadmap

- [ ] Adapter Qdrant / pgvector
- [ ] Dataset evaluasi lebih besar dan beragam (bukan hanya versi dokumen)
- [ ] Embedding model sungguhan (sentence-transformers) sebagai provider
- [ ] Menjalankan fine-tuning cross-encoder LoRA pada dataset hasil mining
- [ ] CI GitHub Actions untuk test dan build frontend

---

<div align="center">

Dibuat sebagai proyek portofolio AI Engineer: fokus pada **diagnosis kegagalan RAG** dan **peningkatan retrieval yang terukur**.

</div>
