# Arsitektur RAG-Relearn

```
Frontend (React/TS)  ->  FastAPI (backend/app)  ->  ml/ (logika RAG murni, tanpa dependensi web)
                              |                         pipeline.py  retrieval/  reranking/  evaluation/
                              |                         failure_detection/  hard_negative/  training/  experiments/
                              +-- PostgreSQL / SQLite (SQLAlchemy)
                              +-- VectorStore (in-memory numpy; antarmuka siap diganti Qdrant/pgvector)
MCP server (mcp-server/) --HTTP--> /api/mcp/invoke  (satu implementasi tool, dipakai juga oleh UI)
```

## Closed loop
1. `ml/pipeline.run_rag`: classify -> embed -> search Top-20 -> rerank -> context (3 chunk) -> LLM -> sitasi -> verifier.
2. `ml/failure_detection.detect`: aturan + hasil verifier -> `failure_type, confidence, evidence, root_cause, recommended_action`.
3. `ml/hard_negative.mine`: Top-20, buang positif/duplikat (content_hash), klasifikasi negatif
   (`wrong_version > wrong_section > keyword_overlap > topical`), quality score.
4. `ml/hard_negative.dataset`: validasi (missing field, duplikat, dokumen tidak valid, label kontradiktif, negatif berkualitas rendah),
   split deterministik per-query (tanpa leakage query).
5. `ml/training.trainer`: reranker linear pairwise (logistic loss) dilatih dari pasangan positif/negatif. Fitur: similarity,
   keyword_overlap, **is_latest**, section_match, title_overlap. Opsi `hf_lora_trainer.py` untuk cross-encoder LoRA nyata.
6. Model baru berstatus `candidate` -> A/B test (metrik mentah, tanpa pemenang otomatis) -> promosi manual -> `production`.

## Desain eksperimen (jujur)
- Query **training** (`data/train_queries.json`) dan query **evaluasi** (`data/eval_dataset.json`) terpisah.
- Dataset evaluasi hanya 12 query dan embedding hashing lokal: ini bukti konsep pipeline, bukan klaim performa umum.
- `RAG + Failure Detection` = heuristik runtime (version guard); `RAG-Relearn` = bobot hasil training. Keduanya dilaporkan terpisah.
