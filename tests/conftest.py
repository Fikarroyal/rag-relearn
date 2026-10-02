from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AUTH_ENABLED"] = "false"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.seed import seed
    seed(reset=True)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def store():
    from ml.experiments.closed_loop import load_store
    return load_store()
