"""RAG-Relearn backend."""
import sys
from pathlib import Path

# Folder root proyek (berisi paket `ml/`) harus ada di sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import fastapi, jwt, numpy, sqlalchemy  # noqa: F401
except ImportError as e:  # pesan jelas, bukan traceback panjang
    raise SystemExit(
        f"Dependensi belum terpasang ({e.name}).\n"
        "Jalankan dari root proyek:  pip install -r backend/requirements.txt\n"
        "Disarankan memakai virtualenv Python 3.10+  (python3 -m venv .venv && source .venv/bin/activate)"
    )
