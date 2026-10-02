"""Query classifier berbasis aturan -> menentukan strategi retrieval."""

from __future__ import annotations
import re

RULES = [
    ("version_sensitive", r"\b(versi|terbaru|terkini|latest|revisi|v\d+)\b"),
    ("temporal", r"\b(kapan|jadwal|tanggal|periode|setiap|harian|mingguan|bulanan)\b"),
    ("comparative", r"\b(beda|perbedaan|bandingkan|dibanding|versus|vs)\b"),
    ("troubleshooting", r"\b(gagal|error|tidak bisa|masalah|rusak|down|troubleshoot)\b"),
    ("multi_hop", r"\b(setelah itu|lalu|kemudian|dan juga|serta)\b|\bsekaligus\b"),
    ("procedural", r"\b(prosedur|langkah|cara|sop|bagaimana)\b"),
    ("factual", r"\b(apa|siapa|berapa|dimana|di mana)\b"),
]

STRATEGY = {
    "version_sensitive": {"prefer_latest": True},
    "procedural": {"prefer_latest": True, "prefer_sop": True},
    "multi_hop": {"multi_doc": True},
    "ambiguous": {"expand_query": True},
    "temporal": {"prefer_latest": True},
    "comparative": {"multi_doc": True},
    "troubleshooting": {},
    "factual": {},
}


def classify(query: str) -> dict:
    q = query.lower().strip()
    for label, pat in RULES:
        if re.search(pat, q):
            return {"type": label, "strategy": STRATEGY[label]}
    label = "ambiguous" if len(q.split()) <= 3 else "factual"
    return {"type": label, "strategy": STRATEGY[label]}


def expand_query(query: str) -> str:
    return query + " prosedur langkah sop"
