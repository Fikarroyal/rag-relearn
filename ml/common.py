"""Utilitas bersama: tokenisasi, embedding hashing lokal (tanpa API key / GPU)."""

from __future__ import annotations
import hashlib
import re
import numpy as np

DIM = 512
STOP = {"yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "ini", "itu", "atau", "the", "of", "to", "a", "bagaimana", "apa", "kapan", "siapa"}


def tokenize(text: str):
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in STOP]


def embed(text: str) -> np.ndarray:
    """Signed feature hashing unigram+bigram -> vektor ter-normalisasi (deterministik)."""
    v = np.zeros(DIM, dtype=np.float32)
    toks = tokenize(text)
    for f in toks + [a + "_" + b for a, b in zip(toks, toks[1:])]:
        h = int(hashlib.md5(f.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 64) & 1 else -1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:16]


def overlap(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    return len(ta & tb) / len(ta) if ta else 0.0
