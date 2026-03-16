# RAG Chatbot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static Recipe Finder modal on Project_1 with an interactive RAG chatbot powered by FastAPI, SQLite + sqlite-vec, and OpenRouter.

**Architecture:** A Python FastAPI backend serves a RAG pipeline (embed → retrieve → generate) while the existing vanilla JS frontend gains a slide-in chat panel triggered by clicking the Project_1 board. Documents can be uploaded via drag-and-drop in the chat panel.

**Tech Stack:** Python 3.11+, FastAPI, sqlite-vec, OpenRouter API, PyMuPDF, vanilla JavaScript (existing), SSE streaming

**Spec:** `docs/superpowers/specs/2026-03-16-rag-chatbot-design.md`

---

## File Structure

### New files to create

```
backend/
├── main.py                  # FastAPI app, CORS, lifespan, route registration
├── config.py                # Pydantic Settings for env vars
├── routes/
│   ├── __init__.py
│   ├── chat.py              # POST /chat (SSE streaming)
│   ├── upload.py            # POST /upload (file ingestion)
│   └── documents.py         # GET /documents, DELETE /documents/{id}
├── rag/
│   ├── __init__.py
│   ├── chunker.py           # Text extraction + recursive chunking
│   ├── embeddings.py        # OpenRouter embedding API calls
│   ├── retrieval.py         # Vector search in SQLite
│   └── generation.py        # Prompt building + LLM streaming
├── db/
│   ├── __init__.py
│   ├── init.py              # DB creation, table setup, sqlite-vec loading
│   └── models.py            # Insert/query/delete helpers
├── tests/
│   ├── __init__.py
│   ├── test_chunker.py
│   ├── test_db.py
│   ├── test_routes.py
│   ├── test_generation.py
│   └── conftest.py          # Shared fixtures (test DB, mock OpenRouter, test client)
├── .gitignore               # Exclude .env, data/, __pycache__/
├── requirements.txt
├── .env.example
└── sample_docs/
    ├── intro-to-web-dev.md
    └── database-basics.md
```

### Existing files to modify

```
index.html         # Add chat panel HTML (after line 185, before mobile controls)
style.css          # Add chat panel CSS (after modal styles, ~line 196)
main.js            # Add chat panel JS logic, modify handleInteraction()
```

---

## Chunk 1: Backend Foundation

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/config.py`

- [ ] **Step 1: Create backend directory and requirements.txt**

```bash
mkdir -p backend/routes backend/rag backend/db backend/tests backend/sample_docs
```

Write `backend/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-dotenv==1.0.1
pydantic-settings==2.7.1
httpx==0.28.1
sqlite-vec==0.1.6
pymupdf==1.25.3
python-multipart==0.0.20
pytest==8.3.4
pytest-asyncio==0.25.0
```

- [ ] **Step 2: Create .env.example**

Write `backend/.env.example`:
```
OPENROUTER_API_KEY=your-key-here
EMBEDDING_MODEL=openai/text-embedding-3-small
CHAT_MODEL=openai/gpt-4o-mini
DB_PATH=./data/rag.db
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
BACKEND_PORT=8081
```

- [ ] **Step 3: Create config.py with Pydantic Settings**

Write `backend/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    embedding_model: str = "openai/text-embedding-3-small"
    chat_model: str = "openai/gpt-4o-mini"
    db_path: str = "./data/rag.db"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    backend_port: int = 8081

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create empty __init__.py files**

Create empty `__init__.py` in: `backend/routes/`, `backend/rag/`, `backend/db/`, `backend/tests/`

- [ ] **Step 5: Install dependencies and verify**

```bash
cd backend && pip install -r requirements.txt
python -c "import fastapi, sqlite_vec, fitz, httpx; print('All imports OK')"
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with dependencies and config"
```

---

### Task 2: Database initialization and models

**Files:**
- Create: `backend/db/init.py`
- Create: `backend/db/models.py`
- Test: `backend/tests/test_db.py`

- [ ] **Step 1: Write failing test for DB initialization**

Write `backend/tests/conftest.py`:
```python
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch
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

    # Patch lifespan so it doesn't init a real DB or call OpenRouter
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.db = test_db
        yield

    app.router.lifespan_context = test_lifespan
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
```

Write `backend/tests/test_db.py`:
```python
def test_init_db_creates_tables(test_db):
    cursor = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "documents" in tables
    assert "chunks" in tables


def test_init_db_creates_vec_table(test_db):
    cursor = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "chunks_vec" in tables
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: FAIL — `db.init` module doesn't exist yet.

- [ ] **Step 3: Implement db/init.py**

Write `backend/db/init.py`:
```python
import os
import sqlite3
import sqlite_vec


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with sqlite-vec extension and create tables."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            position INTEGER NOT NULL,
            token_count INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[1536]
        )
    """)

    conn.commit()
    return conn
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: PASS

- [ ] **Step 5: Write failing tests for db/models.py**

Add to `backend/tests/test_db.py`:
```python
from db.models import insert_document, insert_chunk, get_documents, delete_document


def test_insert_and_get_document(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    docs = get_documents(test_db)
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    assert docs[0]["filename"] == "test.md"


def test_insert_chunk(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    chunk_id = insert_chunk(test_db, doc_id, "Hello world", 0, 2)
    cursor = test_db.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
    row = cursor.fetchone()
    assert row is not None


def test_delete_document_cascades(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    insert_chunk(test_db, doc_id, "Hello world", 0, 2)
    delete_document(test_db, doc_id)
    docs = get_documents(test_db)
    assert len(docs) == 0
    cursor = test_db.execute("SELECT COUNT(*) FROM chunks")
    assert cursor.fetchone()[0] == 0
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: FAIL — `db.models` doesn't exist yet.

- [ ] **Step 7: Implement db/models.py**

Write `backend/db/models.py`:
```python
import sqlite3
import struct


def insert_document(conn: sqlite3.Connection, filename: str, file_type: str) -> int:
    cursor = conn.execute(
        "INSERT INTO documents (filename, file_type) VALUES (?, ?)",
        (filename, file_type),
    )
    conn.commit()
    return cursor.lastrowid


def insert_chunk(
    conn: sqlite3.Connection,
    doc_id: int,
    text: str,
    position: int,
    token_count: int,
) -> int:
    cursor = conn.execute(
        "INSERT INTO chunks (doc_id, text, position, token_count) VALUES (?, ?, ?, ?)",
        (doc_id, text, position, token_count),
    )
    conn.commit()
    return cursor.lastrowid


def insert_chunk_vector(
    conn: sqlite3.Connection, chunk_id: int, embedding: list[float]
) -> None:
    conn.execute(
        "INSERT INTO chunks_vec (chunk_id, embedding) VALUES (?, ?)",
        (chunk_id, serialize_float32(embedding)),
    )
    conn.commit()


def search_chunks(
    conn: sqlite3.Connection, query_embedding: list[float], top_k: int = 5
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT chunks_vec.chunk_id, chunks_vec.distance, chunks.text, documents.filename
        FROM chunks_vec
        LEFT JOIN chunks ON chunks.id = chunks_vec.chunk_id
        LEFT JOIN documents ON documents.id = chunks.doc_id
        WHERE embedding MATCH ?
        AND k = ?
        ORDER BY distance
        """,
        (serialize_float32(query_embedding), top_k),
    ).fetchall()
    return [
        {"chunk_id": r[0], "distance": r[1], "text": r[2], "filename": r[3]}
        for r in rows
    ]


def get_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT d.id, d.filename, d.file_type, d.uploaded_at,
               COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN chunks c ON c.doc_id = d.id
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
        """
    ).fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "file_type": r[2],
            "uploaded_at": r[3],
            "chunk_count": r[4],
        }
        for r in rows
    ]


def delete_document(conn: sqlite3.Connection, doc_id: int) -> bool:
    # Explicit transaction: delete vectors, then document (cascades to chunks)
    conn.execute("BEGIN")
    try:
        chunk_ids = conn.execute(
            "SELECT id FROM chunks WHERE doc_id = ?", (doc_id,)
        ).fetchall()
        for (chunk_id,) in chunk_ids:
            conn.execute("DELETE FROM chunks_vec WHERE chunk_id = ?", (chunk_id,))
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def get_document_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


def get_chunk_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def serialize_float32(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/db/ backend/tests/
git commit -m "feat: add database initialization and model helpers with tests"
```

---

### Task 3: Text chunker

**Files:**
- Create: `backend/rag/chunker.py`
- Test: `backend/tests/test_chunker.py`

- [ ] **Step 1: Write failing tests for chunker**

Write `backend/tests/test_chunker.py`:
```python
from rag.chunker import chunk_text, extract_text


def test_chunk_text_basic():
    text = "Hello world. " * 200  # ~400 tokens at chars/4
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 0


def test_chunk_text_small_input():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_respects_overlap():
    # With overlap, consecutive chunks should share some text
    text = "Sentence one. Sentence two. Sentence three. Sentence four. " * 20
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    if len(chunks) > 1:
        # Last part of chunk N should appear at start of chunk N+1
        assert chunks[0][-20:] in chunks[1] or chunks[1][:20] in chunks[0]


def test_extract_text_markdown():
    content = b"# Hello\n\nThis is a test."
    result = extract_text(content, "md")
    assert "Hello" in result
    assert "This is a test." in result


def test_extract_text_txt():
    content = b"Plain text content."
    result = extract_text(content, "txt")
    assert result == "Plain text content."


def test_extract_text_unsupported():
    import pytest
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text(b"data", "docx")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_chunker.py -v
```

Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement rag/chunker.py**

Write `backend/rag/chunker.py`:
```python
import fitz  # PyMuPDF


def extract_text(content: bytes, file_type: str) -> str:
    """Extract text from file content based on file type."""
    if file_type in ("txt", "md"):
        return content.decode("utf-8")
    elif file_type == "pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def chunk_text(
    text: str, chunk_size: int = 500, chunk_overlap: int = 50
) -> list[str]:
    """Split text into chunks using recursive character splitting.

    chunk_size and chunk_overlap are in approximate token count (chars / 4).
    """
    char_limit = chunk_size * 4
    char_overlap = chunk_overlap * 4

    if len(text) <= char_limit:
        return [text.strip()] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, char_limit, char_overlap)


def _recursive_split(
    text: str,
    separators: list[str],
    char_limit: int,
    char_overlap: int,
) -> list[str]:
    """Recursively split text trying each separator in order."""
    if len(text) <= char_limit:
        return [text.strip()] if text.strip() else []

    sep = separators[0] if separators else " "
    remaining_seps = separators[1:] if len(separators) > 1 else separators

    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) > char_limit and current:
            chunks.append(current.strip())
            # Overlap: keep tail of current chunk
            overlap_text = current[-char_overlap:] if char_overlap else ""
            current = overlap_text + sep + part if overlap_text else part
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    # If any chunk is still too large, split with next separator
    final = []
    for chunk in chunks:
        if len(chunk) > char_limit and remaining_seps != separators:
            final.extend(
                _recursive_split(chunk, remaining_seps, char_limit, char_overlap)
            )
        else:
            final.append(chunk)

    return final


def estimate_tokens(text: str) -> int:
    """Approximate token count as chars / 4."""
    return len(text) // 4
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_chunker.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/rag/chunker.py backend/tests/test_chunker.py
git commit -m "feat: add recursive text chunker with PDF/MD/TXT extraction"
```

---

### Task 4: OpenRouter embeddings client

**Files:**
- Create: `backend/rag/embeddings.py`

- [ ] **Step 1: Implement rag/embeddings.py**

Write `backend/rag/embeddings.py`:
```python
import httpx
from config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a single text string via OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": text,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embedding vectors for multiple texts in one API call."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": texts,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
```

Note: This module calls the real OpenRouter API. Integration tests require a valid API key. Unit tests in `test_routes.py` will mock this module.

- [ ] **Step 2: Commit**

```bash
git add backend/rag/embeddings.py
git commit -m "feat: add OpenRouter embeddings client"
```

---

### Task 5: Retrieval and generation modules

**Files:**
- Create: `backend/rag/retrieval.py`
- Create: `backend/rag/generation.py`

- [ ] **Step 1: Implement rag/retrieval.py**

Write `backend/rag/retrieval.py`:
```python
import sqlite3
from rag.embeddings import get_embedding
from db.models import search_chunks
from config import settings


async def retrieve_context(
    conn: sqlite3.Connection, query: str
) -> list[dict]:
    """Embed the query and search for relevant chunks."""
    query_embedding = await get_embedding(query)
    results = search_chunks(conn, query_embedding, top_k=settings.top_k)
    return results
```

- [ ] **Step 2: Implement rag/generation.py**

Write `backend/rag/generation.py`:
```python
from collections.abc import AsyncGenerator
import json
import httpx
from config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are a helpful course assistant for Edu Oasis. Answer questions \
based on the provided course materials. If the answer isn't in the \
materials, say so honestly. Keep responses concise and educational."""


def build_prompt(
    context_chunks: list[dict],
    user_message: str,
    history: list[dict],
) -> list[dict]:
    """Build the messages array for the LLM call."""
    context_text = "\n\n---\n\n".join(
        f"[Source: {c['filename']}]\n{c['text']}" for c in context_chunks
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Relevant course materials:\n\n{context_text}",
        },
    ]

    # Add conversation history (last 5 exchanges)
    for entry in history[-10:]:
        messages.append({"role": entry["role"], "content": entry["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


async def stream_response(
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream tokens from OpenRouter LLM."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.chat_model,
                "messages": messages,
                "stream": True,
            },
            timeout=60.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
```

- [ ] **Step 3: Commit**

```bash
git add backend/rag/retrieval.py backend/rag/generation.py
git commit -m "feat: add retrieval and generation modules for RAG pipeline"
```

---

### Task 6: FastAPI app and routes

**Files:**
- Create: `backend/main.py`
- Create: `backend/routes/chat.py`
- Create: `backend/routes/upload.py`
- Create: `backend/routes/documents.py`

- [ ] **Step 1: Implement routes/chat.py**

Write `backend/routes/chat.py`:
```python
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from rag.retrieval import retrieve_context
from rag.generation import build_prompt, stream_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    conn = request.app.state.db

    # Retrieve relevant chunks
    context_chunks = await retrieve_context(conn, req.message)

    # Build prompt with context
    messages = build_prompt(context_chunks, req.message, req.history)

    # Track sources for final message
    sources = list({c["filename"] for c in context_chunks if c["filename"]})

    async def event_stream():
        try:
            async for token in stream_response(messages):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Implement routes/upload.py**

Write `backend/routes/upload.py`:
```python
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from rag.chunker import extract_text, chunk_text, estimate_tokens
from rag.embeddings import get_embeddings_batch
from db.models import insert_document, insert_chunk, insert_chunk_vector
from config import settings

router = APIRouter()

ALLOWED_TYPES = {
    "text/plain": "txt",
    "text/markdown": "md",
    "application/pdf": "pdf",
    "application/octet-stream": None,  # fallback to extension
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    conn = request.app.state.db

    # Determine file type from extension
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("txt", "md", "pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: .txt, .md, .pdf",
        )

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    # Extract text
    try:
        text = extract_text(content, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {e}")

    # Chunk
    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text content found in file.")

    # Embed all chunks
    try:
        embeddings = await get_embeddings_batch(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # Store in DB
    doc_id = insert_document(conn, filename, ext)
    for i, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = insert_chunk(
            conn, doc_id, chunk_text_str, i, estimate_tokens(chunk_text_str)
        )
        insert_chunk_vector(conn, chunk_id, embedding)

    return {
        "document_id": doc_id,
        "filename": filename,
        "chunks": len(chunks),
        "status": "indexed",
    }
```

- [ ] **Step 3: Implement routes/documents.py**

Write `backend/routes/documents.py`:
```python
from fastapi import APIRouter, Request, HTTPException
from db.models import get_documents, delete_document

router = APIRouter()


@router.get("/documents")
async def list_documents(request: Request):
    conn = request.app.state.db
    return get_documents(conn)


@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: int, request: Request):
    conn = request.app.state.db
    deleted = delete_document(conn, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}
```

- [ ] **Step 4: Implement main.py with lifespan and CORS**

Write `backend/main.py`:
```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.init import init_db
from db.models import get_document_count
from routes.chat import router as chat_router
from routes.upload import router as upload_router
from routes.documents import router as documents_router


async def seed_sample_docs(app: FastAPI):
    """Seed sample docs on first startup if DB is empty."""
    conn = app.state.db
    if get_document_count(conn) > 0:
        return

    sample_dir = os.path.join(os.path.dirname(__file__), "sample_docs")
    if not os.path.isdir(sample_dir):
        return

    from rag.chunker import extract_text, chunk_text, estimate_tokens
    from rag.embeddings import get_embeddings_batch
    from db.models import insert_document, insert_chunk, insert_chunk_vector

    for filename in os.listdir(sample_dir):
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ("txt", "md", "pdf"):
            continue
        filepath = os.path.join(sample_dir, filename)
        with open(filepath, "rb") as f:
            content = f.read()
        text = extract_text(content, ext)
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue
        try:
            embeddings = await get_embeddings_batch(chunks)
        except Exception as e:
            print(f"Warning: Failed to embed {filename}: {e}")
            continue
        doc_id = insert_document(conn, filename, ext)
        for i, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = insert_chunk(
                conn, doc_id, chunk_text_str, i, estimate_tokens(chunk_text_str)
            )
            insert_chunk_vector(conn, chunk_id, embedding)
    print(f"Seeded {get_document_count(conn)} sample documents.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = init_db(settings.db_path)
    await seed_sample_docs(app)
    yield
    # Shutdown
    app.state.db.close()


app = FastAPI(title="Edu Oasis RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    conn = app.state.db
    from db.models import get_document_count, get_chunk_count
    return {
        "status": "ok",
        "documents": get_document_count(conn),
        "chunks": get_chunk_count(conn),
    }
```

- [ ] **Step 5: Write route tests with mocked OpenRouter**

Write `backend/tests/test_routes.py`:
```python
import json
from unittest.mock import AsyncMock, patch


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "documents" in data
    assert "chunks" in data


def test_get_documents_empty(client):
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_nonexistent_document(client):
    resp = client.delete("/documents/999")
    assert resp.status_code == 404


@patch("routes.upload.get_embeddings_batch", new_callable=AsyncMock)
def test_upload_txt(mock_embed, client):
    mock_embed.return_value = [[0.1] * 1536]
    resp = client.post(
        "/upload",
        files={"file": ("test.txt", b"Hello world content for testing.", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "indexed"
    assert data["filename"] == "test.txt"
    assert data["chunks"] >= 1


def test_upload_unsupported_type(client):
    resp = client.post(
        "/upload",
        files={"file": ("test.docx", b"data", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


@patch("routes.chat.retrieve_context", new_callable=AsyncMock)
@patch("routes.chat.stream_response")
def test_chat_streams_response(mock_stream, mock_retrieve, client):
    mock_retrieve.return_value = [
        {"chunk_id": 1, "distance": 0.1, "text": "Test content", "filename": "test.md"}
    ]

    async def fake_stream(messages):
        yield "Hello "
        yield "world"

    mock_stream.return_value = fake_stream(None)

    resp = client.post(
        "/chat",
        json={"message": "What is this?", "history": []},
    )
    assert resp.status_code == 200
    # SSE response should contain tokens
    text = resp.text
    assert "data:" in text
```

Write `backend/tests/test_generation.py`:
```python
from rag.generation import build_prompt


def test_build_prompt_includes_context():
    chunks = [{"filename": "test.md", "text": "Python is a language."}]
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    messages = build_prompt(chunks, "What is Python?", history)

    # System prompt is first
    assert messages[0]["role"] == "system"
    # Context is injected
    assert any("Python is a language" in m["content"] for m in messages)
    # History is included
    assert any(m["content"] == "Hi" for m in messages)
    # User message is last
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What is Python?"


def test_build_prompt_empty_history():
    chunks = [{"filename": "a.md", "text": "Content"}]
    messages = build_prompt(chunks, "Question?", [])
    # Should have system + context + user = 3 messages
    assert len(messages) == 3
    assert messages[-1]["content"] == "Question?"
```

- [ ] **Step 6: Run all tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 7: Create backend .gitignore**

Write `backend/.gitignore`:
```
.env
data/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 8: Commit**

```bash
git add backend/main.py backend/routes/ backend/tests/ backend/.gitignore
git commit -m "feat: add FastAPI app with chat, upload, documents routes and tests"
```

---

### Task 7: Sample documents

**Files:**
- Create: `backend/sample_docs/intro-to-web-dev.md`
- Create: `backend/sample_docs/database-basics.md`

- [ ] **Step 1: Write sample documents**

Write `backend/sample_docs/intro-to-web-dev.md`:
```markdown
# Introduction to Web Development

## What is Web Development?

Web development is the process of building and maintaining websites and web applications. It involves three core technologies that work together to create what users see and interact with in their browsers.

## HTML (HyperText Markup Language)

HTML is the backbone of every web page. It defines the structure and content using elements called tags. Common tags include:

- `<h1>` to `<h6>` for headings
- `<p>` for paragraphs
- `<a>` for links
- `<img>` for images
- `<div>` and `<span>` for grouping elements

HTML documents follow a standard structure with `<!DOCTYPE html>`, `<html>`, `<head>`, and `<body>` tags.

## CSS (Cascading Style Sheets)

CSS controls how HTML elements look on screen. It handles colors, fonts, spacing, layout, and responsive design. Key concepts include:

- **Selectors**: Target elements to style (class, ID, element, attribute)
- **Box Model**: Every element is a box with margin, border, padding, and content
- **Flexbox**: A layout model for arranging items in rows or columns
- **Grid**: A two-dimensional layout system for complex page layouts
- **Media Queries**: Apply different styles based on screen size

## JavaScript

JavaScript adds interactivity to web pages. It can respond to user actions, modify the page content dynamically, and communicate with servers. Core concepts:

- **Variables**: `let`, `const`, and `var` for storing data
- **Functions**: Reusable blocks of code
- **DOM Manipulation**: Changing HTML and CSS through JavaScript
- **Events**: Responding to clicks, key presses, form submissions
- **Async/Await**: Handling operations that take time (API calls, file loading)

## Frontend vs Backend

- **Frontend**: What users see and interact with (HTML, CSS, JavaScript)
- **Backend**: Server-side logic, databases, authentication (Python, Node.js, etc.)
- **Full-stack**: Working with both frontend and backend
```

Write `backend/sample_docs/database-basics.md`:
```markdown
# Database Basics

## What is a Database?

A database is an organized collection of data stored and accessed electronically. Databases are managed by Database Management Systems (DBMS) that allow users to create, read, update, and delete data efficiently.

## Types of Databases

### Relational Databases (SQL)

Store data in tables with rows and columns. Each table has a defined schema. Examples: PostgreSQL, MySQL, SQLite.

### NoSQL Databases

Store data in flexible formats. Types include:
- **Document stores**: MongoDB (JSON-like documents)
- **Key-value stores**: Redis (simple key-value pairs)
- **Graph databases**: Neo4j (relationships between data)

## SQL Fundamentals

SQL (Structured Query Language) is the standard language for working with relational databases.

### Creating Tables

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    enrollment_date DATE DEFAULT CURRENT_DATE
);
```

### Basic Queries

- **SELECT**: Retrieve data — `SELECT name, email FROM students;`
- **INSERT**: Add data — `INSERT INTO students (name, email) VALUES ('Alice', 'alice@edu.com');`
- **UPDATE**: Modify data — `UPDATE students SET email = 'new@edu.com' WHERE id = 1;`
- **DELETE**: Remove data — `DELETE FROM students WHERE id = 1;`

### Filtering and Sorting

- **WHERE**: Filter rows — `SELECT * FROM students WHERE name LIKE 'A%';`
- **ORDER BY**: Sort results — `SELECT * FROM students ORDER BY name ASC;`
- **LIMIT**: Restrict result count — `SELECT * FROM students LIMIT 10;`

### Joins

Combine data from multiple tables:

```sql
SELECT students.name, courses.title
FROM students
JOIN enrollments ON students.id = enrollments.student_id
JOIN courses ON enrollments.course_id = courses.id;
```

## Database Design Principles

- **Primary Keys**: Unique identifier for each row
- **Foreign Keys**: Link between tables, enforce referential integrity
- **Normalization**: Organize data to reduce redundancy
- **Indexes**: Speed up queries on frequently searched columns
```

- [ ] **Step 2: Commit**

```bash
git add backend/sample_docs/
git commit -m "feat: add sample course documents for RAG demo"
```

---

## Chunk 2: Frontend Integration

### Task 8: Chat panel HTML

**Files:**
- Modify: `index.html:185` (after modal div, before mobile controls)

- [ ] **Step 1: Add chat panel HTML to index.html**

Insert after line 185 (after the closing `</div>` of the modal) and before line 187 (`<!-- Mobile controls -->`):

```html
    <!-- Chat Panel (RAG Chatbot) -->
    <div id="chat-panel" class="chat-panel hidden">
      <div class="chat-panel-header">
        <h2 class="chat-panel-title">Course Assistant</h2>
        <button class="chat-panel-close" id="chat-close-btn">exit</button>
      </div>
      <div class="chat-messages" id="chat-messages">
        <div class="chat-bubble bot">
          Hi! I'm your course assistant. Ask me anything about the course materials, or drag and drop documents here to add to my knowledge base.
        </div>
      </div>
      <div class="chat-dropzone hidden" id="chat-dropzone">
        <p>Drop files here to upload</p>
        <p class="chat-dropzone-formats">.pdf, .md, .txt</p>
      </div>
      <div class="chat-input-bar">
        <input
          type="text"
          class="chat-input"
          id="chat-input"
          placeholder="Ask a question..."
          autocomplete="off"
        />
        <button class="chat-send-btn" id="chat-send-btn">Send</button>
      </div>
    </div>
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add chat panel HTML structure"
```

---

### Task 9: Chat panel CSS

**Files:**
- Modify: `style.css` (add after line 196, before mobile controls section)

- [ ] **Step 1: Add chat panel styles to style.css**

Insert after line 196 (after `.modal-project-visit-button:hover` block), before the `/* Mobile controls */` comment:

```css
/* Chat Panel */
.chat-panel {
  z-index: 999;
  position: fixed;
  top: 0;
  right: 0;
  width: 40%;
  height: 100%;
  background-color: var(--default-bg);
  border-left: 4px solid #fff;
  color: #fff;
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out, background 0.4s ease-in;
}

.chat-panel.visible {
  transform: translateX(0);
}

.chat-panel.hidden {
  display: flex;
  transform: translateX(100%);
}

.chat-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 2px solid #fff;
}

.chat-panel-title {
  font-size: 24px;
}

.chat-panel-close {
  background: transparent;
  border: 2px solid #fff;
  color: #fff;
  padding: 4px 14px;
  cursor: pointer;
  font-weight: 600;
  font-family: "Pixelify Sans", sans-serif;
}

.chat-panel-close:hover {
  background: #fff;
  color: var(--default-bg);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-bubble {
  max-width: 85%;
  padding: 10px 14px;
  font-size: 16px;
  line-height: 1.4;
  word-wrap: break-word;
}

.chat-bubble.bot {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.4);
}

.chat-bubble.user {
  align-self: flex-end;
  background: rgba(255, 255, 255, 0.35);
  border: 2px solid #fff;
}

.chat-bubble.error {
  align-self: flex-start;
  background: rgba(200, 50, 50, 0.3);
  border: 2px solid rgba(200, 50, 50, 0.6);
}

.chat-bubble .sources {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.7;
  font-style: italic;
}

.chat-dropzone {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border: 4px dashed #fff;
  font-size: 22px;
}

.chat-dropzone.hidden {
  display: none;
}

.chat-dropzone-formats {
  font-size: 14px;
  opacity: 0.7;
  margin-top: 4px;
}

.chat-input-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 2px solid #fff;
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid #fff;
  background: transparent;
  color: #fff;
  font-size: 16px;
  font-family: "Pixelify Sans", sans-serif;
  outline: none;
}

.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.chat-send-btn {
  padding: 10px 20px;
  border: 2px solid #fff;
  background: #fff;
  color: var(--default-bg);
  font-weight: 600;
  cursor: pointer;
  font-family: "Pixelify Sans", sans-serif;
  font-size: 16px;
}

.chat-send-btn:hover {
  background: transparent;
  color: #fff;
}
```

- [ ] **Step 2: Verify .hidden override works for chat-panel**

The existing `.hidden { display: none; }` utility (line 43-45 of style.css) would conflict with the slide animation. Verify that the `.chat-panel.hidden` rule added in Step 1 has higher specificity and overrides it with `display: flex; transform: translateX(100%)`. Open the browser, inspect the chat panel element, and confirm `display: flex` wins over `display: none`.

- [ ] **Step 3: Add responsive breakpoint for chat panel**

Add inside the existing `@media (max-width: 1100px)` block:
```css
  .chat-panel {
    width: 100%;
  }
```

- [ ] **Step 4: Commit**

```bash
git add style.css
git commit -m "feat: add chat panel CSS with slide-in animation and responsive layout"
```

---

### Task 10: Chat panel JavaScript logic

**Files:**
- Modify: `main.js`

This is the most involved frontend change. It adds the chat panel open/close logic, SSE message streaming, drag-and-drop file upload, and the `isChatOpen` flag to suppress game controls.

- [ ] **Step 1: Add isChatOpen flag and chat DOM references**

In `main.js`, after line 103 (`let isModalOpen = false;`), add:

```javascript
let isChatOpen = false;
```

After line 121 (the `secondIconTwo` const), add:

```javascript
// Chat panel DOM elements
const chatPanel = document.getElementById("chat-panel");
const chatCloseBtn = document.getElementById("chat-close-btn");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send-btn");
const chatDropzone = document.getElementById("chat-dropzone");

const BACKEND_URL = "http://localhost:8081";
let chatHistory = [];
```

- [ ] **Step 2: Add openChatPanel and closeChatPanel functions**

After the `hideModal()` function (after line 179), add:

```javascript
function openChatPanel() {
  chatPanel.classList.remove("hidden");
  // Trigger reflow so the transition plays
  void chatPanel.offsetWidth;
  chatPanel.classList.add("visible");
  isChatOpen = true;
  isModalOpen = true; // Also set this to block raycasting
  chatInput.focus();
}

function closeChatPanel() {
  chatPanel.classList.remove("visible");
  chatPanel.addEventListener(
    "transitionend",
    () => {
      chatPanel.classList.add("hidden");
    },
    { once: true }
  );
  isChatOpen = false;
  isModalOpen = false;
}
```

- [ ] **Step 3: Add chat message helpers**

After the open/close functions, add:

```javascript
function addChatBubble(text, sender) {
  const bubble = document.createElement("div");
  bubble.classList.add("chat-bubble", sender);
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

function addStreamingBubble() {
  const bubble = document.createElement("div");
  bubble.classList.add("chat-bubble", "bot");
  bubble.textContent = "";
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  chatInput.value = "";
  addChatBubble(text, "user");
  chatHistory.push({ role: "user", content: text });

  const bubble = addStreamingBubble();

  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(-10),
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              fullResponse += data.token;
              bubble.textContent = fullResponse;
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            if (data.done && data.sources && data.sources.length > 0) {
              const sourcesEl = document.createElement("div");
              sourcesEl.classList.add("sources");
              sourcesEl.textContent = "Sources: " + data.sources.join(", ");
              bubble.appendChild(sourcesEl);
            }
            if (data.error) {
              bubble.classList.add("error");
              bubble.textContent = "Error: " + data.error;
            }
          } catch (e) {
            // Skip malformed SSE lines
          }
        }
      }
    }

    if (fullResponse) {
      chatHistory.push({ role: "assistant", content: fullResponse });
    }
  } catch (err) {
    bubble.classList.add("error");
    bubble.textContent = "Could not connect to backend. Is the server running?";
  }
}

async function uploadFile(file) {
  const allowed = ["txt", "md", "pdf"];
  const ext = file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(ext)) {
    addChatBubble(`Unsupported file type: .${ext}. Supported: .txt, .md, .pdf`, "error");
    return;
  }

  addChatBubble(`Uploading ${file.name}...`, "bot");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      addChatBubble(`Upload failed: ${err.detail}`, "error");
      return;
    }

    const data = await response.json();
    addChatBubble(
      `${data.filename} uploaded and indexed (${data.chunks} chunks). You can now ask questions about it!`,
      "bot"
    );
  } catch (err) {
    addChatBubble("Upload failed. Is the backend running?", "error");
  }
}
```

- [ ] **Step 4: Modify handleInteraction to branch on Project_1**

Replace lines 525-531 in `main.js` (the else branch for non-Pokemon objects):

**Old code:**
```javascript
    } else {
      if (intersectObject) {
        showModal(intersectObject);
        if (!isMuted) {
          playSound("projectsSFX");
        }
      }
    }
```

**New code:**
```javascript
    } else {
      if (intersectObject) {
        if (intersectObject === "Project_1") {
          openChatPanel();
        } else {
          showModal(intersectObject);
        }
        if (!isMuted) {
          playSound("projectsSFX");
        }
      }
    }
```

- [ ] **Step 5: Guard keyboard handlers with isChatOpen**

In `onKeyDown` (line 613), add at the very top of the function:
```javascript
  if (isChatOpen) return;
```

In `onKeyUp` (line 651), add at the very top of the function:
```javascript
  if (isChatOpen) return;
```

Also in `handleInteraction` (line 493), add a chat panel check alongside the modal check:
```javascript
  if (!modal.classList.contains("hidden") || isChatOpen) {
    return;
  }
```

- [ ] **Step 6: Add chat panel event listeners**

After line 862 (`audioToggleButton.addEventListener("click", toggleAudio);`), add:

```javascript
// Chat panel event listeners
chatCloseBtn.addEventListener("click", closeChatPanel);
chatSendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Escape key closes chat panel
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && isChatOpen) {
    closeChatPanel();
  }
});

// Drag and drop
chatPanel.addEventListener("dragover", (e) => {
  e.preventDefault();
  chatDropzone.classList.remove("hidden");
});

chatPanel.addEventListener("dragleave", (e) => {
  if (!chatPanel.contains(e.relatedTarget)) {
    chatDropzone.classList.add("hidden");
  }
});

chatDropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  chatDropzone.classList.add("hidden");
  const files = e.dataTransfer.files;
  for (const file of files) {
    uploadFile(file);
  }
});

chatDropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
});
```

- [ ] **Step 7: Test manually**

Start both servers:
```bash
# Terminal 1: Frontend
python start_server.py

# Terminal 2: Backend (needs .env with OPENROUTER_API_KEY)
cd backend && cp .env.example .env
# Edit .env to add your API key
uvicorn main:app --port 8081 --reload
```

Test:
1. Navigate to `http://localhost:8080`
2. Walk to Project_1 board, click it → chat panel should slide in
3. Type a message → should stream a response
4. Drag a .txt file onto the panel → should upload and confirm
5. Press Escape → panel should slide out
6. Verify other project boards still show the normal modal

- [ ] **Step 8: Commit**

```bash
git add main.js
git commit -m "feat: add chat panel JS with SSE streaming, drag-drop upload, and game control guard"
```

---

### Task 11: Update launch.json for dual-server development

**Files:**
- Modify: `.claude/launch.json`

- [ ] **Step 1: Add backend server to launch.json**

Update `.claude/launch.json` to include the backend:
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "eduOasis-frontend",
      "runtimeExecutable": "python",
      "runtimeArgs": ["start_server.py"],
      "port": 8080
    },
    {
      "name": "eduOasis-backend",
      "runtimeExecutable": "uvicorn",
      "runtimeArgs": ["main:app", "--port", "8081", "--reload"],
      "cwd": "backend",
      "port": 8081
    }
  ],
  "autoVerify": false
}
```

- [ ] **Step 2: Commit**

```bash
git add .claude/launch.json
git commit -m "feat: add backend server to launch.json"
```

---

### Task 12: Final integration commit

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 2: Verify the full flow manually**

Run both servers and test the complete flow:
1. Click Project_1 → chat panel opens
2. Send a message → streamed response appears
3. Drag-drop a document → uploads and indexes
4. Ask about the uploaded document → relevant answer
5. Click Project_2/Project_3 → normal modals still work
6. Press Escape → chat panel closes
7. WASD/arrow keys work after closing panel
8. Theme toggle affects chat panel colors

- [ ] **Step 3: Final commit**

```bash
git add index.html style.css main.js .claude/launch.json backend/
git commit -m "feat: complete RAG chatbot integration with Edu Oasis"
```
