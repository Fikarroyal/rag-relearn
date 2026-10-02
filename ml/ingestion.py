"""Document ingestion: ekstraksi teks (PDF/DOCX/TXT/MD) -> cleaning -> section detection -> chunking -> metadata."""

from __future__ import annotations
import re
from pathlib import Path
from ml.common import content_hash, embed

ALLOWED = {".pdf", ".docx", ".txt", ".md"}
MAX_BYTES = 10 * 1024 * 1024


def sanitize(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def extract_text(path: Path) -> list[tuple[int, str]]:
    """Return [(page, text)]."""
    ext = path.suffix.lower()
    if ext not in ALLOWED:
        raise ValueError(f"Tipe file tidak didukung: {ext}")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Ukuran file melebihi 10 MB")
    if ext in {".txt", ".md"}:
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if ext == ".docx":
        import docx
        d = docx.Document(str(path))
        lines = [("## " + p.text if p.style.name.startswith("Heading") else p.text) for p in d.paragraphs]
        return [(1, "\n".join(lines))]
    from pypdf import PdfReader
    return [(i + 1, p.extract_text() or "") for i, p in enumerate(PdfReader(str(path)).pages)]


def split_sections(pages: list[tuple[int, str]]) -> list[dict]:
    sections, cur = [], {"section": "Pendahuluan", "page": 1, "lines": []}
    for page, text in pages:
        for line in sanitize(text).splitlines():
            m = re.match(r"^#{1,3}\s+(.*)", line) or re.match(r"^(Bagian\s+\d+.*|\d+\.\s+[A-Z].{3,60})$", line)
            if m and not line.startswith("# "):
                if cur["lines"]:
                    sections.append(cur)
                cur = {"section": m.group(1).strip(), "page": page, "lines": []}
            elif line.strip() and not line.startswith("# "):
                cur["lines"].append(line)
    if cur["lines"]:
        sections.append(cur)
    return sections


def parse_name(stem: str) -> tuple[str, int]:
    m = re.match(r"^(.*?)_v(\d+)$", stem)
    return (m.group(1), int(m.group(2))) if m else (stem, 1)


def chunk_document(path: Path, max_chars: int = 900) -> dict:
    family, version = parse_name(path.stem)
    document_id = f"{family}_v{version}"
    title = family.replace("_", " ")
    chunks = []
    for n, sec in enumerate(split_sections(extract_text(path)), start=1):
        body = " ".join(sec["lines"])
        parts = [body[i:i + max_chars] for i in range(0, len(body), max_chars)] or [body]
        for j, part in enumerate(parts):
            content = f"{sec['section']}. {part}"
            chunks.append({
                "chunk_id": f"{document_id}_section_{n}" + (f"_{j}" if j else ""),
                "document_id": document_id, "family": family, "version": version, "title": title,
                "section": sec["section"], "page": sec["page"], "chunk_index": len(chunks), "source": path.name,
                "content": content, "content_hash": content_hash(content), "vector": embed(content).tolist(),
            })
    return {"document_id": document_id, "family": family, "version": version, "title": title, "source": path.name, "chunks": chunks}
