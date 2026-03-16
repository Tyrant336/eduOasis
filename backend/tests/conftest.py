import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch

# Set required env vars before any config import happens
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-placeholder")

from db.init import init_db


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = init_db(db_path)
    yield conn
    conn.close()
    os.unlink(db_path)


@pytest.fixture
def client(test_db):
    """TestClient that bypasses lifespan and uses test_db."""
    from main import app

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.db = test_db
        yield

    app.router.lifespan_context = test_lifespan
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
